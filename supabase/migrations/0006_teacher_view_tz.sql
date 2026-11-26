-- teacher_view: the class's day is private.settings.tz, as for the points and the nightly roll-up, not a zone
-- written into the view (review of #80). locked_today and flags_week counted Jerusalem's day.
-- A new migration, not an edit of 0002: a project that already ran 0002 never runs it again (docs/LESSONS.md 16).
-- Same columns in the same order; `create or replace` keeps the view's grants (as 0004_auth.sql does for backend_health).
create or replace view public.teacher_view with (security_barrier = true) as
  select p.id as pupil_id, p.class_id, p.display_name,
         t.points, t.answers, t.first_try, t.wrong,
         case when t.answers > 0 then round(100.0 * t.wrong / t.answers)::int else 0 end as error_pct,
         lv.stars, lv.levels,
         app.safe_int(g.state -> 'k' -> 'words', 1000) as words,
         app.safe_int(g.state -> 'k' -> 'reads', 1000) as reads,
         app.safe_int(g.state -> 'streak', 1000) as streak,
         t.last_at,
         (select count(*)::int from private.auth_lock_events e
           where e.class_id = p.class_id and e.name_key = p.name_key
             and e.at >= (date_trunc('day', now() at time zone z.tz) at time zone z.tz)) as locked_today,
         case when s.code_hash is null then 'waiting' else 'set' end as code_status,
         case when b.locked_until = 'infinity' then 'closed' when b.locked_until > now() then 'locked' else 'open' end as recovery_status,
         b.locked_until as recovery_locked_until,
         (s.pic_hash is not null) as has_picture,
         (select coalesce(sum(f.n), 0)::int from public.flags f
           where f.pupil_id = p.id and f.day > (now() at time zone z.tz)::date - 7) as flags_week
  from public.pupils p
  cross join (select tz from private.settings) z      -- the class's day: settings.tz, as the points and the roll-up
  join public.pupil_totals t on t.pupil_id = p.id
  left join public.progress g on g.pupil_id = p.id
  left join private.pupil_secrets s on s.pupil_id = p.id
  left join private.auth_buckets b on b.class_id = p.class_id and b.name_key = p.name_key and b.kind = 'picture' and b.bucket = '*'
  cross join lateral (
    select coalesce(sum(lb.stars), 0)::int as stars, count(*) filter (where lb.stars > 0)::int as levels
    from public.level_best lb where lb.pupil_id = p.id
  ) lv
  where app.teaches(p.class_id);
