# Phase 3 proposal: the teacher on Supabase, then the Sheet off (DRAFT)

Status: a proposal for the lead and the owner. Steps 1 and 2 are open pull requests (#82, #83); the rest is not built. It assumes `docs/LIVE_STAGE.md` has run to G
(`dual` on for the class, counted equals played).

## What already exists (Phase 1, on the server)

- **The teacher's account:** the `teachers` table (one row per teacher and class, added by the owner), Google as the
  only sign-in provider (runbook A3, A4), and her user created beforehand (B5).
- **Views:** `teacher_view` (per pupil: points, answers, first-try answers, error rate, stars, flags this week, locks today) and `teacher_items`
  (the class's hard words) return rows only for her class.
- **Writes:** `teacher-reset` with `reset` (a 6-digit one-time code, shown once), `unlock` and `unlock_class`;
  `teacher_delete_pupil`; the roster table, with insert and delete open to her by RLS; `backend_health`.
- **The pupil side:** `pupil-register` and `pupil-recover` (secret pictures, one-time code).

**What is missing is the client:**
- Google sign-in in the browser.
- A teacher screen that reads Supabase.
- The pupil screens with the pictures.
- `'supabase'` mode finished: it is refused today unless `config.js` says `unfinished: true`, and, like `dual`, only for a `?dual=1` device unless `everyone: true`.

## The proposal

1. **The teacher's sign-in: a page of its own, `teacher.html`.**
   - The pupils' pages never carry a teacher session.
   - Google through Supabase OAuth, with a redirect, PKCE and the code exchanged at `/auth/v1/token?grant_type=pkce`.
   - Plain `fetch`, no vendored library (as `js/api.js`).
   - The session lives in the page's memory only: nothing of it is written to any storage (the PKCE verifier alone sits in `sessionStorage` for at most 10 minutes and is deleted when used). It ends when the page is left (pagehide: a link, the back button, a reload, closing the tab), after 30 minutes without a tap or a key, or with "sign out"; each time it is revoked on the server, with keepalive when the page is being left.
   - No Google host in `connect-src`: the redirect is a top-level navigation. `teacher.html` has its own policy, stricter than the game's: no inline script or style, `form-action 'none'`, `base-uri 'none'`, no referrer.
   - The Auth redirect list holds `<game>/teacher.html` and nothing else (`docs/BACKEND.md` section 9 step 9).
2. **The teacher screen on Supabase, behind a switch (`?tsb=1`), side by side with today's Sheet screen.**
   - **Read:** her class from `teacher_view`, today's hard words from `teacher_items`, and a warning line from `backend_health`.
   - **Write:**
     - reset a code: the 6-digit code shown once, with what to tell the child;
     - unlock a pupil, unlock the class;
     - add a first name to the roster, and remove a pupil (`teacher_delete_pupil`), with a confirmation.
   - It replaces the lead's "reset on Supabase by hand" step during `dual` (runbook, "During `dual`").
   - Copy and layout by the kids-ui-designer, for an adult this time; the game's look.
3. **The pupil screens for `'supabase'` mode** (kids-ui-designer and the client engineer; the flows are in `docs/BACKEND.md` section 3):
   - registration with two secret pictures;
   - the first sign-in of a pupil who came from the Sheet: a new code and two pictures;
   - "I forgot my code": the pictures, or the teacher's one-time code.
4. **`'supabase'` mode finished in `js/api.js` and `js/state.js`** (step 6, done; the seam with the screens of step 5 is
   `enter()` in `js/state.js`, written at the top of both PRs):
   - the game stops keeping the 4-digit code (`cred()` is `{c, n}`) and keeps the session only; the code goes to
     `pupil-login`, `pupil-register` or `pupil-recover` once and nowhere else;
   - the board (`class_board`, with the pupil's own row) and the pupil's own record (`progress`, read with the session
     when the game opens) come from Supabase;
   - the device keeps the new backend's record under its own key (`wi-new-v1`), bound to the pupil and class it belongs
     to (read with the new session); when another pupil or class signs in, the last pupil's unsaved play is kept aside
     for them and never joined into anyone else's (`docs/PHASE4.md` A), and a sign-in whose pupil cannot be read does
     not count (nothing is joined or dropped on a guess); the
     Sheet's record (`aam-unit1-v1`) is never read or written in this mode, so the way back finds it as it was;
   - a session that ended (expired and not renewable, or signed out everywhere) asks the pupil to sign in again
     (`signin`); what the device played waits for the same pupil;
   - the `unfinished` key goes with whichever of steps 5 and 6 lands second, so the class cannot be switched without
     the sign-in screens.
   Tests: `tests/api_check.mjs` section 9, `tests/supabase_mode.py`.

## What must be true before the Sheet is switched off

All of `docs/BACKEND.md` section 8 step 3, and also:

1. **The teacher has used the Supabase screen for at least a week:** signed in with Google, reset and unlocked there.
2. **The pupil screens are approved** by the owner (they change how children sign in: his explicit yes) and by the teacher.
3. **Counting is exact:** counted equals played (runbook G1), and the per-source points gap is 0, for 3 school days in a row (`docs/BACKEND.md` section 8, step 3).
4. **Backups are current:**
   - the daily keep-alive and backup workflow is green;
   - a restore drill was done within the last 30 days;
   - one encrypted export is kept offline.
5. **The switch day is written as a runbook** like `docs/LIVE_STAGE.md`, with its way back (section 8 steps 4 and 5):
   - a new class code is handed out;
   - every pupil signs in once with the old code and chooses a new code and pictures;
   - the Sheet answers every request with "sign in again";
   - for a month the way back is to point `config.js` at the Sheet again.
   - The change to `backend/Code.gs` is the lead's and the owner's, not this team's.
6. **The free-plan numbers after a month of `dual`** leave room for a second class (`docs/BACKEND.md` section 6).
7. **Every step reviewed:** the engineer's security review on each PR and the security workflow green.
8. **Pupils absent on switch day:** the switch-day runbook says how they get the new class code later, that their old code still works on Supabase until they choose a new one, and that a forgotten code goes through the teacher's one-time code.
9. **Privacy before the Sheet is off:** the owner decides on the note for parents (`docs/BACKEND.md` "Privacy notes"); a request to delete a child's data is `teacher_delete_pupil`, and the encrypted exports that still hold the child age out after a stated number of days; the Sheet's copy of the class (names, progress, code hashes) is deleted on a stated date after the way back closes.
10. **Switch-day headroom:** the whole class signing in at once from the school's address stays under `ip_hour` (each sign-in, new code and pictures counted).

## Order and estimates

These are focused engineer days for each step. Each PR takes about 2 review rounds; Phase 1 took 7 on the hardest part.

| # | Step | Who | Days | Depends on |
|---|---|---|---|---|
| 1 | `teacher.html`: Google sign-in (PKCE), session handling, sign-out, tests with a stand-in GoTrue | engineer | 1.5 | runbook A4 and B5 |
| 2 | The teacher screen, read only, behind `?tsb=1` | engineer + UI designer | 1 | 1 |
| 3 | Its actions: reset, unlock, unlock class, roster add and remove; tests | engineer | 1.5 | 2 |
| 4 | Once with the teacher on the real project (30 minutes, the owner present) | owner, teacher | — | 3 |
| 5 | The pupil screens with the pictures (3 flows), approved by the owner | UI designer + client engineer | 3–4 | the flows of section 3 |
| 6 | `'supabase'` mode finished (no code kept, board and record from Supabase); tests | engineer | 2 | 5 |
| 7 | The switch-day runbook, its way back, and a rehearsal on a second project | engineer, lead | 1 | 6 |
| 8 | The switch | owner (explicit yes: it changes how every child signs in), lead | — | everything above |

In total that is about 11 engineer days, or about 3 to 4 weeks on the calendar with reviews and the teacher's time. Steps 1 to 4 are useful on their own: the teacher gets her own reset and unlock during `dual`, so the lead's manual step goes.

## Step 4: what only the real project and a real device can show (the owner's list)

The security review of #82, #83 and #86 left these for the session with the teacher. Nothing in the tests can stand in for them.

- **Signing out of our page does not sign her out of Google.** On a shared class computer, the next person who opens Google is still her. The page says so and recommends a guest or incognito window. The sign-in asks Google to show the account chooser every time (`prompt=select_account`). Check that Google really shows the chooser, and give the wording a final form with the designer's screen spec.
- **The Auth redirect list holds exactly `<game>/teacher.html`**, and the site URL is the game (runbook A8). Open `<game>/teacher` without `.html`: the page must move itself to `teacher.html` before any sign-in.
- **Sign-up is off** in Authentication → Providers (only the users the owner created can sign in), and Google is the only provider.
- **Her Google Workspace allows the app** (a school account can block outside apps), and Testing mode shows her the "unverified app" screen once.
- **On a real phone and a real laptop, with the back-forward cache:** sign in, go to the game, press back. Nobody is signed in, and Authentication → Users shows her session ended (the keepalive revoke reached the project). Repeat on a slow connection with a second tap on "sign in".
- **The access token outlives a sign-out by up to its expiry** (a JWT is not recalled, only its session). Keep the project's JWT expiry at the default hour or shorter.
- **`app.name_key` under the project's locale:** add "İlknur" and "Élie" to the class list from the page; each must be accepted or refused, never stored twice.
- **The project's log settings:** API and Edge Function logs must not keep request bodies (the one-time code is in a response body).
- **`teacher-reset` with a real token, an expired token and no token:** `ok`, refused, refused. Then 16 new codes in a day with the default cap, all on a test pupil the owner adds for this and deletes afterwards, never on a real child (each new code signs that pupil out everywhere): the 16th is refused and `backend_health` shows 15 of 15.

## Questions for the owner (and the teacher)

- **Which Google account will the teacher use: her personal one or the school's?** A school Google Workspace can block sign-in to outside apps; that has to be tried before step 1.
- **Google's consent screen stays in "Testing"** (free, up to 100 named users) with the teacher's address added. That is enough for one class and needs no verification by Google. In Testing, Google shows the teacher an "unverified app" screen and her consent may need repeating after 7 days; she should see this once with the owner (step 4).
- **Parents** (`docs/PLAN.md` Phase 3, second bullet) are not in this proposal. I suggest a separate one after the switch, because consent records and deleting a child's data need their own design and the owner's decisions.
