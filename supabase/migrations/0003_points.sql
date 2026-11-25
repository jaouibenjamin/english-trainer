-- Points and the board, decided in the database (docs/BACKEND.md section 5).
-- The browser reports typed events; these functions decide what they are worth. Each derives the pupil from the
-- session (auth.uid()); none takes a pupil id.

create function private.flag_add(p_pupil uuid, p_kind text, p_day date) returns void
language sql security definer set search_path = '' as $$
  insert into public.flags (pupil_id, kind, day) values (p_pupil, p_kind, p_day)
  on conflict (pupil_id, kind, day) do update set n = public.flags.n + 1
$$;

-- the counters of one pupil-day, created on first use
create function private.day_row(p_pupil uuid, p_day date) returns private.pupil_days
language plpgsql security definer set search_path = '' as $$
declare d private.pupil_days;
begin
  insert into private.pupil_days (pupil_id, day) values (p_pupil, p_day) on conflict do nothing;
  select * into d from private.pupil_days where pupil_id = p_pupil and day = p_day;
  return d;
end $$;

-- the first points of a day (Israel time) bring the daily bonus
create function private.day_bonus(p_pupil uuid, p_day date, p_at timestamptz, p_pts int) returns int
language plpgsql security definer set search_path = '' as $$
begin
  update private.pupil_days set bonus = true where pupil_id = p_pupil and day = p_day and not bonus;
  if not found then return 0; end if;
  insert into public.points (pupil_id, delta, reason, ref, at) values (p_pupil, p_pts, 'day', p_day::text, p_at);
  return p_pts;
end $$;

-- a non-negative whole number out of an event, or null
create function private.ev_int(v jsonb) returns int language sql immutable set search_path = '' as
  $$ select case when jsonb_typeof(v) = 'number' and (v #>> '{}') ~ '^[0-9]{1,6}$' then (v #>> '{}')::int end $$;

/* Typed events, priced here (docs/BACKEND.md section 5). events: a JSON array of
     {type:'answer', game, item, correct, first_try, t}     t = the client's clock in ms (optional)
     {type:'level',  game, level, stars}
     {type:'read',   text}
     {type:'exam',   paper, right}
     {type:'run',    points}
   Anything else in an event is ignored: there is no field that carries points, a pupil or a flag.
   Returns {ok, points (the pupil's new total), added, flagged, dup}. */
create function public.record_events(p_batch uuid, p_events jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_pupil uuid := app.pupil_id();
  s   private.settings;
  tot public.pupil_totals;
  d   private.pupil_days;      -- the day the event belongs to
  a   private.pupil_days;      -- the day it reached the server
  r   jsonb;
  v_now timestamptz := clock_timestamp();
  v_today date; v_at timestamptz; v_day date; v_ms numeric;
  v_type text; v_game text; v_key text; v_ok boolean; v_first boolean;
  v_item int; v_pts int; v_flag int; n int; v_size int; v_old int;
  added int := 0; flagged int := 0; gained int := 0;
begin
  if v_pupil is null then raise exception 'not a pupil' using errcode = '42501'; end if;
  select * into s from private.settings;
  if p_batch is null or p_events is null or jsonb_typeof(p_events) <> 'array' or jsonb_array_length(p_events) > s.max_batch
     or pg_column_size(p_events) > 65536 then
    raise exception 'bad input' using errcode = '22023';
  end if;
  -- one writer per pupil at a time: two devices, or a retry racing the first try, cannot lose or double an update
  select * into tot from public.pupil_totals where pupil_id = v_pupil for update;
  v_today := (v_now at time zone s.tz)::date;
  -- Storage is finite (500 MB for everybody). A pupil's device may call this so many times a day and add so many
  -- answer rows a day; beyond that nothing is written but one counter, so a console loop cannot fill the database.
  a := private.day_row(v_pupil, v_today);
  update private.pupil_days set calls = calls + 1 where pupil_id = v_pupil and day = v_today;
  if s.storage_brake then      -- checked first: past the day's calls the brake must still say so (review of #35)
    -- the database is near the free plan's size: nothing is written until the owner acts. Not a silent loss (review
    -- S4): the answer says so, and the device keeps the batch and sends it again later with the same id.
    perform private.flag_add(v_pupil, 'storage', v_today);
    return jsonb_build_object('ok', false, 'e', 'brake', 'points', tot.points);
  end if;
  if a.calls >= s.max_calls_day or a.batches >= s.max_batches_day then
    perform private.flag_add(v_pupil, 'daycap', v_today);
    return jsonb_build_object('ok', true, 'capped', true, 'points', tot.points, 'added', 0, 'flagged', jsonb_array_length(p_events));
  end if;
  if jsonb_array_length(p_events) = 0 then      -- nothing to do, nothing to remember
    return jsonb_build_object('ok', true, 'points', tot.points, 'added', 0, 'flagged', 0);
  end if;
  insert into private.answer_batches (pupil_id, batch_id) values (v_pupil, p_batch) on conflict do nothing;
  if not found then return jsonb_build_object('ok', true, 'dup', true, 'points', tot.points, 'added', 0, 'flagged', 0); end if;

  for r in select e.value from jsonb_array_elements(p_events) with ordinality e(value, i) order by e.i loop
    v_type := case when jsonb_typeof(r) = 'object' then r ->> 'type' end;
    v_game := r ->> 'game';
    a := private.day_row(v_pupil, v_today);

    if v_type = 'answer' then
      -- the time of the answer: the client's clock, but never in the future and never older than the back-fill
      -- window. (It is not forced after the pupil's previous answer: a phone that was offline may deliver an hour
      -- that lies before what the laptop sent since, and that is honest play.)
      v_ms := case when jsonb_typeof(r -> 't') = 'number' then (r ->> 't')::numeric end;
      v_at := case when v_ms between 0 and 1e14 then to_timestamp((v_ms / 1000.0)::double precision) else v_now end;
      v_at := least(v_now, greatest(v_at, v_now - make_interval(hours => s.backfill_hours)));
      v_day := (v_at at time zone s.tz)::date;
      d := private.day_row(v_pupil, v_day);
      select id into v_item from public.items where game = v_game and item_key = r ->> 'item';
      if v_item is null then      -- not in the catalogue: nothing is stored
        perform private.flag_add(v_pupil, 'items', v_today); flagged := flagged + 1; continue;
      end if;
      if a.stored >= s.max_rows_day then      -- the day's rows are used up: count it, write nothing
        perform private.flag_add(v_pupil, 'daycap', v_today); flagged := flagged + 1; continue;
      end if;
      update private.pupil_days set stored = stored + 1 where pupil_id = v_pupil and day = v_today;
      v_ok := (r -> 'correct') = 'true'::jsonb;
      v_first := (r -> 'first_try') = 'true'::jsonb;
      v_pts := case when v_ok and v_first then s.pts_first when v_ok then s.pts_later else 0 end;
      v_flag := 0;
      select count(*) into n from public.answers where pupil_id = v_pupil and at > v_at - interval '1 minute' and at <= v_at;
      if n >= s.max_per_minute then
        v_flag := 1;
      elsif v_pts > 0 and (d.pointed >= s.max_pointed_day or a.arrived >= s.max_pointed_day) then
        v_flag := 2;       -- by the day the answer claims, and by the day it arrived: back-dating buys nothing
      elsif v_pts > 0 then
        select count(*) into n from public.answers
         where pupil_id = v_pupil and item_id = v_item and pts > 0
           and at >= (v_day::timestamp at time zone s.tz) and at < ((v_day + 1)::timestamp at time zone s.tz);
        if n >= s.max_item_day then v_flag := 3; end if;
      end if;
      if v_flag > 0 then
        v_pts := 0; flagged := flagged + 1;
        perform private.flag_add(v_pupil, (array['rate', 'daycap', 'repeat'])[v_flag], v_today);
      end if;
      insert into public.answers (at, pupil_id, item_id, pts, flag, correct, first_try)
        values (v_at, v_pupil, v_item, v_pts, v_flag, v_ok, v_first);
      added := added + 1; gained := gained + v_pts;
      tot.answers := tot.answers + 1;
      if v_ok and v_first then tot.first_try := tot.first_try + 1; else tot.wrong := tot.wrong + 1; end if;
      tot.last_at := greatest(coalesce(tot.last_at, v_at), v_at);
      if v_pts > 0 then
        update private.pupil_days set pointed = pointed + 1 where pupil_id = v_pupil and day = v_day;
        update private.pupil_days set arrived = arrived + 1 where pupil_id = v_pupil and day = v_today;
        if a.arrived + 1 = s.unusual_answers then perform private.flag_add(v_pupil, 'unusual', v_today); end if;
        gained := gained + private.day_bonus(v_pupil, v_today, v_now, s.pts_day);     -- by the day it arrived: back-dating collects no extra bonus
      end if;

    elsif v_type = 'level' then
      v_key := r ->> 'level'; n := private.ev_int(r -> 'stars');
      if n is null or n > 3 or not exists (select 1 from public.levels where game = v_game and level_key = v_key and game not in ('read', 'exam')) then
        perform private.flag_add(v_pupil, 'items', v_today); flagged := flagged + 1; continue;
      end if;
      added := added + 1;
      if n = 0 then continue; end if;
      insert into public.level_best as b (pupil_id, game, level_key, stars, at) values (v_pupil, v_game, v_key, n, v_now)
        on conflict (pupil_id, game, level_key) do update set stars = greatest(b.stars, excluded.stars), at = excluded.at;
      if a.levels >= s.max_levels_day then
        perform private.flag_add(v_pupil, 'levels', v_today); flagged := flagged + 1; continue;
      end if;
      insert into public.points (pupil_id, delta, reason, ref, at) values (v_pupil, n * s.pts_star, 'stars', v_game || ':' || v_key, v_now);
      update private.pupil_days set levels = levels + 1 where pupil_id = v_pupil and day = v_today;
      if a.levels + 1 = s.unusual_levels then perform private.flag_add(v_pupil, 'unusual', v_today); end if;
      gained := gained + n * s.pts_star + private.day_bonus(v_pupil, v_today, v_now, s.pts_day);

    elsif v_type = 'read' then
      v_key := r ->> 'text';
      if not exists (select 1 from public.levels where game = 'read' and level_key = v_key) then
        perform private.flag_add(v_pupil, 'items', v_today); flagged := flagged + 1; continue;
      end if;
      added := added + 1;
      -- a perfect text pays once, ever; a repeat is normal play, not a flag
      if exists (select 1 from public.points where pupil_id = v_pupil and reason = 'read' and ref = v_key) then continue; end if;
      insert into public.points (pupil_id, delta, reason, ref, at) values (v_pupil, s.pts_read, 'read', v_key, v_now);
      gained := gained + s.pts_read + private.day_bonus(v_pupil, v_today, v_now, s.pts_day);

    elsif v_type = 'exam' then
      v_key := r ->> 'paper'; n := private.ev_int(r -> 'right');
      select size into v_size from public.levels where game = 'exam' and level_key = v_key;
      if v_size is null or n is null or n > v_size then
        perform private.flag_add(v_pupil, 'items', v_today); flagged := flagged + 1; continue;
      end if;
      added := added + 1;
      if a.exams >= s.max_exams_day then
        perform private.flag_add(v_pupil, 'bonus', v_today); flagged := flagged + 1; continue;
      end if;
      update private.pupil_days set exams = exams + 1 where pupil_id = v_pupil and day = v_today;
      if n > 0 then
        insert into public.points (pupil_id, delta, reason, ref, at) values (v_pupil, n * s.pts_exam_right, 'exam', v_key, v_now);
        gained := gained + n * s.pts_exam_right + private.day_bonus(v_pupil, v_today, v_now, s.pts_day);
      end if;

    elsif v_type = 'run' then
      n := private.ev_int(r -> 'points');
      if n is null or n = 0 or n > s.max_run_day then
        perform private.flag_add(v_pupil, 'bonus', v_today); flagged := flagged + 1; continue;
      end if;
      added := added + 1;
      n := least(n, s.max_run_day - a.run_pts);      -- the game's own daily cap, enforced here
      if n <= 0 then perform private.flag_add(v_pupil, 'bonus', v_today); flagged := flagged + 1; continue; end if;
      update private.pupil_days set run_pts = run_pts + n where pupil_id = v_pupil and day = v_today;
      -- one row per pupil and day, grown in place: a stream of small runs adds no rows
      update public.points set delta = delta + n, at = v_now where pupil_id = v_pupil and reason = 'run' and ref = v_today::text;
      if not found then
        insert into public.points (pupil_id, delta, reason, ref, at) values (v_pupil, n, 'run', v_today::text, v_now);
      end if;
      gained := gained + n + private.day_bonus(v_pupil, v_today, v_now, s.pts_day);

    else
      perform private.flag_add(v_pupil, 'items', v_today); flagged := flagged + 1;
    end if;
  end loop;

  if added = 0 then delete from private.answer_batches where pupil_id = v_pupil and batch_id = p_batch;
  else update private.pupil_days set batches = batches + 1 where pupil_id = v_pupil and day = v_today;
  end if;
  if added > 0 then
    select count(distinct date_trunc('hour', at)) into n from public.answers where pupil_id = v_pupil and at > v_now - interval '24 hours';
    if n >= s.marathon_hours then perform private.flag_add(v_pupil, 'marathon', v_today); end if;
  end if;

  update public.pupil_totals set points = points + gained, answers = tot.answers, first_try = tot.first_try,
         wrong = tot.wrong, last_at = tot.last_at where pupil_id = v_pupil;
  return jsonb_build_object('ok', true, 'points', tot.points + gained, 'added', added, 'flagged', flagged);
end $$;

/* The transitional blob; the caller's own row only. Two devices: when the row changed since p_base (the updated_at
   the device last saw), nothing is written and the current row comes back; the client joins the two with its own
   merge() and saves again. p_base null = the device has never seen the row (first save after registration).
   Storage (review PB1b): each write leaves a dead 40 KB row version behind until vacuum, so writes are rationed per
   pupil: none when the blob is unchanged, at least save_gap_s apart, at most max_saves_day writes and max_save_kb_day
   a day (Israel time).
   A refused save loses nothing: the device keeps its progress and the next save carries all of it.
   Returns {ok, updated_at[, unchanged]} or {ok: false, conflict: true, state, updated_at}
        or {ok: false, e: 'wait' | 'daycap', retry_after: seconds}. */
create function public.save_progress(p_state jsonb, p_base timestamptz default null) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_pupil uuid := app.pupil_id(); v_at timestamptz := clock_timestamp(); g public.progress; s private.settings;
  a private.pupil_days; v_today date; v_kb int := ceil(octet_length(p_state::text) / 1024.0)::int;
begin
  if v_pupil is null then raise exception 'not a pupil' using errcode = '42501'; end if;
  if p_state is null or jsonb_typeof(p_state) <> 'object' or char_length(p_state::text) > 40000 then
    raise exception 'bad input' using errcode = '22023';
  end if;
  select * into g from public.progress where pupil_id = v_pupil for update;      -- one save per pupil at a time
  if g.pupil_id is not null and g.state <> '{}'::jsonb and (p_base is null or g.updated_at <> p_base) then
    return jsonb_build_object('ok', false, 'conflict', true, 'state', g.state, 'updated_at', g.updated_at);
  end if;
  if g.pupil_id is not null and g.state = p_state then      -- nothing new: nothing written, nothing counted
    return jsonb_build_object('ok', true, 'updated_at', g.updated_at, 'unchanged', true);
  end if;
  select * into s from private.settings;
  v_today := (v_at at time zone s.tz)::date;
  a := private.day_row(v_pupil, v_today);
  if a.saves >= s.max_saves_day or a.save_kb + v_kb > s.max_save_kb_day then
    if a.saves <= s.max_saves_day then      -- flag once a day
      perform private.flag_add(v_pupil, 'saves', v_today);
      update private.pupil_days set saves = s.max_saves_day + 1 where pupil_id = v_pupil and day = v_today;
    end if;
    return jsonb_build_object('ok', false, 'e', 'daycap', 'retry_after',
      ceil(extract(epoch from ((v_today + 1)::timestamp at time zone s.tz) - v_at))::int);
  end if;
  if a.last_save_at is not null and a.last_save_at > v_at - make_interval(secs => s.save_gap_s) then
    return jsonb_build_object('ok', false, 'e', 'wait', 'retry_after',
      greatest(1, ceil(extract(epoch from a.last_save_at + make_interval(secs => s.save_gap_s) - v_at)))::int);
  end if;
  update private.pupil_days set saves = saves + 1, save_kb = save_kb + v_kb, last_save_at = v_at where pupil_id = v_pupil and day = v_today;
  insert into public.progress (pupil_id, state, updated_at) values (v_pupil, p_state, v_at)
  on conflict (pupil_id) do update set state = excluded.state, updated_at = excluded.updated_at;
  return jsonb_build_object('ok', true, 'updated_at', v_at);
end $$;

/* a teacher removes a pupil of her own class with everything that belongs to them (answers, points, progress,
   secrets, locks, and the auth user, which ends the sessions). */
create function public.teacher_delete_pupil(p_pupil uuid) returns boolean
language plpgsql security definer set search_path = '' as $$
declare p public.pupils;
begin
  select * into p from public.pupils where id = p_pupil;
  if p.id is null or not app.teaches(p.class_id) then raise exception 'not your pupil' using errcode = '42501'; end if;
  delete from private.auth_attempts    where class_id = p.class_id and name_key = p.name_key;
  delete from private.auth_buckets     where class_id = p.class_id and name_key = p.name_key;
  delete from private.auth_lock_events where class_id = p.class_id and name_key = p.name_key;
  insert into private.deletions (teacher, class_id, pupil_id, answers, points)
    select auth.uid(), p.class_id, p.id, t.answers, t.points from public.pupil_totals t where t.pupil_id = p.id;
  delete from public.pupils where id = p.id;      -- cascades to every table keyed by the pupil, public and private (tested table by table)
  if p.auth_user_id is not null then delete from auth.users where id = p.auth_user_id; end if;
  return true;
end $$;

/* pupil_totals recomputed from the ledgers; any row returned is a bug */
create function private.totals_check() returns table (pupil_id uuid, stored_points int, real_points bigint, stored_answers int, real_answers bigint)
language sql security definer set search_path = '' as $$
  select t.pupil_id, t.points, c.pts, t.answers, c.n
  from public.pupil_totals t
  cross join lateral (
    select coalesce((select sum(a.pts) from public.answers a where a.pupil_id = t.pupil_id), 0)
         + coalesce((select sum(d.pts) from public.answer_daily d where d.pupil_id = t.pupil_id), 0)
         + coalesce((select sum(p.delta) from public.points p where p.pupil_id = t.pupil_id), 0) as pts,
           coalesce((select count(*) from public.answers a where a.pupil_id = t.pupil_id), 0)
         + coalesce((select sum(d.tries) from public.answer_daily d where d.pupil_id = t.pupil_id), 0) as n
  ) c
  where t.points <> c.pts or t.answers <> c.n
$$;

/* Housekeeping. Server role only; run every night by pg_cron inside the database (scheduled at the end of this file),
   never from GitHub Actions, which has no server key. The keep-alive is ping(), with the public key.
   Rolls answers older than the raw window into answer_daily and deletes what has a short life by design. */
create function public.maintenance() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; v_cut timestamptz; rolled int; bad int; purged boolean := true; v_mb int; v_out jsonb;
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
  delete from private.teacher_resets   where at < now() - interval '2 days';
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
  select count(*) into bad from private.totals_check();
  v_mb := (pg_database_size(current_database()) / 1048576)::int;
  -- the storage brake (re-check of PR 12): near the free plan's 500 MB, events are counted but not stored, until
  -- the owner frees space or raises nothing (no paid plan): docs/BACKEND.md section 6
  update private.settings set storage_brake = (v_mb >= s.storage_brake_mb);
  v_out := jsonb_build_object('ok', bad = 0 and purged and v_mb < s.storage_brake_mb, 'rolled', rolled, 'totals_wrong', bad,
                              'audit_purged', purged, 'db_mb', v_mb, 'storage_brake', v_mb >= s.storage_brake_mb);
  insert into private.maintenance_log (result) values (v_out);
  return v_out;
end $$;

revoke all on all functions in schema public, private from public, anon, authenticated;
grant execute on function public.record_events(uuid, jsonb), public.save_progress(jsonb, timestamptz),
                          public.teacher_delete_pupil(uuid) to authenticated;
grant execute on function public.ping() to anon, authenticated;
grant execute on all functions in schema public, private to service_role;

-- every night at 02:17 UTC, inside the database. Where pg_cron is missing (the local test database) this is skipped
-- and said; on the project its presence is item 18 of "verify on a real project" (docs/BACKEND.md section 10).
do $$ begin
  create extension if not exists pg_cron;
  perform cron.schedule('wi-maintenance', '17 2 * * *', 'select public.maintenance()');
  raise notice 'maintenance is scheduled: every night at 02:17 UTC (cron job wi-maintenance)';
exception when others then raise notice 'maintenance is NOT scheduled: %', sqlerrm; end $$;
