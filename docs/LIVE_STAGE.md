# Live stage: from the Sheet alone to the Sheet plus Supabase (`dual`)

The ordered runbook for the owner. The design and the reasons are in `docs/BACKEND.md`; this file is only what to do,
in order, and how to undo each step. During `dual` the Sheet stays the truth: the game answers from it, and Supabase
gets a copy. If anything goes wrong, turning `dual` off loses nothing.

**Who does what**
- **Owner (Benji):** the steps marked 📱 (a phone is enough) or 💻 (needs the laptop, with the Supabase CLI, `openssl`,
  `gpg`, Python 3 and this repository checked out).
- **Engineer:** prepares the code changes as pull requests into `game`.
- **Lead:** reviews them, merges them, and ships `game` to `main`.

**Never** put a key, password, pepper, class code, token or CSV of pupils in a chat, an issue, a commit or this
repository. Public by design, and fine to send the lead: the project address and the publishable key (`sb_publishable_…`).
Everything else stays in the password manager or on the laptop.

In the commands below, `<ref>` is the project's id (the part before `.supabase.co`). The keys come from the
environment of the laptop's terminal, typed there and never saved in a file inside the repository.

---

## A. Project settings (📱 except A4)

The project exists. These are section 9 steps 2 to 11 of `docs/BACKEND.md`.

| # | Who | Step | Rollback |
|---|---|---|---|
| A1 | 📱 Owner | 2FA on the Supabase, GitHub and Google accounts; recovery codes on paper. | none needed |
| A2 | 📱 Owner | GitHub → repository → Settings → Code security: secret scanning and push protection on. | switch off |
| A3 | 📱 Owner | Supabase → Authentication → Sign In / Providers: sign-ups **off**, anonymous off, phone off; email on with "Confirm email" and "Secure email change" on; every OAuth provider off except Google. | set back |
| A4 | 💻 Owner | Authentication → Google: client id and secret from the owner's own Google Cloud project. | remove them |
| A5 | 📱 Owner | Authentication → Multi-factor: enrolment off for every factor; manual identity linking off. | set back |
| A6 | 📱 Owner | Authentication → Sessions: JWT expiry 3600; refresh-token rotation on, reuse interval 10 s. | set back |
| A7 | 📱 Owner | Authentication → Rate limits: token verifications at least 150 per 5 minutes; sign-ups and emails at the minimum. | set back |
| A8 | 📱 Owner | Authentication → URL configuration: site URL and redirect list = the game's address only. | set back |
| A9 | 📱 Owner | Settings → API: exposed schemas `public` only. Database → Extensions: `pg_graphql` off, `pgcrypto` on, `pg_cron` on. Realtime off for every table. | set back |
| A10 | 💻 Owner | Check the settings: `SUPABASE_URL=https://<ref>.supabase.co SUPABASE_ANON_KEY=sb_publishable_… python3 tests/live_check.py --stage 1`. **All green before going on.** | fix the red setting and run it again |

## B. Database, functions, keys, class (💻, owner's laptop)

| # | Who | Step | Rollback |
|---|---|---|---|
| B1 | 💻 Owner | `supabase link --project-ref <ref>`, then `supabase db push` (migrations `0001` to `0005`). Then run `supabase/seed/catalog.sql` in the SQL editor. The output must say **"maintenance is scheduled: every night at 02:17 UTC"**; if it says "NOT scheduled", stop. | Nothing depends on the project yet. Delete the project and create it again (free), then start at A. |
| B2 | 💻 Owner | The pepper, never shown or pasted: `supabase secrets set PUPIL_PEPPER="$(openssl rand -base64 32)"`. Then `supabase secrets set ALLOWED_ORIGINS=https://jaouibenjamin.github.io`. | Set it again. Only before any pupil is copied: a new pepper invalidates every copied code. |
| B3 | 💻 Owner | `supabase functions deploy` (all six: `pupil-login`, `pupil-register`, `pupil-recover`, `teacher-reset`, `admin-class`, `admin-wrap-legacy`). | Deploy the previous version, or delete the function. |
| B4 | 💻 Owner | Backup keys, `docs/BACKEND.md` section 9 step 14: an RSA 4096 pair with `gpg`; the public key into `private.settings`; the private key on the laptop plus one offline copy. The export token: `openssl rand -hex 32`, its sha256 into `private.settings`, the token itself into the password manager. | Generate them again. |
| B5 | 💻 Owner | The teacher: Authentication → Users → create her user with her Google address, auto-confirmed, with a 64-character random password thrown away at once. Insert her row in `teachers` (SQL editor). | Delete the user and the row. |
| B6 | 💻 Owner | The class: `curl -s -X POST https://<ref>.supabase.co/functions/v1/admin-class -H "authorization: Bearer $SUPABASE_SERVICE_KEY" -H "apikey: $SUPABASE_SERVICE_KEY" -H "content-type: application/json" -d '{"action":"create","name":"ה׳1","grade":"5"}'`. It prints `class_id` and the 8-character `class_code` **once**: both go into the password manager. | `{"action":"rotate","class_id":"…"}` gives the class a new code. |
| B7 | 💻 Owner | The full check: `SUPABASE_URL=… SUPABASE_ANON_KEY=… SUPABASE_SERVICE_KEY=… python3 tests/live_check.py` (stage 2). Add `TEACHER_TOKEN` and `BACKUP_TOKEN` for their items. **All green.** Each MANUAL item it prints is done by hand once, including the restore drill (item 15). | Stop, and send the lead the item number and its line only, never a key. |
| B8 | 📱 Owner | GitHub → Settings → Secrets and variables → Actions: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `BACKUP_TOKEN`. **Not** the server key, the database password, the pepper or the backup private key. Then Actions → keepalive → Run workflow: it must be green. | Delete the secrets; the workflow goes back to its "not set up" note. |

## C. The copy of the class (💻)

| # | Who | Step | Rollback |
|---|---|---|---|
| C1 | 💻 Owner | Download the Sheet's pupils tab as CSV (File → Download → CSV) into a folder **outside** the repository. | Delete the file. |
| C2 | 💻 Owner | Dry run: `WI_DATABASE_URL=postgresql://… python3 tools/migrate_sheet.py <file>.csv --class <class_id>`. Read the counts; they must match the class list. | Nothing was written. |
| C3 | 💻 Owner | The same command with `--apply`. Then `SUPABASE_URL=… SUPABASE_SERVICE_KEY=… python3 tools/migrate_sheet.py --wrap`. Then delete the CSV. | Safe to run again: the Sheet's record replaces the copy. |
| C4 | 💻 Owner | Copy phase on: `admin-class` with `{"action":"shadow_on"}` (same `curl` as B6). | `{"action":"shadow_off"}`, which ends every copy session at once. |

## D. The client (engineer and lead)

| # | Who | Step | Rollback |
|---|---|---|---|
| D1 | Engineer → Lead | A pull request that adds `https://<ref>.supabase.co` to `connect-src` in the Content-Security-Policy of every page (`index.html`, `run.html`, `ds.html` and the others that carry it). Merged to `game`, then shipped to `main`. Without it the browser blocks every copy; the game itself goes on, on the Sheet. | Revert the commit. |
| D2 | Lead | **Must be true before `dual`:** A10 and B7 all green; the restore drill done; D1 on `main`; every suite green on `game` (`python3 tests/all.py --quick`); the owner has approved section 3 of `docs/BACKEND.md` (the sign-in flow). | — |
| D3 | Lead | On `main`, `config.js` gets `window.BACKEND={mode:'dual',url:'https://<ref>.supabase.co',key:'sb_publishable_…',trial:true}`. With `trial:true`, **no pupil's device changes**: only a device that opened the game once with `?dual=1` copies to Supabase. Pages updates in about a minute. | Remove the line (one commit). Pages updates in about a minute, and the game is exactly as today. |

## E. One test device

| # | Who | Step | Rollback |
|---|---|---|---|
| E1 | 📱 Owner | The test pupil: on the game, sign up a pupil named e.g. "Test" (it goes to the Sheet), then re-run C2 and C3 so it is copied too. | The teacher removes the pupil in the Sheet; it is removed from Supabase at the next C3. |
| E2 | 📱 Owner | On the test device, open `https://jaouibenjamin.github.io/english-trainer/?dual=1` once (the device remembers it). Sign in as the test pupil. | Open the address with `?dual=0`. |
| E3 | 📱 Owner | Play exactly 10 answers. Close the tab right after the last answer. Open the game again. | — |
| E4 | 💻 Owner | Check that 10 answers are counted for the test pupil (the SQL at the end of this file, "counted"). | If it is not 10, stop and send the lead the two numbers. |
| E5 | 📱 Owner | Two tabs on the same device: sign another test pupil in, in the second tab. The first tab must show "מישהו אחר נכנס במכשיר הזה" with the button "המשך", and reload only when tapped. | — |
| E6 | 📱 Owner | The devices' browsers: on every kind of device the class uses, the iOS version is 15.4 or later (Settings → General → About), or Chrome or Edge is up to date. That gives Web Locks (`docs/BACKEND.md` section 10, item 21). | — |

## F. The class

| # | Who | Step | Rollback |
|---|---|---|---|
| F1 | Lead | After the school day ends: remove `trial:true` from `config.js` on `main`. From the next page load, every device copies to Supabase. | Put `trial:true` back (only the test device keeps copying), or remove the `BACKEND` line (everyone is back to the Sheet alone). Nothing is lost either way: the Sheet is the truth. |
| F2 | 💻 Owner | The same evening: the baseline for day 1 (SQL "baseline" below). From now until G1, do not run C3 (it would replace the copied records). | Drop the table. |

## G. Day 1: what to watch

| # | When | What | If it is wrong |
|---|---|---|---|
| G1 | after school | **Counted equals played, per pupil**: SQL "day 1" below. Every row's `diff` is 0. | Any row not 0: put `trial:true` back (F1 rollback) and send the lead the row numbers (no names). |
| G2 | during the lesson | **Sign-in headroom from the school's one address**: SQL "ip_hour" below. The highest count stays well under `ip_hour` (120). | Above 100: tell the lead the same day. A pause stops only the copy, never the game. |
| G3 | after school | **Free plan**: Supabase → Reports / Usage: database size under 350 MB (where the brake starts); Edge Function calls and monthly active users far below the free limits. Also `select * from public.backend_health` as the teacher: `warn` is false. | Above half of any limit after one day: tell the lead before day 2. |
| G4 | end of week 1 | `docs/BACKEND.md` section 8 step 2: per pupil, points per source against the Sheet's. | As G1. |

## What the reviewer listed, and where it is checked

| Item of the live-stage checklist (review of #63) | Step |
|---|---|
| 1. The project in `connect-src` on every page | D1 |
| 2. Real GoTrue: refresh rotation and reuse window; `logout?scope=local`; a revoked access token until expiry | A6, B7 (items 3 and 6) |
| 3. The client address on the real Edge runtime; `ip_hour` 120 with the whole class on one address | B7 (item 10), G2 |
| 4. Web Locks on every kind of class device | E6 |
| 5. iOS and Android: tab close, app switch, reload, keepalive, the 64 KiB budget, bfcache | E3, E4 |
| 6. `storage` events and the reload on displacement across two real tabs | E5 |
| 7. iOS suspending a background tab that holds the lock | E5 with the first tab in the background for a minute; then G1 |
| 8. Free-plan headroom | G3 |
| 9. A real Apps Script cold start | E2 (the first sign-in of the morning), then G1 |
| 10. After day 1: counted equals played, server points against the Sheet's | G1, G4 |

## The SQL (💻, Supabase → SQL editor, as the owner)

**counted**: answers counted for one pupil today (E4):

```sql
select count(*) as counted
from public.answers a join public.pupils p on p.id = a.pupil_id
where p.display_name = 'Test' and a.at >= date_trunc('day', now());
```

**baseline**: the evening before day 1 (F2). It keeps, per pupil, the number of tries in the copied record:

```sql
create table private.day1_baseline as
select pupil_id, coalesce((select sum((v->>0)::int) from jsonb_each(state->'st') e(k, v)), 0) as tries, now() as at
from public.progress;
```

**day 1**: after school (G1). Tries played since the baseline (from the record each device copied) against answers
counted. One row per pupil, numbered, no names:

```sql
select row_number() over () as row, played, counted, played - counted as diff
from (
  select coalesce((select sum((v->>0)::int) from jsonb_each(g.state->'st') e(k, v)), 0) - b.tries as played,
         (select count(*) from public.answers a where a.pupil_id = g.pupil_id and a.at >= b.at) as counted
  from public.progress g join private.day1_baseline b using (pupil_id)
) x
order by abs(played - counted) desc;
```

**ip_hour**: the busiest address in the last hour (G2). Addresses are kept only as salted buckets:

```sql
select count(*) as calls_last_hour, (select ip_hour from private.settings) as limit_per_hour
from private.auth_attempts where at > now() - interval '1 hour'
group by ip_bucket order by 1 desc limit 1;
```

After week 1: `drop table private.day1_baseline;`

**Known limits** (`docs/BACKEND.md` section 8):
- A pupil whose tab was displaced by another pupil on the same device: their last answers reach the Sheet but not the
  server count. G1 can then show a small `diff` for that pupil on that day.
- Without Web Locks (Safari before 15.4), one pupil in two tabs can count a few answers twice. E6 rules this out.
