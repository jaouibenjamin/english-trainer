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

-- the hidden class of each class that removed a pupil. A class deleted by hand leaves its hidden class behind
-- (class_id becomes null); the purge then deletes what is left in it and drops it (review of #94, S4)
create table private.limbo (
  limbo_id uuid primary key references public.classes on delete cascade,
  class_id uuid unique references public.classes on delete set null
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

create function private.is_limbo(p_class uuid) returns boolean language sql stable security definer set search_path = '' as
  $$ select exists (select 1 from private.limbo where limbo_id = p_class) $$;

-- Locks, always in this order (review of #94, B1, B2, S1): the class's removal lock ('limbo/' || class), then the
-- name (private.name_lock, as every sign-in step and register_pupil), then the class's head count (43, as
-- register_pupil). A sign-in that has the name finishes before a removal starts, and the next step of that sign-in
-- (linking its session, link_auth_user below) takes the name again, so it sees the removal and refuses.

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
  perform private.name_lock(p.class_id, p.name_key);
  select * into p from public.pupils where id = p_pupil for update;      -- as it is now: a sign-in may have linked a session
  if p.id is null or not app.teaches(p.class_id) then raise exception 'not your pupil' using errcode = '42501'; end if;
  select limbo_id into v_limbo from private.limbo where class_id = p.class_id;
  if v_limbo is null then
    insert into public.classes (name, roster_only, max_pupils) values ('removed', true, 200) returning id into v_limbo;
    insert into private.limbo (limbo_id, class_id) values (v_limbo, p.class_id);
  end if;
  if exists (select 1 from public.pupils where class_id = v_limbo and name_key = p.name_key) then
    return jsonb_build_object('ok', false, 'e', 'taken');
  end if;
  insert into private.removed_pupils (pupil_id, class_id, removed_at, removed_by) values (p.id, p.class_id, now(), auth.uid());
  update public.pupils set class_id = v_limbo, auth_user_id = null where id = p.id;
  if p.auth_user_id is not null then delete from auth.users where id = p.auth_user_id; end if;   -- the session ends now
  return jsonb_build_object('ok', true, 'purge_at', now() + make_interval(days => s.removed_days));
end $$;

/* "Undo": back to the class, if the name is still free there and the class is not full. Under the same locks as
   a registration (name, then head count), so the two can never both take the name or the last place. */
create function public.teacher_restore_pupil(p_pupil uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare r private.removed_pupils; p public.pupils; c public.classes; s private.settings;
begin
  select * into s from private.settings;
  select * into r from private.removed_pupils where pupil_id = p_pupil;
  if r.pupil_id is null or not app.teaches(r.class_id) then raise exception 'not your pupil' using errcode = '42501'; end if;
  perform pg_advisory_xact_lock(hashtextextended('limbo/' || r.class_id::text, 42));
  select * into r from private.removed_pupils where pupil_id = p_pupil;   -- the purge may have run meanwhile
  select * into p from public.pupils where id = p_pupil for update;
  if r.pupil_id is null or p.id is null or not private.is_limbo(p.class_id) then return jsonb_build_object('ok', false, 'e', 'gone'); end if;
  perform private.name_lock(r.class_id, p.name_key);
  if exists (select 1 from public.pupils where class_id = r.class_id and name_key = p.name_key) then
    return jsonb_build_object('ok', false, 'e', 'taken', 'purge_at', r.removed_at + make_interval(days => s.removed_days));
  end if;
  perform pg_advisory_xact_lock(hashtextextended(r.class_id::text, 43));
  select * into c from public.classes where id = r.class_id;
  if (select count(*) from public.pupils where class_id = r.class_id) >= c.max_pupils then return jsonb_build_object('ok', false, 'e', 'full'); end if;
  update public.pupils set class_id = r.class_id where id = p.id and class_id = p.class_id;
  if not found then return jsonb_build_object('ok', false, 'e', 'gone'); end if;
  delete from private.removed_pupils where pupil_id = p.id;
  return jsonb_build_object('ok', true);
end $$;

/* Her removed pupils, with the day each is deleted for good */
create function public.teacher_removed() returns table (pupil_id uuid, class_id uuid, display_name text, removed_at timestamptz, purge_at timestamptz)
language sql stable security definer set search_path = '' as $$
  select p.id, r.class_id, p.display_name, r.removed_at, r.removed_at + make_interval(days => s.removed_days)
  from private.removed_pupils r join public.pupils p on p.id = r.pupil_id cross join private.settings s
  where app.teaches(r.class_id) order by p.display_name $$;

/* the deletion itself, shared by "delete for good" and the purge: the pupil (cascading to every table keyed by the
   pupil) and its auth user, a row in private.deletions (never the name), and the name's sign-in records unless
   another pupil of the class holds that name now (they are hers: review of #94, S2) */
create function private.delete_pupil(p_pupil uuid, p_class uuid, p_by uuid) returns void
language plpgsql security definer set search_path = '' as $$
declare p public.pupils;
begin
  select * into p from public.pupils where id = p_pupil;
  if p.id is null then return; end if;
  if not exists (select 1 from public.pupils where class_id = p_class and name_key = p.name_key and id <> p.id) then
    delete from private.auth_attempts    where class_id = p_class and name_key = p.name_key;
    delete from private.auth_buckets     where class_id = p_class and name_key = p.name_key;
    delete from private.auth_lock_events where class_id = p_class and name_key = p.name_key;
  end if;
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
  perform pg_advisory_xact_lock(hashtextextended('limbo/' || v_class::text, 42));
  perform private.delete_pupil(p.id, v_class, auth.uid());
  return true;
end $$;

/* the nightly purge, at most 200 a night (docs/LESSONS.md entry 9): pupils removed more than removed_days ago, each
   checked again under its class's removal lock (an undo that got there first wins: review of #94, B2); then what a
   class deleted by hand left in its hidden class, and the empty hidden classes of deleted classes */
create function private.purge_removed(p_now timestamptz) returns int
language plpgsql security definer set search_path = '' as $$
declare r private.removed_pupils; v record; n int := 0; v_cut timestamptz;
begin
  v_cut := p_now - make_interval(days => (select removed_days from private.settings));
  for r in select * from private.removed_pupils where removed_at < v_cut order by removed_at limit 200 loop
    perform pg_advisory_xact_lock(hashtextextended('limbo/' || r.class_id::text, 42));
    if exists (select 1 from private.removed_pupils x join public.pupils p on p.id = x.pupil_id
                where x.pupil_id = r.pupil_id and x.removed_at < v_cut and private.is_limbo(p.class_id)) then
      perform private.delete_pupil(r.pupil_id, r.class_id, r.removed_by);
      n := n + 1;
    end if;
  end loop;
  for v in select p.id, l.limbo_id from private.limbo l join public.pupils p on p.class_id = l.limbo_id
            where not exists (select 1 from private.removed_pupils x where x.pupil_id = p.id) limit greatest(0, 200 - n) loop
    perform private.delete_pupil(v.id, v.limbo_id, null);
    n := n + 1;
  end loop;
  delete from public.classes c using private.limbo l
   where c.id = l.limbo_id and l.class_id is null and not exists (select 1 from public.pupils p where p.class_id = l.limbo_id);
  return n;
end $$;

/* as in 0004, and never for a pupil in a hidden class (review of #94, B1): a sign-in creates the auth user between
   two steps; when the pupil was removed in between, the link is refused (the function then deletes that user and
   answers "pin"). The name's lock first, as the removal takes it. */
create or replace function private.link_auth_user(p_pupil uuid, p_user uuid) returns uuid
language plpgsql security definer set search_path = '' as $$
declare v uuid; p public.pupils;
begin
  select * into p from public.pupils where id = p_pupil;
  if p.id is null or private.is_limbo(p.class_id) then return null; end if;
  perform private.name_lock(p.class_id, p.name_key);
  update public.pupils set auth_user_id = p_user where id = p_pupil and auth_user_id is null and not private.is_limbo(class_id);
  select auth_user_id into v from public.pupils where id = p_pupil and not private.is_limbo(class_id);
  return v;
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


-- as in 0005, with a name the teacher took out of the class skipped (counted in skipped_removed)
create or replace function private.sheet_import(p_class uuid, p_rows jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; r jsonb; v_id uuid; v_name text; v_pts int; v_state jsonb;
  n_new int := 0; n_seen int := 0; n_removed int := 0; n_blob int := 0; n_hash int := 0; n_bad int := 0; n_err int := 0; v_med numeric; v_out jsonb;
  d_new int; d_blob int; d_hash int;
begin
  if not exists (select 1 from public.classes where id = p_class) then raise exception 'no such class'; end if;
  if jsonb_typeof(p_rows) <> 'array' then raise exception 'rows must be an array'; end if;
  select * into s from private.settings;
  for r in select * from jsonb_array_elements(p_rows) loop
    v_name := btrim(regexp_replace(normalize(coalesce(r ->> 'name', ''), NFC), '\s+', ' ', 'g'));
    if not app.name_ok(v_name) then n_bad := n_bad + 1; continue; end if;
    -- a pupil the teacher took out of this class is not brought back by a copy (review of #94, S3)
    if exists (select 1 from private.removed_pupils x join public.pupils p on p.id = x.pupil_id
                where x.class_id = p_class and p.name_key = app.name_key(v_name)) then n_removed := n_removed + 1; continue; end if;
    v_state := case when jsonb_typeof(r -> 'state') = 'object' and char_length((r -> 'state')::text) <= 40000 then r -> 'state' else '{}'::jsonb end;
    v_pts := least(app.safe_int(r -> 'points', 1000000), s.migrated_cap);
    d_new := 0; d_blob := 0; d_hash := 0;
    -- one row at a time: a row the database refuses is counted and skipped. Caught here, its error and the
    -- "Failing row contains (...)" detail never reach the server's log (review of #27, B3-bis)
    begin
      select id into v_id from public.pupils where class_id = p_class and name_key = app.name_key(v_name);
      if v_id is null then
        d_new := 1;
        insert into public.pupils (class_id, display_name) values (p_class, v_name) returning id into v_id;
        if v_pts > 0 then
          insert into public.points (pupil_id, delta, reason, ref) values (v_id, v_pts, 'migrated', 'sheet');
          update public.pupil_totals set points = points + v_pts where pupil_id = v_id;
        end if;
      end if;
      insert into public.progress (pupil_id, state, updated_at) values (v_id, v_state, now())
        on conflict (pupil_id) do update set state = excluded.state, updated_at = excluded.updated_at
        where public.progress.state is distinct from excluded.state;
      get diagnostics d_blob = row_count;
      if coalesce(r ->> 'hash', '') ~ '^[0-9a-f]{64}$' and coalesce(r ->> 'salt', '') <> ''
         and not exists (select 1 from private.pupil_secrets where pupil_id = v_id and code_hash is not null) then
        insert into private.legacy_import (pupil_id, salt, hash) values (v_id, r ->> 'salt', r ->> 'hash')
          on conflict (pupil_id) do update set salt = excluded.salt, hash = excluded.hash;
        d_hash := 1;
      end if;
      n_new := n_new + d_new; n_seen := n_seen + (1 - d_new); n_blob := n_blob + d_blob; n_hash := n_hash + d_hash;
    exception when others then
      n_err := n_err + 1;
    end;
  end loop;
  select percentile_cont(0.5) within group (order by t.points) into v_med
    from public.pupil_totals t join public.pupils p on p.id = t.pupil_id where p.class_id = p_class;
  select jsonb_build_object('new', n_new, 'existing', n_seen, 'blobs', n_blob, 'hashes_staged', n_hash, 'refused_names', n_bad,
           'refused_rows', n_err, 'skipped_removed', n_removed, 'median', coalesce(v_med, 0),
           'look_at', coalesce((select jsonb_agg(p.display_name order by t.points desc) from public.pupil_totals t
                                join public.pupils p on p.id = t.pupil_id
                               where p.class_id = p_class and v_med > 0 and t.points > 3 * v_med), '[]'::jsonb))
    into v_out;
  -- a dry run is the caller's ROLLBACK (tools/migrate_sheet.py)
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
