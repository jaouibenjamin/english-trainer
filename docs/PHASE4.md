# Phase 4 proposal: a fresh start, the whole school by grade and class, and new levels from teachers' material (DRAFT)

Status: a proposal for the lead and the owner, written from the owner's decisions of 2026-11-26 (and his additions of
the same day: codes per grade and class, subject groups, and the upload inbox instead of teachers publishing). The
owner will check the details with the teacher, so this is direction, not final. No code yet. It
builds on `docs/BACKEND.md` (the Supabase backend, Phase 1), `docs/PHASE3.md` (the teacher on Supabase) and the
open pull requests #82, #83, #86, #87, #93, #94. Decisions that are the owner's are marked **[owner]** and listed at
the end.

The three decisions:

- **A. Fresh start.** When the class moves to the new game, everyone starts from zero, in English and in Fraction Bay,
  with a new sign-in. Nothing is imported from the Sheet. The Sheet (backend/Code.gs version 3, deployed today) stays
  as it is for today's class until the new game is live and fully tested; then it is switched off.
- **B. The whole school, by grade (שכבה) and class.** A code per grade and, under it, a code per class. Every pupil
  belongs to one home class, and every class to one grade. In English and in math the grade is also split into
  **subject groups** ("each class is a different colour") that cut across home classes; a teacher puts a pupil in a
  group, never the child. Leaderboards by class, by grade and by group. Teachers sign in and are attached to the
  classes, grades or groups and subjects they teach.
- **C. New levels from teachers' material.** Teachers do **not** publish to children. A teacher uploads a PDF or
  names textbook pages; it reaches us through a private inbox; the engineer builds a level from it (her words copied
  exactly, reviewed as always); the owner releases it to a grade, class or group, and can withdraw it, without a site
  ship.

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
| `dual` mode in `js/api.js` (each answer sent to both backends, gates 5 to 8) | the way to compare | **not needed for existing pupils**. See "What I would keep". |
| Runbook E (a test pupil copied from the Sheet), F (the class copies), G (counted equals played, day 1) | needed | **replaced** by a simpler trial and a switch day (below). |
| `docs/PHASE3.md` "before the Sheet is switched off": counted equals played for 3 days, the Sheet's copy deleted on a date | conditions | **simplify**: no copy to compare or delete. What stays: the teacher used the new screen, the pupil screens are approved, backups and a restore drill, the switch-day runbook, and the privacy note for parents. |
| `PHASE3.md` step 5, the "first sign-in of a pupil who came from the Sheet" flow (a new code and two pictures) | one of three pupil flows | **goes**. Two flows stay: registration, and "I forgot my code" (pictures, or the teacher's one-time code). |

### What I would keep, and why

- **The device switch for trying the new game** (today `?dual=1`, `everyone: true`). Renamed to a plain trial switch
  (for example `?new=1`): only a device that opened the game once with it talks to Supabase, everyone else stays on
  the Sheet. This is how the teacher and the owner test the new game in the real classroom, side by side, without
  touching the class. It is the same code that gates 5 to 8 reviewed, with the copying removed.
- **The adapter's session guards** (one operation bound to one session and one pupil, the late-answer guards, the
  64 KiB keepalive budget, the displaced-tab dialog): they protect the new game too.
- **Everything of Phase 3** (teacher sign-in, screen, actions, lock scope, remove with undo): unchanged.
- **The Sheet untouched until the switch**, and for a short way back after it **[owner: how long; I suggest two
  weeks]**: `config.js` can point the class back at the Sheet in one commit. After that, the Sheet is switched off
  (the owner's own step; this team never edits `backend/Code.gs` or the Sheet).

### Switch day, in short (the full runbook is a later PR)

1. The new game has run on the trial devices for at least a week (the teacher and the owner), and the security
   reviews are green.
2. The teacher gets her class code (made by the owner as admin, section B) and hands it out in class.
3. Each child registers: first name or nickname, a 4-digit code, two secret pictures. Everyone starts at zero.
4. `config.js` on `main` points the class at the new game. The Sheet stays readable for the way back.
5. After the way back closes, the owner switches the Sheet off and deletes its copy of the class (names, progress,
   code hashes) on a stated date. This goes into the note for parents.

### What must be decided before the fresh start, so that there is no second reset

These are cheap now and expensive later, because every row written after the start depends on them:

- **Ids**: every row keyed by a uuid (already so). A pupil, a class, a grade and a content item keep their id for
  ever, so answers and points never need rewriting.
- **School year**: classes belong to a school year. A pupil moves to next year's class by a teacher's or the owner's
  action (their record goes with them); last year's class is archived, not reused. **[owner: do points carry over
  to the next year, or does the board start again each September?]**
- **Grade on the class, not on the pupil**: a pupil's grade is always their class's grade. The pupil never states
  either.
- **Names**: unique per class (already `unique (class_id, name_key)`). Two children with the same first name in one
  class need a nickname or an initial (the class list decides), never a surname.
- **Codes**: a grade code and a class code under it (section B), random, no grade or class name in them (a code that
  encodes the grade can be guessed across classes). The server looks them up and decides class and grade.
- **Subject groups from the start** (section B): a pupil's group is a row per subject, so adding groups later needs no
  change to answers or points. A pupil in no group yet simply sees grade and class content.
- **Level ids**: a level and each of its items keep their id across versions (a typo fix is a new version, same
  items), so a child's history on an item survives it (section C).

---

## B. The whole school, by grade and class

### The rule that answers the owner's worry ("a child can declare any class")

A child never declares a class, a grade or a group. The **codes** the teacher hands out decide class and grade, on the
server, at registration; a teacher decides the group. After that:

- the pupil's row has no column the pupil can write (no `update` grant on `pupils` for a session, as today);
- every read is filtered by row-level security through `app.class_id()` / `app.grade_id()`, functions that read the
  pupil's own row, never anything the client sends;
- only a teacher of that class (or the owner as admin) can move a pupil, through one function that checks both
  classes and writes an audit row.

A child who learns another class's code can register a second name there. That is the same risk as today (the code
is a class secret), handled as today: a roster per class (`roster_only`, on by default), so only names the teacher
listed can register, and a new code when one leaks (`admin-class rotate`).

### Codes: one per grade, and one per class under it

- **What the child types** is one code, printed on the board as two parts: `KQ7MXT-4H9P`. The first part is the
  **grade code** (6 characters), the second the **class code** (4 characters), both from the alphabet without
  look-alikes. One field, the dash optional, so a 10-year-old types one thing, as today.
- **On the server** the grade code finds the grade (`private.grade_codes`, a keyed hash as today), and the class code
  is looked up **only among that grade's classes** (`private.class_codes` gets `grade_id`; unique per grade). Wrong
  either way is the same answer and the same counted miss (`class_misses`, today's rate limits), so a child cannot
  learn which half was wrong.
- **Neither half works alone.** The grade code never shows a list of classes to choose from (that would be the
  self-declaration again), and a class code means nothing without its grade code.
- **Rotation**: a new grade code (for example each September, or when it leaks to another grade) is one action and
  keeps every class code under it; a new class code changes one class only. Old codes stop at once; pupils who are
  signed in stay signed in, and the device remembers the class for the next sign-in, as today.
- **Strength**: 6 + 4 characters from 31 letters and digits is about 50 bits, behind the existing per-address and
  per-device limits. The codes are identifiers, not passwords (`docs/BACKEND.md` section 2): what protects a child is
  their own 4-digit code, pictures and the roster.
- **Not a teacher's key.** A grade code never gives a teacher anything; teachers come in by invite (below).

**[owner, with the teacher: one code in two parts as above (recommended), or two separate fields, or the grade code
only for the teacher's screen and a class code for the children]**

### Subject groups ("each class is a different colour")

In English and in math the children of a grade are regrouped by level, across home classes. The model:

- A **group** belongs to one grade, one subject and one school year, and has a label and a colour (`subject_groups`).
  A colour name is a label, not a secret.
- A pupil has **one home class** and, **per subject, at most one group** (`group_members`, primary key
  `(pupil_id, subject)`). A trigger and the setting function both check that the group's grade is the pupil's grade and
  its subject is that subject.
- **Who sets it**: a teacher assigned to that subject for the whole grade, or the owner, through one function
  (`teacher_set_groups(subject, [(pupil, group)])`) that writes an audit row per change. Never the child: no grant on
  the table for a pupil's session, and nothing the client sends is trusted. **[owner, with the teacher: can the
  teacher of one group also move children in and out of her group, or only the grade's subject coordinator?]**
- **Moving a pupil** between groups mid-year changes only that row. Answers, points and item history stay with the
  pupil (they are keyed by pupil and item, never by group).
- **Scopes**: content (section C) and boards can be scoped to the grade, a home class, or a subject group. A pupil
  sees what is released to their grade, their class, and the group they are in for that subject.

### Schema (new tables and columns; one migration, append-only)

| Table | Columns | Notes |
|---|---|---|
| `schools` | `id`, `name` | One row now. Costs nothing and saves a reset if a second school ever joins. |
| `grades` | `id`, `school_id`, `level` (1 to 12), `label` (e.g. "ה׳"), `school_year` | One row per grade per year. |
| `classes` | + `grade_id` not null, + `school_year` | `grade` (text, today) is replaced by `grade_id`. |
| `private.grade_codes` | `grade_id` pk, `code_lookup` unique | The grade half of the code, a keyed hash like today's class codes. |
| `private.class_codes` | + `grade_id`; `unique (grade_id, code_lookup)` | The class half, looked up only under its grade. |
| `subjects` | `key` (`english`, `math`), `label` | Fixed list, added by the owner. |
| `subject_groups` | `id`, `grade_id`, `subject`, `label`, `colour`, `school_year` | The regrouping per subject. |
| `group_members` | `pupil_id`, `subject`, `group_id`, `set_by`, `set_at`; pk `(pupil_id, subject)` | At most one group per pupil per subject; set by a teacher only. Changes go to `group_events` (append-only). |
| `teacher_assignments` | `user_id`, exactly one of `class_id`, `grade_id`, `group_id`, `subject`, `role` (`teacher`), `granted_by`, `granted_at` | Replaces `teachers` (kept as a view for the existing functions). A grade-wide assignment is how a 4th-grade English coordinator reaches all 4th-grade classes and groups. |
| `private.teacher_invites` | `code_lookup` (keyed hash), one of `class_id`, `grade_id`, `group_id`, `subject`, `expires_at`, `used_by`, `created_by` | One-time, 7 days, shown once to the owner. |
| `admins` | `user_id` | The owner. Nobody becomes an admin through the app. |
| `content_requests`, `levels`, `level_versions`, `level_releases`, … | section C | |

### How a teacher becomes a teacher of a class

1. The owner (admin) creates an invite for one class (or one grade, or one group) and one subject in the admin page. The code is
   shown once and stored only as a keyed hash, like class codes.
2. He gives it to the teacher in person or on the phone, never in a group chat.
3. The teacher signs in with Google on `teacher.html` and types the invite code. The server checks it (unused, not
   expired, rate-limited per teacher and per address like the pupils' codes), writes the assignment, and marks the
   invite used.
4. The owner sees every assignment and can revoke one at any time.

The alternatives are worse. "Any teacher with a school address": a school Google Workspace may not exist, and
anyone with an address could join. "Teachers pick their class": that is exactly the self-declaration the owner wants
to avoid.

### Row-level security, reader by reader

| Reader | Sees |
|---|---|
| Anonymous | nothing (`ping()` only, as today) |
| Pupil (session) | own row and record; the class board; the grade board; their group's board; levels released to their grade, their class or their group for that subject; nothing else (not even the name of their group's other members outside the board) |
| Teacher | pupils, boards and views of the classes, grades and groups she is assigned to, for her subjects; her own content requests and their status; a preview of levels built for her requests |
| Admin | everything, through security-definer functions only (no direct table rights) |
| Server key | everything; never in the browser or in GitHub |

Every row in every table is reached through one of these, and `tests/db.py` gets a matrix like today's: a pupil of
class 4A, a pupil of 4B, a pupil of 5A, a 4A English teacher, a 4th-grade math teacher, a stranger with a Google
account, anonymous; plus a pupil of 4A in the blue English group with a pupil of 4B in the same group, and a 4A
pupil in the red group. Each one against each table, view and function.

### Leaderboards

- **Class board**: as today (`class_board`): first name or nickname, points, words, streak.
- **Grade board**, two options **[owner]**:
  1. *Classes only* (recommended for the first version): each class of the grade with its total or average points
     and active pupils. No child's name leaves their class.
  2. *Children of the grade*: first name or nickname **and class** ("Noa, 4B"), top 20 only. A child's name is then
     seen by about 100 children instead of 30.
- **Group board** **[owner]**: the children of a group learn together in the same room, so a board with first name
  or nickname and points, like the class board, is recommended. The other option is points per group only.
- No school-wide board of children.

### The free plan for a whole school

From `docs/BACKEND.md` section 6 (35 pupils a class, 80 answers a day, the 90-day roll-up):

| Classes | Database, steady | Comment |
|---|---|---|
| 1 | about 40 MB | today's plan |
| 5 (one grade) | about 200 MB | fits |
| 10 | about 400 MB | over the 350 MB brake |
| 15 (a small school) | about 600 MB | over the 500 MB limit |

So a whole school needs one of: raw answers kept 30 days instead of 90 (roll-up sooner; about 15 MB a class), or
fewer answer rows (one row per item per day instead of per answer). Both are settings and a roll-up change, not a
redesign. I suggest the 30-day window from the start (decided now, while there is no data). Levels are small
(5 to 20 KB each). Egress stays far under 5 GB if the game caches levels by version; the upload inbox has its own
numbers and brake (section C). Auth users stay
far under 50,000. Edge Function calls only grow with sign-ins.

---

## C. New levels from teachers' material (teachers do not publish to children)

The owner's flow, which is safer than letting teachers publish: **a teacher sends material, we build the level, the
owner releases it.** Nothing a teacher types or uploads ever reaches a child as it is. What a child sees went through
the engineer, the lead's review and the teacher's own check of her words.

```
teacher: request (+ PDF or pages)  ->  private inbox  ->  engineer builds a level  ->  lead reviews
   ->  teacher checks the preview (her words exactly)  ->  owner releases to a grade / class / group  ->  pupils
```

### The request (what a teacher sends)

A **request** is a record, with or without files:

| Field | Rule |
|---|---|
| scope | one grade, one class or one subject group, among those she is assigned to (checked on the server) |
| subject | `english` or `math`, one of her assignments |
| pages | free text up to 200 characters, e.g. "Fantastic 5, pages 12 to 14" (a request may name pages and upload nothing) |
| note | up to 500 characters, shown to the owner and the engineer only |
| due date | the day she wants it in class; at least 2 school days ahead, as a wish, not a promise |
| files | 0 to 5 files, PDF, JPEG or PNG, up to 10 MB each (below) |

Tables (append-only migration): `content_requests` (the fields above, `created_by`, `status`),
`content_request_files` (`request_id`, storage path, bytes, sha256, the checked type, `deleted_at`) and
`content_request_events` (append-only: every status change, who, when, the message to the teacher). Only security-
definer functions write them; a teacher reads her own through `my_requests()`.

### Who can upload, and how much

- **Only a signed-in teacher with an assignment**, for a scope she is assigned to, and the owner. Never a pupil (no
  pupil session reaches any of these functions or the bucket), never an anonymous caller.
- **Caps** (in `settings`, tunable without a migration): 5 files a request, 10 MB a file, 5 requests a day and 20 a
  month per teacher, and an inbox brake (below). Above a cap the request is refused with a plain reason.
- **Types**: PDF, JPEG, PNG only. No Word or PowerPoint files (macros), no archives, no HTML or SVG (scripts), no
  video. The teacher page says "save it as PDF" for anything else.

### How a file is handled (virus-safe, private)

1. `request-upload` (an Edge Function) checks the teacher, the scope and the caps, creates the request as `draft`,
   and returns one **signed upload URL** per declared file, for a fixed path `inbox/<request id>/<n>.<pdf|jpg|png>`.
   The bucket `inbox` is **private** (no public URL), with the bucket's own `file_size_limit` (10 MB) and
   `allowed_mime_types` set. There is no storage policy that lets a session list, read, overwrite or delete an object:
   the signed URLs are the only way in, and none is ever made for reading by a teacher or a pupil.
2. `request-submit` reads each file once on the server, checks its **type by its bytes** (`%PDF-`, the PNG and JPEG
   signatures), not by its name or the browser's word, checks the size, and stores the sha256. A file that fails is
   deleted at once and the teacher is told which one. Then the request becomes `new`.
3. **Nothing is ever run, rendered or served from an upload on the server or to a child.** Files are opened only by
   the owner (a signed read URL from the admin page, valid 5 minutes) or in the engineer's throwaway cloud container:
   scanned with ClamAV (free) first, then read with `pdftotext` / `pdftoppm` (no JavaScript, no viewer plug-ins). The
   container is deleted at the end of the session.
4. **Never in the repository.** Textbook pages are copyrighted and worksheets can carry pupil names. A new CI check
   (in the `security` workflow) fails on any PDF, and on any image outside `assets/` that is not listed in
   `assets/sources.tsv`. The engineer copies into a level only the exercise content: no names, no scans.

### Status the teacher sees

On `teacher.html`, a list of her requests: `new` (sent), `seen` (the owner opened it), `building`, `check` (a
preview is ready for her: the real game screen, fed the built level; she confirms her words or answers with what to
fix), `released` (to which scope, from which day), `declined` (with a reason, e.g. "the pages are not readable"), and
`withdrawn`. Each change is a `content_request_events` row. She can cancel a request until it is `building`.

### Building a level (the engineer)

- A level is **data, not code**: a list of items of the kinds the game already plays (`word`: English, Hebrew, an
  optional example sentence; `sentence`: English and Hebrew; `fraction`: from Fraction Bay's fixed item types). A
  request that needs a new kind of game is a normal feature: a code change and a site ship.
- **Her words and translations exactly** (`CLAUDE.md`). Anything we write ourselves (an extra sentence, a story) uses
  only the unit's vocabulary and is flagged in the preview for her check.
- The same validation as for names today, in the database so no tool can skip it: an allow-list of characters (no
  control or invisible characters, no direction overrides), length caps (a word up to 40 characters, a sentence up to
  160), no URL-like text, at most 60 items a level. The game shows every value with `textContent`.
- The level goes through a pull request like any change (the engineer's security review, the lead's review), then
  `tools/level.py upload` (run by the owner with his key, never in GitHub) writes it as a new **version** in
  `level_versions`. A published version never changes; a fix is a new version with the same item ids.
- **[owner: where the level's text lives for review]**: in this public repository (as Unit 1 is today; fine for word
  lists and the teacher's own sentences), or in a free private repository of the owner's (if the teacher's material
  should not be public). The uploads themselves are never in either.

### Release and withdraw, without a site ship

- `level_releases` (`level_id`, `version`, scope: one of grade, class or group, `opens_on`, `released_by`,
  `withdrawn_at`, `withdrawn_by`). The owner releases from the admin page after the teacher's check; release is
  refused for a version the teacher has not confirmed. **[owner: may the teacher press "release" herself on a level we
  built and she checked, for her own scope only? Recommended: not in the first version.]**
- **The game** asks once on start-up: `my_levels()` returns the released level ids and versions for the pupil's grade,
  class and groups (security definer; scope from the pupil's own rows, never from the client). It downloads
  `level_items(level, version)` only for a version it has not cached, and keeps them in the browser by version. With no
  connection it plays the last levels it has. The built-in units stay in the repository and are always there.
- **Withdraw** sets `withdrawn_at`: the level is gone at the next start-up (and the game drops it from its cache).
  Children's answers and points on it are kept. A level can be re-released.
- Pupils have no read right on these tables: only the two functions, tested in the reader matrix (a 4th grader never
  gets a 5th-grade level, a red-group pupil never gets a blue-group level).
- "The same day or week" is honest for a level of a kind the game already plays: about half a day to two days of
  building plus a review round. The owner sees the due date in the inbox.

### Free-plan numbers (Supabase free: 1 GB file storage, 5 GB egress a month, 500 MB database)

| | Worst case at the caps | Expected |
|---|---|---|
| Inbox storage | a school of 10 teachers at 20 requests a month and 2 files of 5 MB: 2 GB a month; so the **inbox brake** refuses uploads above **600 MB** stored and tells the owner | a few teachers, a few requests a week, about 2 MB a file: 20 to 50 MB a month, under 100 MB with the retention below |
| Egress, inbox | each file read once or twice (owner, engineer): about twice what was uploaded | under 200 MB a month |
| Egress, levels | a level is 5 to 20 KB; 500 pupils x 20 levels x 10 KB = 100 MB once, then only new versions (cached) | under 100 MB a month |
| Database | requests, events and levels: a few MB a year | |

The brake is checked by `request-upload` (the sum of the inbox's object sizes) and reported by `maintenance()` and
`backend_health` next to the database brake.

### Retention for uploads

- A file is deleted **30 days after its request is released, declined, cancelled or withdrawn**, and in any case
  **90 days after upload**. **[owner: these two numbers]**
- Deletion goes through the Storage API (a nightly scheduled function with the server key), not by deleting rows in
  `storage.objects` (which would leave the file). The file row keeps `deleted_at` and the sha256, never the file.
- The request record (scope, pages, status, events; no file) is kept a year, then deleted by `maintenance()`.
- Copies in the engineer's container die with the container; the CI check above keeps them out of the repository.
- Backups (`docs/BACKEND.md` section 6) do not include the inbox bucket.

### What stays hand-curated

The built-in units, the recorded voice (no browser speech for content, ever: a new level has no voice until we record
it, and the game shows it as text), all art, the mock exam.

---

## Phases (honest estimates, engineer days, about two review rounds each)

| # | Step | Who | Days | Depends on |
|---|---|---|---|---|
| 1 | The owner's decisions below | owner | — | — |
| 2 | Schema: schools, grades, classes.grade_id and school_year, grade and class codes, subjects, subject groups and members, assignments (class, grade or group), admins; RLS and the reader matrix in db.py; registration decides class and grade from the two-part code | engineer | 4 | 1 |
| 3 | Admin page (owner only): grades, classes, codes and rotation, groups, teacher invites, revoke | engineer + UI designer | 3 | 2 |
| 4 | Teacher invite redemption on `teacher.html`; the screen scoped to her assignments and subjects; setting pupils' groups | engineer + UI designer | 3 | 3 |
| 5 | Grade and group boards (the chosen options) and the game's board screen | engineer + client engineer | 2 | 2 |
| 6 | Cleanup migration: the Sheet import, the copy phase and `legacy` paths removed; LIVE_STAGE and PHASE3 rewritten for a fresh start; the trial switch | engineer | 2 | 2 |
| 7 | New levels v1: the private inbox (bucket, `request-upload`, `request-submit`, caps, brake, retention job, the CI check against PDFs and stray images); requests and their status on `teacher.html`; levels, versions, releases, `my_levels()`, `level_items()`, `tools/level.py`; the teacher's preview and check; release and withdraw in the admin page; the game reader with the cache | engineer + client engineer + UI designer | 7 to 9 | 4 |
| 8 | Security review of 2 to 7, a rehearsal on a second free project, a week on the trial devices | lead, reviewer, owner, teacher | 5 | 7 |
| 9 | Switch day for the first class | owner, lead | — | 8 |

Steps 2 to 6 are about two weeks of work and one month with reviews. New levels (7) add about another month. After
that, each request is about half a day to two days of building plus a review round.
**The first class could move before step 7.** The fresh start, the grades, the groups, the boards and the teacher
screen do not need the inbox. I suggest moving the first class after step 6 and step 8's review, and adding the inbox
after that, behind its own switch. Until then a teacher's material can reach us the way it does today (to the owner,
by hand), and a level can still be built and shipped as code.

---

## Decisions that are the owner's

1. How long the Sheet stays as the way back after the switch (two weeks suggested), and the date its copy of the class
   is deleted.
2. The boards: the grade board as classes only (recommended) or children's first names with their class (top 20);
   the group board with first names (recommended) or points per group only.
3. School year: do points carry over to the next grade, or start again each September?
4. Raw answers kept 30 days instead of 90 (needed for more than 8 classes on the free plan).
5. Teacher invites made by the owner as the only admin (recommended), or another way.
6. Codes, with the teacher: one code in two parts, grade and class (recommended), or two fields, or another split.
7. Subject groups, with the teacher: who moves a child between groups (the grade's subject coordinator only, or also
   the teacher of the group).
8. The inbox: the caps (5 files of 10 MB a request, 20 requests a month a teacher, a 600 MB brake) and the retention
   (30 days after the request ends, 90 days at most).
9. Where a level's text is reviewed: this public repository (as Unit 1 today) or a free private repository of his.
10. Who presses "release": the owner only (recommended for the first version), or also the teacher for her own scope
    once she has checked the level.
11. The note for parents: the fresh start, what is stored, how a child's data is deleted (`teacher_delete_pupil`, and
   the 14 days of "remove from class").
