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

## Done means

Tests green on phone and laptop sizes, screenshots looked at, engineer's security review passed, nothing personal in
the repo, and the owner told what was not tested on real devices.
