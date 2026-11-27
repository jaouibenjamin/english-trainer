-- The grade board sends only what the screen shows (review of the board, after #128). 0010's grade_board() sent up
-- to 1,000 rows (every pupil of the grade: name with the surname letter, class, points) to every pupil's device, and
-- only the screen cut it to the top 10 and the pupil's own row: the rest could be read in the browser's console.
-- Now the server cuts: the top 10 of the grade, plus the caller's own row when it is not among them. Append-only:
-- 0010 is not edited.
--
-- The answer, ordered by place: at most 11 rows of (display_name, class, points, me, rank).
--   rank: 1 + the number of pupils of the grade with more points (ties share a rank: 1, 2, 2, 4).
--   The top 10 are picked by points, then name, then an id nobody sees, so ties never make it longer than 10.
--   A teacher has no own row: she gets the top 10.
-- The size of the grade is never sent: rank says how many have more points than the caller, nothing more.
drop function public.grade_board();
create function public.grade_board() returns table (display_name text, class text, points int, me boolean, rank int)
language sql stable security definer set search_path = '' as $$
  with mine as (
    select c.grade_id from public.classes c where c.id = app.reads_class() and c.kind = 'class'
    union
    select c.grade_id from public.classes c join public.teachers t on t.class_id = c.id where t.user_id = auth.uid() and c.kind = 'class'
  ),
  grade as (
    select p.display_name, c.name as class, t.points, (p.auth_user_id is not distinct from auth.uid()) as me,
           rank() over (order by t.points desc)::int as rank,
           row_number() over (order by t.points desc, p.display_name, p.id) as place
    from public.pupils p
    join public.classes c on c.id = p.class_id
    join public.pupil_totals t on t.pupil_id = p.id
    where auth.uid() is not null and c.kind = 'class' and c.grade_id is not null
      and c.grade_id in (select grade_id from mine where grade_id is not null)
  )
  select g.display_name, g.class, g.points, g.me, g.rank
  from grade g
  where g.place <= 10 or g.me
  order by g.place $$;

revoke all on function public.grade_board() from public, anon;
grant execute on function public.grade_board() to authenticated;
