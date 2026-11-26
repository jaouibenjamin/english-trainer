-- Every "locked" answer of a sign-in, a recovery or a registration says whom it is for and who can end it (the
-- design review of the pupil sign-in screens, PR #84; the answers are listed in docs/BACKEND.md section 4): the child
-- sees "only your name, for N minutes" or "everyone at school waits until HH:MM", and the screen offers "ask the
-- teacher" only when she can help. No limit changes. A new migration, not an edit of 0004 (docs/LESSONS.md entry 15):
-- auth_begin as in 0004, with `by` and `help` added to each {s: 'locked'}.
-- help: 'teacher'  her unlock (a name), her class lift (the class, or the class from one address) or a new code ends it
--       'wait'     only time ends it: calls, wrong class codes and registrations per address per hour, every class this
--                  hour, the copy phase. The screen must not promise the teacher can lift these.
-- by:
--   name      this name (from this address or device for an unknown device, or the name's daily ceiling; the
--             pictures or the one-time code of this name: wait -1 means ask the teacher)
--   device    this pupil's own known device: only its own wrong codes count
--   address   everyone at this address (the school's network): calls per hour, wrong class codes per hour,
--             registrations per hour, wrong codes or pictures across the class from this address
--   class     the whole class from every address: the class brake (codes) or the class's picture pause
--   everyone  every class this hour (wrong class codes from all addresses together)
--   system    the copy phase: registration and recovery are off for now
create or replace function private.auth_begin(p_kind text, p_class_lookup text, p_name text, p_dev text, p_ip text, p_ip_prev text, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  s private.settings; v_class uuid; v_key text := app.name_key(p_name);
  v_pupil uuid; sec private.pupil_secrets; b private.auth_buckets; rc private.reset_codes;
  v_known boolean := false; v_until timestamptz; v_attempt bigint; v_oldest timestamptz; v_old2 timestamptz;
  n_all int; n_str int; n_dev int; n_ip int; n_ipc int; n_cls int;
  v_salt bytea; v_iter int; v_algo text := 'v1'; v_legacy text; v_hour timestamptz;
  day constant interval := interval '24 hours';
begin
  if p_kind not in ('code', 'picture', 'otc', 'register') then raise exception 'bad kind'; end if;
  select * into s from private.settings;

  -- Every limit below is a count followed by an insert. Parallel requests must not all read the same count (review
  -- S1), so the counts are taken under advisory locks held to the end of this statement: first the address, then the
  -- class and kind (then, further down, the name). Always in this order, so two requests cannot wait on each other.
  perform pg_advisory_xact_lock(hashtextextended('ip/' || p_ip, 42));
  v_hour := date_trunc('hour', p_now);

  -- the address: any calls, then wrong class codes (counted per hour, review S3)
  select count(*), min(at) into n_ip, v_oldest from private.auth_attempts where ip_bucket in (p_ip, p_ip_prev) and at > p_now - interval '1 hour';
  n_ip := n_ip + coalesce((select n from private.class_misses where bucket = p_ip and hour = v_hour), 0);
  if n_ip >= s.ip_hour then return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'wait', 'wait', private.wait_s(coalesce(v_oldest, v_hour) + interval '1 hour', p_now)); end if;
  if coalesce((select n from private.class_misses where bucket = p_ip and hour = v_hour), 0) >= s.class_ip_hour then
    return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'wait', 'wait', private.wait_s(v_hour + interval '1 hour', p_now));
  end if;

  select class_id into v_class from private.class_codes where code_lookup = decode(p_class_lookup, 'hex');
  if v_class is null then
    perform pg_advisory_xact_lock(hashtextextended('class-misses', 42));
    if (select coalesce(sum(n), 0) from private.class_misses where hour = v_hour and bucket <> 'unreadable') >= s.class_miss_hour then
      return jsonb_build_object('s', 'locked', 'by', 'everyone', 'help', 'wait', 'wait', private.wait_s(v_hour + interval '1 hour', p_now));      -- everyone, this hour
    end if;
    insert into private.class_misses (bucket, hour, n) values (p_ip, v_hour, 1)
      on conflict (bucket, hour) do update set n = private.class_misses.n + 1;
    return jsonb_build_object('s', 'class');
  end if;
  perform pg_advisory_xact_lock(hashtextextended('kind/' || v_class::text || '/' || p_kind, 42));

  -- while the copy phase runs, this side only receives copies: no registration, no recovery
  if s.shadow_mode and p_kind <> 'code' then return jsonb_build_object('s', 'locked', 'by', 'system', 'help', 'wait', 'wait', -1); end if;

  if p_kind = 'register' then
    select count(*), min(at) into n_ip, v_oldest from private.auth_attempts
     where ip_bucket in (p_ip, p_ip_prev) and kind = 'register' and at > p_now - interval '1 hour';
    if n_ip >= s.register_ip_hour then return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'wait', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now)); end if;
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
    if v_until is not null then return jsonb_build_object('s', 'locked', 'by', case when v_known then 'device' else 'name' end, 'help', 'teacher', 'wait', private.wait_s(v_until, p_now)); end if;
    -- wrong (or unfinished) codes of the last 24 hours: this name; this address on this name; this device
    select count(*), count(*) filter (where not trusted and not lifted), count(*) filter (where trusted and dev_bucket = p_dev and not lifted),
           count(*) filter (where not trusted and not lifted and ip_bucket in (p_ip, p_ip_prev)), min(at)
      into n_all, n_str, n_dev, n_ip, v_oldest
      from private.auth_attempts
     where class_id = v_class and name_key = v_key and kind = 'code' and outcome <> 'ok' and at > p_now - day;
    -- a known device (the pupil's own phone, review S2) is judged only by its own wrong codes, so strangers and unlocks
    -- can never use up its reserve; strangers stop at the name's daily ceiling, whatever was lifted
    if (v_known and n_dev >= s.code_bucket_day)
       or (not v_known and (n_all >= s.code_ceiling_day or n_str >= private.name_allow(v_class, v_key, p_now) or n_ip >= s.code_bucket_day)) then
      return jsonb_build_object('s', 'locked', 'by', case when v_known then 'device' else 'name' end, 'help', 'teacher', 'wait', private.wait_s(v_oldest + day, p_now));
    end if;
    if not v_known then
      -- strangers, across the names of the class: one address, and everybody together (the class brake)
      select count(*) filter (where ip_bucket in (p_ip, p_ip_prev)), count(*), min(at) filter (where ip_bucket in (p_ip, p_ip_prev)), min(at)
        into n_ipc, n_cls, v_oldest, v_old2
        from private.auth_attempts where class_id = v_class and kind = 'code' and outcome <> 'ok' and not trusted and not lifted and at > p_now - day;
      if n_ipc >= s.code_ip_class_day then return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'teacher', 'wait', private.wait_s(v_oldest + day, p_now)); end if;
      if n_cls >= private.class_allow(v_class, p_now) then return jsonb_build_object('s', 'locked', 'by', 'class', 'help', 'teacher', 'wait', private.wait_s(v_old2 + day, p_now)); end if;
    end if;
    if sec.code_hash is not null then
      v_salt := sec.code_salt; v_iter := sec.code_iter; v_algo := sec.code_algo; v_legacy := sec.legacy_salt;
    end if;

  elsif p_kind = 'picture' then
    -- per address and per class first (they hold for names that do not exist too)
    select count(*) filter (where ip_bucket in (p_ip, p_ip_prev)), count(*), min(at) filter (where ip_bucket in (p_ip, p_ip_prev)), min(at)
      into n_ipc, n_cls, v_oldest, v_old2
      from private.auth_attempts where class_id = v_class and kind = 'picture' and outcome <> 'ok' and not lifted and at > p_now - day;
    if n_ipc >= s.pic_ip_day then return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'teacher', 'wait', private.wait_s(v_oldest + day, p_now)); end if;
    if n_cls >= s.pic_class_day then return jsonb_build_object('s', 'locked', 'by', 'class', 'help', 'teacher', 'wait', private.wait_s(v_old2 + day, p_now)); end if;
    insert into private.auth_buckets (class_id, name_key, kind, bucket) values (v_class, v_key, 'picture', '*') on conflict do nothing;
    select * into b from private.auth_buckets where class_id = v_class and name_key = v_key and kind = 'picture' and bucket = '*' for update;
    -- closed after the tries are used; closed while a teacher reset waits; once in 30 days
    if b.locked_until > p_now or b.fails >= s.pic_tries
       or exists (select 1 from private.reset_codes r where r.pupil_id = v_pupil and r.expires_at > p_now)
       or sec.code_hash is null and v_pupil is not null
       or sec.pic_recovered_at > p_now - make_interval(days => s.pic_again_days) then
      return jsonb_build_object('s', 'locked', 'by', 'name', 'help', 'teacher', 'wait', -1);
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
    if n_ip >= s.otc_ip_tries then return jsonb_build_object('s', 'locked', 'by', 'name', 'help', 'teacher', 'wait', private.wait_s(v_oldest + day, p_now)); end if;
    if rc.pupil_id is not null and rc.fails >= s.otc_tries then      -- used up (also by tries running in parallel, N1)
      delete from private.reset_codes where pupil_id = v_pupil;
      perform private.lock_event(v_class, v_key, 'otc', p_now, null);
      return jsonb_build_object('s', 'locked', 'by', 'name', 'help', 'teacher', 'wait', -1);
    end if;
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

revoke all on all functions in schema private from public, anon, authenticated;
grant execute on all functions in schema private to service_role;
