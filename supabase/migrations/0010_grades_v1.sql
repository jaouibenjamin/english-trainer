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
-- the classes that exist keep 'first'; every hidden "removed" class of 0009 is marked, also one whose home class was
-- deleted by hand (its class_id is null then), and takes its home class's grade and form where there is one
update public.classes set kind = 'limbo' where id in (select limbo_id from private.limbo);
update public.classes c set name_form = h.name_form, grade_id = h.grade_id
  from private.limbo l join public.classes h on h.id = l.class_id where c.id = l.limbo_id;
-- a class name names one class (add-teacher finds the class by it)
create unique index classes_name_one on public.classes (name) where kind = 'class';

-- teacher_remove_pupil (0009) as it was, except that the hidden class is made with kind 'limbo' from the start, so a
-- real class named "removed" never collides with it (classes_name_one counts kind 'class' only)
create or replace function public.teacher_remove_pupil(p_pupil uuid) returns jsonb
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
    insert into public.classes (name, roster_only, max_pupils, kind) values ('removed', true, 200, 'limbo') returning id into v_limbo;
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

-- a new hidden class also takes its home class's grade and name form
create function private.limbo_mark() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  update public.classes c set kind = 'limbo', grade_id = h.grade_id, name_form = h.name_form
    from public.classes h where c.id = new.limbo_id and h.id = new.class_id;
  return new;
end $$;
create trigger limbo_mark after insert on private.limbo for each row execute function private.limbo_mark();

-- a day of the year as MM-DD that exists in every year (so not 02-29)
create function app.mmdd_ok(p text) returns boolean language plpgsql immutable set search_path = '' as $$
begin
  if p !~ '^\d\d-\d\d$' then return false; end if;
  perform make_date(2001, split_part(p, '-', 1)::int, split_part(p, '-', 2)::int);
  return true;
exception when others then return false;
end $$;

-- the school year a moment belongs to: it starts the day after settings.year_end (below)
alter table private.settings
  add column year_end        text not null default '08-31' check (app.mmdd_ok(year_end)),   -- a real day: not 02-30, not 02-29
  add column year_end_delete boolean not null default true,       -- item history deleted when a school year ends
  add column daily_days      int not null default 120 check (daily_days between 30 and 3650),
  add column fold_per_run    int not null default 50000 check (fold_per_run between 1 and 1000000),   -- rows a night (LESSONS 9)
  add column ip_class_hour          int not null default 300,     -- calls from one address for one class in an hour
  add column register_ip_class_hour int not null default 150;     -- registrations from one address for one class
-- One school address now carries a grade. The arithmetic, for a class of 35 and for 10 such classes, all in one hour,
-- every child at worst (a registration and two retries, two sign-ins, one "I forgot my code"; every call counts):
--   per (address, class): registrations 35 x 3 = 105, limit 150 (+43%); calls 35 x (3 + 2 + 1) = 210, limit 300 (+43%).
--   per address, 10 classes: registrations 1,050, limit 1,500 (+43%); calls 2,100, limit 3,000 (+43%).
-- The brakes against guessing stay where they are: per name, per class and the wrong-class-code limits of 0004/0008.
update private.settings set ip_hour = 3000 where ip_hour = 120;
update private.settings set register_ip_hour = 1500 where register_ip_hour = 60;

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
  if lower(btrim(p_name)) = 'removed' then raise exception 'that is the name of the hidden classes' using errcode = '22023'; end if;
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
-- The first name carries no dot and at most one hyphen (בת-אל), so "דנה-כהן-לוי" or "דנה.כהן" cannot carry a whole
-- surname; one hyphen cannot be told from a double first name, so the class list (roster_only) is the real guard.
create function app.name_form_ok(p_form text, p_name text, p_two boolean) returns boolean language sql immutable set search_path = '' as $$
  select case
    when p_form = 'first_initial' and (split_part(p_name, ' ', 1) ~ '\.' or split_part(p_name, ' ', 1) ~ '-.*-') then false
    when p_form = 'first_initial' then
         (app.name_ok(p_name) and p_name ~ '^[^ ]+ [A-Za-zÀ-ÖØ-öø-žא-ת]\.$')
      or (p_two and app.name_chars_ok(p_name) and p_name ~ '[2-9]\.$')
    else app.name_ok(p_name) end $$;

-- Hebrew final letters are the plain letter (ך ם ן ף ץ as כ מ נ פ צ, the screen's rule): "נועה ך." and "נועה כ." are one
-- pupil. name_key is the generated key of pupils and the checked key of roster, so both are recomputed here.
create or replace function app.name_key(n text) returns text language sql immutable set search_path = '' as
  $$ select translate(lower(regexp_replace(btrim(n), '\s+', ' ', 'g')), 'ךםןףץ', 'כמנפצ') $$;
-- Two names of one class that differ only by a final letter would become one: the migration stops before changing
-- anything, and says so without naming a pupil (rename one in the class list, then run it again).
do $$ begin
  if exists (select 1 from public.pupils group by class_id, translate(name_key, 'ךםןףץ', 'כמנפצ') having count(*) > 1)
     or exists (select 1 from public.roster group by class_id, translate(name_key, 'ךםןףץ', 'כמנפצ') having count(*) > 1) then
    raise exception 'two names in one class differ only by a final letter: rename one of them in the class list, then run again';
  end if;
end $$;
update public.pupils set display_name = display_name where name_key ~ '[ךםןףץ]';                 -- the generated key again
update public.roster set name_key = app.name_key(display_name) where name_key ~ '[ךםןףץ]';
-- the sign-in bookkeeping follows the key, so a locked name stays locked; two spellings' buckets merge (the later lock
-- and the larger counts win)
update private.auth_attempts    set name_key = translate(name_key, 'ךםןףץ', 'כמנפצ') where name_key ~ '[ךםןףץ]';
update private.auth_lock_events set name_key = translate(name_key, 'ךםןףץ', 'כמנפצ') where name_key ~ '[ךםןףץ]';
insert into private.auth_buckets as b (class_id, name_key, kind, bucket, fails, round, locked_until, last_fail_at)
  select class_id, translate(name_key, 'ךםןףץ', 'כמנפצ'), kind, bucket, fails, round, locked_until, last_fail_at
  from private.auth_buckets where name_key ~ '[ךםןףץ]'
  on conflict (class_id, name_key, kind, bucket) do update
    set fails = greatest(b.fails, excluded.fails), round = greatest(b.round, excluded.round),
        locked_until = greatest(b.locked_until, excluded.locked_until), last_fail_at = greatest(b.last_fail_at, excluded.last_fail_at);
delete from private.auth_buckets where name_key ~ '[ךםןףץ]';

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
declare s private.settings; v_class uuid; v_form text; v_key text := app.name_key(p_name); v_n int; v_oldest timestamptz;
        v_hour timestamptz := date_trunc('hour', p_now);
begin
  if p_kind not in ('code', 'picture', 'otc', 'register') then raise exception 'bad kind'; end if;
  select * into s from private.settings;
  perform pg_advisory_xact_lock(hashtextextended('ip/' || p_ip, 42));
  -- the address first, exactly as 0008 counts it (every call, and wrong class codes), and the copy-phase lock: nothing
  -- below, the form answer included, is reachable past them
  select count(*), min(at) into v_n, v_oldest from private.auth_attempts where ip_bucket in (p_ip, p_ip_prev) and at > p_now - interval '1 hour';
  v_n := v_n + coalesce((select m.n from private.class_misses m where m.bucket = p_ip and m.hour = v_hour), 0);
  if v_n >= s.ip_hour then
    return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'wait', 'wait', private.wait_s(coalesce(v_oldest, v_hour) + interval '1 hour', p_now));
  end if;
  if s.shadow_mode and p_kind <> 'code' then return jsonb_build_object('s', 'locked', 'by', 'system', 'help', 'wait', 'wait', -1); end if;
  select c.id, c.name_form into v_class, v_form
    from private.class_codes k join public.classes c on c.id = k.class_id where k.code_lookup = decode(p_class_lookup, 'hex');
  if v_class is not null then
    -- this address on this class: a grade at one school address is many classes, each with its own allowance
    select count(*), min(at) into v_n, v_oldest from private.auth_attempts
     where ip_bucket in (p_ip, p_ip_prev) and class_id = v_class and at > p_now - interval '1 hour';
    if v_n >= s.ip_class_hour then
      return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'wait', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now));
    end if;
    if p_kind = 'register' then
      select count(*), min(at) into v_n, v_oldest from private.auth_attempts
       where ip_bucket in (p_ip, p_ip_prev) and class_id = v_class and kind = 'register' and at > p_now - interval '1 hour';
      if v_n >= s.register_ip_class_hour then
        return jsonb_build_object('s', 'locked', 'by', 'address', 'help', 'wait', 'wait', private.wait_s(v_oldest + interval '1 hour', p_now));
      end if;
    end if;
    -- the name's SHAPE for this class, never whether the class list holds it (that would list names nobody has
    -- registered yet): a pupil who left out the letter is told so instead of a wrong code. The call is counted like
    -- any other (outcome 'ok': it is not a wrong code against any name), so it is never free.
    if not app.name_form_ok(v_form, p_name, true) then
      insert into private.auth_attempts (at, class_id, name_key, kind, dev_bucket, ip_bucket, outcome)
        values (p_now, v_class, v_key, p_kind, p_dev, p_ip, 'ok');
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
  limit 1000 $$;      -- a grade of 10 classes of 35 is 350 pupils; tested with more than 300

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
  -- at most fold_per_run rows of each kind a night: a first night after a long time cannot run for hours
  with old as (delete from public.answer_daily d using (select pupil_id, day, item_id from public.answer_daily where day < v_daily limit s.fold_per_run) x
               where d.pupil_id = x.pupil_id and d.day = x.day and d.item_id = x.item_id returning d.pupil_id, d.pts, d.tries),
  agg as (select pupil_id, sum(pts)::bigint as pts, sum(tries)::bigint as tries from old group by 1),
  ins as (insert into private.pupil_carry as c (pupil_id, pts, tries) select * from agg
          on conflict (pupil_id) do update set pts = c.pts + excluded.pts, tries = c.tries + excluded.tries returning 1)
  select (select count(*) from old) into n_daily;
  if s.year_end_delete then
    with old as (delete from public.answers where id in (select id from public.answers where at < (v_start::timestamp at time zone s.tz) limit s.fold_per_run)
                 returning pupil_id, pts),
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
