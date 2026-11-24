-- Row level security, grants and views (docs/BACKEND.md section 2).
-- Supabase gives anon and authenticated every right on new objects in public by default and relies on RLS alone.
-- We do not: everything is revoked first and only what is listed here is granted back, so a table without a policy
-- and a table without a grant both read as "nothing".

-- who is calling. security definer: they must see the caller's own row without depending on the policies they serve.
create function app.pupil_id() returns uuid language sql stable security definer set search_path = '' as
  $$ select id from public.pupils where auth_user_id = auth.uid() $$;
create function app.class_id() returns uuid language sql stable security definer set search_path = '' as
  $$ select class_id from public.pupils where auth_user_id = auth.uid() $$;
create function app.teaches(c uuid) returns boolean language sql stable security definer set search_path = '' as
  $$ select exists (select 1 from public.teachers where user_id = auth.uid() and class_id = c) $$;
create function app.teaches_pupil(p uuid) returns boolean language sql stable security definer set search_path = '' as
  $$ select exists (select 1 from public.pupils pu join public.teachers t on t.class_id = pu.class_id
                    where pu.id = p and t.user_id = auth.uid()) $$;

-- a number out of the client's blob, never an error: anything that is not a number is 0
create function app.safe_int(v jsonb, hi int) returns int language sql immutable set search_path = '' as
  $$ select case when jsonb_typeof(v) = 'number' then least(greatest(floor((v #>> '{}')::numeric), 0), hi)::int else 0 end $$;
create function app.obj(v jsonb) returns jsonb language sql immutable set search_path = '' as
  $$ select case when jsonb_typeof(v) = 'object' then v else '{}'::jsonb end $$;

alter table public.classes      enable row level security;
alter table public.roster       enable row level security;
alter table public.teachers     enable row level security;
alter table public.pupils       enable row level security;
alter table public.items        enable row level security;
alter table public.levels       enable row level security;
alter table public.level_best   enable row level security;
alter table public.answers      enable row level security;
alter table public.points       enable row level security;
alter table public.pupil_totals enable row level security;
alter table public.progress     enable row level security;
alter table public.flags        enable row level security;
alter table public.answer_daily enable row level security;
-- private is closed by having no grant and no API route; RLS with no policy is the third lock
alter table private.class_codes      enable row level security;
alter table private.pupil_secrets    enable row level security;
alter table private.reset_codes      enable row level security;
alter table private.pupil_devices    enable row level security;
alter table private.legacy_import    enable row level security;
alter table private.auth_attempts    enable row level security;
alter table private.auth_buckets     enable row level security;
alter table private.auth_lock_events enable row level security;
alter table private.ip_salts         enable row level security;
alter table private.answer_batches   enable row level security;
alter table private.pupil_days       enable row level security;
alter table private.settings         enable row level security;
alter table private.deletions        enable row level security;

-- (select app.x()) is evaluated once per statement, not once per row
create policy classes_read on public.classes for select to authenticated
  using (id = (select app.class_id()) or app.teaches(id));

create policy roster_teacher on public.roster for all to authenticated
  using (app.teaches(class_id)) with check (app.teaches(class_id));

create policy teachers_self on public.teachers for select to authenticated
  using (user_id = (select auth.uid()));

create policy pupils_read on public.pupils for select to authenticated
  using (auth_user_id = (select auth.uid()) or app.teaches(class_id));

-- items, levels: no policy and no grant. The server reads them to price events; no browser needs them.

create policy answers_read on public.answers for select to authenticated
  using (pupil_id = (select app.pupil_id()) or app.teaches_pupil(pupil_id));
create policy points_read on public.points for select to authenticated
  using (pupil_id = (select app.pupil_id()) or app.teaches_pupil(pupil_id));
create policy totals_read on public.pupil_totals for select to authenticated
  using (pupil_id = (select app.pupil_id()) or app.teaches_pupil(pupil_id));
create policy daily_read on public.answer_daily for select to authenticated
  using (pupil_id = (select app.pupil_id()) or app.teaches_pupil(pupil_id));
create policy best_read on public.level_best for select to authenticated
  using (pupil_id = (select app.pupil_id()) or app.teaches_pupil(pupil_id));
create policy progress_read on public.progress for select to authenticated
  using (pupil_id = (select app.pupil_id()) or app.teaches_pupil(pupil_id));

create policy flags_teacher on public.flags for select to authenticated
  using (app.teaches_pupil(pupil_id));

-- ---------------------------------------------------------------- views
-- These must show rows the table policies hide (classmates on the board, the lock tables), so they run with their
-- owner's rights and carry the rule themselves. Only the listed columns leave. security_barrier: a caller's own
-- function in a WHERE cannot be run on rows the view filters out.

create view public.class_board with (security_barrier = true) as
  select p.display_name,
         t.points,
         app.safe_int(g.state -> 'k' -> 'words', 1000) as words,     -- self-reported, shown only
         app.safe_int(g.state -> 'streak', 1000)       as streak,    -- self-reported, shown only
         (p.auth_user_id is not distinct from auth.uid()) as me
  from public.pupils p
  join public.pupil_totals t on t.pupil_id = p.id
  left join public.progress g on g.pupil_id = p.id
  where auth.uid() is not null
    and (p.class_id = app.class_id() or app.teaches(p.class_id));

create view public.teacher_view with (security_barrier = true) as
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
             and e.at >= (date_trunc('day', now() at time zone 'Asia/Jerusalem') at time zone 'Asia/Jerusalem')) as locked_today,
         case when s.code_hash is null then 'waiting' else 'set' end as code_status,
         case when b.locked_until = 'infinity' then 'closed' when b.locked_until > now() then 'locked' else 'open' end as recovery_status,
         b.locked_until as recovery_locked_until,
         (s.pic_hash is not null) as has_picture,
         (select coalesce(sum(f.n), 0)::int from public.flags f
           where f.pupil_id = p.id and f.day > (now() at time zone 'Asia/Jerusalem')::date - 7) as flags_week
  from public.pupils p
  join public.pupil_totals t on t.pupil_id = p.id
  left join public.progress g on g.pupil_id = p.id
  left join private.pupil_secrets s on s.pupil_id = p.id
  left join private.auth_buckets b on b.class_id = p.class_id and b.name_key = p.name_key and b.kind = 'picture' and b.bucket = '*'
  cross join lateral (
    select coalesce(sum(lb.stars), 0)::int as stars, count(*) filter (where lb.stars > 0)::int as levels
    from public.level_best lb where lb.pupil_id = p.id
  ) lv
  where app.teaches(p.class_id);

-- the class's weak items: at least 3 tries and at least one wrong, raw rows and the roll-up together
create view public.teacher_items with (security_barrier = true) as
  select x.class_id, i.game, i.item_key, i.skill,
         sum(x.tries)::int as tries, sum(x.wrong)::int as wrong,
         round(100.0 * sum(x.wrong) / sum(x.tries))::int as error_pct
  from (
    select p.class_id, a.item_id, 1 as tries, (not (a.correct and a.first_try))::int as wrong
      from public.answers a join public.pupils p on p.id = a.pupil_id where app.teaches(p.class_id)
    union all
    select p.class_id, d.item_id, d.tries, d.tries - d.first_try
      from public.answer_daily d join public.pupils p on p.id = d.pupil_id where app.teaches(p.class_id)
  ) x join public.items i on i.id = x.item_id
  group by x.class_id, i.id
  having sum(x.tries) >= 3 and sum(x.wrong) > 0;

-- ---------------------------------------------------------------- grants: nothing, then the list
revoke all on schema private from public, anon, authenticated;
revoke all on all tables    in schema public, private, app from public, anon, authenticated;
revoke all on all sequences in schema public, private, app from public, anon, authenticated;
revoke all on all functions in schema public, private, app from public, anon, authenticated;
alter default privileges in schema public, private, app revoke all on tables    from public, anon, authenticated;
alter default privileges in schema public, private, app revoke all on sequences from public, anon, authenticated;
alter default privileges in schema public, private, app revoke execute on functions from public, anon, authenticated;
alter default privileges revoke execute on functions from public;

-- the keep-alive: the one thing a visitor without a session may run. It reads nothing.
create function public.ping() returns boolean language sql immutable set search_path = '' as $$ select true $$;
grant execute on function public.ping() to anon, authenticated;

grant usage on schema app to authenticated;
grant execute on function app.pupil_id(), app.class_id(), app.teaches(uuid), app.teaches_pupil(uuid),
                          app.safe_int(jsonb, int), app.obj(jsonb), app.name_key(text), app.name_ok(text) to authenticated;

grant select on public.classes, public.teachers, public.pupils, public.answers, public.points,
                public.pupil_totals, public.progress, public.flags, public.answer_daily, public.level_best,
                public.class_board, public.teacher_view, public.teacher_items to authenticated;
grant select, insert, delete on public.roster to authenticated;

-- the server role (Edge Functions, the migration tool, the keep-alive job): everything, RLS does not apply to it
grant usage on schema app, private to service_role;
grant all on all tables    in schema public, private to service_role;
grant all on all sequences in schema public, private to service_role;
grant execute on all functions in schema app to service_role;
alter default privileges in schema public, private grant all on tables    to service_role;
alter default privileges in schema public, private grant all on sequences to service_role;
alter default privileges in schema public, private, app grant execute on functions to service_role;
