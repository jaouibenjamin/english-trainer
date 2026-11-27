# Grade-ready v1 (plan, one page)

Owner's direction (2026-11-26): grades before the class goes live, and a pupil is named by first name plus ONE letter
of the surname. Built on the project that exists (Frankfurt) and on migrations 0001 to 0009, append-only: new files
0010 and on. Subject groups are not in v1 (the owner is asking the teacher); v1 leaves a seam for them (end).

## What changes, migration by migration

**0010 grades.** `schools (id, name)`; `grades (id, school_id, level 1..12, label "ה׳", school_year)`; `classes`
gains `grade_id` (nullable), `kind` (`class` | `limbo`, set only by `teacher_remove_pupil`) and `name_form`
(`first` | `first_initial`, below). There is no table check that a class has a grade (hidden classes and the trial
have none): a real class gets its grade where real classes are made, `class_create` and `admin-class`, which refuse
a class without one. `teacher_remove_pupil` is replaced so a new hidden class is inserted as `kind = 'limbo'` (never
found by its name, so a real class may be called anything but `removed`, which `class_create` and the tool refuse),
and 0010 marks every existing hidden class `limbo`, also those whose home class was deleted; every grade-scoped read
leaves `limbo` out.

**0011 names: first name + one letter.** The class says which form it takes (`name_form`; existing classes keep
`first`, new ones get `first_initial`). In a `first_initial` class a name is `<first> <L>.`: the first name with no
space (a hyphen or an apostrophe allowed, as in `app.name_ok` today), then one letter (Hebrew or Latin) and a dot,
e.g. `נועה כ.`. `app.name_form_ok(form, name)` is the one rule; `roster`, `register_pupil` and the teacher's roster
function apply it; nothing anywhere has a column for a full surname, and the second part is refused when it is longer than
one letter (a digit after it only from the roster, below). A two-word first name (בת אל) is written with a hyphen. Uniqueness stays `unique (class_id, name_key)` on the whole `"noa k."`, so two Noas with different letters
are two pupils. For a remaining clash the teacher's roster may hold a digit after the letter (`נועה כ2.`, 2 to 9; never a second
letter, which would store more of the surname); a pupil can only register a name the roster holds (`roster_only`, on by
default), so the digit is the teacher's, never the child's. Hebrew final letters count as the plain letter in the key
(`נועה ך.` is `נועה כ.`); 0010 re-keys existing rows (pupils, roster, attempts, locks, kept locked) and stops with
a clear message naming no pupil if two names of one class differ only by a final letter. A name in the wrong form is
counted like any other call, after the address check, and the answer depends on the shape alone, never on the class
list. **What the rule cannot stop:** a surname written into the first name (`דנה-כהן כ.`): a dot or a second hyphen in
the first name is refused, one hyphen is not (בת-אל). The teacher's guide says so; keep `roster_only` on, so only the
teacher's list is registered. `name_key` and `display_name` keep their meaning; the client composes the name from two fields.

**0012 boards.** `class_board` as today (it shows `display_name`, now "נועה כ."). `grade_board` (new, security
definer): the pupils of the caller's grade, `display_name` and the class's name ("נועה כ., ה׳2"), points, me; only
`kind = 'class'` rows of the same grade; a teacher sees her class's grade. No school-wide board.

**0013 limits per address and class.** A grade registers from one school address, so the per-address counters get a
per-(address, class) twin. Worst case in one hour, every child registering with two retries, two sign-ins and one "I
forgot my code" (every call counts): per (address, class), 35 x 3 = 105 registrations (limit 150) and 35 x 6 = 210
calls (limit 300); per address, 10 classes, 1,050 registrations (limit 1,500) and 2,100 calls (limit 3,000); 43%
headroom each. Wrong class codes stay counted per address (a wrong code has no class) plus the existing limit for
all addresses. All are settings. The Auth token-check setting is the owner's
(150 per 5 minutes; about 300 at 10 classes).

**0014 room for about 10 classes.** `raw_days` is already 30. New settings: `daily_days` (120): `answer_daily` older
than that is folded into a per-pupil `pupil_carry` row (points and tries) that `totals_check` and the totals add, then
deleted; and `year_end` (`08-31`) with `year_end_delete` (on): `maintenance()` deletes item history (`answers`,
`answer_daily`) of the school year that ended, after folding it into `pupil_carry`. Points are kept for good. Steady
size: about 12 MB raw + 10 MB daily + under 1 MB carry per class, so 10 classes stay near 230 MB, under the 350 MB
brake. (Boards restarting each September is a read of points since `year_end`; it is a later change, not needed
before September 2027.)

## The owner's steps for N classes (never a secret in chat or in a log)

Two new modes of `tools/supabase_setup.py`, run from the protected workflow on `main`:
- `add-class` (inputs: the class's name and grade label, e.g. `ה׳2`, `ה׳`): makes the grade if it is missing and
  the class through `admin-class` (now with the grade), its code into the Vault as `wi_class_code_<class name>`.
- `add-teacher` (inputs: the class's name and the teacher's **user id**): the owner first adds her in Supabase →
  Authentication → Add user (her address stays in the dashboard, never in a workflow input, which is public), copies
  the user id, and the tool writes the `teachers` row. A home-class teacher per class; `app.teaches` keeps its
  meaning.

## The trial class through the migration

It keeps working unchanged: no grade (the setup tool makes it with none; a table check would not allow that), `name_form = first` (Test, Tester stay valid),
`kind = 'class'`, its code and roster untouched. It is on no grade board. When the real classes are made, it is
deleted as `docs/LIVE_STAGE.md` E7 says.

## What changes for the client (the contract, for client engineer 1)

- Registration, sign-in and "I forgot my code" send `name` as today; in a `first_initial` class it must be
  `<first> <letter>.`. The screen has two fields (first name; one letter) and sends `${first} ${letter}.`.
- A name in the wrong form answers `{ok:false, e:"name", form:"first_initial"}` (new), and only once the class code
  is right (a wrong code answers exactly as today), so the form of a class cannot be probed without its code. The
  trial class (`first`) takes a first name alone, so one screen serves both: it sends the letter when one was typed.
- `grade_board` is a new read, a function (0010), not a view: `GET /rest/v1/rpc/grade_board` with the pupil's session
  (js/api.js names no columns, so the same read works before and after 0011). From 0011 it answers `display_name`,
  `class`, `points`, `me` and `rank`: at most 11 rows in place order, the grade's top ten and then the caller's own row
  only when it is not among them; `rank` is 1 + the number with more points, so ties share it (1,2,2,4) and the screen
  shows `rank`, never the row's position. The grade's size is not sent. It stays a function: it runs as its owner and
  picks the caller's grade itself, so no table under it is readable by a pupil.

## Tests (one PR with the code)

`db.py`: names (form, one letter, the second letter only from the roster, no full surname, uniqueness), the grade
board (no other grade, no limbo, no trial), the limits per (address, class), the carry and year-end deletion
(totals unchanged), the reader matrix grown by a second class and a second grade. `functions.py`: the `name` error,
`name_form` in the answers. `migrations_check.py`: 0010+ on a database with rows: a class, pupils, a removed pupil,
answers. `setup_check.py`: `add-class` and `add-teacher`, no secret in the log.

## Weekly boards (owner's decision, 2026-11-27; migration 0012)

Both boards rank **this week's points**; nothing else about them changes.

- **Where weekly points come from:** the points ledger that exists (`public.points`: `pupil_id`, `delta`, `at`),
  summed since the week began. No new column, no new counter to keep in step: the ledger is already what
  `pupil_totals` adds up. The nightly roll-up only merges `day` and `run` rows older than `raw_days` (30 today), so
  the last 7 days are always whole rows; 0012 adds the check `raw_days >= 8` so that stays true. Rows of reason
  `migrated` (a one-off import) are left out of the week; `fix` rows count (a correction is a correction). A point
  belongs to the week it reached the server (`at` is the server's time); a batch a device kept offline counts when it
  arrives. One index, `points (at, pupil_id)`, keeps the sum cheap (a grade is about 350 pupils).
- **The week:** from **Sunday 00:00 Asia/Jerusalem** (`private.settings.tz`, as the daily bonus and the teacher's
  day) to the next Sunday 00:00. Summer time changes nothing: the boundary is a local midnight.
- **The pupil's all-time total** stays where it is: `pupil_totals.points` (the pupil reads their own row only) and
  `class_board.points`. The map and the profile keep showing it; only the boards rank by the week.
- **`grade_board()`** (dropped and made again in 0012): `(display_name, class, week, me, rank)`, at most 11 rows in
  place order, as 0011: the top 10 of the grade **by `week`**, then the caller's own row when it is not among them.
  Only pupils with points this week are in the top 10 (on Sunday morning it is empty, not ten names in alphabetical
  order); the caller's own row always comes, with `week` 0 if so. `rank` = 1 + the number with more points this
  week. `points` is renamed `week` on purpose: a client still asking for `points` gets an error, never an all-time
  number on a weekly board.
- **`class_board`** (the view): gains a last column `week` (this week's points); its other columns, `points`
  included, stay, so today's client keeps working unchanged until it switches. It still holds the pupil's own class
  only.
- **Privacy:** unchanged. The grade board sends the top 10 and the caller's row, no ids, not the grade's size; the
  class board sends the pupil's own class, as today (above, "Later"). The week adds no new data about a child: it is
  a sum of rows the pupil can already read for themselves.
- **The client** (client engineer 1):
  - grade board: `GET /rest/v1/rpc/grade_board?select=display_name,class,week,me,rank`; show `rank` and `week`;
    an empty top 10 is "the week has just begun";
  - class board: `select=display_name,points,week,words,streak,me&order=week.desc,display_name`, rank and the
    "points to the next place" from `week`; the pupil's own all-time total from `points`;
  - both say "this week" (from Sunday), and nothing changes on the map or the profile.
- **Tests (0012, the local stand-in):** the week starts on Sunday 00:00 in `tz` (a point at Saturday 23:59 local is
  last week's, at Sunday 00:00 this week's, also across a summer-time change); `migrated` rows do not count;
  rolled-up rows never fall inside the week; the grade board's top 10 by week, ties, the empty Sunday, the own row
  with `week` 0; `class_board.week` per pupil; an old `select=points` on `grade_board` fails; `raw_days` below 8 is
  refused.

## Later (not in v1)

- **The class board sends the whole class** (`class_board`: every classmate's name, points, words, streak) though the
  screen shows the podium, the top five, the pupil's own place and the row above it. Left as is for v1 (lead, after
  #134): it is the pupil's own class, names they know, and today's Sheet board shows the whole class too. A server cut
  would be top 5 + own row + the row above + the class's size, with a client change.

## The seam for subject groups

Groups would be `subject_groups (grade_id, subject)` and `group_members (pupil_id, subject)`, read through a new
per-pupil `app.reads_subject(pupil, subject)`; nothing in v1 assumes a pupil has only a class. Boards take a scope.

## Privacy rule (CLAUDE.md, same PR)

"First name and the first letter of the surname only (e.g. נועה כ.). Never a full surname, an email, a birth date
or a photo of a child."
