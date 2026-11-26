-- The teacher's daily cap of new one-time codes (review of #86, S7). Each new code costs 600,000 hash rounds on the
-- server and signs the pupil out everywhere; a class needs a few a week. A new migration, not an edit of 0004: a
-- project that ran 0001 to 0006 gets exactly this (docs/LESSONS.md entry 16).

-- new one-time codes one teacher may make in 24 hours
alter table private.settings add column reset_teacher_day int not null default 15 check (reset_teacher_day between 1 and 200);

-- every new one-time code a teacher made: who and when only (no pupil, no name), for her cap. teacher_reset keeps it
-- to 2 days; it is not backed up (backup_excluded below)
create table private.teacher_resets (
  teacher uuid not null,
  at      timestamptz not null
);
alter table private.teacher_resets enable row level security;
create index teacher_resets_by on private.teacher_resets (teacher, at);

-- how many new codes she may still make now: asked before the slow hashing, and enforced again inside teacher_reset
create function private.teacher_resets_left(p_teacher uuid, p_now timestamptz) returns int language sql stable security definer set search_path = '' as
  $$ select greatest(0, s.reset_teacher_day - (select count(*)::int from private.teacher_resets r
                                               where r.teacher = p_teacher and r.at > p_now - interval '24 hours'))
     from private.settings s $$;

-- as in 0004, with her cap: counted under a lock of her own (two resets at once cannot both take the last one), then
-- the name's lock, in that order everywhere
create or replace function private.teacher_reset(p_teacher uuid, p_pupil uuid, p_salt text, p_hash text, p_iter int, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; p public.pupils; v_exp timestamptz;
begin
  select * into s from private.settings;
  select pu.* into p from public.pupils pu join public.teachers t on t.class_id = pu.class_id
   where pu.id = p_pupil and t.user_id = p_teacher;
  if p.id is null or s.shadow_mode then return jsonb_build_object('ok', false); end if;      -- during the copy phase resets happen on the Sheet
  -- her daily cap, counted under a lock of her own (two resets at once cannot both take the last one), then the name
  perform pg_advisory_xact_lock(hashtextextended('resets/' || p_teacher::text, 42));
  if private.teacher_resets_left(p_teacher, p_now) < 1 then return jsonb_build_object('ok', false, 'e', 'limit'); end if;
  insert into private.teacher_resets (teacher, at) values (p_teacher, p_now);
  delete from private.teacher_resets where teacher = p_teacher and at < p_now - interval '2 days';   -- the counter keeps 2 days
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

-- as in 0004, with her own count and cap (the screen shows how many are left). Counted here, not with
-- private.teacher_resets_left: a view's caller needs the right to run the functions it calls.
create or replace view public.backend_health with (security_barrier = true) as
  select l.at as last_run_at,
         coalesce((l.result ->> 'ok')::boolean, false) as ok,
         coalesce((l.result ->> 'db_mb')::int, 0) as db_mb,
         coalesce((l.result ->> 'storage_brake')::boolean, false) as storage_brake,
         (l.at is null or l.at < now() - interval '36 hours' or not coalesce((l.result ->> 'ok')::boolean, false)
          or coalesce((l.result ->> 'db_mb')::int, 0) >= (select storage_brake_mb from private.settings)
          or u.n > 0) as warn,
         u.n as unreadable_day,
         -- her own new codes in the last 24 hours and her cap (review of #86, S7): the screen shows how many are left
         -- (counted here, not with private.teacher_resets_left: a view's caller needs the right to run its functions)
         (select count(*)::int from private.teacher_resets r where r.teacher = auth.uid() and r.at > now() - interval '24 hours') as resets_day,
         (select s.reset_teacher_day from private.settings s) as resets_cap
  from (select 1) one
  left join lateral (select at, result from private.maintenance_log order by at desc limit 1) l on true
  cross join lateral (select coalesce(sum(m.n), 0)::int as n from private.class_misses m
                       where m.bucket = 'unreadable' and m.hour > now() - interval '24 hours') u
  where exists (select 1 from public.teachers t where t.user_id = auth.uid());

-- as in 0005, with the counter (2 days of who-and-when, nothing to restore)
--   teacher_resets: a counter for the teacher's daily cap of new codes, 2 days long
create or replace function private.backup_excluded() returns text[] language sql immutable set search_path = '' as $$
  select array['private.ip_salts', 'private.auth_buckets', 'private.class_misses', 'private.auth_attempts',
    'private.auth_lock_events', 'private.legacy_import', 'private.teacher_resets'] $$;

revoke all on all functions in schema private from public, anon, authenticated;
grant execute on all functions in schema private to service_role;
