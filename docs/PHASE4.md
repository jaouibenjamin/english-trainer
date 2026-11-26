# Phase 4 proposal: a fresh start, the whole school by grade and class, and new levels from teachers' material (DRAFT)

Status: a proposal for the lead and the owner, written from the owner's decisions of 2026-11-26 and his additions of
the same day. Revised after the lead's review of the first version (2909e59), and checked against migrations 0001
to 0009 as they are on `game`. The owner will check the details with the teacher, so this is direction, not final.
No code yet. Decisions that are the owner's are marked **[owner]**; each has a recommended answer at the end.

The owner's three decisions:

- **A. Fresh start.** When the class moves to the new game, everyone starts from zero, in English and in Fraction Bay,
  with a new sign-in. Nothing is imported from the Sheet. The Sheet (backend/Code.gs version 3, deployed today) stays
  as it is for today's class until the new game is live and fully tested; then it is switched off.
- **B. The whole school, by grade (שכבה) and class**, and in English and math by **subject groups** ("each class is a
  different colour") that cut across home classes. A teacher puts a child in a group, never the child. Boards by
  class, grade and group. Teachers attached to what they teach.
- **C. New levels from teachers' material.** Teachers do **not** publish to children. A teacher sends a PDF or names
  textbook pages; we build the level (her words exactly, reviewed); the owner releases it to a grade, class or group,
  and can withdraw it, without a site ship.

---

## 0. What the first version is, and what waits

**Version 1 moves one class**, the class that uses the game today, onto a schema that is already ready for grades,
so that nothing has to be reset when the second class comes. Everything else is built after that, one step at a
time, each with its own review:

| In version 1 | After version 1 |
|---|---|
| The fresh start (A): new sign-in, its own storage on the device, a trial class, switch day | Subject groups and the group board |
| Grades and school years in the schema; `classes.grade_id`; a subject on items and points | The grade board |
| The teacher check split into "home-class teacher" (may change) and "reads a subject" (reads only) | Teachers of a whole grade or of a group |
| One random class code per class, as today | An admin page (version 1 is the owner's command line) |
| The roll-ups that stop the database from growing with time (B, "Growth") | The upload inbox (C). Until then the teacher gives her material to the owner, and he passes it on by hand |

The rest of this document describes the whole design, so that version 1's schema is right for it.

---

## A. Fresh start

### What goes away

Nothing of the Sheet ever reaches Supabase. That removes a whole class of risk (the Sheet's fast hashes, the copy
phase, the comparison of two ledgers) and a lot of runbook.

| Part | Today | With a fresh start |
|---|---|---|
| Runbook C (`docs/LIVE_STAGE.md`): export the Sheet, `tools/migrate_sheet.py`, `--wrap` | needed | **goes**. No CSV of the class ever leaves the Sheet. |
| `private.legacy_import`, `private.sheet_import`, `wrapLegacy` (`admin-wrap-legacy`), the `legacy-sha256` code path in `auth_finish` | needed for C3 | **goes** (a cleanup migration drops them, append-only; their tests go with them). |
| `shadow_mode` (the copy phase), `pupil-login`'s "Sheet-era code opens a copy session" | needed for `dual` | **goes**. |
| `dual` mode in `js/api.js` (each answer sent to both backends, gates 5 to 8) | the way to compare | **not needed**. See "What I would keep". |
| Runbook E (a test pupil copied from the Sheet), F (the class copies), G (counted equals played, day 1) | needed | **replaced** by the trial class and switch day (below). |
| `docs/PHASE3.md` "before the Sheet is switched off": counted equals played for 3 days, the Sheet's copy deleted on a date | conditions | **simplified**: no copy to compare or delete. What stays: the teacher used the new screen, the pupil screens are approved, backups and a restore drill, the switch-day runbook, section D. |
| `PHASE3.md` step 5, the "first sign-in of a pupil who came from the Sheet" flow | one of three pupil flows | **goes**. Two flows stay: registration, and "I forgot my code". |

### What I would keep, and why

- **A device switch for trying the new game** (today `?dual=1`), renamed to a plain trial switch (for example
  `?new=1`). Only a device that opened the game once with it talks to Supabase, and it signs in to a **trial class**,
  never the real one. The trial class is deleted (`teacher_delete_pupil` for each pupil, then the class) before switch
  day, so nothing played on trial survives into the fresh start.
- **The adapter's session guards** (one operation bound to one session and one pupil, the late-answer guards, the
  64 KiB keepalive budget, the displaced-tab dialog): they protect the new game too.
- **Everything of Phase 3** (teacher sign-in, screen, actions, lock scope, remove with undo): unchanged, apart from
  the teacher check in section B.

### The device: its own storage for the new backend

Today the game keeps progress on the device under `aam-unit1-v1` (`js/state.js`, shared with `trainer.html`), and
`merge()` joins the device's copy with the server's. If the new backend used the same key, the first sign-in on a
class device would `merge()` the old local progress into the "fresh" account. And a way back to the Sheet would find
that old progress overwritten by the new game's.

So the new backend gets **its own keys on the device** (for example `wi-new-v1-<project ref>`), and it never reads the
old key. The old key stays as it is, so the way back finds the Sheet-era progress where it was. This is a change in
the trial switch's client code (the client engineer's), with a test: a device with old progress signs in to the new
backend and starts at zero, then switches back and finds the old progress unchanged.

### The way back, honestly

For a short time after the switch **[owner]**, `config.js` can point the class back at the Sheet in one commit.
**What was played on the new backend in that time does not go back to the Sheet**: the children find the progress
they had on switch day. The owner accepts that before switch day, or there is no way back. After it closes, the owner
switches the Sheet off (his own step; this team never edits `backend/Code.gs` or the Sheet) and deletes the Sheet's
copy of the class on a stated date.

### Switch day, in short (the full runbook is a later PR)

1. The new game has run on the trial devices, in the trial class, for at least a week (the teacher and the owner),
   and the security reviews are green. The trial class is deleted.
2. The owner creates the class (in its grade and school year) and its code from the command line, and gives the code
   to the teacher.
3. Each child registers: first name or nickname, a 4-digit code, two secret pictures. Everyone starts at zero. **One
   class a day**, its registration spread over the lesson (the address limits in section B).
4. `config.js` on `main` points the class at the new game. The Sheet stays readable for the way back.
5. After the way back closes, the Sheet is switched off and its copy of the class is deleted on the stated date.

### What must be decided before the fresh start, so that there is no second reset

These are cheap now and expensive later, because every row written after the start depends on them:

- **Ids**: every row keyed by a uuid (already so). A pupil, a class, a grade and a level keep their id for ever.
- **School year on grades only.** A class belongs to a grade, and a grade to a school year. A pupil moves to next
  year's class by the owner's or a teacher's action (their record goes with them). Last year's class is archived,
  not reused.
- **Points per subject.** `items` gets a `subject` (`english` or `math`, from its game), and the ledger and the totals
  are kept per subject, so a board can be English-only or math-only and a subject teacher reads only her subject.
  This changes `pupil_totals` and the boards' reads (a new migration), and is much cheaper before the first answer.
- **Points carry over; boards restart.** A child's points stay with them for good. The boards show the current
  school year only, so every September everyone starts level on the board. **[owner]**
- **Item history** (`answers`, `answer_daily`) is deleted at the end of each school year, after the totals are kept.
  This is also what keeps the database inside the free plan ("Growth", section B). **[owner]**
- **Names**: unique per class (already `unique (class_id, name_key)`). Two children with the same first name in one
  class need a nickname or an initial (the class list decides), never a surname.

---

## B. The whole school, by grade and class

### The rule that answers the owner's worry ("a child can declare any class")

A child never declares a class, a grade or a group. **The class code decides the class, and the class decides the
grade**, on the server, at registration. A teacher decides the group. After that:

- the pupil's row has no column the pupil can write (no `update` grant on `pupils` for a session, as today);
- every read is filtered by row-level security through functions that read the pupil's own rows, never anything the
  client sends;
- only the owner, or a teacher of both classes, can move a pupil to another class (below).

A child who learns another class's code can register a second name there. That is the same risk as today, handled
as today: a roster per class (`roster_only`, on by default), so only names the teacher listed can register, and a new
code when one leaks (`admin-class rotate`).

### Codes: one random class code per class ("a code per grade" becomes "the class decides the grade")

The first version of this proposal had a two-part code, a grade code and a class code under it. That is **weaker,
not stronger**: the grade half is known to the whole grade (100 or more children), so what is left is a 4-character
class half, 31^4 ≈ 920,000 values, against today's 8-character code, 31^8 ≈ 850 billion. So:

- **One random 8-character code per class**, as today (`private.class_codes`, a keyed hash, the alphabet without
  look-alikes). The class implies the grade, so a code per grade adds nothing a child needs.
- The grade's **label** ("ה׳") can still be shown with the class name on the boards and the teacher's screen. It is
  never part of a code.
- **Rotation**: one class at a time, as today. Signed-in pupils stay signed in.

### Teachers: added by the owner, no invites

Sign-ups are off (`docs/BACKEND.md` 4.1, runbook A3: "sign-ups off"), and with Google sign-in in Testing mode every
teacher is on a named list of test users anyway. So the invite codes of the first version go: **the owner adds a
teacher and her assignment in one step** from the command line (later the admin page): her auth user, her Google
address on the test-user list, and her row. He removes her the same way. Nobody becomes a teacher, or an admin,
through the app. **[owner: Google in Testing mode with a named list, or in Production with only the basic scopes]**

### Two checks, not one (a blocker of the first version)

Today `app.teaches(class)` (0002, line 11) reads `public.teachers` and grants **writes** as well as reads:

- the roster policy is `for all` (0002, line 56): add, change and delete names;
- `teacher_reset` and `teacher_unlock` (0004), the reset cap (0007), `teacher_remove_pupil`, `teacher_restore_pupil`
  and `teacher_delete_pupil` (0009);
- the reads of `pupils`, `answers`, `points`, `pupil_totals`, `answer_daily`, `level_best` and `progress` (0002,
  0004), and `teacher_view` (0006).

The first version kept `teachers` as a view over all assignments, so a grade or group teacher would have passed
`app.teaches` for **every class of the grade**: she could have reset, unlocked, removed or deleted any child there.
So there are two separate checks:

| Check | Who passes | What it allows |
|---|---|---|
| `app.teaches(class)`, unchanged in meaning: reads `teachers`, which stays a **table of home-class teachers** | the teacher of that home class; the owner as admin through his own functions | everything it allows today: the roster, reset, unlock, remove, restore, delete, the class's full view |
| `app.reads_subject(class, subject)`, new | a teacher assigned to that subject for the class, its grade, or a group with pupils of it | **reads only**, through security-definer functions, filtered by subject: names, points, stars and how often a child played, in her subject. No progress blob, no raw answers, no lock or code details, no roster |

`teacher_assignments` (subject teachers of a class, a grade or a group) is a separate table that never feeds
`app.teaches`. `tests/db.py` proves it: a grade teacher and a group teacher call every write function and policy of
0002 to 0009 on a pupil of the grade and get `not your pupil` (42501), and read only their subject.

### Subject groups ("each class is a different colour"), after version 1

- A **group** belongs to one grade and one subject, and has a label and a colour (`subject_groups`). A colour name is
  a label, not a secret.
- A pupil has **one home class** and, **per subject, at most one group** (`group_members`, primary key
  `(pupil_id, subject)`). A trigger and the setting function both check that the group's grade is the pupil's grade and
  its subject is that subject.
- **Who sets it**: the grade's subject coordinator (a teacher assigned to that subject for the whole grade) or the
  owner, through one function that writes a `group_events` row per change. Never the child: no grant on the table for
  a pupil's session. **[owner, with the teacher]**
- **Moving a child** between groups changes only that row. Answers, points and item history stay with the child (they
  are keyed by pupil and item, never by group).
- Content (section C) and boards can be scoped to the grade, a home class or a group. A pupil sees what is released
  to their grade, their class, and their group for that subject.

### Moving a pupil to another class

One function, for the owner or a teacher of **both** classes (`app.teaches` on each). It checks that the name is free
in the new class (`unique (class_id, name_key)`, under the name locks of both classes, taken in a fixed order), moves
the pupil, ends their sessions (as `teacher_reset` does), and writes an audit row. Their record goes with them. A move
to another grade also clears their groups.

### Schema (append-only migrations; version 1 has the first seven rows)

| Table | Columns | Notes |
|---|---|---|
| `schools` | `id`, `name` | One row. Saves a reset if a second school ever joins. |
| `grades` | `id`, `school_id`, `level` (1 to 12), `label` (e.g. "ה׳"), `school_year` | One row per grade per year. The school year lives here only. |
| `classes` | + `grade_id` | `grade` (text, today) is replaced by `grade_id`. See "The limbo class" below. |
| `items`, the ledger, `pupil_totals` | + `subject` | Points and totals per subject (section A). |
| `teacher_assignments` | `user_id`, exactly one of `class_id`, `grade_id`, `group_id`; `subject`, `granted_by`, `granted_at` | Subject teachers. Feeds `app.reads_subject` only, never `app.teaches`. |
| `admins` | `user_id` | The owner. |
| `private.admin_events` | who, what, when, on what | Append-only audit of the owner's actions (classes, codes, teachers, moves). |
| `subject_groups`, `group_members`, `group_events` | above | After version 1. |
| `content_*` | section C | After version 1. |

**The limbo class.** `teacher_remove_pupil` (0009, line 57) creates a class named `removed` for each class's removed
pupils, with no grade. A `not null` on `classes.grade_id` would break it. So the new migration first replaces
`teacher_remove_pupil` with a version that gives the limbo class its home class's grade, fills `grade_id` for limbo
classes that already exist (from `private.limbo`), and only then sets `grade_id not null`. `tests/migrations_check.py`
already runs new migrations on a database with a removed pupil in it, so it proves the order works.

### Row-level security, reader by reader

| Reader | Sees |
|---|---|
| Anonymous | nothing (`ping()` only, as today) |
| Pupil (session) | own row and record; the class board; later the grade board (classes only) and their group's board; levels released to their grade, class or group; nothing else |
| Home-class teacher | as today, for her class |
| Subject teacher (class, grade or group) | through functions only: names, points and stars of the pupils in her scope, in her subject |
| Revoked teacher | nothing, at once (her row is gone; a session made before the revoke reads nothing; tested) |
| Admin | everything, through security-definer functions only (no direct table rights) |
| Server key | everything; never in the browser or in GitHub |

`backend_health` (0004, redefined in 0007) shows the whole project's state (database size, unreadable addresses in
the last day) to any teacher. That is fine for one class. With many classes it becomes the owner's: teachers see only
`ok` or `warn`, and their own reset count.

The reader matrix in `tests/db.py` grows to: a pupil of 4A, of 4B and of 5A; a 4A pupil in the blue English group with
a 4B pupil in the same group, and a 4A pupil in the red group; a removed (limbo) pupil; a pupil of last year's class;
a 4A home-class teacher; a 4th-grade English teacher; a blue-group teacher; a revoked teacher; a stranger with a
Google account; anonymous. Each one against each table, view and function, including `group_events`,
`private.admin_events`, `backend_health`, and the storage bucket's policies (section C).

### Leaderboards

- **Class board**: as today (`class_board`), per subject and per school year.
- **Grade board** (after version 1): **classes only**, each class with its total or average points and active
  pupils. No child's name leaves their class. **[owner]**
- **Group board** (after version 1): first name or nickname and points, like the class board, because the children
  of a group learn together in one room. When two children in a group share a first name, the board adds their class
  ("Noa, 4B"). **[owner]**
- No school-wide board of children.

### Many children at one school address (sign-in capacity)

A school is usually one address on the internet. Today's limits, all per calling address:

| Limit | Where | Value | What it means at a school |
|---|---|---|---|
| Registrations an hour | `register_ip_hour` (0001, line 340) | 60 | the 61st child registering in an hour is told to wait |
| Function calls of any kind an hour | `ip_hour` (0004, line 8) | 120 | registrations, sign-ins and "I forgot my code", together |
| Wrong class codes an hour | `class_ip_hour` (0001, line 339) | 30 | 30 mistyped codes lock code entry for the **whole school's address** for the rest of the hour |
| Supabase Auth token checks | project setting (`BACKEND.md` section 9, step 8) | 150 per 5 minutes, raised for one class | every sign-in and registration passes through our functions, which share **one** address at Supabase Auth: a project-wide limit, not a school-wide one |

One class (about 35 children) fits all four. A grade of 5 classes registering at 8:00 does not: refused after about
60 children, and a handful of mistyped codes can lock the address for everyone.

What changes:

- **Counted per address and class**, not per address only: registrations, calls and misses keyed by (address,
  class), with a higher per-address ceiling as the last guard (for example 400 calls an hour). A mistyped code has no
  class, so wrong codes are counted per (address, the code's first two characters), with a per-address ceiling of 150
  an hour. The numbers are tuned on the rehearsal project.
- **One class switches per day**, its registration spread over the lesson. The Auth token-check setting is raised
  to fit one class at a time (150 per 5 minutes covers 35 children with room), never a whole grade at once.
- After registration, sign-ins spread by themselves (classes start at different times). At 15 classes the busiest
  five minutes may need about 300 token checks: the owner raises the setting before that (free).

### Growth: which free-plan limit comes first, and when

From `docs/BACKEND.md` section 6 (35 pupils a class, 80 answers per pupil per school day): raw answers are about
12 MB a class a month. What section 6 left out:

- `answer_daily` (0001, line 141) is **never deleted**: about 30 MB per class per school year.
- The auth tables (`auth.users`, sessions, refresh tokens, `auth.audit_log_entries`) are not measured yet. A rough
  guess is 1 KB a sign-in, about 6 MB per class per year. The server role may delete old `auth.audit_log_entries`
  (`BACKEND.md` section 9, check 7), so `maintenance()` can keep this small. To be measured on the rehearsal project.

The database brake is at 350 MB (the limit is 500 MB). The other limits are far away: egress (5 GB a month) carries
sign-ins and small reads, and auth users stay far under 50,000.

| Classes | With today's settings (raw answers for 90 days, `answer_daily` for ever) | With the proposal (below) |
|---|---|---|
| 1 | 36 MB of raw answers, plus about 36 MB a year: the brake after about 8 years | about 22 MB, flat |
| 5 (one grade) | 180 MB, plus about 180 MB a year: **the brake in about 1 year** | about 110 MB, flat |
| 15 | 540 MB of raw answers alone: **over the 500 MB limit in about 3 months** | about 330 MB: at the brake. With raw answers kept 14 days: about 230 MB |

The "with the proposal" column assumes the auth clean-up runs. Without it, add about 6 MB per class per year.

The proposal is three settings and one roll-up, decided before the first answer:

1. Raw answers kept **30 days** (not 90), then rolled into `answer_daily` (about 12 MB a class).
2. `answer_daily` kept **90 days**, then folded into one row per pupil and item (`answer_item`, a new table: about
   2 MB a class). That is all the game and the teacher need for "what is weak".
3. **Item history deleted at the end of the school year** (after the totals per subject are kept), so the database
   does not grow with time.
4. The brake stays at 350 MB, and `backend_health` shows the owner the database size per class.

So: **one grade fits easily; the whole school (about 15 classes) needs raw answers kept 14 days and the auth
clean-up.** The first limit hit is always the database, never egress or auth users.

---

## C. New levels from teachers' material (after version 1; teachers do not publish to children)

**A teacher sends material, we build the level, the owner releases it.** Nothing a teacher types or uploads ever
reaches a child as it is. What a child sees went through the engineer, the lead's review and the teacher's own check
of her words.

```
teacher: request (+ PDF or pages) -> private inbox -> checked copy -> engineer builds a level -> lead reviews
   -> teacher checks the preview (her words exactly) -> owner releases to a grade / class / group -> pupils
```

Until this exists, the teacher gives her material to the owner, and he passes it on by hand.

### The request

| Field | Rule |
|---|---|
| scope | one grade, class or group among those she is assigned to (checked on the server) |
| subject | one of her assignments |
| pages | free text up to 200 characters, e.g. "Fantastic 5, pages 12 to 14" (a request may name pages and upload nothing) |
| note | up to 500 characters, for the owner and the engineer only |
| due date | the day she wants it in class: a wish, not a promise |
| files | 0 to 5 files, PDF, JPEG or PNG, up to 10 MB each |

Tables: `content_requests` (the fields above, `created_by`, `status`), `content_request_files` (`request_id`, path,
bytes, sha256, the checked type, `deleted_at`) and `content_request_events` (append-only: each status change, who,
when, the message to the teacher). Only security-definer functions write them; a teacher reads her own through
`my_requests()`. **She sends blank pages only**: no page a child has written on, no children's names. The upload
screen says so, and the engineer refuses a page that carries a name.

Status she sees on `teacher.html`: `new`, `seen`, `building`, `check` (a preview is ready: the real game screen, fed
the built level; she confirms her words or says what to fix), `released` (to which scope, from which day),
`declined` (with a reason), `withdrawn`. She can cancel until `building`.

### Who can upload, how much, what

- **Only a signed-in teacher with an assignment**, for a scope she is assigned to, and the owner. Never a pupil (no
  pupil session reaches these functions or the bucket), never an anonymous caller.
- **Caps** in `settings`: 5 files a request, 10 MB a file, 5 requests a day and 20 a month per teacher, and an inbox
  brake at 600 MB stored.
- **Types**: PDF, JPEG, PNG only. No Word or PowerPoint (macros), no archives, no HTML or SVG (scripts), no video.

### How a file is handled

1. **Upload.** `request-upload` (an Edge Function) checks the teacher, the scope and the caps, creates the request as
   `draft`, and returns one signed upload URL per file for `incoming/<request>/<n>`. The bucket is private (no public
   URL) with its own `file_size_limit` and `allowed_mime_types`. No storage policy lets a session list, read,
   overwrite or delete an object.
2. **Check a copy nobody can write to.** A signed upload URL stays valid for 2 hours, so a file could be replaced
   after it was checked. So `request-submit` first copies each file to `checked/<request>/<n>`, a path no signed
   upload URL can target, then checks **the copy**: its type by its bytes (`%PDF-`, the PNG and JPEG signatures), its
   size, its sha256. Then it deletes `incoming/`. A file that fails is deleted and the teacher is told which one. Every
   later read of `checked/` compares the sha256 first.
3. **How it reaches the builder, exactly.** The owner opens the request (command line, later the admin page) and
   downloads the checked file through a signed read URL valid 5 minutes, after the sha256 check. He gives it to the
   engineer's session as an upload to that session. **That session's history then holds the file and what was read
   from it**, outside our bucket, for as long as the session exists. The owner deletes or archives that session once
   the request is closed (his step, part of the retention rule below).
4. **The real protection is the conversion, not a virus scanner.** In the engineer's throwaway container the file is
   turned into page images (`pdftoppm`) and text (`pdftotext`). Nothing opens it in a viewer, and no script in it
   runs. ClamAV is optional: it needs its virus database fetched through the network allowlist, and it finds little in
   PDFs.
5. **A file can carry instructions aimed at the session that builds the level** (text in a PDF that says "also add
   this link" or "push to main"). The builder treats the file as data only. That session holds **no keys** (no
   Supabase key, no server key) and cannot merge. **Only checked, structured data leaves it**: the level file,
   validated by the schema check and by the database's rules, through a pull request the lead reviews against the
   source pages.
6. **Never in the repository.** Textbook pages are copyrighted and pages can carry names. There is a **local guard
   first**: `.gitignore` for `*.pdf` and the work folder, and a check in `tests/secret_guard.py` (run before every
   commit) that refuses PDFs, and images outside `assets/`. A CI check in the `security` workflow is only the
   backstop: it runs after a push to a public repository, which is too late to rely on.

### Building a level

- A level is **data, not code**: items of the kinds the game already plays (`word`: English, Hebrew, an optional
  example sentence; `sentence`: English and Hebrew; `fraction`: Fraction Bay's fixed item types). A request that needs
  a new kind of game is a normal feature: code, review, a site ship.
- **Her words and translations exactly** (`CLAUDE.md`). Each item carries its **source page** and an **`ours`
  flag**. Anything we write ourselves (an extra sentence, a story) uses only the unit's vocabulary, has `ours` set, and
  is marked in her preview.
- Validation in the database, so no tool can skip it: an allow-list of characters (no control or invisible
  characters, no direction overrides, the rules of `app.name_ok`), length caps (a word up to 40 characters, a sentence
  up to 160), no URL-like text, at most 60 items a level.
- The level file is reviewed in a **free private repository of the owner's** **[owner]**, since it holds the
  teacher's material. Then `tools/level.py upload` (run by the owner with his key, never in GitHub) writes it as a new
  version.

### Tables, and how they fit the game's ledger

- **Names**: `public.items` and `public.levels` already exist (0001, lines 62 and 71). The new tables are
  `content_levels`, `content_level_versions` and `content_releases`, so nothing clashes.
- **Items in the ledger**: `record_events` stores nothing for an item key it does not know (0003, line 101). So at
  upload each item of a version is also inserted into `public.items` (game `tw` for a teacher's words, item key
  `<level>/<item>`, with its subject). These rows **stay after a withdraw**, so children's answers and points on a
  withdrawn level remain valid.
- **A published version never changes**: a trigger refuses any update or delete of a released version. A typo fix is a
  new version with the same item ids. **A changed answer is a new item id**, so old answers are never counted against
  a new right answer.

### Release and withdraw, without a site ship

- `content_releases` (`level`, `version`, scope: one of grade, class or group, `opens_on`, `released_by`,
  `withdrawn_at`, `withdrawn_by`). **The owner releases**, and only a version the teacher has confirmed. **[owner]**
- **The game** asks once on start-up: `my_levels()` returns the released level ids and versions for the pupil's grade,
  class and groups (scope from the pupil's own rows, never from the client). It downloads `level_items(level,
  version)` only for a version it has not cached, and keeps them by version. Pupils have no read right on the tables:
  only these two functions, in the reader matrix.
- **Withdraw** sets `withdrawn_at`. The level is gone at the next online start-up. **A device that stays offline
  keeps a withdrawn level until it next starts online.** Answers and points on it are kept.
- **Showing a level's text**: the game writes HTML in 26 places today (`innerHTML`: 15 in `js/main.js`, 11 in
  `js/math.js`). Every place that could show a level's text uses `textContent` instead, and a test feeds a level whose
  words are an `<img onerror>` tag and checks they appear as text.
- **The page's content policy**: `connect-src` adds only `https://<project ref>.supabase.co`, nothing else.

### Free-plan numbers (1 GB file storage, 5 GB egress a month, 500 MB database)

| | Worst case at the caps | Expected |
|---|---|---|
| Inbox storage | 10 teachers at 20 requests a month with 2 files of 5 MB: 2 GB a month, so the **brake refuses uploads above 600 MB** and tells the owner | a few requests a week, about 2 MB a file: under 100 MB with the retention below |
| Egress, inbox | each file read once or twice: about twice what was uploaded | under 200 MB a month |
| Egress, levels | 5 to 20 KB a level; 500 pupils x 20 levels x 10 KB = 100 MB once, then only new versions | under 100 MB a month |
| Database | requests, events and levels: a few MB a year | |

### Retention for uploads, and what it covers

- **The bucket** (`incoming/` and `checked/`): a file is deleted **30 days after its request is released, declined,
  cancelled or withdrawn, and 60 days after upload at most** **[owner]**. Deletion goes through the Storage API (a
  nightly scheduled function with the server key), not by deleting rows in `storage.objects` (that would leave the
  file). The file row keeps `deleted_at` and the sha256, never the file.
- **The engineer's session** holds the file and what was read from it until the owner deletes or archives that
  session. The promise above covers it only when the owner does this on the same schedule. The throwaway container
  itself is gone when the session ends.
- **The repositories** never hold a file. The private repository holds only the level's words, with page numbers.
- The request record (scope, pages, status, events; no file) is kept a year.
- Backups (`docs/BACKEND.md` section 6) do not include the bucket.

### What stays hand-curated

The built-in units, the recorded voice (no browser speech for content, ever: a new level has no voice until we record
it, and the game shows it as text), all art, the mock exam.

---

## D. Privacy, for the owner (facts to decide with, not legal advice)

Today this is one parent's tool for one class. A whole school is a different thing: other parents' children, other
teachers' material, the school's name on it. Before it grows past one class:

- **The principal's written agreement**: who is responsible for the children's data (the school or the owner), and
  that the school agrees to this tool. One page, signed, kept by the owner.
- **A note for parents** before switch day: what is stored (first name or nickname, class, answers and points; the
  4-digit code and the pictures only as hashes), where (Supabase, EU region), for how long (item history to the end of
  the school year, totals while the child is in the school), how a child's data is deleted (`teacher_delete_pupil`;
  the 14 days of "remove from class"), that a leaver's data is deleted, and that **Claude sessions (an AI service)
  process the teachers' material and the code**, never the children's names or answers.
- **Teachers send blank pages only**, never pages with children's names or handwriting (section C).
- **A leaver**: when a child leaves the school, their data is deleted, not kept "in case". **[owner]**

---

## Phases (honest estimates, engineer days, about two review rounds each)

| # | Step | Who | Days | Depends on |
|---|---|---|---|---|
| 1 | The owner's decisions below, and the principal's agreement | owner | — | — |
| 2 | Version 1 schema: schools, grades with school year, `classes.grade_id` (with the limbo class), subject on items, points and totals, `teacher_assignments` with `app.reads_subject` (`app.teaches` unchanged), admins and the admin audit, the address-and-class limits, the 30-day window, the per-item roll-up, the year-end deletion; the reader matrix and the write-refusal tests in `db.py` | engineer | 10 to 15 (2 to 3 weeks) | 1 |
| 3 | The owner's command line: grades, classes, codes, teachers and assignments, moves, all audited | engineer | 3 | 2 |
| 4 | The fresh start: the cleanup migration (Sheet import, copy phase, `legacy` paths), the trial switch with its own device storage and a trial class, LIVE_STAGE and PHASE3 rewritten | engineer + client engineer | 4 | 2 |
| 5 | Security review of 2 to 4, a rehearsal on a second free project (the address limits, the auth table sizes), a week on the trial devices | lead, reviewer, owner, teacher | 5 | 4 |
| 6 | **Switch day for one class (version 1)** | owner, lead | — | 5 |
| 7 | More classes, one a day; subject teachers' read screens | engineer + UI designer | 3 | 6 |
| 8 | Subject groups, the group board and the grade board | engineer + client engineer + UI designer | 5 | 7 |
| 9 | The admin page | engineer + UI designer | 4 | 7 |
| 10 | The upload inbox and levels (section C) | engineer + client engineer + UI designer | 10 to 15 | 7 |

Version 1 (steps 2 to 6) is about five weeks of work and about two months with reviews. Each step after it is its own
proposal and review.

---

## Decisions that are the owner's (each with the recommended answer)

| # | Decision | Recommended |
|---|---|---|
| 1 | How long the Sheet stays as the way back, accepting that what is played on the new backend in that time does not go back | two weeks |
| 2 | The grade board | classes only, not children's names; not in version 1 |
| 3 | The group board | first names, with the class added when two share a name; not in version 1 |
| 4 | Points and boards across school years | points kept for good; boards restart each September |
| 5 | Item history | deleted at the end of each school year |
| 6 | Raw answers | kept 30 days (14 days if the whole school joins) |
| 7 | Who is an admin | the owner only |
| 8 | Codes | one random class code per class; the class decides the grade |
| 9 | Who moves a child between groups | the grade's subject coordinator only |
| 10 | The upload inbox | after version 1; until then the owner forwards material by hand |
| 11 | Upload retention | deleted 30 days after the request closes, 60 days at most; the builder's session deleted on the same schedule |
| 12 | Where a level's text is reviewed | a free private repository of the owner's |
| 13 | Who releases a level | the owner only |
| 14 | The note for parents | written and sent before switch day |
| 15 | The principal's written agreement | before the second class joins |
| 16 | Google sign-in for teachers | Testing mode with a named list while it is a few teachers |
| 17 | A leaver's data | deleted by the home-class teacher within 30 days |
| 18 | Classes switching | one class a day, never a whole grade at once |
