# Plan

Status: November 2026. The class uses the game daily and usage jumped. The Google Sheet backend works but will not
carry more classes, more subjects or heavy simultaneous use. This plan moves it to proper infrastructure without
breaking the class.

## Phase 0: freeze (until the English exam, Wed 25.11.2026)

No backend changes. Only content fixes the owner asks for.

## Phase 1: Supabase backend (free plan)

Why: real database, real auth, access rules enforced in the database, many simultaneous saves, room for more classes.
Watch: free projects pause after 7 days without activity. Add a weekly GitHub Actions job that makes one query.

Owner does by hand (we cannot): create a Supabase account with GitHub (no card), create one project, send the project
URL and the anon (public) key. The service-role key goes only into GitHub Actions secrets, never into the repo or chat.

Schema (first cut, the engineer refines it):

- `classes(id, name, grade, created_at)`
- `class_codes(class_id, code_hash)`: the join code, hashed.
- `teachers(user_id, class_id)`: a teacher signs in with Google (Supabase OAuth) and sees only her class.
- `pupils(id, class_id, display_name, auth_user_id, created_at)`, unique (class_id, lower(display_name)).
- `answers(id, pupil_id, game, item_key, skill, correct, first_try, at)`: append only, one row per answer.
- `points(id, pupil_id, delta, reason, at)`: append only ledger; the board is a sum.
- `progress(pupil_id, state jsonb, updated_at)`: transitional, holds today's `pack()` blob so the client changes little.
- Views: `class_board` (display name and points of one class), `teacher_view` (per pupil stars, levels, error rate, weak items).

Pupil login stays class code + first name + 4-digit code. Design decision for the engineer: a 4-digit code cannot be
a plain Supabase password (too short, easy to brute-force). Preferred: an Edge Function `pupil-login` that checks the
class code and the code hash, applies the lockout, and returns a session for that pupil's auth user. Teacher reset of
a code is an Edge Function too.

Row level security on every table: a pupil reads and writes only their own rows and reads only their class board; a
teacher reads only her class; nobody reads code hashes from the client.

### Weaknesses of the Sheet backend that Phase 1 must close

From comparing with navemath.com (another parent's learning-games site: WordPress with one accounts plugin), 24.11.2026.
Each item is an acceptance test for Phase 1, not a wish.

1. **The 4-digit code can be guessed in about a week.** Today: 5 wrong codes lock a pupil for 5 minutes and the counter
   starts again (`MAX_FAILS`, `LOCK_MS` in `backend/Code.gs`), so about 1,440 guesses a day and all 10,000 codes in 7
   days. In `pupil-login`: the lock grows with every round (for example 5 min, 15 min, 1 h, 4 h) and there is a daily
   ceiling of wrong codes per pupil. Target: under 30 guesses a day, so a full sweep takes about a year. Test: a script
   that guesses for a simulated day gets no more than the ceiling.
2. **The lock can be used to bully.** Whoever knows the class code can lock a classmate again and again, and a longer
   lock (item 1) makes that worse. So: a lock stops new sign-ins only, never a session that is already open (item 3),
   so the pupil on their own device keeps playing and saving. Count wrong codes per device as well as per name (a
   device id plus a salted, short-lived hash of the address inside the Edge Function, never stored raw), so one
   device burning its tries does not lock the pupil for everyone. The teacher screen shows "locked N times today"
   next to a name.
3. **The code travels with every request and is kept on the device.** Today `cred()` in `js/state.js` sends class
   code, name and code on every save, and the code sits in `localStorage`. After sign-in the client holds a session
   (Supabase access and refresh tokens) and the code is never stored or sent again. This is also what "stay signed in
   on this device" needs.
4. **Points are decided in the browser.** Today `save` accepts `pts` up to 1,000,000 from the client and the class
   board sorts by it. The board becomes a view computed in the database from `answers` (and the `points` ledger is
   written by the server, not the client), with a sanity check: answers per minute, an item answered correctly more
   often than it can be asked, a session longer than a day. Suspicious rows are flagged for the teacher, not deleted.
5. **Load.** Today every request takes one global lock (`LockService`, 15 s wait, then `busy`) and reads every
   pupil's row including the state blob. Test before the switch: 35 pupils saving in the same 10 seconds, three
   times, with no lost save and no error shown to a pupil.

Found while checking these (same phase): after a teacher resets a code, the first sign-in with that name sets the new
code, whoever it is. In Phase 1 a reset is finished by the pupil with their secret picture (below) or by a one-time
code the teacher hands over.

Decided by the owner, 24.11.2026 (changes how pupils log in, so the exact flow is shown to him before it is built):
pupils stay signed in on their own device; a forgotten code is recovered by the pupil with a secret picture chosen
at registration (three wrong pictures lock recovery for a while); teacher reset stays as the fallback.

Client: one adapter `js/api.js` with the same calls the game makes today (register, login, save, board, teacher,
reset). Pick the backend in `config.js`. The game screens do not change.

Migration: a script reads the Sheet (names, hashes, state JSON) and writes Supabase rows. Codes keep working because
the hash scheme is kept, or pupils reset on first login (owner decides).

## Phase 2: run side by side, then switch

Write to both backends for a few days, compare totals daily, then switch reads to Supabase. Keep the Sheet as a backup
for a month.

## Phase 3: grown-up logins

- Teacher: Google sign-in.
- Parents (optional): Google sign-in, add their child, reset the code, see progress, delete the data.
- Parent account with several children (seen on navemath.com): the parent registers once, ticks a consent box, and
  the children are profiles under that account. Take from it: one grown-up owns the children's data and can reset a
  code or delete everything; consent is recorded with a date. Do not take: children without their own way in. Ours
  play in class and on their own phones without a parent next to them, so a profile under a parent is an extra way to
  manage a pupil, not a replacement for name + code.
- Kids keep name + code. Under 13 in Israel a Google account must be parent-supervised, and third-party sign-in then
  needs the parent's approval each time, so kids do not sign in with Google.
- If the school issues pupil accounts (Google or Microsoft), consider those for kids. Ask the teacher first.

## Phase 4: learning features (backlog)

From comparing with a similar 8th-grade site (no login, device-only progress, many game types):

1. Tap any English word for its translation; a button translates the whole sentence.
2. Slow playback (🐢) on every audio clip.
3. More game types over the same words: swipe true/false, memory pairs, letter scramble, word search, escape room.
4. Print any level as a worksheet.
5. A result card a pupil can send to the teacher (fallback for kids who don't log in).
6. Mock exam results on the teacher screen.

## Phase 5: more classes and subjects

- Content engine: the teacher's material (photos, word lists) in, every game type out, with her review before it goes live.
- Classes and subjects as data, not code. One deployment, many classes.
- Exam calendar per class with reminders (the owner's idea, after the English feedback).
- Game contract in an iframe (seen on navemath.com), so a game is added without touching the core. Each game is one
  self-contained file. It reports to the page around it with `postMessage`: message type, game id, and the answers
  (item key, correct, first try), not only stars. The wrapping page saves only after it has checked the origin, that
  the message came from its own iframe (`event.source`), that the game id is the one it loaded, and that the values
  are in range. The iframe is sandboxed (scripts only, no same-origin access to the pupil's session) and the server
  still computes points from the answers (Phase 1, item 4), so a game cannot award itself anything.
- A landing page per grade and no-friction entry, for when more classes join: a pupil can start playing before
  signing in, and progress made on the device moves into the account at sign-in. Playing without sign-in already
  works when `config.js` is empty; the move of device progress into the account exists too (`merge()`).

## Not copying (from the navemath.com comparison)

- Browser speech for content. Our recorded clips are better; browser speech stays a last fallback only.
- Saving stars only. We keep answers, because the teacher view and "today's focus" need them.
- Email as a condition for children. No email, ever, for pupils.

## Open decisions for the owner

- Our own domain. It adds trust with parents, but it costs money every year and breaks the "free only" rule. Not to
  be advanced without the owner's explicit approval.

## Done means

Tests green on phone and laptop sizes, screenshots looked at, engineer's security review passed, nothing personal in
the repo, and the owner told what was not tested on real devices.
