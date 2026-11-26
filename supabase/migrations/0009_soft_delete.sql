-- Removing a pupil from the class, with 14 days to undo it (docs/PHASE3.md; the design review of the teacher screen).
-- Two actions, never one: "remove from class" (this file: can be undone for removed_days) and "delete for good"
-- (teacher_delete_pupil: immediate, for a parent's deletion request; also on a removed pupil).
--
-- How: the pupil's row moves to a hidden class of its own (one per class, "limbo"): no class code, no teacher, nobody
-- reads it. Every rule that is scoped by class then leaves the pupil out by itself, with no change to them: the
-- sign-in finds no such name in the class, the board, the teacher's views and the class's hard words do not show
-- the pupil, and the pupil's session is ended (its auth user is deleted, as at a reset). The records stay, keyed by the
-- pupil, for the way back. After removed_days, maintenance() deletes the pupil for good, exactly as
-- teacher_delete_pupil does, and records it in private.deletions.
-- A new migration, not an edit of 0001 to 0005 (docs/LESSONS.md entry 15).

alter table private.settings add column removed_days int not null default 14 check (removed_days between 1 and 60);

-- the hidden class of each class that removed a pupil
create table private.limbo (
  class_id uuid primary key references public.classes on delete cascade,
  limbo_id uuid not null unique references public.classes on delete cascade
);
alter table private.limbo enable row level security;

-- each removed pupil: the class to go back to, when, by whom
create table private.removed_pupils (
  pupil_id   uuid primary key references public.pupils on delete cascade,
  class_id   uuid not null references public.classes on delete cascade,
  removed_at timestamptz not null,
  removed_by uuid
);
alter table private.removed_pupils enable row level security;
create index removed_pupils_at on private.removed_pupils (removed_at);

/* "Remove from class": hers only. Returns {ok, purge_at} or {ok: false, e: 'taken'} when a pupil of the same name is
   already waiting in this class's removed list. */
create function public.teacher_remove_pupil(p_pupil uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare p public.pupils; v_limbo uuid; s private.settings;
begin
  select * into s from private.settings;
  select * into p from public.pupils where id = p_pupil;
  if p.id is null or not app.teaches(p.class_id) then raise exception 'not your pupil' using errcode = '42501'; end if;
  perform pg_advisory_xact_lock(hashtextextended('limbo/' || p.class_id::text, 42));
  select limbo_id into v_limbo from private.limbo where class_id = p.class_id;
  if v_limbo is null then
    insert into public.classes (name, roster_only, max_pupils) values ('removed', true, 200) returning id into v_limbo;
    insert into private.limbo (class_id, limbo_id) values (p.class_id, v_limbo);
  end if;
  if exists (select 1 from public.pupils where class_id = v_limbo and name_key = p.name_key) then
    return jsonb_build_object('ok', false, 'e', 'taken');
  end if;
  insert into private.removed_pupils (pupil_id, class_id, removed_at, removed_by) values (p.id, p.class_id, now(), auth.uid());
  update public.pupils set class_id = v_limbo, auth_user_id = null where id = p.id;
  if p.auth_user_id is not null then delete from auth.users where id = p.auth_user_id; end if;   -- the session ends now
  return jsonb_build_object('ok', true, 'purge_at', now() + make_interval(days => s.removed_days));
end $$;

/* "Undo": back to the class, if the name is still free there and the class is not full. */
create function public.teacher_restore_pupil(p_pupil uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare r private.removed_pupils; p public.pupils; c public.classes;
begin
  select * into r from private.removed_pupils where pupil_id = p_pupil;
  if r.pupil_id is null or not app.teaches(r.class_id) then raise exception 'not your pupil' using errcode = '42501'; end if;
  perform pg_advisory_xact_lock(hashtextextended('limbo/' || r.class_id::text, 42));
  select * into p from public.pupils where id = r.pupil_id;
  select * into c from public.classes where id = r.class_id;
  if exists (select 1 from public.pupils where class_id = r.class_id and name_key = p.name_key) then
    return jsonb_build_object('ok', false, 'e', 'taken');
  end if;
  if (select count(*) from public.pupils where class_id = r.class_id) >= c.max_pupils then return jsonb_build_object('ok', false, 'e', 'full'); end if;
  update public.pupils set class_id = r.class_id where id = p.id;
  delete from private.removed_pupils where pupil_id = p.id;
  return jsonb_build_object('ok', true);
end $$;

/* Her removed pupils, with the day each is deleted for good */
create function public.teacher_removed() returns table (pupil_id uuid, class_id uuid, display_name text, removed_at timestamptz, purge_at timestamptz)
language sql stable security definer set search_path = '' as $$
  select p.id, r.class_id, p.display_name, r.removed_at, r.removed_at + make_interval(days => s.removed_days)
  from private.removed_pupils r join public.pupils p on p.id = r.pupil_id cross join private.settings s
  where app.teaches(r.class_id) order by p.display_name $$;

/* the deletion itself, shared by "delete for good" and the purge: the name's sign-in records, then the pupil
   (cascading to every table keyed by the pupil) and its auth user; a row in private.deletions, never the name */
create function private.delete_pupil(p_pupil uuid, p_class uuid, p_by uuid) returns void
language plpgsql security definer set search_path = '' as $$
declare p public.pupils;
begin
  select * into p from public.pupils where id = p_pupil;
  if p.id is null then return; end if;
  delete from private.auth_attempts    where class_id = p_class and name_key = p.name_key;
  delete from private.auth_buckets     where class_id = p_class and name_key = p.name_key;
  delete from private.auth_lock_events where class_id = p_class and name_key = p.name_key;
  insert into private.deletions (teacher, class_id, pupil_id, answers, points)
    select p_by, p_class, p.id, t.answers, t.points from public.pupil_totals t where t.pupil_id = p.id;
  delete from public.pupils where id = p.id;
  if p.auth_user_id is not null then delete from auth.users where id = p.auth_user_id; end if;
end $$;

/* as in 0003, and also for a pupil in her removed list (a parent's deletion request does not wait 14 days) */
create or replace function public.teacher_delete_pupil(p_pupil uuid) returns boolean
language plpgsql security definer set search_path = '' as $$
declare p public.pupils; v_class uuid;
begin
  select * into p from public.pupils where id = p_pupil;
  v_class := coalesce((select class_id from private.removed_pupils where pupil_id = p_pupil), p.class_id);
  if p.id is null or not app.teaches(v_class) then raise exception 'not your pupil' using errcode = '42501'; end if;
  perform private.delete_pupil(p.id, v_class, auth.uid());
  return true;
end $$;

/* the nightly purge: pupils removed more than removed_days ago */
create function private.purge_removed(p_now timestamptz) returns int
language plpgsql security definer set search_path = '' as $$
declare r private.removed_pupils; n int := 0;
begin
  for r in select * from private.removed_pupils
            where removed_at < p_now - make_interval(days => (select removed_days from private.settings)) loop
    perform private.delete_pupil(r.pupil_id, r.class_id, r.removed_by);
    n := n + 1;
  end loop;
  return n;
end $$;

-- as in 0003, with the purge of removed pupils
create or replace function public.maintenance() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; v_cut timestamptz; rolled int; bad int; purged boolean := true; v_mb int; v_out jsonb; v_gone int;
begin
  select * into s from private.settings;
  -- under the storage brake the roll-up waits (review S3): it writes new roll-up rows before vacuum can reuse the
  -- space of the deleted ones, so it grows the database exactly when it must not
  v_cut := case when s.storage_brake then '-infinity'::timestamptz
                else ((now() at time zone s.tz)::date - s.raw_days)::timestamp at time zone s.tz end;
  with old as (delete from public.answers where at < v_cut returning *),
  agg as (
    select pupil_id, (at at time zone s.tz)::date as day, item_id, count(*)::int as tries,
           count(*) filter (where correct)::int as correct, count(*) filter (where correct and first_try)::int as first_try,
           sum(pts)::int as pts
    from old group by 1, 2, 3
  ), ins as (
    insert into public.answer_daily as t (pupil_id, day, item_id, tries, correct, first_try, pts)
    select * from agg
    on conflict (pupil_id, day, item_id) do update
      set tries = t.tries + excluded.tries, correct = t.correct + excluded.correct,
          first_try = t.first_try + excluded.first_try, pts = t.pts + excluded.pts
    returning 1
  )
  select (select count(*) from old) into rolled;
  delete from private.auth_attempts    where at < now() - interval '30 days';
  delete from private.auth_lock_events where at < now() - interval '30 days';
  delete from private.auth_buckets     where coalesce(locked_until, last_fail_at, '-infinity') < now() - interval '30 days';
  delete from private.answer_batches   where at < now() - interval '30 days';
  delete from private.deletions        where at < now() - interval '400 days';
  delete from private.pupil_days       where day < (now() at time zone s.tz)::date - 30;
  delete from private.ip_salts         where day < (now() at time zone 'utc')::date - 2;
  delete from private.class_misses     where hour < now() - interval '2 days';
  delete from private.reset_codes      where expires_at < now() - interval '7 days';
  delete from private.pupil_devices    where last_ok_at < now() - make_interval(days => s.device_days);
  delete from public.flags             where day < (now() at time zone s.tz)::date - s.flags_days;
  delete from private.maintenance_log  where at < now() - make_interval(days => s.log_days);
  -- the daily bonus and Beach Run rows older than the raw window become one row per pupil and reason (totals unchanged);
  -- 'read' rows stay (a text pays once, ever) and so do stars and exams (few by their own caps)
  with old as (delete from public.points where reason in ('day', 'run') and at < v_cut returning *)
  insert into public.points (pupil_id, delta, reason, ref, at)
    select pupil_id, sum(delta)::int, reason, 'rolled', max(at) from old group by pupil_id, reason;
  begin   -- Supabase Auth's own log holds addresses; keep 30 days. Where the platform does not allow it, say so.
    delete from auth.audit_log_entries where created_at < now() - interval '30 days';
  exception when others then purged := false;
  end;
  v_gone := private.purge_removed(now());      -- pupils removed more than removed_days ago are deleted for good (0009)
  select count(*) into bad from private.totals_check();
  v_mb := (pg_database_size(current_database()) / 1048576)::int;
  -- the storage brake (re-check of PR 12): near the free plan's 500 MB, events are counted but not stored, until
  -- the owner frees space or raises nothing (no paid plan): docs/BACKEND.md section 6
  update private.settings set storage_brake = (v_mb >= s.storage_brake_mb);
  v_out := jsonb_build_object('ok', bad = 0 and purged and v_mb < s.storage_brake_mb, 'rolled', rolled, 'totals_wrong', bad,
                              'audit_purged', purged, 'removed_purged', v_gone, 'db_mb', v_mb, 'storage_brake', v_mb >= s.storage_brake_mb);
  insert into private.maintenance_log (result) values (v_out);
  return v_out;
end $$;


-- as in 0005, with the two new tables (after the pupils, for the restore's order)
create or replace function private.backup_tables() returns text[] language sql immutable set search_path = '' as $$
  select array['public.classes', 'public.roster', 'public.teachers', 'public.pupils', 'private.limbo', 'private.removed_pupils', 'public.items', 'public.levels',
    'public.answers', 'public.points', 'public.pupil_totals', 'public.progress', 'public.flags', 'public.level_best',
    'public.answer_daily', 'private.class_codes', 'private.pupil_secrets', 'private.reset_codes',
    'private.pupil_devices', 'private.answer_batches', 'private.pupil_days', 'private.deletions', 'private.maintenance_log',
    'private.settings'] $$;

revoke all on function public.teacher_remove_pupil(uuid), public.teacher_restore_pupil(uuid), public.teacher_removed() from public, anon;
grant execute on function public.teacher_remove_pupil(uuid), public.teacher_restore_pupil(uuid), public.teacher_removed(), public.teacher_delete_pupil(uuid) to authenticated;
revoke all on all functions in schema private from public, anon, authenticated;
grant execute on all functions in schema private to service_role;
