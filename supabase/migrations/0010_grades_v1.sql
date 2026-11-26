-- Grade-ready v1 (docs/GRADES_V1.md). Append-only: nothing of 0001 to 0009 is edited (docs/LESSONS.md entry 16); what
-- changes is added or replaced here. The trial class made before this file keeps working as it is: no grade, names
-- without a surname letter (name_form 'first'), its code and roster untouched.

-- ---------- schools, grades, classes.grade_id / kind / name_form ----------
create table private.schools (
  id         uuid primary key default gen_random_uuid(),
  name       text not null check (char_length(name) between 1 and 60),
  created_at timestamptz not null default now()
);
create table private.grades (
  id          uuid primary key default gen_random_uuid(),
  school_id   uuid not null references private.schools on delete cascade,
  label       text not null check (char_length(label) between 1 and 20),     -- e.g. ה׳
  school_year int  not null check (school_year between 2020 and 2100),       -- the year the school year starts
  created_at  timestamptz not null default now(),
  unique (school_id, label, school_year)
);
alter table private.schools enable row level security;
alter table private.grades  enable row level security;

alter table public.classes
  add column grade_id  uuid references private.grades on delete set null,
  add column kind      text not null default 'class' check (kind in ('class', 'limbo')),
  -- 'first': a first name or nickname (the trial class, and every class made before this file);
  -- 'first_initial': a first name and one letter of the surname, "נועה כ." (the owner's decision of 2026-11-26)
  add column name_form text not null default 'first' check (name_form in ('first', 'first_initial'));
alter table public.classes alter column name_form set default 'first_initial';     -- classes made from now on
-- the classes that exist keep 'first'; the hidden "removed" classes of 0009 are marked
update public.classes c set kind = 'limbo', name_form = h.name_form, grade_id = h.grade_id
  from private.limbo l join public.classes h on h.id = l.class_id where c.id = l.limbo_id;
-- a class name names one class (add-teacher finds the class by it)
create unique index classes_name_one on public.classes (name) where kind = 'class';

-- a new hidden "removed" class (teacher_remove_pupil, 0009) is marked and takes its home class's grade and name form
create function private.limbo_mark() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  update public.classes c set kind = 'limbo', grade_id = h.grade_id, name_form = h.name_form
    from public.classes h where c.id = new.limbo_id and h.id = new.class_id;
  return new;
end $$;
create trigger limbo_mark after insert on private.limbo for each row execute function private.limbo_mark();

-- the school year a moment belongs to: it starts the day after settings.year_end (below)
alter table private.settings
  add column year_end        text not null default '08-31' check (year_end ~ '^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$'),
  add column year_end_delete boolean not null default true,       -- item history deleted when a school year ends
  add column daily_days      int not null default 120 check (daily_days between 30 and 3650),
  add column ip_class_hour          int not null default 120,     -- calls from one address for one class in an hour
  add column register_ip_class_hour int not null default 60;      -- registrations from one address for one class
-- one school address now carries a grade: the per-address ceilings rise, the per-(address, class) ones hold a class
update private.settings set ip_hour = 600 where ip_hour = 120;
update private.settings set register_ip_hour = 300 where register_ip_hour = 60;

create function private.year_start(p_now timestamptz) returns date language sql stable set search_path = '' as $$
  with s as (select year_end, tz from private.settings),
       d as (select (p_now at time zone s.tz)::date as today, s.year_end from s),
       e as (select today, make_date(extract(year from today)::int, split_part(year_end, '-', 1)::int, split_part(year_end, '-', 2)::int) as end_this from d)
  select case when today > end_this then end_this + 1 else (end_this - interval '1 year')::date + 1 end from e $$;

create function private.grade_for(p_label text, p_now timestamptz) returns uuid
language plpgsql security definer set search_path = '' as $$
declare v_school uuid; v_grade uuid; v_year int := extract(year from private.year_start(p_now))::int;
begin
  perform pg_advisory_xact_lock(hashtextextended('grades', 42));
  select id into v_school from private.schools order by created_at limit 1;
  if v_school is null then insert into private.schools (name) values ('school') returning id into v_school; end if;
  select id into v_grade from private.grades where school_id = v_school and label = p_label and school_year = v_year;
  if v_grade is null then
    insert into private.grades (school_id, label, school_year) values (v_school, p_label, v_year) returning id into v_grade;
  end if;
  return v_grade;
end $$;

-- every class made from now on has a grade (admin-class sends it); the name of the grade is enough to make it
create or replace function private.class_create(p_name text, p_grade text, p_lookup text) returns uuid
language plpgsql security definer set search_path = '' as $$
declare v uuid;
begin
  if coalesce(btrim(p_grade), '') = '' then raise exception 'a class needs its grade' using errcode = '22023'; end if;
  insert into public.classes (name, grade, grade_id) values (p_name, btrim(p_grade), private.grade_for(btrim(p_grade), now())) returning id into v;
  insert into private.class_codes (class_id, code_lookup) values (v, decode(p_lookup, 'hex'));
  return v;
end $$;

-- the owner adds a class's home teacher by her user id (never her address in a public input); app.teaches unchanged
create function private.teacher_add(p_user uuid, p_class_name text) returns text
language plpgsql security definer set search_path = '' as $$
declare v_class uuid;
begin
  select id into v_class from public.classes where name = p_class_name and kind = 'class';
  if v_class is null then return 'class'; end if;
  if not exists (select 1 from auth.users where id = p_user) then return 'user'; end if;
  if exists (select 1 from public.teachers where user_id = p_user and class_id = v_class) then return 'already'; end if;
  insert into public.teachers (user_id, class_id) values (p_user, v_class);
  return 'ok';
end $$;

-- ---------- names: a first name and ONE letter of the surname ----------
-- name_ok (0001) stays the rule for the characters and the length. In a 'first_initial' class the name is
-- "<first> <letter>." : no space inside the first name (a hyphen joins a double one), then exactly one letter and a
-- dot. A clash that remains is told apart by a DIGIT after the letter, "נועה כ2." (2 to 9), and only for a name the
-- teacher's roster holds; never a second letter, which would store more of the surname (the owner's rule).
-- The digit form is the one place a digit is allowed in a name: name_chars_ok is name_ok plus that form, and it
-- replaces name_ok in the two tables' checks.
create function app.name_chars_ok(p_name text) returns boolean language sql immutable set search_path = '' as $$
  select app.name_ok(p_name)
      or (p_name ~ '^[^ ]+ [A-Za-zÀ-ÖØ-öø-žא-ת][2-9]\.$' and app.name_ok(regexp_replace(p_name, '[2-9]\.$', '.'))) $$;
alter table public.pupils drop constraint pupils_display_name_check, add constraint pupils_display_name_check check (app.name_chars_ok(display_name));
alter table public.roster drop constraint roster_display_name_check, add constraint roster_display_name_check check (app.name_chars_ok(display_name));
create function app.name_form_ok(p_form text, p_name text, p_two boolean) returns boolean language sql immutable set search_path = '' as $$
  select case
    when p_form = 'first_initial' then
         (app.name_ok(p_name) and p_name ~ '^[^ ]+ [A-Za-zÀ-ÖØ-öø-žא-ת]\.$')
      or (p_two and app.name_chars_ok(p_name) and p_name ~ '[2-9]\.$')
    else app.name_ok(p_name) end $$;

-- Hebrew final letters are the plain letter (ך ם ן ף ץ as כ מ נ פ צ, the screen's rule): "נועה ך." and "נועה כ." are one
-- pupil. name_key is the generated key of pupils and the checked key of roster, so both are recomputed here.
create or replace function app.name_key(n text) returns text language sql immutable set search_path = '' as
  $$ select translate(lower(regexp_replace(btrim(n), '\s+', ' ', 'g')), 'ךםןףץ', 'כמנפצ') $$;
update public.pupils set display_name = display_name;
update public.roster set name_key = app.name_key(display_name);

create function private.roster_form() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  -- a name the table's own check refuses is left to that check (its message); this adds the class's form
  if app.name_chars_ok(new.display_name) and not app.name_form_ok((select name_form from public.classes where id = new.class_id), new.display_name, true) then
    raise exception 'the name is not in the form of this class' using errcode = '22023';
  end if;
  return new;
end $$;
create trigger roster_form before insert or update on public.roster for each row execute function private.roster_form();

-- a new pupil (registration): one letter, or two when the roster holds exactly that name
create function private.pupil_form() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if app.name_chars_ok(new.display_name) and not app.name_form_ok((select name_form from public.classes where id = new.class_id), new.display_name,
                          exists (select 1 from public.roster r where r.class_id = new.class_id and r.name_key = app.name_key(new.display_name))) then   -- name_key is generated: not set yet here
    raise exception 'the name is not in the form of this class' using errcode = '22023';
  end if;
  return new;
end $$;
create trigger pupil_form before insert on public.pupils for each row execute function private.pupil_form();

-- ---------- sign-in: per (address, class), and the name's form before anything else of the name ----------
-- The checks of 0008 run unchanged after these (renamed, called below). The order of the advisory locks stays: the
-- address first, then (inside) the class and kind, then the name.
alter function private.auth_begin(text, text, text, text, text, text, timestamptz) rename to auth_begin_0008;
create function private.auth_begin(p_kind text, p_class_lookup text, p_name text, p_dev text, p_ip text, p_ip_prev text, p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; v_class uuid; v_form text; v_key text := app.name_key(p_name); n int; v_oldest timestamptz;
begin
  if p_kind not in ('code', 'picture', 'otc', 'register') then raise exception 'bad kind'; end if;
  select * into s from private.settings;
  perform pg_advisory_xact_lock(hashtextextended('ip/' || p_ip, 42));
  select c.id, c.name_form into v_class, v_form
    from private.class_codes k join public.classes c on c.id = k.class_id where k.code_lookup = decode(p_class_lookup, 'hex');
  if v_class is not null then
    -- this address on this class: a grade at one school address is many classes, each with its own allowance
    select count(*), min(at) into n, v_oldest from private.auth_attempts
     where ip_bucket in (p_ip, p_ip_prev) and class_id = v_class and at > p_now - interval '1 hour';
    if n >= s.ip_class_hour then
      return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'wait', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now));
    end if;
    if p_kind = 'register' then
      select count(*), min(at) into n, v_oldest from private.auth_attempts
       where ip_bucket in (p_ip, p_ip_prev) and class_id = v_class and kind = 'register' and at > p_now - interval '1 hour';
      if n >= s.register_ip_class_hour then
        return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'wait', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now));
      end if;
    end if;
    -- the name's form, told only to a caller who has the class code: a pupil who left out the letter is told so,
    -- instead of a wrong code that would count towards a lock
    if not app.name_form_ok(v_form, p_name, exists (select 1 from public.roster r where r.class_id = v_class and r.name_key = v_key)
                                            or exists (select 1 from public.pupils p where p.class_id = v_class and p.name_key = v_key)) then
      return jsonb_build_object('s', 'name', 'form', v_form);
    end if;
  end if;
  return private.auth_begin_0008(p_kind, p_class_lookup, p_name, p_dev, p_ip, p_ip_prev, p_now);
end $$;

-- ---------- the grade board ----------
-- The pupils of the caller's grade (a pupil: their class's grade; a teacher: her classes' grades): name with the
-- surname letter, the class, points. Hidden "removed" classes, classes without a grade (the trial) and other grades
-- are never in it. No ids.
create function public.grade_board() returns table (display_name text, class text, points int, me boolean)
language sql stable security definer set search_path = '' as $$
  with mine as (
    select c.grade_id from public.classes c where c.id = app.reads_class() and c.kind = 'class'
    union
    select c.grade_id from public.classes c join public.teachers t on t.class_id = c.id where t.user_id = auth.uid() and c.kind = 'class'
  )
  select p.display_name, c.name, t.points, (p.auth_user_id is not distinct from auth.uid())
  from public.pupils p
  join public.classes c on c.id = p.class_id
  join public.pupil_totals t on t.pupil_id = p.id
  where auth.uid() is not null and c.kind = 'class' and c.grade_id is not null
    and c.grade_id in (select grade_id from mine where grade_id is not null)
  order by t.points desc, p.display_name
  limit 300 $$;

-- ---------- room for about 10 classes: older item history folded into a per-pupil carry ----------
create table private.pupil_carry (
  pupil_id uuid primary key references public.pupils on delete cascade,
  pts      bigint not null default 0,
  tries    bigint not null default 0
);
alter table private.pupil_carry enable row level security;

-- Daily rows older than daily_days, and (when year_end_delete) all item history of a school year that ended, are
-- folded into pupil_carry and deleted. Points and totals do not change: pupil_totals is kept as it is, and
-- totals_check adds the carry.
create function private.fold_history(p_now timestamptz) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; v_start date := private.year_start(p_now); v_daily date; n_daily int; n_year int := 0;
begin
  select * into s from private.settings;
  v_daily := (p_now at time zone s.tz)::date - s.daily_days;
  if s.year_end_delete and v_start > v_daily then v_daily := v_start; end if;
  with old as (delete from public.answer_daily where day < v_daily returning pupil_id, pts, tries),
  agg as (select pupil_id, sum(pts)::bigint as pts, sum(tries)::bigint as tries from old group by 1),
  ins as (insert into private.pupil_carry as c (pupil_id, pts, tries) select * from agg
          on conflict (pupil_id) do update set pts = c.pts + excluded.pts, tries = c.tries + excluded.tries returning 1)
  select (select count(*) from old) into n_daily;
  if s.year_end_delete then
    with old as (delete from public.answers where at < (v_start::timestamp at time zone s.tz) returning pupil_id, pts),
    agg as (select pupil_id, sum(pts)::bigint as pts, count(*)::bigint as tries from old group by 1),
    ins as (insert into private.pupil_carry as c (pupil_id, pts, tries) select * from agg
            on conflict (pupil_id) do update set pts = c.pts + excluded.pts, tries = c.tries + excluded.tries returning 1)
    select (select count(*) from old) into n_year;
  end if;
  return jsonb_build_object('daily_folded', n_daily, 'answers_folded', n_year, 'year_start', v_start);
end $$;

create or replace function private.totals_check() returns table (pupil_id uuid, stored_points int, real_points bigint, stored_answers int, real_answers bigint)
language sql security definer set search_path = '' as $$
  select t.pupil_id, t.points, c.pts, t.answers, c.n
  from public.pupil_totals t
  cross join lateral (
    select coalesce((select sum(a.pts) from public.answers a where a.pupil_id = t.pupil_id), 0)
         + coalesce((select sum(d.pts) from public.answer_daily d where d.pupil_id = t.pupil_id), 0)
         + coalesce((select k.pts from private.pupil_carry k where k.pupil_id = t.pupil_id), 0)
         + coalesce((select sum(p.delta) from public.points p where p.pupil_id = t.pupil_id), 0) as pts,
           coalesce((select count(*) from public.answers a where a.pupil_id = t.pupil_id), 0)
         + coalesce((select sum(d.tries) from public.answer_daily d where d.pupil_id = t.pupil_id), 0)
         + coalesce((select k.tries from private.pupil_carry k where k.pupil_id = t.pupil_id), 0) as n
  ) c
  where t.points <> c.pts or t.answers <> c.n
$$;

create or replace function private.backup_tables() returns text[] language sql immutable set search_path = '' as $$
  select array['private.schools', 'private.grades', 'public.classes', 'public.roster', 'public.teachers', 'public.pupils', 'private.limbo',
    'private.removed_pupils', 'public.items', 'public.levels',
    'public.answers', 'public.points', 'public.pupil_totals', 'public.progress', 'public.flags', 'public.level_best',
    'public.answer_daily', 'private.pupil_carry', 'private.class_codes', 'private.pupil_secrets', 'private.reset_codes',
    'private.pupil_devices', 'private.answer_batches', 'private.pupil_days', 'private.deletions', 'private.maintenance_log',
    'private.settings'] $$;

-- nightly, after maintenance(); where pg_cron is missing (the local test database) this is skipped and said
do $$ begin
  perform cron.schedule('wi-history', '37 2 * * *', 'select private.fold_history(now())');
  raise notice 'history fold is scheduled: every night at 02:37 UTC (cron job wi-history)';
exception when others then raise notice 'history fold is NOT scheduled: %', sqlerrm; end $$;

-- ---------- rights ----------
revoke all on private.schools, private.grades, private.pupil_carry from public, anon, authenticated;
revoke all on function public.grade_board() from public, anon;
grant execute on function public.grade_board() to authenticated;
revoke all on function app.name_form_ok(text, text, boolean), app.name_chars_ok(text) from public, anon, authenticated;
grant execute on function app.name_form_ok(text, text, boolean) to service_role;
-- the tables' checks run with the writer's rights: a teacher adding to her roster needs it, as she needs name_ok
grant execute on function app.name_chars_ok(text) to authenticated, service_role;
revoke all on all functions in schema private from public, anon, authenticated;
grant execute on all functions in schema private to service_role;
