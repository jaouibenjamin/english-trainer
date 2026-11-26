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

In the commands below, `<ref>` is the project's id (the part before `.supabase.co`).

**Type keys only with `read -rs SUPABASE_SERVICE_KEY; export SUPABASE_SERVICE_KEY`** (the same for
`SUPABASE_ANON_KEY`, `WI_DATABASE_URL`, `TEACHER_TOKEN` and `BACKUP_TOKEN`), **never on the command line**: a key typed
as `NAME=value` in front of a command lands in the shell's history. The commands below then use `$NAME`.

**Steps that touch the live class's data or change how the children sign in need the owner's explicit yes** (his
rule). They are marked ⚠.

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
| A10 | 💻 Owner | Check the settings: `export SUPABASE_URL=https://<ref>.supabase.co`, the publishable key with `read -rs SUPABASE_ANON_KEY; export SUPABASE_ANON_KEY`, then `python3 tests/live_check.py --stage 1`. **All green before going on.** | fix the red setting and run it again |

## B. Database, functions, keys, class (💻, owner's laptop)

| # | Who | Step | Rollback |
|---|---|---|---|
| B1 | 💻 Owner | `supabase link --project-ref <ref>`, then `supabase db push` (migrations `0001` to `0008`). Then run `supabase/seed/catalog.sql` in the SQL editor. The output must say **"maintenance is scheduled: every night at 02:17 UTC"**; if it says "NOT scheduled", stop. | Nothing depends on the project yet. Delete the project and create it again (free), then start at A. |
| B2 | 💻 Owner | The pepper, never shown or pasted: `supabase secrets set PUPIL_PEPPER="$(openssl rand -base64 32)"`. Then `supabase secrets set ALLOWED_ORIGINS=https://jaouibenjamin.github.io`. **Run B2 exactly once.** | Before C3 only: run it again. **If the pepper ever changes after C3, every copied code is broken: stop and tell the lead** (the import never stages a code again). |
| B3 | 💻 Owner | `supabase functions deploy` (all six: `pupil-login`, `pupil-register`, `pupil-recover`, `teacher-reset`, `admin-class`, `admin-wrap-legacy`). | Deploy the previous version, or delete the function. |
| B4 | 💻 Owner | Backup keys, `docs/BACKEND.md` section 9 step 14: an RSA 4096 pair with `gpg`; the public key into `private.settings`; the private key on the laptop plus one offline copy. The export token: `openssl rand -hex 32`, its sha256 into `private.settings`, the token itself into the password manager. | Generate them again. |
| B5 | 💻 Owner | The teacher: Authentication → Users → create her user with her Google address, auto-confirmed, with a 64-character random password thrown away at once. Insert her row in `teachers` (SQL editor). | Delete the user and the row. |
| B6 | 💻 Owner | The class, **once**: `curl -s -X POST https://<ref>.supabase.co/functions/v1/admin-class -H "authorization: Bearer $SUPABASE_SERVICE_KEY" -H "apikey: $SUPABASE_SERVICE_KEY" -H "content-type: application/json" -d '{"action":"create","name":"ה׳1","grade":"5"}'`. It prints `class_id` and the 8-character `class_code` **once**: both go into the password manager. | `{"action":"rotate","class_id":"…"}` gives the class a new code. |
| B7 | 💻 Owner | The full check, with the keys read as above: `python3 tests/live_check.py` (stage 2). Add `TEACHER_TOKEN` and `BACKUP_TOKEN` for their items. **All green.** Each MANUAL item it prints is done by hand once, including the restore drill (item 15). | Stop, and send the lead the item number and its line only, never a key. |
| B8 | 📱 Owner | GitHub → Settings → Secrets and variables → Actions: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `BACKUP_TOKEN`. **Not** the server key, the database password, the pepper or the backup private key. Then Actions → keepalive → Run workflow: it must be green. | Delete the secrets; the workflow goes back to its "not set up" note. |

## C. The copy of the class (💻)

| # | Who | Step | Rollback |
|---|---|---|---|
| C1 | 💻 Owner | Download the Sheet's pupils tab as CSV (File → Download → CSV) into a folder **outside** the repository. | Delete the file. |
| C2 | 💻 Owner ⚠ | **Copies the class's names and code hashes into Supabase (the dry run reads them all): needs the owner's explicit yes.** Dry run, with `WI_DATABASE_URL` read as above: `python3 tools/migrate_sheet.py <file>.csv --class <class_id>`. Read the counts; they must match the class list. | Nothing was written. |
| C3 | 💻 Owner ⚠ | **Copies the class's names and code hashes into Supabase: needs the owner's explicit yes.** The same command with `--apply`. Then `python3 tools/migrate_sheet.py --wrap` (with `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in the environment). Then delete the CSV. | Safe to run again: the Sheet's record replaces the copy. |
| C4 | 💻 Owner | Copy phase on: `admin-class` with `{"action":"shadow_on"}` (same `curl` as B6). | `{"action":"shadow_off"}`, which ends every copy session at once. |

## D. The client (engineer and lead)

| # | Who | Step | Rollback |
|---|---|---|---|
| D1 | Engineer → Lead | A pull request that adds `https://<ref>.supabase.co` to `connect-src` in the Content-Security-Policy of every page (`index.html`, `run.html`, `ds.html` and the others that carry it). Merged to `game`, then shipped to `main`. Without it the browser blocks every copy; the game itself goes on, on the Sheet. | Revert the commit. |
| D2 | Lead | **Must be true before `dual`:** A10 and B7 all green; the restore drill done; D1 on `main`; every suite green on `game` (`python3 tests/all.py --quick`); the owner has approved section 3 of `docs/BACKEND.md` (the sign-in flow). | — |
| D3 | Lead | On `main`, `config.js` gets `window.BACKEND={mode:'dual',url:'https://<ref>.supabase.co',key:'sb_publishable_…'}`. With a project and no `everyone` key, the default is a trial: **no pupil's device changes**; only a device that opened the game once with `?dual=1` copies to Supabase. Pages updates in about a minute. | Remove the line (one commit). Pages updates in about a minute, and the game is exactly as today. |

## E. One test device

| # | Who | Step | Rollback |
|---|---|---|---|
| E1 | 📱 Owner ⚠ | **Touches the live class's data: needs the owner's explicit yes.** A test pupil named "Test" in the **live** class: first add the name to the roster tab of the Sheet, then sign it up in the game (it goes to the Sheet), then re-run C2 and C3 so it is copied too. Test is visible on the leaderboard and on the teacher's screen. E5 needs a second test pupil ("Test2"), added the same way. | Remove Test (and Test2) from the Sheet and the roster tab. On Supabase they stay until removed by hand (lead: `teacher_delete_pupil`). |
| E2 | 📱 Owner | On the test device, open `https://jaouibenjamin.github.io/english-trainer/?dual=1` once (the device remembers it). Sign in as Test. | Open the address with `?dual=0`: the device's session is ended and nothing of it stays. |
| E3 | 📱 Owner | On each phone, first do E2 there (open the address with `?dual=1` once and sign in as Test). Then play exactly 10 answers, then close the tab right after the last one. Open the game again and give 1 more answer, then switch to another app for a few seconds and back. Do the same on one iPhone and one Android phone: there, switch app instead of closing, and also reload the page once. | — |
| E4 | 💻 Owner | Check the answers counted for Test today (the SQL "counted" at the end of this file): **11** after the test device, **22** after the iPhone, **33** after the Android (the same pupil, so the count adds up). | If a number is not right, stop and send the lead the two numbers. |
| E5 | 📱 Owner ⚠ | **Touches the live class's data (Test2): needs the owner's explicit yes.** Two tabs on the same device. Test plays in the first; leave it in the background for a minute; then sign Test2 in, in the second. The first tab must show "מישהו אחר נכנס במכשיר הזה" with the button "המשך" and reload only when tapped. **After the tap, the first tab shows Test2, and the second tab does NOT show the message.** | — |
| E6 | 📱 Owner | The devices' browsers: on every kind of device the class uses, the iOS version is 15.4 or later (Settings → General → About), or Chrome or Edge is up to date. That gives Web Locks (`docs/BACKEND.md` section 10, item 21). | — |

## F. The class

| # | Who | Step | Rollback |
|---|---|---|---|
| F1 | Lead ⚠ | **Changes what happens when the children sign in: needs the owner's explicit yes.** From this step on, each pupil's 4-digit code is also sent to Supabase's sign-in function at every sign-in (not only to the Sheet). After the school day ends: add `everyone:true` to the `BACKEND` line of `config.js` on `main`, exactly that key and exactly the value `true` (anything else, a typo, `'true'` in quotes, `1`, keeps the class off). From the next page load, every device copies to Supabase. | Remove `everyone:true` (only the test devices keep copying), or remove the `BACKEND` line (everyone is back to the Sheet alone). Nothing is lost either way: the Sheet is the truth. |
| F2 | 💻 Owner | The same evening: the baseline for day 1 (SQL "baseline" below). From now until G1, do not run C3 (it would replace the copied records). | Drop the table. |

**During `dual`:** a teacher reset of a pupil's code in the Sheet must also be done on Supabase, or that pupil is not
counted from then on (their copy cannot sign in with the new code). **Tell the lead the same day; the lead resets it on
Supabase** (the game has no teacher screen for Supabase yet).

## G. Day 1: what to watch

| # | When | What | If it is wrong |
|---|---|---|---|
| G1 | after school | **Counted equals played, per pupil**: SQL "day 1" below. Every row's `diff` is 0. | Any row not 0: remove `everyone:true` (F1 rollback) and send the lead the row numbers (no names). |
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
| 5. iOS and Android: tab close, app switch, reload, keepalive, the 64 KiB budget, bfcache | E3, E4 (on the test device, one iPhone, one Android) |
| 6. `storage` events and the reload on displacement across two real tabs | E5 |
| 7. iOS suspending a background tab that holds the lock | E5 (its minute in the background); then G1 |
| 8. Free-plan headroom | G3 |
| 9. A real Apps Script cold start | E2 (the first sign-in of the morning), then G1 |
| 10. After day 1: counted equals played, server points against the Sheet's | G1, G4 |

## The SQL (💻, Supabase → SQL editor, as the owner)

**counted**: answers counted for one pupil today (E4):

```sql
select count(*) as counted
from public.answers a join public.pupils p on p.id = a.pupil_id
where p.display_name = 'Test' and a.at >= date_trunc('day', now());   -- E4: 11, then 22, then 33
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
- Without Web Locks (Safari before 15.4), one pupil in two tabs can count answers twice, and not only a few: one test
  run in three counted 11 for 6 answers. E6 rules this out.
