# Live stage: the fresh start on Supabase (a trial class first, then the class)

The ordered runbook for the owner. The plan is `docs/PHASE4.md` (version 1: one class, a fresh start); the design and
the reasons are in `docs/BACKEND.md`. This file is only what to do, in order, and how to undo each step.

**Fresh start**: nothing of the Sheet is copied. Every child registers again and starts from zero. The Sheet and
`backend/Code.gs` stay exactly as they are until the way back closes (G4); this runbook never touches them.

**A trial class first.** The new game is tried in a throwaway class ("Trial", pupils `Test` and `Tester`) on the
owner's own devices. Only a device opened once with the trial switch talks to Supabase; every child stays on the Sheet.
The trial class is deleted before the real class is made (E7).

**Who does what**
- **Owner (Benji):** the steps marked 📱 (a phone is enough) or 💻 (needs the laptop, with the Supabase CLI, `openssl`,
  `gpg`, Python 3 and this repository checked out).
- **Engineer:** prepares the code changes as pull requests into `game`.
- **Lead:** reviews them, merges them, and ships `game` to `main`.

**Never** put a key, password, pepper, class code, token or list of pupils in a chat, an issue, a commit or this
repository. Public by design, and fine to send the lead: the project's ref and the publishable key
(`sb_publishable_…`). Everything else stays in the password manager or on the laptop.

In the commands below, `<ref>` is the project's id (the part before `.supabase.co`).

**Type keys only with `read -rs SUPABASE_SERVICE_KEY; export SUPABASE_SERVICE_KEY`** (the same for
`SUPABASE_ANON_KEY`, `TEACHER_TOKEN` and `BACKUP_TOKEN`), **never on the command line**: a key typed as `NAME=value`
in front of a command lands in the shell's history. `read -rs` waits, shows nothing while you paste, and the commands
below then use `$NAME`.

**Steps that touch the class's data or change how the children sign in need the owner's explicit yes** (his rule).
They are marked ⚠.

### The shortest list: what only the owner does on day 0 (about an hour)

1. A1 to A10 (settings, mostly on the phone), until `live_check.py --stage 1` is all green.
2. B1, B2, B3 (database, pepper, functions), then B6 (the trial class and its two test names).
3. Send the lead **only** the ref and the publishable key.

Everything else waits: B4, B5, B7 and B8 come before the class (section E), not before the trial.

---

## A. Project settings (📱 except A4 and A10)

The project exists. These are section 9 steps 2 to 11 of `docs/BACKEND.md`.

| # | Who | Step | Rollback |
|---|---|---|---|
| A1 | 📱 Owner | 2FA on the Supabase, GitHub and Google accounts; recovery codes on paper. | none needed |
| A2 | 📱 Owner | GitHub → repository → Settings → Code security: secret scanning and push protection on. | switch off |
| A3 | 📱 Owner | Supabase → Authentication → Sign In / Providers: sign-ups **off**, anonymous off, phone off; email on with "Confirm email" and "Secure email change" on; every OAuth provider off except Google. | set back |
| A4 | 💻 Owner | Authentication → Google: client id and secret from the owner's own Google Cloud project (only the teacher uses it; it can wait until B5, but stage 1 of A10 reports it). | remove them |
| A5 | 📱 Owner | Authentication → Multi-factor: enrolment off for every factor; manual identity linking off. | set back |
| A6 | 📱 Owner | Authentication → Sessions: JWT expiry 3600; refresh-token rotation on, reuse interval 10 s. | set back |
| A7 | 📱 Owner | Authentication → Rate limits: token verifications at least 150 per 5 minutes; sign-ups and emails at the minimum. | set back |
| A8 | 📱 Owner | Authentication → URL configuration: site URL = the game's address; redirect list = `<game>/teacher.html` and nothing else (`docs/BACKEND.md` section 9 step 9). | set back |
| A9 | 📱 Owner | Settings → API: exposed schemas `public` only. Database → Extensions: `pg_graphql` off, `pgcrypto` on, `pg_cron` on. Realtime off for every table. | set back |
| A10 | 💻 Owner | Check the settings, in the repository folder: `export SUPABASE_URL=https://<ref>.supabase.co`, then `read -rs SUPABASE_ANON_KEY; export SUPABASE_ANON_KEY` (paste the publishable key), then `python3 tests/live_check.py --stage 1`. **All green before going on.** | fix the red setting and run it again |

## B. Database, functions, keys, classes (💻, owner's laptop)

Day 0 is B1, B2, B3 and B6. B4, B5, B7 and B8 come before the class (section E).

| # | Who | Step | Rollback |
|---|---|---|---|
| B1 | 💻 Owner | `supabase login` (once; it opens the browser), then `supabase link --project-ref <ref>` (it asks for the database password: type it at its prompt), then `supabase db push` (migrations `0001` to `0009`). Then, in Supabase → SQL editor, run the whole of `supabase/seed/catalog.sql`. The output must say **"maintenance is scheduled: every night at 02:17 UTC"**; if it says "NOT scheduled", stop. Then, in the SQL editor: `update private.settings set raw_days = 30;` (raw answers kept 30 days, `docs/PHASE4.md` "Growth"). | Nothing depends on the project yet. Delete the project and create it again (free), then start at A. |
| B2 | 💻 Owner | The pepper, never shown or pasted: `supabase secrets set PUPIL_PEPPER="$(openssl rand -base64 32)"`. Then `supabase secrets set ALLOWED_ORIGINS=https://jaouibenjamin.github.io`. **Run B2 once.** | Before E7: running it again only breaks the trial class's codes (delete it and make it again with B6). **After E7, never**: every child's code would stop working. |
| B3 | 💻 Owner | Deploy the five functions the fresh start uses: `for f in pupil-login pupil-register pupil-recover teacher-reset admin-class; do supabase functions deploy "$f"; done`. **Not** `admin-wrap-legacy` (the Sheet import; not used). | Deploy the previous version, or delete the function. |
| B4 | 💻 Owner | Backup keys, `docs/BACKEND.md` section 9 step 14: an RSA 4096 pair with `gpg`; the public key into `private.settings`; the private key on the laptop plus one offline copy. The export token: `openssl rand -hex 32`, its sha256 into `private.settings`, the token itself into the password manager. | Generate them again. |
| B5 | 💻 Owner | The teacher: Authentication → Users → create her user with her Google address, auto-confirmed, with a 64-character random password thrown away at once. Her row in `teachers` comes with the real class (E8). | Delete the user. |
| B6 | 💻 Owner | **The trial class.** `read -rs SUPABASE_SERVICE_KEY; export SUPABASE_SERVICE_KEY` (Settings → API keys → the secret key), then: `curl -s -X POST https://<ref>.supabase.co/functions/v1/admin-class -H "authorization: Bearer $SUPABASE_SERVICE_KEY" -H "apikey: $SUPABASE_SERVICE_KEY" -H "content-type: application/json" -d '{"action":"create","name":"Trial","grade":"5"}'`. It prints `class_id` and the 8-character `class_code` **once**: both into the password manager (as "Trial"). Then its two test names, in the SQL editor, with that `class_id`: the SQL "roster" at the end of this file. | E7 deletes it. `{"action":"rotate","class_id":"…"}` gives it a new code. |
| B7 | 💻 Owner | The full check, with the keys read as above: `python3 tests/live_check.py` (stage 2). Add `TEACHER_TOKEN` and `BACKUP_TOKEN` for their items. **All green.** Each MANUAL item it prints is done by hand once, including the restore drill (item 15). It makes and deletes its own "live check" class; it never touches the trial or the real class. | Stop, and send the lead the item number and its line only, never a key. |
| B8 | 📱 Owner | GitHub → Settings → Secrets and variables → Actions: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `BACKUP_TOKEN`. **Not** the server key, the database password, the pepper or the backup private key. Then Actions → keepalive → Run workflow: it must be green. | Delete the secrets; the workflow goes back to its "not set up" note. |

## C. (none: nothing is copied from the Sheet)

The import of the first plan (the Sheet's CSV, `tools/migrate_sheet.py`, `--wrap`, the copy phase) is not used: see
`docs/PHASE4.md` section A. The Sheet's pupils never leave the Sheet.

## D. The client (engineer and lead)

| # | Who | Step | Rollback |
|---|---|---|---|
| D1 | Engineer → Lead | `'supabase'` mode finished (`docs/PHASE4.md` version 1, `PHASE3.md` steps 5 and 6): the pupil screens with the pictures, sign-in, saves, record and board from Supabase with no Sheet call, the device's own storage key cleared when the class or pupil changes, and `https://<ref>.supabase.co` in `connect-src` of every page's Content-Security-Policy. Reviewed in full, merged to `game`, shipped to `main`. | Revert the commits. |
| D2 | Lead | **Must be true before D3:** A10 green; B1, B2, B3 and B6 done; D1 on `main`; every suite green on `game` (`python3 tests/all.py --quick`); the owner has approved the pupil screens. | — |
| D3 | Lead | On `main`, `config.js` gets `window.BACKEND={mode:'supabase',url:'https://<ref>.supabase.co',key:'sb_publishable_…'}`, with no `everyone` key. That is a trial: **no child's device changes**; only a device that opened the game once with the trial switch (`?dual=1` today; D1 may rename it, and then this line follows) talks to Supabase. Pages updates in about a minute. | Remove the line (one commit). Pages updates in about a minute, and the game is exactly as today. |

## E. The trial, then the class prepared

| # | Who | Step | Rollback |
|---|---|---|---|
| E1 | 📱 Owner | On the test device, open `https://jaouibenjamin.github.io/english-trainer/?dual=1` once (the device remembers it). Register `Test` with the trial class's code: a 4-digit code and two pictures. | Open the address with `?dual=0`: the device's session is ended and nothing of it stays. |
| E2 | 📱 Owner | Sign out, then sign in again as `Test`, and once more with "I forgot my code" (the pictures). | — |
| E3 | 📱 Owner | On each phone, first open the address with `?dual=1` once and sign in as `Test`. Then play exactly 10 answers and close the tab right after the last one. Open the game again and give 1 more answer, then switch to another app for a few seconds and back. Do the same on one iPhone and one Android phone: there, switch app instead of closing, and also reload the page once. | — |
| E4 | 💻 Owner | Check the answers counted for `Test` today (the SQL "counted" below): **11** after the test device, **22** after the iPhone, **33** after the Android (the same pupil, so the count adds up). | If a number is not right, stop and send the lead the two numbers. |
| E5 | 📱 Owner | Register `Tester` on the same device in a second tab. `Test` plays in the first tab; leave it in the background for a minute; then sign `Tester` in, in the second. The first tab must show "מישהו אחר נכנס במכשיר הזה" with the button "המשך" and reload only when tapped. **After the tap, the first tab shows `Tester`, and the second tab does NOT show the message.** Then sign `Test` in again: **`Test` finds nothing of `Tester`'s on the device.** | — |
| E6 | 📱 Owner | The devices' browsers: on every kind of device the class uses, the iOS version is 15.4 or later (Settings → General → About), or Chrome or Edge is up to date. That gives Web Locks (`docs/BACKEND.md` section 10, item 21). Then a few school days on those devices, with E4's check each evening. | — |
| E7 | 💻 Owner ⚠ | **Deletes the trial class, its pupils and their sign-ins: needs the owner's explicit yes.** Before the real class: B4, B7 and B8 done and green. Then the SQL "delete the trial" below, with the trial's `class_id`. On every trial device open the game with `?dual=0` once. | Not needed: nothing of a child is in it. |
| E8 | 💻 Owner ⚠ | **Creates the real class: needs the owner's explicit yes.** B6's `curl` again with `"name":"ה׳1"`: its `class_id` and `class_code` into the password manager. Then B5 if not done, and her row: `insert into public.teachers (user_id, class_id) select id, '<class_id>' from auth.users where email = '<her address>';` in the SQL editor. Then once with her on `teacher.html` (`docs/PHASE3.md` step 4, 30 minutes): she adds her class list (first names) and sees an empty class. The class code goes to her in person. | `delete from public.classes where id = '<class_id>';` (no child has registered yet). |
| E9 | Owner | Before switch day: the note for parents is sent (`docs/PHASE4.md` section D), and the owner accepts the way back as it is: for two weeks `config.js` can send the class back to the Sheet, and **what was played on the new game in that time does not go back**. | — |

## F. Switch day

| # | Who | Step | Rollback |
|---|---|---|---|
| F1 | Lead ⚠ | **Changes how every child signs in: needs the owner's explicit yes.** After school the day before: add `everyone:true` to the `BACKEND` line of `config.js` on `main`, exactly that key and exactly the value `true` (anything else, a typo, `'true'` in quotes, `1`, keeps the class on the Sheet). From the next page load, every device uses the new game. | Remove `everyone:true` (only the trial devices stay on Supabase), or remove the `BACKEND` line (everyone is back on the Sheet). What was played on Supabase does not go back to the Sheet (E9). |
| F2 | Teacher | In one lesson, each child registers: first name or nickname from her list, a 4-digit code, two secret pictures. Everyone starts at zero. One class a day, never more (the address limits of `docs/PHASE4.md` section B). | A child who could not register plays on and registers the next day. |

## G. Day 1 and after

| # | When | Check | If not |
|---|---|---|---|
| G1 | after school | **Counted equals played, per pupil**: SQL "day 1" below. Every row's `diff` is 0. | Any row not 0: send the lead the row numbers (no names). Above a few rows: F1 rollback. |
| G2 | during the lesson | **Sign-in headroom from the school's one address**: SQL "ip_hour" below. The highest count stays well under `ip_hour` (120). | Above 100: tell the lead the same day. |
| G3 | after school | **Free plan**: Supabase → Reports / Usage: database size under 350 MB (where the brake starts); Edge Function calls and monthly active users far below the free limits. Also `select * from public.backend_health` as the teacher: `warn` is false. | Above half of any limit after one day: tell the lead before day 2. |
| G4 | after two weeks | The way back closes. The owner switches the Sheet off (his own step: this team never edits `backend/Code.gs` or the Sheet) and deletes the Sheet's copy of the class on the date given in the note for parents. | — |

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
| 9. A real Apps Script cold start | not needed: `'supabase'` mode makes no Sheet call |
| 10. After day 1: counted equals played | E4, G1 |

## The SQL (💻, Supabase → SQL editor, as the owner)

**roster**: the trial class's two test names (B6). Letters only: a name with a digit is refused.

```sql
insert into public.roster (class_id, name_key, display_name)
select '<trial class_id>', app.name_key(n), n from unnest(array['Test', 'Tester']) n;
```

**counted**: answers counted for one pupil today (E4):

```sql
select count(*) as counted
from public.answers a join public.pupils p on p.id = a.pupil_id
where p.display_name = 'Test' and a.at >= date_trunc('day', now());   -- E4: 11, then 22, then 33
```

**delete the trial** (E7): its pupils with their sign-ins (also any removed to its hidden "removed" class), then the
class itself. Run it as one piece:

```sql
begin;
select private.delete_pupil(p.id, p.class_id, null) from public.pupils p
 where p.class_id = '<trial class_id>'
    or p.class_id in (select limbo_id from private.limbo where class_id = '<trial class_id>');
delete from public.classes
 where id = '<trial class_id>' or id in (select limbo_id from private.limbo where class_id = '<trial class_id>');
commit;
```

**day 1**: after school (G1). Tries played (from the record each device saved) against answers counted, since
everyone started at zero. One row per pupil, numbered, no names:

```sql
select row_number() over () as row, played, counted, played - counted as diff
from (
  select coalesce((select sum((v->>0)::int) from jsonb_each(g.state->'st') e(k, v)), 0) as played,
         (select count(*) from public.answers a where a.pupil_id = g.pupil_id) as counted
  from public.progress g
) x
order by abs(played - counted) desc;
```

**ip_hour**: the busiest address in the last hour (G2). Addresses are kept only as salted buckets:

```sql
select count(*) as calls_last_hour, (select ip_hour from private.settings) as limit_per_hour
from private.auth_attempts where at > now() - interval '1 hour'
group by ip_bucket order by 1 desc limit 1;
```

**Known limits** (`docs/BACKEND.md` section 8):
- A pupil whose tab was displaced by another pupil on the same device: the answers the displaced tab still held may
  not be counted. G1 can then show a small `diff` for that pupil on that day.
- Without Web Locks (Safari before 15.4), one pupil in two tabs can count answers twice, and not only a few: one test
  run in three counted 11 for 6 answers. E6 rules this out.
