# Phase 4 proposal: a fresh start, the whole school by grade and class, and teachers' own content (DRAFT)

Status: a proposal for the lead and the owner, written from the owner's decisions of 2026-11-26. No code yet. It
builds on `docs/BACKEND.md` (the Supabase backend, Phase 1), `docs/PHASE3.md` (the teacher on Supabase) and the
open pull requests #82, #83, #86, #87, #93, #94. Decisions that are the owner's are marked **[owner]** and listed at
the end.

The three decisions:

- **A. Fresh start.** When the class moves to the new game, everyone starts from zero, in English and in Fraction Bay,
  with a new sign-in. Nothing is imported from the Sheet. The Sheet (backend/Code.gs version 3, deployed today) stays
  as it is for today's class until the new game is live and fully tested; then it is switched off.
- **B. The whole school, by grade (שכבה) and class.** Every pupil belongs to one class, and every class to one grade.
  Leaderboards by class and by grade. Teachers sign in, are attached to the classes or grades and subjects they teach,
  and add content that reaches only that grade or class.
- **C. Teachers' own content** is shown to children: the safest first version.

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
- **Class codes**: random, 8 characters, no grade in them (a code that encodes the grade can be guessed across
  classes). The server looks the code up and decides class and grade.
- **Content ids**: a teacher's item keeps its id across edits (a new version, same item), so a child's history on an
  item survives a typo fix (section C).

---

## B. The whole school, by grade and class

### The rule that answers the owner's worry ("a child can declare any class")

A child never declares a class or a grade. The **class code** the teacher hands out decides both, on the server, at
registration. After that:

- the pupil's row has no column the pupil can write (no `update` grant on `pupils` for a session, as today);
- every read is filtered by row-level security through `app.class_id()` / `app.grade_id()`, functions that read the
  pupil's own row, never anything the client sends;
- only a teacher of that class (or the owner as admin) can move a pupil, through one function that checks both
  classes and writes an audit row.

A child who learns another class's code can register a second name there. That is the same risk as today (the code
is a class secret), handled as today: a roster per class (`roster_only`, on by default), so only names the teacher
listed can register, and a new code when one leaks (`admin-class rotate`).

### Schema (new tables and columns; one migration, append-only)

| Table | Columns | Notes |
|---|---|---|
| `schools` | `id`, `name` | One row now. Costs nothing and saves a reset if a second school ever joins. |
| `grades` | `id`, `school_id`, `level` (1 to 12), `label` (e.g. "ה׳"), `school_year` | One row per grade per year. |
| `classes` | + `grade_id` not null, + `school_year` | `grade` (text, today) is replaced by `grade_id`. The class code stays in `private.class_codes`. |
| `subjects` | `key` (`english`, `math`), `label` | Fixed list, added by the owner. |
| `teacher_assignments` | `user_id`, `class_id` or `grade_id` (exactly one), `subject`, `role` (`teacher`), `granted_by`, `granted_at` | Replaces `teachers` (kept as a view for the existing functions). A grade-wide assignment is how a 4th-grade English coordinator reaches all 4th-grade classes. |
| `private.teacher_invites` | `code_lookup` (keyed hash), `class_id` or `grade_id`, `subject`, `expires_at`, `used_by`, `created_by` | One-time, 7 days, shown once to the owner. |
| `admins` | `user_id` | The owner. Nobody becomes an admin through the app. |
| `content_packs`, `pack_items`, `pack_events` | section C | |

### How a teacher becomes a teacher of a class

1. The owner (admin) creates an invite for one class (or one grade) and one subject in the admin page. The code is
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
| Pupil (session) | own row and record; the class board; the grade board; published content packs whose scope is their class or their grade (and subject), nothing else |
| Teacher | pupils, boards, views and packs of the classes and grades she is assigned to, for her subjects; her own draft packs |
| Admin | everything, through security-definer functions only (no direct table rights) |
| Server key | everything; never in the browser or in GitHub |

Every row in every table is reached through one of these, and `tests/db.py` gets a matrix like today's: a pupil of
class 4A, a pupil of 4B, a pupil of 5A, a 4A English teacher, a 4th-grade math teacher, a stranger with a Google
account, anonymous. Each one against each table and view.

### Leaderboards

- **Class board**: as today (`class_board`): first name or nickname, points, words, streak.
- **Grade board**, two options **[owner]**:
  1. *Classes only* (recommended for the first version): each class of the grade with its total or average points
     and active pupils. No child's name leaves their class.
  2. *Children of the grade*: first name or nickname **and class** ("Noa, 4B"), top 20 only. A child's name is then
     seen by about 100 children instead of 30.
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
redesign. I suggest the 30-day window from the start (decided now, while there is no data). Content packs are small
(about 5 KB a pack). Egress stays far under 5 GB if the game caches packs by version (section C). Auth users stay
far under 50,000. Edge Function calls only grow with sign-ins.

---

## C. Teachers' own content (the risky part: it is shown to children)

### The first version

- **Structured input only.** A pack is a list of items. Each item is one of a few kinds with fixed fields:
  - `word`: the English word, its Hebrew translation, an optional example sentence;
  - `sentence`: an English sentence and its Hebrew translation (for reading and ordering games);
  - `fraction` (Fraction Bay): numerator and denominator, from a fixed set of item types.

  No free HTML, no Markdown, no links, no files, no images, no audio in the first version.
- **Validation in the database** (check constraints and one function, so no client can skip it), as for names today:
  - an allow-list of characters: Hebrew, Latin, digits, a short list of punctuation; no control or invisible
    characters, no direction overrides (the rules of `app.name_ok`);
  - length caps: a word up to 40 characters, a sentence up to 160;
  - no URL-like text (`http`, `www.`, `@`, a dot between letters without a space);
  - at most 60 items a pack and 20 packs a class per subject;
  - a deny-list of words, kept by the owner **[owner: wanted?]**.
- **Shown as text only.** The game and the teacher page put every value in with `textContent`, as names today
  (`tests/teacher.py` already proves an HTML name stays text).
- **Scope**: a pack belongs to exactly one class or one grade, and one subject. A 4th-grade pack can never be read by a
  5th grader: row-level security on `pack_items` through the pack's scope, tested with the matrix above.
- **Drafts, preview, publish**:
  - A teacher writes a draft, sees a preview exactly as a child will see it (the real game screen, fed the draft),
    and asks to publish.
  - In the first version **the owner approves every first publication of a teacher** **[owner: or trust a teacher
    after N approved packs, or never require approval]**.
  - A published version never changes. An edit makes a new version, published the same way. Children keep their
    history per item (stable item ids).
  - Unpublishing takes a pack away from children at once; the teacher and the owner can both do it.
- **Audit trail**: `pack_events` is append-only: who did what (created, edited, asked, approved, published,
  unpublished), when, to which version. Nobody can change or delete it, the owner included, except the nightly
  clean-up after a set time **[owner: how long; I suggest a year]**.
- **How the game reads packs**: one read on start-up, `published_packs()`, for the pupil's class and grade. It returns
  the ids and versions. The game keeps the packs in the browser cache by version and downloads only what changed. With
  no connection it uses the last packs it has. The built-in curriculum (Fantastic 5 Unit 1, Fraction Bay) stays in the
  repository and is always there.
- **What stays hand-curated**: the built-in units, the recorded voice (no browser speech for content, ever: a
  teacher's pack has no voice in the first version, and the game shows it as text), all art, the mock exam.
- **The hard rules stay**: the teacher's material is the source of truth (her words and translations exactly, never
  "corrected" by the game); first name only; free only; nothing of pupils in the repository.

### Later, if wanted (each its own proposal and review)

- **Images**:
  - a teacher uploads to a private storage bucket;
  - a server step checks the type by its bytes, caps the size (about 200 KB) and strips metadata (EXIF, location);
  - the owner approves;
  - only then is it copied to a public bucket the game reads.

  It needs the 1 GB storage limit watched.
- **Recorded audio** for a pack, through the same pipeline as images.
- **Teacher-to-teacher sharing** of packs across classes of a grade.

---

## Phases (honest estimates, engineer days, about two review rounds each)

| # | Step | Who | Days | Depends on |
|---|---|---|---|---|
| 1 | The owner's decisions below | owner | — | — |
| 2 | Schema: schools, grades, classes.grade_id and school_year, subjects, assignments, admins; RLS and the reader matrix in db.py; registration decides class and grade from the code | engineer | 3 | 1 |
| 3 | Admin page (owner only): grades, classes, class codes, teacher invites, revoke | engineer + UI designer | 3 | 2 |
| 4 | Teacher invite redemption on `teacher.html`; the screen scoped to her assignments and subjects | engineer | 2 | 3 |
| 5 | Grade board (the chosen option) and the game's board screen | engineer + client engineer | 2 | 2 |
| 6 | Cleanup migration: the Sheet import, the copy phase and `legacy` paths removed; LIVE_STAGE and PHASE3 rewritten for a fresh start; the trial switch | engineer | 2 | 2 |
| 7 | Content packs v1: tables, validation, RLS, drafts, approval, audit, `published_packs()`; the teacher editor with preview; the game reader with the cache | engineer + client engineer + UI designer | 8 to 10 | 4 |
| 8 | Security review of 2 to 7, a rehearsal on a second free project, a week on the trial devices | lead, reviewer, owner, teacher | 5 | 7 |
| 9 | Switch day for the first class | owner, lead | — | 8 |

Steps 2 to 6 are about two weeks of work and one month with reviews. Content packs (7) add about another month.
**The first class could move before step 7.** The fresh start, the grades, the boards and the teacher screen do not
need teachers' own content. I suggest moving the first class after step 6 and step 8's review, and adding content
packs after that, behind their own switch.

---

## Decisions that are the owner's

1. How long the Sheet stays as the way back after the switch (two weeks suggested), and the date its copy of the class
   is deleted.
2. The grade board: classes only (recommended) or children's first names with their class (top 20).
3. School year: do points carry over to the next grade, or start again each September?
4. Raw answers kept 30 days instead of 90 (needed for more than 8 classes on the free plan).
5. Teacher invites made by the owner as the only admin (recommended), or another way.
6. Content approval: every first publication approved by the owner, after N packs, or never.
7. A deny-list of words for teacher content: yes or no.
8. How long the content audit trail is kept (a year suggested).
9. The note for parents: the fresh start, what is stored, how a child's data is deleted (`teacher_delete_pupil`, and
   the 14 days of "remove from class").
