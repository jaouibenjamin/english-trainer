-- Points and the board, decided in the database (docs/BACKEND.md section 5).
-- The browser reports what happened; these functions decide what it is worth. Each derives the pupil from the
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

/* rows: [{game, item_key, skill, correct, first_try, t}], t = the client's clock in ms (optional).
   Returns {ok, points (the pupil's new total), added, flagged, dup}. */
create function public.record_answers(p_batch uuid, p_rows jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_pupil uuid := app.pupil_id();
  s   private.settings;
  tot public.pupil_totals;
  d   private.pupil_days;
  r   jsonb;
  v_now timestamptz := clock_timestamp();
  v_at timestamptz; v_day date; v_ms numeric;
  v_game text; v_key text; v_skill text; v_ok boolean; v_first boolean;
  v_item int; v_pts int; v_flag int; v_new boolean; n int;
  added int := 0; flagged int := 0; gained int := 0;
begin
  if v_pupil is null then raise exception 'not a pupil' using errcode = '42501'; end if;
  select * into s from private.settings;
  if p_batch is null or p_rows is null or jsonb_typeof(p_rows) <> 'array' or jsonb_array_length(p_rows) > s.max_batch then
    raise exception 'bad input' using errcode = '22023';
  end if;
  -- one writer per pupil at a time: two devices, or a retry racing the first try, cannot lose or double an update
  select * into tot from public.pupil_totals where pupil_id = v_pupil for update;
  insert into private.answer_batches (pupil_id, batch_id) values (v_pupil, p_batch) on conflict do nothing;
  if not found then return jsonb_build_object('ok', true, 'dup', true, 'points', tot.points, 'added', 0, 'flagged', 0); end if;

  for r in select e.value from jsonb_array_elements(p_rows) with ordinality e(value, i) order by e.i loop
    -- the time of the answer: the client's clock, but never in the future, never older than the back-fill window,
    -- never before this pupil's previous answer
    v_ms := case when jsonb_typeof(r -> 't') = 'number' then (r ->> 't')::numeric end;
    v_at := case when v_ms between 0 and 1e14 then to_timestamp((v_ms / 1000.0)::double precision) else v_now end;
    v_at := least(v_now, greatest(v_at, v_now - make_interval(hours => s.backfill_hours), coalesce(tot.last_at, '-infinity')));
    v_day := (v_at at time zone s.tz)::date;
    d := private.day_row(v_pupil, v_day);

    v_game := r ->> 'game'; v_key := r ->> 'item_key'; v_skill := coalesce(r ->> 'skill', '');
    if jsonb_typeof(r) <> 'object' or v_game is null or v_key is null or v_game !~ '^[a-z0-9_]{1,16}$'
       or char_length(v_key) not between 1 and 64 or v_key ~ '[\u0001-\u001f]' then
      perform private.flag_add(v_pupil, 'items', v_day); flagged := flagged + 1; continue;
    end if;
    if v_skill !~ '^[a-z0-9_-]{0,24}$' then v_skill := ''; end if;
    v_ok := (r -> 'correct') = 'true'::jsonb;
    v_first := (r -> 'first_try') = 'true'::jsonb;

    select id into v_item from public.items where game = v_game and item_key = v_key;
    if v_item is null then
      if d.new_items >= s.max_new_items then
        perform private.flag_add(v_pupil, 'items', v_day); flagged := flagged + 1; continue;
      end if;
      insert into public.items (game, item_key, skill) values (v_game, v_key, v_skill) on conflict (game, item_key) do nothing;
      select id into v_item from public.items where game = v_game and item_key = v_key;
      update private.pupil_days set new_items = new_items + 1 where pupil_id = v_pupil and day = v_day;
    end if;

    v_pts := case when v_ok and v_first then s.pts_first when v_ok then s.pts_later else 0 end;
    v_flag := 0;
    select count(*) into n from public.answers where pupil_id = v_pupil and at > v_at - interval '1 minute' and at <= v_at;
    if n >= s.max_per_minute then
      v_flag := 1;
    elsif v_pts > 0 and d.pointed >= s.max_pointed_day then
      v_flag := 2;
    elsif v_pts > 0 then
      select count(*) into n from public.answers
       where pupil_id = v_pupil and item_id = v_item and pts > 0
         and at >= (v_day::timestamp at time zone s.tz) and at < ((v_day + 1)::timestamp at time zone s.tz);
      if n >= s.max_item_day then v_flag := 3; end if;
    end if;
    if v_flag > 0 then
      v_pts := 0; flagged := flagged + 1;
      perform private.flag_add(v_pupil, (array['rate', 'daycap', 'repeat'])[v_flag], v_day);
    end if;

    insert into public.answers (at, pupil_id, item_id, pts, flag, correct, first_try)
      values (v_at, v_pupil, v_item, v_pts, v_flag, v_ok, v_first);
    added := added + 1; gained := gained + v_pts;
    tot.answers := tot.answers + 1;
    if v_ok and v_first then tot.first_try := tot.first_try + 1; else tot.wrong := tot.wrong + 1; end if;
    tot.last_at := v_at;
    if v_pts > 0 then
      update private.pupil_days set pointed = pointed + 1 where pupil_id = v_pupil and day = v_day;
      gained := gained + private.day_bonus(v_pupil, v_day, v_at, s.pts_day);
    end if;
  end loop;

  if added > 0 then
    select count(distinct date_trunc('hour', at)) into n from public.answers where pupil_id = v_pupil and at > v_now - interval '24 hours';
    if n >= s.marathon_hours then perform private.flag_add(v_pupil, 'marathon', (v_now at time zone s.tz)::date); end if;
  end if;

  update public.pupil_totals set points = points + gained, answers = tot.answers, first_try = tot.first_try,
         wrong = tot.wrong, last_at = tot.last_at where pupil_id = v_pupil;
  return jsonb_build_object('ok', true, 'points', tot.points + gained, 'added', added, 'flagged', flagged);
end $$;

/* a level finished with 0 to 3 stars. Returns {ok, points, gained}. */
create function public.record_level(p_game text, p_level text, p_stars int) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_pupil uuid := app.pupil_id();
  s private.settings; tot public.pupil_totals; d private.pupil_days;
  v_now timestamptz := clock_timestamp(); v_day date; gained int := 0;
begin
  if v_pupil is null then raise exception 'not a pupil' using errcode = '42501'; end if;
  if p_game is null or p_game !~ '^[a-z0-9_]{1,16}$' or p_level is null or char_length(p_level) not between 1 and 60
     or p_level ~ '[\u0001-\u001f]' or p_stars is null or p_stars not between 0 and 3 then
    raise exception 'bad input' using errcode = '22023';
  end if;
  select * into s from private.settings;
  select * into tot from public.pupil_totals where pupil_id = v_pupil for update;
  v_day := (v_now at time zone s.tz)::date;
  d := private.day_row(v_pupil, v_day);
  if p_stars > 0 then
    if d.levels >= s.max_levels_day then
      perform private.flag_add(v_pupil, 'levels', v_day);
    else
      gained := p_stars * s.pts_star;
      insert into public.points (pupil_id, delta, reason, ref, at) values (v_pupil, gained, 'stars', p_game || ':' || p_level, v_now);
      update private.pupil_days set levels = levels + 1 where pupil_id = v_pupil and day = v_day;
      gained := gained + private.day_bonus(v_pupil, v_day, v_now, s.pts_day);
      update public.pupil_totals set points = points + gained where pupil_id = v_pupil;
    end if;
  end if;
  return jsonb_build_object('ok', true, 'points', tot.points + gained, 'gained', gained);
end $$;

/* the transitional blob. The caller's own row only; the size and shape are checked by the table. */
create function public.save_progress(p_state jsonb) returns timestamptz
language plpgsql security definer set search_path = '' as $$
declare v_pupil uuid := app.pupil_id(); v_at timestamptz := clock_timestamp();
begin
  if v_pupil is null then raise exception 'not a pupil' using errcode = '42501'; end if;
  if p_state is null or jsonb_typeof(p_state) <> 'object' or char_length(p_state::text) > 40000 then
    raise exception 'bad input' using errcode = '22023';
  end if;
  insert into public.progress (pupil_id, state, updated_at) values (v_pupil, p_state, v_at)
  on conflict (pupil_id) do update set state = excluded.state, updated_at = excluded.updated_at;
  return v_at;
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
  delete from public.pupils where id = p.id;
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

/* Housekeeping, also the keep-alive query (.github/workflows/keepalive.yml). Server role only.
   Rolls answers older than the raw window into answer_daily and deletes what has a short life by design. */
create function public.maintenance() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; v_cut timestamptz; rolled int; bad int;
begin
  select * into s from private.settings;
  v_cut := ((now() at time zone s.tz)::date - s.raw_days)::timestamp at time zone s.tz;
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
  delete from private.answer_batches   where at < now() - interval '7 days';
  delete from private.pupil_days       where day < (now() at time zone s.tz)::date - 30;
  delete from private.ip_salts         where day < (now() at time zone 'utc')::date - 2;
  delete from private.reset_codes      where expires_at < now() - interval '7 days';
  select count(*) into bad from private.totals_check();
  return jsonb_build_object('ok', bad = 0, 'rolled', rolled, 'totals_wrong', bad,
                            'db_mb', (pg_database_size(current_database()) / 1048576)::int);
end $$;

revoke all on all functions in schema public, private from public, anon, authenticated;
grant execute on function public.record_answers(uuid, jsonb), public.record_level(text, text, int),
                          public.save_progress(jsonb), public.teacher_delete_pupil(uuid) to authenticated;
grant execute on all functions in schema public, private to service_role;
