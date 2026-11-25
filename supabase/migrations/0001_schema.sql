-- Word Islands backend, Phase 1 (docs/BACKEND.md section 1). Tables only; access rules are in 0002, functions in 0003.
-- Nothing here is live: the Google Sheet stays the class's backend until the owner switches.
-- public  = reachable through the API, always behind row level security
-- private = not exposed by the API, no right for any browser role (codes, pictures, locks)
-- app     = helper functions the policies call

create schema if not exists app;
create schema if not exists private;

-- What a first name may be (docs/BACKEND.md 4.4): an allow-list, not a list of what is forbidden. Letters only,
-- Hebrew (U+05D0-U+05EA) or Latin (A-Z, a-z, Latin-1 U+00C0-U+00FF without the signs U+00D7 and U+00F7, and Latin
-- Extended-A U+0100-U+017E without the look-alikes ı Ĳ ĳ ĸ ŉ ſ: Łukasz, Žofie), with a space, apostrophe ' or ’, geresh ׳, gershayim ״, dot or hyphen
-- inside; 2 to 20 characters; it starts with a letter and ends with a letter, a dot, or an apostrophe or geresh
-- right after a letter (ג׳ורג׳, ג'ורג'). Everything else is refused: markup, digits, emoji, look-alike letters of other
-- scripts, invisible and direction characters, blank-looking letters, combining marks, a leading or trailing space.
-- Written with \u escapes so no invisible character hides in this file. supabase/functions/_shared/validate.ts has
-- the same rule, and both are tested with the same names.
create function app.name_ok(n text) returns boolean language sql immutable set search_path = '' as
  $$ select n ~ '^[A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u0130\u0134-\u0137\u0139-\u0148\u014A-\u017E\u05D0-\u05EA](?:[A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u0130\u0134-\u0137\u0139-\u0148\u014A-\u017E\u05D0-\u05EA\u05F3\u05F4\u2019'' .-]{0,18}[A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u0130\u0134-\u0137\u0139-\u0148\u014A-\u017E\u05D0-\u05EA.]|(?:[A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u0130\u0134-\u0137\u0139-\u0148\u014A-\u017E\u05D0-\u05EA\u05F3\u05F4\u2019'' .-]{0,17}[A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u0130\u0134-\u0137\u0139-\u0148\u014A-\u017E\u05D0-\u05EA])?[\u05F3\u2019''])$' $$;

-- "Noa", " noa " and "NOA" are one pupil: trimmed, inner spaces squeezed, lower-cased
create function app.name_key(n text) returns text language sql immutable
  set search_path = '' as
  $$ select lower(regexp_replace(btrim(n), '\s+', ' ', 'g')) $$;

create table public.classes (
  id          uuid primary key default gen_random_uuid(),
  name        text not null check (char_length(name) between 1 and 40),
  grade       text not null default '' check (char_length(grade) <= 20),
  roster_only boolean not null default true,
  max_pupils  int not null default 60 check (max_pupils between 1 and 200),
  created_at  timestamptz not null default now()
);

create table public.roster (
  class_id     uuid not null references public.classes on delete cascade,
  name_key     text not null,
  display_name text not null check (app.name_ok(display_name)),
  primary key (class_id, name_key),
  check (name_key = app.name_key(display_name))
);

create table public.teachers (
  user_id  uuid not null references auth.users (id) on delete cascade,
  class_id uuid not null references public.classes on delete cascade,
  primary key (user_id, class_id)
);

-- First name or nickname only.
create table public.pupils (
  id           uuid primary key default gen_random_uuid(),
  class_id     uuid not null references public.classes on delete cascade,
  display_name text not null check (app.name_ok(display_name)),
  name_key     text not null generated always as (app.name_key(display_name)) stored,
  auth_user_id uuid unique references auth.users (id) on delete set null,   -- filled at the first sign-in
  created_at   timestamptz not null default now(),
  unique (class_id, name_key)
);

-- what can be answered. Seeded from the repo's content files; an event with an unknown key earns nothing and is
-- not stored, so a pupil's device cannot write free text here.
create table public.items (
  id       int generated always as identity primary key,
  game     text not null check (game ~ '^[a-z0-9_]{1,16}$'),
  item_key text not null check (char_length(item_key) between 1 and 64 and item_key !~ '[\u0001-\u001f]'),
  skill    text not null default '' check (skill ~ '^[a-z0-9_-]{0,24}$'),
  unique (game, item_key)
);

-- levels, reading texts (game 'read') and exam papers (game 'exam', size = number of questions); seeded like items
create table public.levels (
  game      text not null check (game ~ '^[a-z0-9_]{1,16}$'),
  level_key text not null check (char_length(level_key) between 1 and 60 and level_key !~ '[\u0001-\u001f]'),
  size      int not null default 0 check (size between 0 and 500),
  primary key (game, level_key)
);

-- append only, one row per item answered. pts and flag are decided by the server (0003), never by the client.
-- flag: 0 fine, 1 rate, 2 daycap, 3 repeat
create table public.answers (
  id        bigint generated always as identity primary key,
  at        timestamptz not null default now(),
  pupil_id  uuid not null references public.pupils on delete cascade,
  item_id   int not null references public.items,
  pts       smallint not null default 0 check (pts between 0 and 100),
  flag      smallint not null default 0,
  correct   boolean not null,
  first_try boolean not null
);
create index answers_pupil_at on public.answers (pupil_id, at);

-- append only ledger for points that are not one answer
create table public.points (
  id       bigint generated always as identity primary key,
  at       timestamptz not null default now(),
  pupil_id uuid not null references public.pupils on delete cascade,
  delta    int not null check (delta between -1000000 and 1000000),
  reason   text not null check (reason in ('day', 'stars', 'read', 'exam', 'run', 'migrated', 'fix')),
  ref      text not null default '' check (char_length(ref) <= 80)
);
create index points_pupil on public.points (pupil_id);

-- what the board reads; kept by the functions that write answers and points
create table public.pupil_totals (
  pupil_id  uuid primary key references public.pupils on delete cascade,
  points    int not null default 0,
  answers   int not null default 0,
  first_try int not null default 0,
  wrong     int not null default 0,
  last_at   timestamptz
);

-- transitional: today's pack() blob. state.pts is not used for the board.
create table public.progress (
  pupil_id   uuid primary key references public.pupils on delete cascade,
  state      jsonb not null default '{}' check (jsonb_typeof(state) = 'object' and char_length(state::text) <= 40000),
  updated_at timestamptz not null default now()
);

-- sanity-check findings for the teacher: one row per pupil, kind and day, with a counter
create table public.flags (
  id       bigint generated always as identity primary key,
  pupil_id uuid not null references public.pupils on delete cascade,
  kind     text not null check (kind in ('rate', 'daycap', 'repeat', 'items', 'levels', 'marathon', 'unusual', 'bonus', 'saves', 'storage')),
  day      date not null,
  n        int not null default 1,
  unique (pupil_id, kind, day)
);

-- the best stars a pupil reached on each level, kept by record_events(); the teacher's stars come from here
create table public.level_best (
  pupil_id  uuid not null references public.pupils on delete cascade,
  game      text not null,
  level_key text not null,
  stars     smallint not null check (stars between 0 and 3),
  at        timestamptz not null default now(),
  primary key (pupil_id, game, level_key)
);

-- roll-up of answers older than the raw window (maintenance() in 0003)
create table public.answer_daily (
  pupil_id  uuid not null references public.pupils on delete cascade,
  day       date not null,
  item_id   int not null references public.items,
  tries     int not null default 0,
  correct   int not null default 0,
  first_try int not null default 0,
  pts       int not null default 0,
  primary key (pupil_id, day, item_id)
);

create function app.new_pupil() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.pupil_totals (pupil_id) values (new.id);
  insert into public.progress (pupil_id) values (new.id);
  return new;
end $$;
create trigger pupils_new after insert on public.pupils for each row execute function app.new_pupil();

-- ---------------------------------------------------------------- private

-- code_lookup = HMAC-SHA256(pepper, upper-cased class code); the pepper exists only in the functions' secrets
create table private.class_codes (
  class_id    uuid primary key references public.classes on delete cascade,
  code_lookup bytea not null unique check (octet_length(code_lookup) = 32)
);

-- docs/BACKEND.md 4.2. code_hash null = reset by the teacher, not set again yet. pic_hash null = no picture yet.
create table private.pupil_secrets (
  pupil_id    uuid primary key references public.pupils on delete cascade,
  code_algo   text not null default 'v1' check (code_algo in ('v1', 'legacy-sha256')),
  code_salt   bytea,
  code_hash   bytea check (code_hash is null or octet_length(code_hash) = 32),
  code_iter   int not null default 600000 check (code_iter >= 100000),
  legacy_salt text,                                   -- the Sheet's salt, only while code_algo = 'legacy-sha256'
  code_set_at timestamptz,
  pic_salt    bytea,
  pic_hash    bytea check (pic_hash is null or octet_length(pic_hash) = 32),
  pic_iter    int not null default 600000 check (pic_iter >= 100000),
  pic_recovered_at timestamptz,                       -- last recovery by pictures: once in 30 days
  pepper_id   smallint not null default 1
);

create table private.reset_codes (
  pupil_id   uuid primary key references public.pupils on delete cascade,
  salt       bytea not null,
  hash       bytea not null check (octet_length(hash) = 32),
  iter       int not null default 600000,
  expires_at timestamptz not null,
  fails      smallint not null default 0,
  created_by uuid,
  created_at timestamptz not null default now()
);

-- staging for the Sheet's fast hashes during migration; emptied by the one-off admin function that wraps them
create table private.legacy_import (
  pupil_id uuid primary key references public.pupils on delete cascade,
  salt     text not null,
  hash     text not null check (hash ~ '^[0-9a-f]{64}$')
);

create table private.pupil_devices (
  pupil_id    uuid not null references public.pupils on delete cascade,
  device_hash bytea not null,
  last_ok_at  timestamptz not null default now(),
  primary key (pupil_id, device_hash)
);

-- keyed by class and name, not by pupil, so a name that does not exist behaves like one that does
create table private.auth_attempts (
  id         bigint generated always as identity primary key,
  at         timestamptz not null default now(),
  class_id   uuid,
  name_key   text not null default '',
  kind       text not null check (kind in ('code', 'picture', 'otc', 'class', 'register')),
  dev_bucket text not null default '',
  ip_bucket  text not null default '',
  trusted    boolean not null default false,
  outcome    text not null default 'pending' check (outcome in ('pending', 'ok', 'wrong'))
);
create index auth_attempts_name on private.auth_attempts (class_id, name_key, kind, at);
create index auth_attempts_ip on private.auth_attempts (ip_bucket, kind, at);

create table private.auth_buckets (
  class_id     uuid not null,
  name_key     text not null,
  kind         text not null,
  bucket       text not null,
  fails        int not null default 0,
  round        int not null default 0,
  locked_until timestamptz,
  last_fail_at timestamptz,
  primary key (class_id, name_key, kind, bucket)
);

create table private.auth_lock_events (
  id       bigint generated always as identity primary key,
  class_id uuid not null,
  name_key text not null,
  kind     text not null,
  at       timestamptz not null default now(),
  until    timestamptz
);
create index auth_lock_events_name on private.auth_lock_events (class_id, name_key, at);

create table private.ip_salts (
  day  date primary key,
  salt bytea not null
);

create table private.answer_batches (
  pupil_id uuid not null references public.pupils on delete cascade,
  batch_id uuid not null,
  at       timestamptz not null default now(),
  primary key (pupil_id, batch_id)
);

-- per pupil and day (Israel time): the counters behind the daily caps
create table private.pupil_days (
  pupil_id  uuid not null references public.pupils on delete cascade,
  day       date not null,
  pointed   int not null default 0,      -- answers with points whose own day (the client's clock, clamped) is this day
  arrived   int not null default 0,      -- answers with points that reached the server on this day, whatever they claim
  stored    int not null default 0,      -- answer rows written on this day: the ceiling that protects the free 500 MB
  calls     int not null default 0,      -- record_events calls on this day
  batches   int not null default 0,      -- batch ids kept on this day (one per call that stored something)
  saves     int not null default 0,      -- save_progress writes on this day
  save_kb   int not null default 0,      -- and their size: every write leaves a dead copy until vacuum
  last_save_at timestamptz,              -- the last of them: two writes are at least save_gap_s apart
  levels    int not null default 0,
  exams     int not null default 0,
  run_pts   int not null default 0,
  bonus     boolean not null default false,
  primary key (pupil_id, day)
);

-- who removed which pupil and when. No name is kept: the point of deleting is that the child is gone.
create table private.deletions (
  id       bigint generated always as identity primary key,
  at       timestamptz not null default now(),
  teacher  uuid,
  class_id uuid,
  pupil_id uuid not null,
  answers  int not null default 0,
  points   int not null default 0
);

-- each night's maintenance() answer: under pg_cron nobody reads it otherwise. Kept log_days; the teacher's health
-- view warns from the last row.
create table private.maintenance_log (
  id     bigint generated always as identity primary key,
  at     timestamptz not null default now(),
  result jsonb not null
);

-- one row: every limit of docs/BACKEND.md sections 4 and 5, tunable without a migration
create table private.settings (
  one              boolean primary key default true check (one),
  tz               text not null default 'Asia/Jerusalem',
  pts_first        int not null default 10,
  pts_later        int not null default 4,
  pts_star         int not null default 15,
  pts_day          int not null default 20,
  max_batch        int not null default 200,
  max_per_minute   int not null default 20,
  max_pointed_day  int not null default 600,
  max_item_day     int not null default 6,
  max_rows_day     int not null default 300,    -- answer rows one pupil may add in a day (honest play: about 80); beyond it only a counter moves
  max_calls_day    int not null default 1500,
  max_levels_day   int not null default 20,
  unusual_answers  int not null default 300,
  unusual_levels   int not null default 12,
  pts_read         int not null default 50,
  pts_exam_right   int not null default 5,
  max_exams_day    int not null default 3,
  max_run_day      int not null default 60,
  migrated_cap     int not null default 50000,
  marathon_hours   int not null default 18,
  backfill_hours   int not null default 48,
  raw_days         int not null default 90,
  code_round       int not null default 5,
  code_locks_min   int[] not null default '{5,15,60,240}',
  code_bucket_day  int not null default 10,
  code_name_day    int not null default 20,
  code_ceiling_day int not null default 29,
  code_ip_class_day int not null default 30,
  code_class_alarm int not null default 60,
  code_class_brake int not null default 100,
  device_days      int not null default 30,
  pic_tries        int not null default 3,
  pic_count        int not null default 2,
  pic_choices      int not null default 20,
  pic_ip_day       int not null default 5,
  pic_class_day    int not null default 10,
  pic_again_days   int not null default 30,
  otc_ip_tries     int not null default 5,
  otc_tries        int not null default 30,
  otc_hours        int not null default 48,
  class_ip_hour    int not null default 30,
  register_ip_hour int not null default 60,
  -- storage (review PB1b and the re-check): what one pupil's device can add in a day, and the brake for all
  max_saves_day    int not null default 300,     -- honest play saves about every 3 s of play at most, and far less
  save_gap_s       int not null default 5,
  max_save_kb_day  int not null default 4000,    -- 4 MB a pupil a day: 35 pupils at worst add 140 MB before vacuum
  max_batches_day  int not null default 300,     -- a batch follows a save
  storage_brake_mb int not null default 350,     -- maintenance() switches the brake on at this size (limit 500 MB)
  storage_brake    boolean not null default false,
  flags_days       int not null default 365,
  log_days         int not null default 60
);
insert into private.settings default values;
