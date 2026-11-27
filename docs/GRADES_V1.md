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
- `grade_board` is a new read (`/rest/v1/grade_board`), same shape as `class_board` plus `class`.

## Tests (one PR with the code)

`db.py`: names (form, one letter, the second letter only from the roster, no full surname, uniqueness), the grade
board (no other grade, no limbo, no trial), the limits per (address, class), the carry and year-end deletion
(totals unchanged), the reader matrix grown by a second class and a second grade. `functions.py`: the `name` error,
`name_form` in the answers. `migrations_check.py`: 0010+ on a database with rows: a class, pupils, a removed pupil,
answers. `setup_check.py`: `add-class` and `add-teacher`, no secret in the log.

## The seam for subject groups

Groups would be `subject_groups (grade_id, subject)` and `group_members (pupil_id, subject)`, read through a new
per-pupil `app.reads_subject(pupil, subject)`; nothing in v1 assumes a pupil has only a class. Boards take a scope.

## Privacy rule (CLAUDE.md, same PR)

"First name and the first letter of the surname only (e.g. נועה כ.). Never a full surname, an email, a birth date
or a photo of a child."
