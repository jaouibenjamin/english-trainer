-- Sign-in bookkeeping for the Edge Functions (docs/BACKEND.md sections 3 and 4). Server role only.
-- The functions hold the pepper and do the slow hashing; everything that must be atomic (limits, locks, comparing,
-- changing a code) happens here, under one lock per class and name. Binary values travel as hex text.
-- Every function takes the time as a parameter, so a day of guessing can be simulated in tests.

alter table private.settings
  add column kdf_iter int not null default 600000 check (kdf_iter >= 100000),
  add column ip_hour  int not null default 120,            -- any calls from one address in an hour
  -- Phase 2 only (docs/BACKEND.md section 8): a right Sheet-era code opens a session without a new code or pictures,
  -- so the dual-write copy has something to write with. Off by default; private.shadow_set() switches it.
  add column shadow_mode boolean not null default false;
create index auth_attempts_ip_at on private.auth_attempts (ip_bucket, at);
create index auth_attempts_class on private.auth_attempts (class_id, kind, at);
create index pupil_devices_hash on private.pupil_devices (device_hash);

-- ---------------------------------------------------------------- the auth user stays as we made it
-- A pupil's session can call the Auth API directly. Whatever the project settings say, a pupil's auth user
-- (label p-...@pupils.invalid) never gets a password, a phone, another email or a second factor: we only ever
-- create and delete these users. Supabase lets the owner add triggers on auth.users; if a platform refuses one,
-- the migration goes on and says so (docs/BACKEND.md section 10, item 4), and the check at sign-in still holds.
create function private.pupil_user_frozen() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if old.email like 'p-%@pupils.invalid' and (new.email is distinct from old.email
       or coalesce(new.encrypted_password, '') <> '' or coalesce(new.phone, '') <> '') then
    raise exception 'this account cannot be changed' using errcode = '42501';
  end if;
  return new;
end $$;
create function private.pupil_user_no_factor() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if exists (select 1 from auth.users u where u.id = new.user_id and u.email like 'p-%@pupils.invalid') then
    raise exception 'this account cannot be changed' using errcode = '42501';
  end if;
  return new;
end $$;
do $$ begin
  create trigger pupil_user_frozen before update on auth.users for each row execute function private.pupil_user_frozen();
exception when others then raise notice 'trigger on auth.users not created: %', sqlerrm; end $$;
do $$ begin
  create trigger pupil_user_no_factor before insert on auth.mfa_factors for each row execute function private.pupil_user_no_factor();
exception when others then raise notice 'trigger on auth.mfa_factors not created: %', sqlerrm; end $$;

-- is this still the auth user we created: our label, no password, no phone
create function private.auth_user_clean(p_user uuid) returns boolean language plpgsql security definer set search_path = '' as $$
declare ok boolean;
begin
  select email like 'p-%@pupils.invalid' and coalesce(encrypted_password, '') = '' and coalesce(phone, '') = '' into ok from auth.users where id = p_user;
  return coalesce(ok, false);
end $$;

-- ---------------------------------------------------------------- helpers
create function private.name_lock(p_class uuid, p_key text) returns void language sql set search_path = '' as
  $$ select pg_advisory_xact_lock(hashtextextended(p_class::text || '/' || p_key, 42)) $$;

create function private.lock_event(p_class uuid, p_key text, p_kind text, p_now timestamptz, p_until timestamptz) returns void
language sql security definer set search_path = '' as
  $$ insert into private.auth_lock_events (class_id, name_key, kind, at, until) values (p_class, p_key, p_kind, p_now, p_until) $$;

create function private.wait_s(p_until timestamptz, p_now timestamptz) returns int language sql immutable set search_path = '' as
  $$ select case when p_until = 'infinity' then -1 else greatest(1, ceil(extract(epoch from p_until - p_now)))::int end $$;

-- today's random salt for hashing addresses; the caller offers a fresh one, the first offer of a day wins
create function private.ip_salt(p_day date, p_new text) returns text
language plpgsql security definer set search_path = '' as $$
declare v bytea;
begin
  insert into private.ip_salts (day, salt) values (p_day, decode(p_new, 'hex')) on conflict do nothing;
  select salt into v from private.ip_salts where day = p_day;
  return encode(v, 'hex');
end $$;

-- one more wrong code in a bucket (a known device, or an address for strangers); returns the end of a lock it started
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

/* Step 1 of every sign-in, recovery or registration. Checks the limits of the address, the class and the name and
   RESERVES the try (it counts as wrong until auth_finish says otherwise), so parallel guesses cannot outrun a limit.
   A name that does not exist goes through exactly the same steps.
   p_kind: code | picture | otc | register.  p_dev: hex HMAC of the device token the server once issued, or ''.
   p_ip: hex bucket of the address under today's salt; p_ip_prev: the same address under yesterday's salt, so the
   per-address limits do not start again when the salt changes at midnight. Returns
     {s: 'go', attempt, class, pupil, algo, salt, iter, legacy_salt, iter_default, pic_count, pic_choices}
     {s: 'locked', wait}   wait in seconds, -1 = ask the teacher
     {s: 'class'}          no class with this code */
create function private.auth_begin(p_kind text, p_class_lookup text, p_name text, p_dev text, p_ip text, p_ip_prev text, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  s private.settings; v_class uuid; v_key text := app.name_key(p_name);
  v_pupil uuid; sec private.pupil_secrets; b private.auth_buckets; rc private.reset_codes;
  v_known boolean := false; v_until timestamptz; v_attempt bigint; v_oldest timestamptz; v_old2 timestamptz;
  n_all int; n_str int; n_dev int; n_ip int; n_ipc int; n_cls int;
  v_salt bytea; v_iter int; v_algo text := 'v1'; v_legacy text;
  day constant interval := interval '24 hours';
begin
  if p_kind not in ('code', 'picture', 'otc', 'register') then raise exception 'bad kind'; end if;
  select * into s from private.settings;

  -- the address: any calls, then wrong class codes
  select count(*), min(at) into n_ip, v_oldest from private.auth_attempts where ip_bucket in (p_ip, p_ip_prev) and at > p_now - interval '1 hour';
  if n_ip >= s.ip_hour then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now)); end if;
  select count(*), min(at) into n_ip, v_oldest from private.auth_attempts
   where ip_bucket in (p_ip, p_ip_prev) and kind = 'class' and at > p_now - interval '1 hour';
  if n_ip >= s.class_ip_hour then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now)); end if;

  select class_id into v_class from private.class_codes where code_lookup = decode(p_class_lookup, 'hex');
  if v_class is null then
    insert into private.auth_attempts (at, kind, dev_bucket, ip_bucket, outcome) values (p_now, 'class', p_dev, p_ip, 'wrong');
    return jsonb_build_object('s', 'class');
  end if;

  -- while the copy phase runs, this side only receives copies: no registration, no recovery
  if s.shadow_mode and p_kind <> 'code' then return jsonb_build_object('s', 'locked', 'wait', -1); end if;

  if p_kind = 'register' then
    select count(*), min(at) into n_ip, v_oldest from private.auth_attempts
     where ip_bucket in (p_ip, p_ip_prev) and kind = 'register' and at > p_now - interval '1 hour';
    if n_ip >= s.register_ip_hour then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now)); end if;
    insert into private.auth_attempts (at, class_id, name_key, kind, dev_bucket, ip_bucket, outcome)
      values (p_now, v_class, v_key, 'register', p_dev, p_ip, 'ok');
    return jsonb_build_object('s', 'go', 'class', v_class, 'iter_default', s.kdf_iter, 'pic_count', s.pic_count, 'pic_choices', s.pic_choices);
  end if;

  perform private.name_lock(v_class, v_key);
  select id into v_pupil from public.pupils where class_id = v_class and name_key = v_key;
  select * into sec from private.pupil_secrets where pupil_id = v_pupil;

  if p_kind = 'code' then
    -- known: this device signed in correctly as this pupil lately, and as nobody else (a shared computer is a stranger)
    v_known := v_pupil is not null and p_dev <> '' and exists (
        select 1 from private.pupil_devices d where d.pupil_id = v_pupil and d.device_hash = decode(p_dev, 'hex')
           and d.last_ok_at > p_now - make_interval(days => s.device_days))
      and not exists (select 1 from private.pupil_devices d where d.device_hash = decode(p_dev, 'hex') and d.pupil_id <> v_pupil);
    select max(locked_until) into v_until from private.auth_buckets
     where class_id = v_class and name_key = v_key and kind = 'code' and locked_until > p_now
       and (case when v_known then bucket = 'd:' || p_dev else bucket in ('i:' || p_ip, 'i:' || p_ip_prev) end);
    if v_until is not null then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_until, p_now)); end if;
    -- wrong (or unfinished) codes of the last 24 hours: this name; this address on this name; this device
    select count(*), count(*) filter (where not trusted), count(*) filter (where trusted and dev_bucket = p_dev),
           count(*) filter (where not trusted and ip_bucket in (p_ip, p_ip_prev)), min(at)
      into n_all, n_str, n_dev, n_ip, v_oldest
      from private.auth_attempts
     where class_id = v_class and name_key = v_key and kind = 'code' and outcome <> 'ok' and at > p_now - day;
    if n_all >= s.code_ceiling_day or (v_known and n_dev >= s.code_bucket_day)
       or (not v_known and (n_str >= s.code_name_day or n_ip >= s.code_bucket_day)) then
      return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + day, p_now));
    end if;
    if not v_known then
      -- strangers, across the names of the class: one address, and everybody together (the class brake)
      select count(*) filter (where ip_bucket in (p_ip, p_ip_prev)), count(*), min(at) filter (where ip_bucket in (p_ip, p_ip_prev)), min(at)
        into n_ipc, n_cls, v_oldest, v_old2
        from private.auth_attempts where class_id = v_class and kind = 'code' and outcome <> 'ok' and not trusted and at > p_now - day;
      if n_ipc >= s.code_ip_class_day then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + day, p_now)); end if;
      if n_cls >= s.code_class_brake then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_old2 + day, p_now)); end if;
    end if;
    if sec.code_hash is not null then
      v_salt := sec.code_salt; v_iter := sec.code_iter; v_algo := sec.code_algo; v_legacy := sec.legacy_salt;
    end if;

  elsif p_kind = 'picture' then
    -- per address and per class first (they hold for names that do not exist too)
    select count(*) filter (where ip_bucket in (p_ip, p_ip_prev)), count(*), min(at) filter (where ip_bucket in (p_ip, p_ip_prev)), min(at)
      into n_ipc, n_cls, v_oldest, v_old2
      from private.auth_attempts where class_id = v_class and kind = 'picture' and outcome <> 'ok' and at > p_now - day;
    if n_ipc >= s.pic_ip_day then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + day, p_now)); end if;
    if n_cls >= s.pic_class_day then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_old2 + day, p_now)); end if;
    insert into private.auth_buckets (class_id, name_key, kind, bucket) values (v_class, v_key, 'picture', '*') on conflict do nothing;
    select * into b from private.auth_buckets where class_id = v_class and name_key = v_key and kind = 'picture' and bucket = '*' for update;
    -- closed after the tries are used; closed while a teacher reset waits; once in 30 days
    if b.locked_until > p_now or b.fails >= s.pic_tries
       or exists (select 1 from private.reset_codes r where r.pupil_id = v_pupil and r.expires_at > p_now)
       or sec.code_hash is null and v_pupil is not null
       or sec.pic_recovered_at > p_now - make_interval(days => s.pic_again_days) then
      return jsonb_build_object('s', 'locked', 'wait', -1);
    end if;
    update private.auth_buckets set fails = fails + 1, last_fail_at = p_now
     where class_id = v_class and name_key = v_key and kind = 'picture' and bucket = '*';
    if sec.pic_hash is not null then v_salt := sec.pic_salt; v_iter := sec.pic_iter; end if;

  else  -- otc: 5 wrong per address, 30 in all, then the code is cancelled
    select * into rc from private.reset_codes where pupil_id = v_pupil for update;
    if rc.pupil_id is not null and rc.expires_at <= p_now then
      delete from private.reset_codes where pupil_id = v_pupil; rc := null;
    end if;
    select count(*), min(at) into n_ip, v_oldest from private.auth_attempts
     where class_id = v_class and name_key = v_key and kind = 'otc' and outcome <> 'ok' and ip_bucket in (p_ip, p_ip_prev) and at > p_now - day;
    if n_ip >= s.otc_ip_tries then return jsonb_build_object('s', 'locked', 'wait', private.wait_s(v_oldest + day, p_now)); end if;
    if rc.pupil_id is not null then
      update private.reset_codes set fails = fails + 1 where pupil_id = v_pupil;
      v_salt := rc.salt; v_iter := rc.iter;
    end if;
  end if;

  insert into private.auth_attempts (at, class_id, name_key, kind, dev_bucket, ip_bucket, trusted)
    values (p_now, v_class, v_key, p_kind, p_dev, p_ip, v_known) returning id into v_attempt;
  -- without a stored secret the caller still gets "go" and hashes against a throw-away salt: same work, same answer
  return jsonb_build_object('s', 'go', 'attempt', v_attempt, 'class', v_class,
    'pupil', case when v_salt is not null then v_pupil end,
    'algo', v_algo, 'salt', encode(v_salt, 'hex'), 'iter', v_iter, 'legacy_salt', v_legacy,
    'iter_default', s.kdf_iter, 'pic_count', s.pic_count, 'pic_choices', s.pic_choices);
end $$;

-- a new code and pictures for a pupil, from hashes the function made. p_revoke: also forget known devices and cut
-- the link to the auth user, which ends every open session at once. Returns the old auth user to delete.
create function private.set_secrets(p_pupil uuid, p_new jsonb, p_revoke boolean, p_now timestamptz) returns uuid
language plpgsql security definer set search_path = '' as $$
declare v_old uuid;
begin
  if (p_new ->> 'code_hash') is null or (p_new ->> 'pic_hash') is null then raise exception 'a new code and pictures are required'; end if;
  insert into private.pupil_secrets (pupil_id) values (p_pupil) on conflict do nothing;
  update private.pupil_secrets set code_algo = 'v1', legacy_salt = null, code_set_at = p_now,
         code_salt = decode(p_new ->> 'code_salt', 'hex'), code_hash = decode(p_new ->> 'code_hash', 'hex'), code_iter = (p_new ->> 'iter')::int,
         pic_salt = decode(p_new ->> 'pic_salt', 'hex'), pic_hash = decode(p_new ->> 'pic_hash', 'hex'), pic_iter = (p_new ->> 'iter')::int
   where pupil_id = p_pupil;
  if p_revoke then
    delete from private.pupil_devices where pupil_id = p_pupil;
    select auth_user_id into v_old from public.pupils where id = p_pupil;
    update public.pupils set auth_user_id = null where id = p_pupil;
  end if;
  return v_old;
end $$;

/* Step 2. p_hash: what the function computed from what was typed. Compares, books the result, starts locks.
   p_new: the new code and pictures, already hashed ({code_salt, code_hash, pic_salt, pic_hash, iter}); required for
   picture and otc, and for the first sign-in of a pupil who came from the Sheet. Applied in the same transaction
   as the proof. p_dev_new: hex HMAC of a device token the function is about to hand out (stored only on success).
   Returns {ok, pupil, auth_user, old_auth_user, name, wait} or {ok: false, setup: true} (old code right, new one needed). */
create function private.auth_finish(p_attempt bigint, p_hash text, p_new jsonb, p_dev_new text, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  s private.settings; a private.auth_attempts; p public.pupils; sec private.pupil_secrets; rc private.reset_codes;
  v_hash bytea; v_ok boolean := false; v_until timestamptz; v_old uuid; v_user uuid; v_dev text;
  n_all int; n_str int; n_cls int; day constant interval := interval '24 hours';
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
  v_dev := coalesce(nullif(p_dev_new, ''), nullif(a.dev_bucket, ''));

  if a.kind = 'code' then
    v_ok := coalesce(sec.code_hash = v_hash, false);
    if not v_ok then
      update private.auth_attempts set outcome = 'wrong' where id = a.id;
      v_until := private.bucket_fail(a.class_id, a.name_key, case when a.trusted then 'd:' || a.dev_bucket else 'i:' || a.ip_bucket end, p_now);
      select count(*), count(*) filter (where not trusted) into n_all, n_str from private.auth_attempts
       where class_id = a.class_id and name_key = a.name_key and kind = 'code' and outcome <> 'ok' and at > p_now - day;
      if n_all = s.code_ceiling_day or (not a.trusted and n_str = s.code_name_day) then
        perform private.lock_event(a.class_id, a.name_key, 'name', p_now, null);       -- the name is closed for the day
      elsif v_until is not null then
        perform private.lock_event(a.class_id, a.name_key, 'code', p_now, v_until);
      end if;
      if not a.trusted then     -- the class as a whole: tell the teacher at the alarm mark and at the brake
        select count(*) into n_cls from private.auth_attempts
         where class_id = a.class_id and kind = 'code' and outcome <> 'ok' and not trusted and at > p_now - day;
        if n_cls in (s.code_class_alarm, s.code_class_brake) then
          perform private.lock_event(a.class_id, '', case when n_cls = s.code_class_brake then 'class-brake' else 'class-alarm' end, p_now, null);
        end if;
      end if;
      return jsonb_build_object('ok', false);
    end if;
    if sec.code_algo <> 'v1' or sec.pic_hash is null then
      -- came from the Sheet: the old code is right, but nothing opens until a new code and pictures are chosen
      update private.auth_attempts set outcome = 'ok' where id = a.id;
      if s.shadow_mode then null;      -- copy phase: the Sheet-era code opens a session and nothing is changed
      elsif p_new is null then return jsonb_build_object('ok', false, 'setup', true);
      else perform private.set_secrets(p.id, p_new, false, p_now);
      end if;
    else
      update private.auth_attempts set outcome = 'ok' where id = a.id;
    end if;
    delete from private.auth_buckets where class_id = a.class_id and name_key = a.name_key and kind = 'code'
       and bucket in ('d:' || a.dev_bucket, 'i:' || a.ip_bucket);
    v_user := p.auth_user_id;
    if v_user is not null and not private.auth_user_clean(v_user) then      -- somebody changed the auth user: replace it
      v_old := v_user; v_user := null;
      update public.pupils set auth_user_id = null where id = p.id;
    end if;

  elsif a.kind = 'picture' then
    v_ok := coalesce(sec.pic_hash = v_hash, false);
    if not v_ok then
      update private.auth_attempts set outcome = 'wrong' where id = a.id;
      if (select fails from private.auth_buckets where class_id = a.class_id and name_key = a.name_key and kind = 'picture' and bucket = '*') >= s.pic_tries then
        update private.auth_buckets set locked_until = 'infinity', round = round + 1
         where class_id = a.class_id and name_key = a.name_key and kind = 'picture' and bucket = '*' and locked_until is distinct from 'infinity';
        if found then perform private.lock_event(a.class_id, a.name_key, 'picture', p_now, 'infinity'); end if;
      end if;
      select count(*) into n_cls from private.auth_attempts where class_id = a.class_id and kind = 'picture' and outcome <> 'ok' and at > p_now - day;
      if n_cls = s.pic_class_day then perform private.lock_event(a.class_id, '', 'class-picture', p_now, null); end if;
      return jsonb_build_object('ok', false);
    end if;
    update private.auth_attempts set outcome = 'ok' where id = a.id;
    v_old := private.set_secrets(p.id, p_new, true, p_now);
    update private.pupil_secrets set pic_recovered_at = p_now where pupil_id = p.id;
    delete from private.auth_buckets where class_id = a.class_id and name_key = a.name_key and kind in ('code', 'picture');

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
    update private.auth_attempts set outcome = 'ok' where id = a.id;
    v_old := private.set_secrets(p.id, p_new, true, p_now);       -- the one-time code is used up in this same transaction
    delete from private.reset_codes where pupil_id = p.id;
    delete from private.auth_buckets where class_id = a.class_id and name_key = a.name_key and kind in ('code', 'picture');
  end if;

  if v_dev is not null then
    insert into private.pupil_devices (pupil_id, device_hash, last_ok_at) values (p.id, decode(v_dev, 'hex'), p_now)
      on conflict (pupil_id, device_hash) do update set last_ok_at = excluded.last_ok_at;
  end if;
  return jsonb_build_object('ok', true, 'pupil', p.id, 'auth_user', v_user, 'old_auth_user', v_old, 'name', p.display_name);
end $$;

/* A new pupil. The class list, the size of the class and the free name are checked here, under the name lock.
   p_new as in auth_finish. Returns {s: 'ok' | 'taken' | 'roster' | 'full'}. */
create function private.register_pupil(p_id uuid, p_class uuid, p_name text, p_new jsonb, p_dev text, p_now timestamptz) returns jsonb
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
  perform private.set_secrets(p_id, p_new, false, p_now);
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
  $$ select coalesce((select jsonb_build_object('state', state, 'updated_at', updated_at) from public.progress where pupil_id = p_pupil), '{}'::jsonb) $$;

/* The teacher resets a pupil of her own class (checked here again, not only in the function): the code stops working,
   every device is signed out, the name's locks are cleared, and a one-time code (already hashed) is stored. Recovery
   by pictures stays closed while that code waits. Returns {ok, old_auth_user, expires_at, name} or {ok: false}. */
create function private.teacher_reset(p_teacher uuid, p_pupil uuid, p_salt text, p_hash text, p_iter int, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; p public.pupils; v_exp timestamptz;
begin
  select * into s from private.settings;
  select pu.* into p from public.pupils pu join public.teachers t on t.class_id = pu.class_id
   where pu.id = p_pupil and t.user_id = p_teacher;
  if p.id is null or s.shadow_mode then return jsonb_build_object('ok', false); end if;      -- during the copy phase resets happen on the Sheet
  perform private.name_lock(p.class_id, p.name_key);
  v_exp := p_now + make_interval(hours => s.otc_hours);
  insert into private.pupil_secrets (pupil_id) values (p.id) on conflict do nothing;
  update private.pupil_secrets set code_algo = 'v1', code_salt = null, code_hash = null, legacy_salt = null, code_set_at = null,
         pic_recovered_at = null where pupil_id = p.id;
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

/* The teacher clears the locks of one pupil of her class without touching the code or the pictures: wrong codes and
   wrong pictures of that name are forgotten and recovery is reopened. For the pupil kept out by somebody's guesses. */
create function private.teacher_unlock(p_teacher uuid, p_pupil uuid, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare p public.pupils;
begin
  select pu.* into p from public.pupils pu join public.teachers t on t.class_id = pu.class_id
   where pu.id = p_pupil and t.user_id = p_teacher;
  if p.id is null or (select shadow_mode from private.settings) then return jsonb_build_object('ok', false); end if;
  perform private.name_lock(p.class_id, p.name_key);
  delete from private.auth_buckets  where class_id = p.class_id and name_key = p.name_key and kind in ('code', 'picture');
  delete from private.auth_attempts where class_id = p.class_id and name_key = p.name_key and kind in ('code', 'picture') and outcome <> 'ok';
  perform private.lock_event(p.class_id, p.name_key, 'unlock', p_now, null);
  return jsonb_build_object('ok', true, 'name', p.display_name);
end $$;

/* The teacher lifts the class-wide pauses (wrong codes and wrong pictures from unknown devices in the last day), so
   guesses made before school cannot cost a lesson. Per-name locks stay. */
create function private.teacher_unlock_class(p_teacher uuid, p_class uuid, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
begin
  if not exists (select 1 from public.teachers where user_id = p_teacher and class_id = p_class) or (select shadow_mode from private.settings) then
    return jsonb_build_object('ok', false);
  end if;
  -- the tries are kept as history under another kind, so they stop counting but the day's story stays readable
  update private.auth_attempts set kind = 'class', class_id = null, name_key = ''
   where class_id = p_class and kind in ('code', 'picture') and outcome <> 'ok' and not trusted and at > p_now - interval '24 hours';
  perform private.lock_event(p_class, '', 'unlock-class', p_now, null);
  return jsonb_build_object('ok', true);
end $$;

-- a class and its code; the lookup is made by the admin function, which holds the pepper
create function private.class_create(p_name text, p_grade text, p_lookup text) returns uuid
language plpgsql security definer set search_path = '' as $$
declare v uuid;
begin
  insert into public.classes (name, grade) values (p_name, coalesce(p_grade, '')) returning id into v;
  insert into private.class_codes (class_id, code_lookup) values (v, decode(p_lookup, 'hex'));
  return v;
end $$;
create function private.class_rotate(p_class uuid, p_lookup text) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  update private.class_codes set code_lookup = decode(p_lookup, 'hex') where class_id = p_class;
  return found;
end $$;

/* The copy phase on or off. Turning it OFF cuts every pupil from their auth user, which ends every session opened
   during the copy phase at once; the caller deletes the returned auth users. */
create function private.shadow_set(p_on boolean) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v jsonb := '[]'::jsonb;
begin
  if not p_on then
    select coalesce(jsonb_agg(auth_user_id), '[]'::jsonb) into v from public.pupils where auth_user_id is not null;
    update public.pupils set auth_user_id = null where auth_user_id is not null;
    delete from private.pupil_devices;
  end if;
  update private.settings set shadow_mode = p_on;
  return jsonb_build_object('ok', true, 'shadow_mode', p_on, 'old_auth_users', v);
end $$;

-- migration, once: the next Sheet hashes waiting to be wrapped, and storing one that the function wrapped
create function private.legacy_next(p_limit int) returns jsonb language sql security definer set search_path = '' as
  $$ select coalesce(jsonb_agg(jsonb_build_object('pupil', pupil_id, 'salt', salt, 'hash', hash)), '[]'::jsonb)
       from (select * from private.legacy_import order by pupil_id limit p_limit) x $$;
create function private.legacy_store(p_pupil uuid, p_salt text, p_hash text, p_iter int) returns int
language plpgsql security definer set search_path = '' as $$
declare l private.legacy_import; n int;
begin
  select * into l from private.legacy_import where pupil_id = p_pupil for update;
  if l.pupil_id is not null then
    insert into private.pupil_secrets (pupil_id) values (p_pupil) on conflict do nothing;
    update private.pupil_secrets set code_algo = 'legacy-sha256', legacy_salt = l.salt, code_salt = decode(p_salt, 'hex'),
           code_hash = decode(p_hash, 'hex'), code_iter = p_iter where pupil_id = p_pupil and code_hash is null;
    delete from private.legacy_import where pupil_id = p_pupil;
  end if;
  select count(*) into n from private.legacy_import;
  return n;
end $$;

revoke all on all functions in schema private from public, anon, authenticated;
grant execute on all functions in schema private to service_role;
