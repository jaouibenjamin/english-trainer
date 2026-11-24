-- Sign-in bookkeeping for the Edge Functions (docs/BACKEND.md sections 3 and 4). Server role only.
-- The functions hold the pepper and do the slow hashing; everything that must be atomic (limits, locks, comparing,
-- changing a code) happens here, under one lock per class and name. Binary values travel as hex text.
-- Every function takes the time as a parameter, so a day of guessing can be simulated in tests.

alter table private.settings
  add column kdf_iter int not null default 600000 check (kdf_iter >= 100000),
  add column ip_hour  int not null default 120;            -- any calls from one address in an hour
create index auth_attempts_ip_at on private.auth_attempts (ip_bucket, at);

create function private.name_lock(p_class uuid, p_key text) returns void language sql set search_path = '' as
  $$ select pg_advisory_xact_lock(hashtextextended(p_class::text || '/' || p_key, 42)) $$;

create function private.lock_event(p_class uuid, p_key text, p_kind text, p_now timestamptz, p_until timestamptz) returns void
language sql security definer set search_path = '' as
  $$ insert into private.auth_lock_events (class_id, name_key, kind, at, until) values (p_class, p_key, p_kind, p_now, p_until) $$;

-- today's random salt for hashing addresses; the caller offers a fresh one, the first offer of a day wins
create function private.ip_salt(p_day date, p_new text) returns text
language plpgsql security definer set search_path = '' as $$
declare v bytea;
begin
  insert into private.ip_salts (day, salt) values (p_day, decode(p_new, 'hex')) on conflict do nothing;
  select salt into v from private.ip_salts where day = p_day;
  return encode(v, 'hex');
end $$;

-- one more wrong code in a device or address bucket; returns the end of the lock if this one started a lock
create function private.bucket_fail(p_class uuid, p_key text, p_bucket text, p_now timestamptz) returns timestamptz
language plpgsql security definer set search_path = '' as $$
declare b private.auth_buckets; s private.settings; v_until timestamptz;
begin
  select * into s from private.settings;
  insert into private.auth_buckets (class_id, name_key, kind, bucket) values (p_class, p_key, 'code', p_bucket) on conflict do nothing;
  select * into b from private.auth_buckets where class_id = p_class and name_key = p_key and kind = 'code' and bucket = p_bucket for update;
  if b.last_fail_at is not null and b.last_fail_at < p_now - interval '24 hours' then b.fails := 0; b.round := 0; end if;
  b.fails := b.fails + 1;
  if b.fails >= s.code_round then
    b.round := b.round + 1; b.fails := 0;
    v_until := p_now + make_interval(mins => s.code_locks_min[least(b.round, array_length(s.code_locks_min, 1))]);
  end if;
  update private.auth_buckets set fails = b.fails, round = b.round, last_fail_at = p_now, locked_until = coalesce(v_until, locked_until)
   where class_id = p_class and name_key = p_key and kind = 'code' and bucket = p_bucket;
  return v_until;
end $$;

-- the picture bucket of a name ran out of tries: 24 hours the first time, closed until the teacher resets after that
create function private.picture_lock(p_class uuid, p_key text, p_now timestamptz) returns timestamptz
language plpgsql security definer set search_path = '' as $$
declare s private.settings; v_until timestamptz; v_round int;
begin
  select * into s from private.settings;
  select round + 1 into v_round from private.auth_buckets where class_id = p_class and name_key = p_key and kind = 'picture' and bucket = '*';
  v_until := case when v_round <= 1 then p_now + make_interval(hours => s.pic_lock_hours) else 'infinity' end;
  update private.auth_buckets set round = v_round, fails = 0, locked_until = v_until
   where class_id = p_class and name_key = p_key and kind = 'picture' and bucket = '*';
  perform private.lock_event(p_class, p_key, 'picture', p_now, v_until);
  return v_until;
end $$;

create function private.wait_s(p_until timestamptz, p_now timestamptz) returns int language sql immutable set search_path = '' as
  $$ select case when p_until = 'infinity' then -1 else greatest(1, ceil(extract(epoch from p_until - p_now)))::int end $$;

/* Step 1 of every sign-in, recovery or registration. Checks the address limits, finds the class, checks the limits of
   the name and RESERVES the try (it counts as wrong until auth_finish says otherwise), so parallel guesses cannot
   outrun the limits. A name that does not exist goes through exactly the same steps.
   p_kind: code | picture | otc | register.  p_dev, p_ip: hex bucket ids made by the function.
   Returns {s: 'go', attempt, pupil, algo, salt, iter, legacy_salt, iter_default, class}
        or {s: 'locked', wait}  (wait in seconds, -1 = until the teacher resets)
        or {s: 'class'}         (no class with this code) */
create function private.auth_begin(p_kind text, p_class_lookup text, p_name text, p_dev text, p_ip text, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  s private.settings; v_class uuid; v_key text := app.name_key(p_name);
  v_pupil uuid; sec private.pupil_secrets; b private.auth_buckets; rc private.reset_codes;
  v_trusted boolean := false; v_until timestamptz; v_attempt bigint; v_oldest timestamptz;
  n_all int; n_untrusted int; n_dev int; n_ip int;
  v_salt bytea; v_iter int; v_algo text := 'v1'; v_legacy text;
begin
  if p_kind not in ('code', 'picture', 'otc', 'register') then raise exception 'bad kind'; end if;
  select * into s from private.settings;

  -- the address: any calls, then wrong class codes
  select count(*), min(at) into n_ip, v_oldest from private.auth_attempts where ip_bucket = p_ip and at > p_now - interval '1 hour';
  if n_ip >= s.ip_hour then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now)); end if;
  select count(*), min(at) into n_ip, v_oldest from private.auth_attempts
   where ip_bucket = p_ip and kind = 'class' and at > p_now - interval '1 hour';
  if n_ip >= s.class_ip_hour then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now)); end if;

  select class_id into v_class from private.class_codes where code_lookup = decode(p_class_lookup, 'hex');
  if v_class is null then
    insert into private.auth_attempts (at, kind, dev_bucket, ip_bucket, outcome) values (p_now, 'class', p_dev, p_ip, 'wrong');
    return jsonb_build_object('s', 'class');
  end if;

  if p_kind = 'register' then
    select count(*), min(at) into n_ip, v_oldest from private.auth_attempts
     where ip_bucket = p_ip and kind = 'register' and at > p_now - interval '1 hour';
    if n_ip >= s.register_ip_hour then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now)); end if;
    insert into private.auth_attempts (at, class_id, name_key, kind, dev_bucket, ip_bucket, outcome)
      values (p_now, v_class, v_key, 'register', p_dev, p_ip, 'ok');
    return jsonb_build_object('s', 'go', 'class', v_class, 'iter_default', s.kdf_iter);
  end if;

  perform private.name_lock(v_class, v_key);
  select id into v_pupil from public.pupils where class_id = v_class and name_key = v_key;
  select * into sec from private.pupil_secrets where pupil_id = v_pupil;

  if p_kind = 'code' then
    v_trusted := v_pupil is not null and exists (select 1 from private.pupil_devices where pupil_id = v_pupil and device_hash = decode(p_dev, 'hex'));
    -- a device that signed in correctly as this pupil is judged by its own bucket only, not by the address it shares
    select max(locked_until) into v_until from private.auth_buckets
     where class_id = v_class and name_key = v_key and kind = 'code' and locked_until > p_now
       and (bucket = 'd:' || p_dev or (not v_trusted and bucket = 'i:' || p_ip));
    if v_until is not null then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_until, p_now)); end if;
    select count(*), count(*) filter (where not trusted), count(*) filter (where dev_bucket = p_dev),
           count(*) filter (where ip_bucket = p_ip and not trusted), min(at)
      into n_all, n_untrusted, n_dev, n_ip, v_oldest
      from private.auth_attempts
     where class_id = v_class and name_key = v_key and kind = 'code' and outcome <> 'ok' and at > p_now - interval '24 hours';
    if n_all >= s.code_ceiling_day or (not v_trusted and n_untrusted >= s.code_name_day)
       or n_dev >= s.code_bucket_day or (not v_trusted and n_ip >= s.code_bucket_day) then
      return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + interval '24 hours', p_now));
    end if;
    if sec.code_hash is not null then
      v_salt := sec.code_salt; v_iter := sec.code_iter; v_algo := sec.code_algo; v_legacy := sec.legacy_salt;
    end if;

  elsif p_kind = 'picture' then
    insert into private.auth_buckets (class_id, name_key, kind, bucket) values (v_class, v_key, 'picture', '*') on conflict do nothing;
    select * into b from private.auth_buckets where class_id = v_class and name_key = v_key and kind = 'picture' and bucket = '*' for update;
    if b.locked_until > p_now then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(b.locked_until, p_now)); end if;
    if b.fails >= s.pic_round then      -- all tries of the round are taken by calls that never finished
      return jsonb_build_object('s', 'locked', 'wait', private.wait_s(private.picture_lock(v_class, v_key, p_now), p_now));
    end if;
    update private.auth_buckets set fails = fails + 1, last_fail_at = p_now
     where class_id = v_class and name_key = v_key and kind = 'picture' and bucket = '*';
    if sec.pic_hash is not null then v_salt := sec.pic_salt; v_iter := sec.pic_iter; end if;

  else  -- otc
    select * into rc from private.reset_codes where pupil_id = v_pupil for update;
    if rc.pupil_id is not null and (rc.expires_at <= p_now or rc.fails >= s.otc_tries) then
      delete from private.reset_codes where pupil_id = v_pupil; rc := null;
    end if;
    if rc.pupil_id is not null then
      update private.reset_codes set fails = fails + 1 where pupil_id = v_pupil;
      v_salt := rc.salt; v_iter := rc.iter;
    end if;
  end if;

  insert into private.auth_attempts (at, class_id, name_key, kind, dev_bucket, ip_bucket, trusted)
    values (p_now, v_class, v_key, p_kind, p_dev, p_ip, v_trusted) returning id into v_attempt;
  -- without a stored secret the caller still gets "go" and hashes against a throw-away salt: same work, same answer
  return jsonb_build_object('s', 'go', 'attempt', v_attempt, 'class', v_class,
    'pupil', case when v_salt is not null then v_pupil end,
    'algo', v_algo, 'salt', encode(v_salt, 'hex'), 'iter', v_iter, 'legacy_salt', v_legacy, 'iter_default', s.kdf_iter);
end $$;

-- a new code for a pupil. p_revoke: also forget known devices and cut the link to the auth user, which ends every
-- open session at once (the policies find no pupil for the old user). Returns the old auth user to delete.
create function private.set_code(p_pupil uuid, p_salt text, p_hash text, p_iter int, p_revoke boolean, p_now timestamptz) returns uuid
language plpgsql security definer set search_path = '' as $$
declare v_old uuid;
begin
  insert into private.pupil_secrets (pupil_id) values (p_pupil) on conflict do nothing;
  update private.pupil_secrets set code_algo = 'v1', code_salt = decode(p_salt, 'hex'), code_hash = decode(p_hash, 'hex'),
         code_iter = p_iter, legacy_salt = null, code_set_at = p_now where pupil_id = p_pupil;
  if p_revoke then
    delete from private.pupil_devices where pupil_id = p_pupil;
    select auth_user_id into v_old from public.pupils where id = p_pupil;
    update public.pupils set auth_user_id = null where id = p_pupil;
  end if;
  return v_old;
end $$;

create function private.set_picture(p_pupil uuid, p_salt text, p_hash text, p_iter int, p_only_if_missing boolean) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  insert into private.pupil_secrets (pupil_id) values (p_pupil) on conflict do nothing;
  update private.pupil_secrets set pic_salt = decode(p_salt, 'hex'), pic_hash = decode(p_hash, 'hex'), pic_iter = p_iter
   where pupil_id = p_pupil and (not p_only_if_missing or pic_hash is null);
  return found;
end $$;

/* Step 2. p_hash: what the function computed from what was typed. Compares, books the result, starts locks.
   For picture and otc, p_new carries the new code (and, with otc, the new picture) already hashed:
   {code_salt, code_hash, pic_salt, pic_hash, iter}; it is applied in the same transaction as the proof.
   Returns {ok, pupil, auth_user, old_auth_user, name, needs_picture, legacy, wait}. */
create function private.auth_finish(p_attempt bigint, p_hash text, p_new jsonb, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  s private.settings; a private.auth_attempts; p public.pupils; sec private.pupil_secrets; rc private.reset_codes;
  b private.auth_buckets; v_hash bytea; v_ok boolean := false; v_until timestamptz; v_u2 timestamptz; v_old uuid;
  n_all int; n_untrusted int;
begin
  select * into s from private.settings;
  begin v_hash := decode(p_hash, 'hex'); exception when others then v_hash := null; end;
  select * into a from private.auth_attempts where id = p_attempt for update;
  if a.id is null or a.outcome <> 'pending' or a.kind not in ('code', 'picture', 'otc') or a.at < p_now - interval '2 minutes' then
    return jsonb_build_object('ok', false);
  end if;
  perform private.name_lock(a.class_id, a.name_key);
  select * into p from public.pupils where class_id = a.class_id and name_key = a.name_key;
  select * into sec from private.pupil_secrets where pupil_id = p.id;

  if a.kind = 'code' then
    v_ok := coalesce(sec.code_hash = v_hash, false);
    if v_ok then
      update private.auth_attempts set outcome = 'ok' where id = a.id;
      delete from private.auth_buckets where class_id = a.class_id and name_key = a.name_key and kind = 'code'
         and bucket in ('d:' || a.dev_bucket, 'i:' || a.ip_bucket);
      insert into private.pupil_devices (pupil_id, device_hash, last_ok_at) values (p.id, decode(a.dev_bucket, 'hex'), p_now)
        on conflict (pupil_id, device_hash) do update set last_ok_at = excluded.last_ok_at;
      return jsonb_build_object('ok', true, 'pupil', p.id, 'auth_user', p.auth_user_id, 'name', p.display_name,
                                'needs_picture', sec.pic_hash is null, 'legacy', sec.code_algo <> 'v1');
    end if;
    update private.auth_attempts set outcome = 'wrong' where id = a.id;
    v_until := private.bucket_fail(a.class_id, a.name_key, 'd:' || a.dev_bucket, p_now);
    if not a.trusted then v_u2 := private.bucket_fail(a.class_id, a.name_key, 'i:' || a.ip_bucket, p_now); end if;
    v_until := greatest(v_until, v_u2);
    select count(*), count(*) filter (where not trusted) into n_all, n_untrusted from private.auth_attempts
     where class_id = a.class_id and name_key = a.name_key and kind = 'code' and outcome <> 'ok' and at > p_now - interval '24 hours';
    if n_all = s.code_ceiling_day or (not a.trusted and n_untrusted = s.code_name_day) then
      v_until := greatest(v_until, p_now + interval '1 minute');      -- the name is closed for the day: the teacher sees it
      perform private.lock_event(a.class_id, a.name_key, 'name', p_now, null);
    elsif v_until is not null then
      perform private.lock_event(a.class_id, a.name_key, 'code', p_now, v_until);
    end if;
    return jsonb_build_object('ok', false);

  elsif a.kind = 'picture' then
    v_ok := coalesce(sec.pic_hash = v_hash, false);
    if not v_ok then
      update private.auth_attempts set outcome = 'wrong' where id = a.id;
      select * into b from private.auth_buckets where class_id = a.class_id and name_key = a.name_key and kind = 'picture' and bucket = '*' for update;
      if b.fails >= s.pic_round and coalesce(b.locked_until, '-infinity') <= p_now then
        v_until := private.picture_lock(a.class_id, a.name_key, p_now);
        return jsonb_build_object('ok', false, 'wait', private.wait_s(v_until, p_now));
      end if;
      return jsonb_build_object('ok', false);
    end if;

  else  -- otc
    select * into rc from private.reset_codes where pupil_id = p.id for update;
    v_ok := coalesce(rc.hash = v_hash and rc.expires_at > p_now, false);
    if not v_ok then
      update private.auth_attempts set outcome = 'wrong' where id = a.id;
      if rc.pupil_id is not null and rc.fails >= s.otc_tries then
        delete from private.reset_codes where pupil_id = p.id;
        perform private.lock_event(a.class_id, a.name_key, 'otc', p_now, null);
      end if;
      return jsonb_build_object('ok', false);
    end if;
  end if;

  -- picture or one-time code proved: the new code takes effect now, every other device is signed out
  if p_new is null or (p_new ->> 'code_hash') is null or (a.kind = 'otc' and (p_new ->> 'pic_hash') is null) then
    raise exception 'recovery without a new code';
  end if;
  update private.auth_attempts set outcome = 'ok' where id = a.id;
  v_old := private.set_code(p.id, p_new ->> 'code_salt', p_new ->> 'code_hash', (p_new ->> 'iter')::int, true, p_now);
  if a.kind = 'otc' then
    perform private.set_picture(p.id, p_new ->> 'pic_salt', p_new ->> 'pic_hash', (p_new ->> 'iter')::int, false);
    delete from private.reset_codes where pupil_id = p.id;
  end if;
  delete from private.auth_buckets where class_id = a.class_id and name_key = a.name_key and kind in ('code', 'picture');
  insert into private.pupil_devices (pupil_id, device_hash, last_ok_at) values (p.id, decode(a.dev_bucket, 'hex'), p_now) on conflict do nothing;
  return jsonb_build_object('ok', true, 'pupil', p.id, 'auth_user', null, 'old_auth_user', v_old, 'name', p.display_name, 'needs_picture', false);
end $$;

/* A new pupil. The class list, the size of the class and the free name are checked here, under the name lock.
   Returns {s: 'ok' | 'taken' | 'roster' | 'full'}. */
create function private.register_pupil(p_id uuid, p_class uuid, p_name text, p_code_salt text, p_code_hash text,
                                       p_pic_salt text, p_pic_hash text, p_iter int, p_dev text, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare c public.classes; v_key text := app.name_key(p_name); v_name text := regexp_replace(btrim(p_name), '\s+', ' ', 'g');
begin
  select * into c from public.classes where id = p_class;
  if c.id is null then raise exception 'no class'; end if;
  perform private.name_lock(p_class, v_key);
  if exists (select 1 from public.pupils where class_id = p_class and name_key = v_key) then return jsonb_build_object('s', 'taken'); end if;
  if c.roster_only and not exists (select 1 from public.roster where class_id = p_class and name_key = v_key) then
    return jsonb_build_object('s', 'roster');
  end if;
  perform pg_advisory_xact_lock(hashtextextended(p_class::text, 43));       -- the head count
  if (select count(*) from public.pupils where class_id = p_class) >= c.max_pupils then return jsonb_build_object('s', 'full'); end if;
  insert into public.pupils (id, class_id, display_name, created_at) values (p_id, p_class, v_name, p_now);
  insert into private.pupil_secrets (pupil_id, code_algo, code_salt, code_hash, code_iter, code_set_at, pic_salt, pic_hash, pic_iter)
    values (p_id, 'v1', decode(p_code_salt, 'hex'), decode(p_code_hash, 'hex'), p_iter, p_now, decode(p_pic_salt, 'hex'), decode(p_pic_hash, 'hex'), p_iter);
  insert into private.pupil_devices (pupil_id, device_hash, last_ok_at) values (p_id, decode(p_dev, 'hex'), p_now);
  return jsonb_build_object('s', 'ok', 'name', v_name);
end $$;

-- the pupil's auth user, created by the function when missing. Returns the one that is linked (a parallel sign-in may have won).
create function private.link_auth_user(p_pupil uuid, p_user uuid) returns uuid
language plpgsql security definer set search_path = '' as $$
declare v uuid;
begin
  update public.pupils set auth_user_id = p_user where id = p_pupil and auth_user_id is null;
  select auth_user_id into v from public.pupils where id = p_pupil;
  return v;
end $$;

create function private.pupil_state(p_pupil uuid) returns jsonb language sql security definer set search_path = '' as
  $$ select coalesce((select state from public.progress where pupil_id = p_pupil), '{}'::jsonb) $$;

create function private.pupil_of_user(p_user uuid) returns jsonb language sql security definer set search_path = '' as
  $$ select jsonb_build_object('pupil', p.id, 'has_picture', coalesce(s.pic_hash is not null, false))
       from public.pupils p left join private.pupil_secrets s on s.pupil_id = p.id where p.auth_user_id = p_user $$;

/* The teacher resets a pupil of her own class (checked here again, not only in the function): the code stops working,
   every device is signed out, locks are cleared, recovery is reopened, and a one-time code (already hashed) is stored.
   Returns {ok, old_auth_user, expires_at} or {ok: false}. */
create function private.teacher_reset(p_teacher uuid, p_pupil uuid, p_salt text, p_hash text, p_iter int, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; p public.pupils; v_exp timestamptz;
begin
  select * into s from private.settings;
  select pu.* into p from public.pupils pu join public.teachers t on t.class_id = pu.class_id
   where pu.id = p_pupil and t.user_id = p_teacher;
  if p.id is null then return jsonb_build_object('ok', false); end if;
  perform private.name_lock(p.class_id, p.name_key);
  v_exp := p_now + make_interval(hours => s.otc_hours);
  insert into private.pupil_secrets (pupil_id) values (p.id) on conflict do nothing;
  update private.pupil_secrets set code_algo = 'v1', code_salt = null, code_hash = null, legacy_salt = null, code_set_at = null where pupil_id = p.id;
  delete from private.pupil_devices where pupil_id = p.id;
  delete from private.auth_buckets  where class_id = p.class_id and name_key = p.name_key;
  delete from private.auth_attempts where class_id = p.class_id and name_key = p.name_key and kind in ('code', 'picture', 'otc');
  insert into private.reset_codes (pupil_id, salt, hash, iter, expires_at, fails, created_by, created_at)
    values (p.id, decode(p_salt, 'hex'), decode(p_hash, 'hex'), p_iter, v_exp, 0, p_teacher, p_now)
  on conflict (pupil_id) do update set salt = excluded.salt, hash = excluded.hash, iter = excluded.iter,
     expires_at = excluded.expires_at, fails = 0, created_by = excluded.created_by, created_at = excluded.created_at;
  update public.pupils set auth_user_id = null where id = p.id;
  return jsonb_build_object('ok', true, 'old_auth_user', p.auth_user_id, 'expires_at', v_exp, 'name', p.display_name);
end $$;

revoke all on all functions in schema private from public, anon, authenticated;
grant execute on all functions in schema private to service_role;
