# Day 0: what only Benji does (about an hour)

For the project whose ref is in `supabase/project_ref` (the lead sets it; `python3 tools/project_ref.py` prints it). This is `docs/LIVE_STAGE.md`
steps A and B for day 0 only, in the order to do them, with every command ready to copy. Nothing here touches the
Sheet or the class: the class keeps playing as today.

**The one rule.** Send the lead **only** the publishable key (`sb_publishable_…`), at the very end. Never the secret
key, the `service_role` key, the database password, the pepper or the trial class's code: not in a chat, not in an
issue, not in a commit. Those go into the password manager, or nowhere.

Steps marked 📱 work on the phone; 💻 needs the laptop.

---

## The fast way: one button (📱, about 15 minutes, no laptop)

GitHub does sections 0 and 3 to 7 below for you (`.github/workflows/supabase-setup.yml`, running
`tools/supabase_setup.py`). It also makes the pepper inside the job, so nobody ever sees it. Section 1's A1 and A2, and
anything the job could not set, it prints at the end as a short list. The button appears once the lead has shipped
the workflow to `main`; a real run works only from `main`.

**Before** (once):

1. **2FA** on the Supabase, GitHub and Google accounts (A1), recovery codes on paper.
2. **An access token**: supabase.com → Account → Access Tokens → Generate new token, name `wi-setup`, **only for this
   project** and **expiring in 7 days** (if the page offers no project choice, the token can act on every project of
   your account: all the more reason for step 9).
3. **The database password**: Supabase → Project Settings → Database → Reset database password (fine on an empty
   project). Keep it in the password manager.
4. **Delete any repository secrets** named `SUPABASE_ACCESS_TOKEN` or `SUPABASE_DB_PASSWORD` (GitHub →
   `english-trainer` → Settings → Secrets and variables → Actions → Repository secrets). A repository secret can be read
   by a workflow on any branch, so these two must never be there.
5. **The environment** `supabase-setup` (Settings → Environments → New environment):
   - Required reviewers: yourself; "Prevent self-review" **off** (you approve your own run);
   - Deployment branches and tags: Selected branches: **`main` only**;
   - Environment secrets: `SUPABASE_ACCESS_TOKEN` (step 2) and `SUPABASE_DB_PASSWORD` (step 3).

**The run:**

6. **The rehearsal**: Actions → supabase-setup → Run workflow → branch `main` (or `game`), confirm `setup trial`, mode
   `dry-run`. It runs the whole setup against a stand-in on GitHub's machine and sends nothing to Supabase. **Done
   when** green.
7. **The real run**: branch `main`, confirm `setup trial`, mode `real`; approve it when GitHub asks. It stops by itself,
   before changing anything, if the project is paused, outside the EU, not on the Free plan, or not new (tables that
   are not ours, users, storage buckets). **Done when** green and the log ends with "changes made" (a second run would
   say "nothing changed"). **Never** use "Re-run with debug logging": it prints more than the job does.

**After** (right away):

8. **The trial class's code**: Supabase → Project Settings → Vault (or Integrations → Vault) → `wi_trial_class_code` →
   reveal, copy it into the password manager as "Trial", then **delete that secret**. It is never in the log. If it is
   not there, or you lost it: run the workflow with mode `rotate-trial` (branch `main`) for a new one.
9. **Revoke the token** (supabase.com → Account → Access Tokens → `wi-setup` → Revoke) and **delete both secrets** from
   the `supabase-setup` environment.
10. **The short list at the end of the log**: do each item (A2 secret scanning, and anything it could not set). Google
    for the teacher (A4) comes later, with her.
11. **Send back** as in section 8: "setup done" and the publishable key, nothing else.

If the button stops with a line you do not understand, send the lead that line (the log hides every secret) and use
the manual way below from the step it names.

---

## The manual way (the laptop)

## 0. Check the project first (📱, 5 minutes)

It may have been made a while ago. In the Supabase dashboard, the project (its ref is in `supabase/project_ref`):

| Check | Where | Must be | If not |
|---|---|---|---|
| Not paused | the project's home page | "Active" / healthy | press **Restore** (free) and wait until it is active |
| Region in the EU | Settings → General → Region | starts with `eu-` (for example `eu-central-1`, Frankfurt) | stop: delete the project and create it again in Frankfurt (nothing depends on it yet), then tell the lead the new address |
| Free plan | Organization → Billing | **Free**, no card | stop and tell the lead |
| Empty | SQL editor: `select count(*) from pg_tables where schemaname = 'public';` | `0` | stop and tell the lead the number (do not push on top of old tables) |

**Done when** all four are as above.

## 1. Settings (📱, 15 minutes)

| # | Where | Set |
|---|---|---|
| A1 | Supabase, GitHub and Google accounts | 2FA on; recovery codes on paper |
| A2 | GitHub → `english-trainer` → Settings → Code security | secret scanning **on**, push protection **on** |
| A3 | Supabase → Authentication → Sign In / Providers | "Allow new users to sign up" **off**; anonymous **off**; phone **off**; email **on**, with "Confirm email" **on** and "Secure email change" **on**; every other provider **off** (Google stays off today; it comes with the teacher) |
| A5 | Authentication → Multi-factor | enrolment **off** for every factor; manual identity linking **off** |
| A6 | Authentication → Sessions | JWT expiry **3600**; refresh-token rotation **on**; reuse interval **10** s |
| A7 | Authentication → Rate limits | token verifications **150** per 5 minutes (or more); sign-ups and emails at the minimum |
| A8 | Authentication → URL configuration | site URL `https://jaouibenjamin.github.io/english-trainer/`; redirect list: only `https://jaouibenjamin.github.io/english-trainer/teacher.html` |
| A9 | Settings → API → exposed schemas: `public` only. Database → Extensions: `pg_graphql` **off**, `pgcrypto` **on**, `pg_cron` **on**. Database → Publications / Realtime: **no table** | as written |

**Done when** every row is set. (A4, Google for the teacher, waits for the teacher's day.)

## 2. The laptop, once (💻, 5 minutes)

Needs Python 3, `openssl`, `curl`, git and the Supabase CLI (`brew install supabase/tap/supabase` on a Mac; or put
`npx supabase` wherever these steps say `supabase`).

```sh
git clone https://github.com/jaouibenjamin/english-trainer.git   # skip if you have it
cd english-trainer
git checkout game && git pull
```

**Done when** `ls supabase/migrations` lists `0001_schema.sql` to `0009_soft_delete.sql`.

## 3. Check the settings (💻, A10, 2 minutes)

The publishable key is in Settings → API Keys (`sb_publishable_…`). `read -rs` waits and shows nothing while you
paste: paste the key, press Enter.

```sh
export SUPABASE_URL="https://$(cat supabase/project_ref).supabase.co"
read -rs SUPABASE_ANON_KEY; export SUPABASE_ANON_KEY
python3 tests/live_check.py --stage 1
```

**Done when** it ends with `stage 1: N passed, 0 failed`. A red line names the setting of section 1 to fix; fix it
and run the last command again.

## 4. The database (💻, B1, 10 minutes)

```sh
supabase login
supabase link --project-ref "$(cat supabase/project_ref)"
supabase db push
```

`link` and `push` ask for the database password: type it at the prompt. If you do not have it: Settings → Database →
Reset database password (fine on an empty project), and keep it in the password manager.

**Done when** `db push` applied `0001` to `0009` and its output includes
**`maintenance is scheduled: every night at 02:17 UTC`**. If it says "NOT scheduled", stop and tell the lead (A9:
`pg_cron` on?).

Then in Supabase → SQL editor: open `supabase/seed/catalog.sql` from the repository, paste all of it, **Run**. Then
run this, in the SQL editor too:

```sql
update private.settings set raw_days = 30;
select raw_days from private.settings;
```

**Done when** the seed ran without an error and the last query shows `30`.

## 5. The pepper and the allowed address (💻, B2, 1 minute)

**Once.** The pepper is made and stored in one go; nobody ever sees it.

```sh
supabase secrets set PUPIL_PEPPER="$(openssl rand -base64 32)"
supabase secrets set ALLOWED_ORIGINS=https://jaouibenjamin.github.io
supabase secrets list
```

**Done when** `secrets list` shows `PUPIL_PEPPER` and `ALLOWED_ORIGINS` (as digests, not values). Never run the first
line again after the real class exists: every child's code would stop working.

## 6. The functions (💻, B3, 5 minutes)

Five, not six: `admin-wrap-legacy` (the Sheet import) is not deployed.

```sh
for f in pupil-login pupil-register pupil-recover teacher-reset admin-class; do supabase functions deploy "$f"; done
supabase functions list
```

**Done when** `functions list` shows exactly those five, active.

## 7. The trial class (💻, B6, 5 minutes)

The server key is in Settings → API Keys → **Legacy API keys → `service_role`** (reveal, copy). Paste it at the
`read -rs` prompt; it is never shown.

```sh
read -rs SUPABASE_SERVICE_KEY; export SUPABASE_SERVICE_KEY
curl -s -X POST "https://$(cat supabase/project_ref).supabase.co/functions/v1/admin-class" \
  -H "authorization: Bearer $SUPABASE_SERVICE_KEY" -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "content-type: application/json" \
  -d '{"action":"create","name":"Trial","grade":"5"}'
unset SUPABASE_SERVICE_KEY
```

It prints `{"ok":true,"class_id":"…","class_code":"…"}` **once**. Put both into the password manager as "Trial".
If it prints `{"ok":false,"e":"forbidden"}`: run the three lines again with the **secret** key instead (Settings →
API Keys → `sb_secret_…`). If that is refused too, stop and send the lead only the word `forbidden`.

Then the trial's two test pupils, in the SQL editor, with the `class_id` you just saved (names with letters only: a
name with a digit is refused):

```sql
insert into public.roster (class_id, name_key, display_name)
select '<the Trial class_id>', app.name_key(n), n from unnest(array['Test', 'Tester']) n;
select count(*) from public.roster;
```

**Done when** the count is `2`.

## 8. Send back (📱, 1 minute)

To the lead, in one message:

- "day 0 done", or the step number where it stopped and the line it printed (never a key);
- the **publishable key** (`sb_publishable_…`): public by design, it goes into `config.js`.

Nothing else. The secret key, the `service_role` key, the database password, the pepper and the trial's class code
stay with you.

---

What comes after day 0 (not today): the game's trial switch on your phone once the client work ships
(`docs/LIVE_STAGE.md` D and E), then the backup keys, the full check and the teacher (B4, B5, B7, B8) before the real
class.
