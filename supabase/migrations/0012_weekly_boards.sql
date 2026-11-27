-- Weekly boards (owner's decision, 2026-11-27; docs/GRADES_V1.md "Weekly boards"). Append-only: 0001 to 0011 are not
-- edited. Both boards rank this week's points: the sum of the points ledger (public.points) since Sunday 00:00 in
-- settings.tz. No new column or counter: the ledger is what pupil_totals already adds up. Left out of the week:
-- 'migrated' rows (a one-off import) and the nightly roll-up's merged rows (reason 'day' or 'run', ref 'rolled'),
-- which carry the time of the last row they merged; with raw_days at 8 or more (30 today) the roll-up never reaches
-- into the week, so the week is exact. A point counts in the week it reached the server (at is the server's time).
-- The pupil's all-time total is unchanged: pupil_totals.points and class_board.points.

-- Sunday 00:00 of the week holding p_now, in the class's zone (summer time changes nothing: a local midnight).
create function app.week_start(p_now timestamptz) returns timestamptz
language sql stable security definer set search_path = '' as $$
  select ((x.d - (extract(isodow from x.d)::int % 7))::timestamp at time zone s.tz)
  from private.settings s, lateral (select (p_now at time zone s.tz)::date as d) x $$;

-- A pupil's points this week (the rows above; one index makes it a short range read).
create function app.week_points(p_pupil uuid, p_from timestamptz) returns int
language sql stable security definer set search_path = '' as $$
  select coalesce(sum(x.delta), 0)::int from public.points x
  where x.pupil_id = p_pupil and x.at >= p_from and x.reason <> 'migrated' and not (x.reason in ('day', 'run') and x.ref = 'rolled') $$;
create index points_pupil_at on public.points (pupil_id, at);

-- The grade board: as 0011 (at most 11 rows in place order, the top 10 then the caller's own row, rank, no ids, not
-- the grade's size), ranked by the week. Only pupils with points this week are in the top 10 (on Sunday morning it
-- is empty, not ten names in alphabetical order); the caller's own row always comes, with week 0 if so. The column
-- is named week, not points, on purpose: a client still asking for points gets an error, never an all-time number.
drop function public.grade_board();
create function public.grade_board() returns table (display_name text, class text, week int, me boolean, rank int)
language sql stable security definer set search_path = '' as $$
  with mine as (
    select c.grade_id from public.classes c where c.id = app.reads_class() and c.kind = 'class'
    union
    select c.grade_id from public.classes c join public.teachers t on t.class_id = c.id where t.user_id = auth.uid() and c.kind = 'class'
  ),
  grade as (
    select p.id, p.display_name, c.name as class, (p.auth_user_id is not distinct from auth.uid()) as me,
           app.week_points(p.id, app.week_start(now())) as week
    from public.pupils p
    join public.classes c on c.id = p.class_id
    where auth.uid() is not null and c.kind = 'class' and c.grade_id is not null
      and c.grade_id in (select grade_id from mine where grade_id is not null)
  ),
  ranked as (
    select g.*, rank() over (order by g.week desc)::int as rank,
           row_number() over (order by g.week desc, g.display_name, g.id) as place
    from grade g
  )
  select r.display_name, r.class, r.week, r.me, r.rank
  from ranked r
  where (r.place <= 10 and r.week > 0) or r.me
  order by r.place $$;

-- The class board: as 0004, plus a last column week. Its other columns stay, points (all-time) included, so the
-- client of today keeps working until it ranks by week. Still the pupil's own class only.
create or replace view public.class_board with (security_barrier = true) as
  select p.display_name,
         t.points,
         app.safe_int(g.state -> 'k' -> 'words', 1000) as words,     -- self-reported, shown only
         app.safe_int(g.state -> 'streak', 1000)       as streak,    -- self-reported, shown only
         (p.auth_user_id is not distinct from auth.uid()) as me,
         coalesce((select sum(x.delta) from public.points x      -- app.week_points written out: a view's functions run
                   where x.pupil_id = p.id and x.at >= app.week_start(now()) and x.reason <> 'migrated'   -- as the reader
                     and not (x.reason in ('day', 'run') and x.ref = 'rolled')), 0)::int as week
  from public.pupils p
  join public.pupil_totals t on t.pupil_id = p.id
  left join public.progress g on g.pupil_id = p.id
  where auth.uid() is not null
    and (p.class_id = app.reads_class() or app.teaches(p.class_id));

-- week_start says only when the week began, so the view's readers may call it; week_points takes any pupil's id, so
-- only the definer functions call it
revoke all on function app.week_start(timestamptz), app.week_points(uuid, timestamptz) from public, anon, authenticated;
grant execute on function app.week_start(timestamptz) to authenticated, service_role;
grant execute on function app.week_points(uuid, timestamptz) to service_role;
revoke all on function public.grade_board() from public, anon;
grant execute on function public.grade_board() to authenticated;
