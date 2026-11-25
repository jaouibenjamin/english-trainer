# Backend design: Supabase (Phase 1)

Status: design, revised 24.11.2026 after the independent design review (section 12 maps every finding). Nothing here is live. The Google Sheet stays the only backend the class uses until the
owner approves section 3 (the login flow) and says "switch". No Supabase project exists yet; everything is built and
tested against a local PostgreSQL.

Read with `docs/PLAN.md` (Phase 1 and "Weaknesses of the Sheet backend that Phase 1 must close").

Words used below:

- **code**: the pupil's 4-digit secret code. **class code**: the join code of the class. **pictures**: the two
  secret pictures, in order, a pupil picks at registration. **one-time code**: 6 digits the teacher hands over after a reset.
- **the function**: a Supabase Edge Function. It runs on the server; the browser cannot read its secrets.
- **pepper**: a long random secret that exists only in the functions' secrets. It is never in the database, the repo,
  the client or a chat.
- **server role**: the privileged database role the functions and the migration tool use. The browser never has it.
- **session**: Supabase access token (1 hour) plus refresh token, kept on the device after sign-in.

## 1. Schema

Two schemas. `public` is what the browser can reach through the API, always behind row level security. `private` is
not exposed by the API at all and no browser role has any right on it; only the functions (server role) touch it.
`app` holds a few helper functions the policies call.

### public

| Table | Columns | Notes |
|---|---|---|
| `classes` | `id uuid pk`, `name`, `grade`, `roster_only bool`, `max_pupils int default 60`, `created_at` | `roster_only`: only names on the roster may register (recommended on). |
| `roster` | `class_id`, `name_key`, `display_name`, pk (`class_id`,`name_key`) | The teacher's list of first names. |
| `teachers` | `user_id` (auth user), `class_id`, pk both | A row is added by the owner by hand. Google sign-in. |
| `pupils` | `id uuid pk`, `class_id`, `display_name` (2 to 20 letters, same rule as today), `name_key` (lower-cased, spaces squeezed), `auth_user_id` unique nullable, `created_at` | unique (`class_id`,`name_key`). `auth_user_id` is filled at the first sign-in, so migrated pupils need no auth user up front. |
| `items` | `id int pk`, `game`, `item_key`, `skill`, unique (`game`,`item_key`) | Catalogue of things that can be answered, seeded from the repo's content files (section 5). An unknown key is refused. Keeps `answers` rows small. |
| `levels` | `game`, `level_key`, `size int`, pk (`game`,`level_key`) | Catalogue of levels, reading texts (`game = 'read'`) and exam papers (`game = 'exam'`, `size` = number of questions), seeded the same way. |
| `level_best` | `pupil_id`, `game`, `level_key`, `stars`, `at`, pk (first three) | Best stars per level, kept by the server. The teacher's stars come from here, not from the blob. |
| `answers` | `id bigint pk`, `pupil_id`, `item_id`, `correct bool`, `first_try bool`, `pts smallint`, `flag smallint`, `at timestamptz` | Append only. One row per item answered. `pts` and `flag` are set by the server, never by the client. |
| `points` | `id bigint pk`, `pupil_id`, `delta int`, `reason` (`day`, `stars`, `read`, `exam`, `run`, `migrated`, `fix`), `ref text`, `at` | Append only ledger for points that are not one answer: daily bonus, level stars, the total carried over from the Sheet, a teacher's correction. Written by the server only. |
| `pupil_totals` | `pupil_id pk`, `points int`, `answers int`, `first_try int`, `wrong int`, `last_at` | Kept up to date by the same server function that writes `answers` and `points`. The board reads this, so it never scans `answers`. A check function recomputes it from the two ledgers and must match (tested). |
| `progress` | `pupil_id pk`, `state jsonb` (at most 40,000 characters of JSON; the game's own limit stays 30,000), `updated_at` | Transitional: today's `pack()` blob, so the game changes little. `state.pts` is ignored by the board. |
| `flags` | `id bigint pk`, `pupil_id`, `kind` (`rate`, `repeat`, `daycap`, `marathon`, `items`, `levels`, `unusual`, `bonus`), `day date`, `n int`, unique (`pupil_id`,`kind`,`day`) | Sanity-check findings for the teacher. One row per pupil, kind and day with a counter, so a cheater cannot fill the table. |
| `answer_daily` | `pupil_id`, `day`, `item_id`, `tries`, `correct`, `first_try`, `pts` | Roll-up of `answers` older than 90 days (the raw rows are then deleted). Keeps the database inside the free 500 MB. |

Views (section 2 explains how they are protected):

- `class_board`: `display_name`, `points`, `words`, `streak`, `me bool` for the caller's own class. `points` comes
  from `pupil_totals`. `words` and `streak` are read from the pupil's `progress` blob for display only (self-reported,
  not used for the order).
- `teacher_view`: per pupil of the teacher's class: name, points, answers, first-try rate, error rate, stars and levels
  (from `level_best`), last active day, `locked_today` (how many times the name was locked today), code status
  (`set`, `waiting for the pupil` after a reset), recovery status (`open`, `locked until …`, `closed`), open flags.
- `teacher_items`: the class's weakest items (at least 3 tries, highest error rate first), today's "hard words".

### private (never reachable from a browser)

| Table | Columns | Purpose |
|---|---|---|
| `class_codes` | `class_id pk`, `code_lookup bytea unique` | `code_lookup = HMAC-SHA256(pepper, upper-cased class code)`. The class code is an identifier, not a secret: 8 characters from an alphabet without look-alikes (no 0/O, 1/I/L), new at the switch. |
| `pupil_secrets` | `pupil_id pk`, `code_algo`, `code_salt`, `code_hash`, `code_iter`, `code_set_at`, `pic_salt`, `pic_hash`, `pic_iter`, `pepper_id`, `pic_recovered_at` | The code and picture hashes (section 4). `code_hash` null = the teacher reset the code and the pupil has not set a new one yet. |
| `reset_codes` | `pupil_id pk`, `salt`, `hash`, `iter`, `expires_at`, `fails`, `created_by` | The one-time code after a teacher reset, hashed like a code. Valid 48 hours; limits in 4.3. While a row exists, recovery by pictures is refused. |
| `pupil_devices` | `pupil_id`, `device_hash`, `last_ok_at` | Devices that signed in correctly as this pupil. `device_hash = HMAC(pepper, the token the server issued to the device)`. Emptied when the code changes. |
| `legacy_import` | `pupil_id pk`, `salt text`, `hash text` | Staging for the Sheet's hashes during migration; emptied by `admin-wrap-legacy` (4.2). |
| `auth_attempts` | `id`, `class_id`, `name_key`, `kind` (`code`, `picture`, `otc`, `class`), `dev_bucket`, `ip_bucket`, `trusted bool`, `outcome` (`pending`, `ok`, `wrong`), `at` | One row per try. Keyed by class and name, not by pupil id, so a name that does not exist behaves exactly like one that does. Deleted after 30 days. |
| `auth_buckets` | `class_id`, `name_key`, `kind`, `bucket`, `fails`, `round`, `locked_until`, `last_fail_at` | The growing lock per device and per address (section 4). |
| `auth_lock_events` | `class_id`, `name_key`, `kind`, `at`, `until` | One row each time a lock starts. Feeds "locked N times today". |
| `ip_salts` | `day date pk`, `salt bytea` | A random salt per day for hashing addresses. Rows older than 2 days are deleted, after which the hashes cannot be linked to an address by anyone. |
| `answer_batches` | `pupil_id`, `batch_id uuid`, `at`, pk both | A batch of answers that is sent twice (retry on a bad network) is counted once. Deleted after 7 days. |
| `settings` | one row | The limits in sections 4 and 5, so they can be tuned without a migration; also `storage_brake` (section 6), `shadow_mode` (section 8, added with the functions), `backup_pubkey`, `backup_token_hash`, `backup_opened_at` (section 6, added with the backup). |

What changed from the first cut in `PLAN.md`: `class_codes` and all secrets moved to a schema the API cannot see;
`answers` points at a small `items` catalogue and carries its own points; `points` holds only non-answer awards;
`pupil_totals`, `flags`, `roster`, `answer_daily` and the attempt and lock tables are new.

## 2. Row level security

Rules that hold everywhere:

- RLS is enabled on every table in `public` and `private`. With no matching policy, nothing is returned. It is not
  *forced* on the owner: the owner-rights views and functions below are the deliberate, narrow exceptions, and no
  browser role is ever the owner.
- Supabase gives the browser roles every right on new objects in `public` by default and relies on RLS alone. The
  migrations revoke all of that first and grant back only what is listed here.
- `anon` (a visitor who is not signed in) has no right on any table or view and may run one database function,
  `ping()`. Beyond that it can only call the Edge Functions over HTTPS.
- `authenticated` (a signed-in pupil or teacher) gets `select` where listed below and nothing else (the teacher's
  class list is the one table with a direct write). Every other write goes through a database function that checks
  the caller itself.
- `private` has no grant for `anon` or `authenticated`, and the schema is not in the API's exposed list. So "nobody
  reads code hashes from the client" holds twice: no grant, and no route.
- Helper functions (`security definer`, fixed `search_path`):

```sql
create function app.pupil_id() returns uuid language sql stable security definer set search_path = '' as
  $$ select id from public.pupils where auth_user_id = auth.uid() $$;
create function app.class_id() returns uuid language sql stable security definer set search_path = '' as
  $$ select class_id from public.pupils where auth_user_id = auth.uid() $$;
create function app.teaches(c uuid) returns boolean language sql stable security definer set search_path = '' as
  $$ select exists (select 1 from public.teachers where user_id = auth.uid() and class_id = c) $$;
```

| Object | Who may do what | SQL |
|---|---|---|
| `classes` | A pupil reads the row of their own class; a teacher reads the classes she teaches. No client writes. | `create policy classes_read on classes for select to authenticated using (id = app.class_id() or app.teaches(id));` |
| `roster` | The teacher of the class reads, adds and removes names. Pupils: nothing. | `create policy roster_teacher on roster for all to authenticated using (app.teaches(class_id)) with check (app.teaches(class_id));` |
| `teachers` | A teacher reads her own rows. No client writes (the owner adds a teacher by hand). | `create policy teachers_self on teachers for select to authenticated using (user_id = auth.uid());` |
| `pupils` | A pupil reads only their own row. A teacher reads her class. No client writes. Classmates' names are reachable only through `class_board`. | `create policy pupils_read on pupils for select to authenticated using (auth_user_id = auth.uid() or app.teaches(class_id));` |
| `items` | Nobody from a browser, read or write. Item keys are text a pupil's device sends, so a readable catalogue would be a notice board between children. The teacher sees her class's keys through `teacher_items`. | no policy, no grant |
| `answers` | A pupil reads their own; a teacher reads her class. **No insert, update or delete grant for any browser role.** Rows are written only by `record_events()`. | `create policy answers_read on answers for select to authenticated using (pupil_id = (select app.pupil_id()) or app.teaches_pupil(pupil_id));` |
| `points` | Same as `answers`: read own or own class (teacher). No client writes at all. | same shape as `answers_read` |
| `pupil_totals` | Read own, or own class as teacher. No client writes. Classmates' totals only through `class_board`. | same shape as `answers_read` |
| `answer_daily` | Same as `answers`. | same shape as `answers_read` |
| `progress` | A pupil reads only their own row; a teacher reads her class. Written only by `save_progress()`, which takes no pupil id. | same shape as `answers_read` |
| `levels` | Nobody from a browser (the server reads it to price events). | no policy, no grant |
| `level_best` | Same as `answers`: read own, or own class as teacher. No client writes. | same shape as `answers_read` |
| `flags` | Only the teacher of the class reads. A pupil cannot see or clear their own flags. | `create policy flags_teacher on flags for select to authenticated using (app.teaches_pupil(pupil_id));` |
| `class_board` (view) | A pupil sees name and points of every pupil **of their own class only**; a teacher sees her classes. | The view must show classmates, whom the `pupils` policy hides. So it runs with its owner's rights and carries the rule itself: `create view class_board with (security_barrier) as select … from pupils p join pupil_totals t … where p.class_id = app.class_id() or app.teaches(p.class_id);` It exposes four columns and no ids. |
| `teacher_view`, `teacher_items` (views) | Only a teacher, only her class. A pupil gets zero rows. | Same technique: `… where app.teaches(p.class_id)`. They also read the lock tables in `private`, which is why they are owner-rights views; only the listed columns leave. |

Database functions a signed-in pupil may call (each derives the pupil from `auth.uid()` and takes no pupil id):

- `record_events(batch_id uuid, events jsonb)`: section 5.
- `save_progress(state jsonb, base_updated_at timestamptz)`: the caller's own `progress` row, with the size check and
  the two-device rule of section 5.

`anon` may call exactly one function, `ping()`, which returns `true` (the keep-alive).

A teacher may call `teacher_delete_pupil(pupil uuid)` (her class only): deletes the pupil, their answers, points,
progress, secrets and their auth user. This is the "data a teacher or parent can ask to delete" path.

`maintenance()` (the roll-up, the deletions with a short life, a totals check, the storage brake) runs for the server
role only, every night from pg_cron. pg_cron keeps only "1 row" of its answer, so each night's answer is written to
`private.maintenance_log` (kept 60 days), and the view `backend_health` shows the teacher and the owner the last one,
with `warn` set when it is not ok, is older than 36 hours, or the database is at the storage mark.

Tests: `python3 tests/db.py` runs every policy as written on a throw-away local PostgreSQL with a stand-in for what
Supabase provides (`tests/db/stub.sql`: the `auth` schema, the three API roles, `auth.uid()` from the JWT claims, and
Supabase's open default grants): pupil A against pupil B's rows and against another class, the secret tables, direct
writes to `answers`/`points`/`pupil_totals`, the board, a teacher against another class, `anon` against everything,
whole-catalogue checks that catch a table or function added later without its lock, and the load test (35 pupils,
three rounds, plus one pupil from two devices at once).

## 3. The pupil's login, step by step (for the owner's approval)

What a pupil has to know: **the class code, their first name, a 4-digit code, and two secret pictures in order.**
Nothing else. No email, no phone, no birth date.

### A. First time: register

1. The pupil opens the game and taps "I'm new".
2. They type the class code the teacher gave the class (8 letters and digits, on the board).
3. They type their first name. It must be on the teacher's class list.
4. They choose a 4-digit code and type it twice. Codes that everybody tries first are refused with a friendly
   "pick a harder one": four equal digits, runs like 1234 or 4321, pairs like 1212, and years like 2015.
5. They are shown about 20 simple pictures (animals, fruit, objects; no characters, no brands) and tap **two, one
   after the other**: "first this one, then that one. They help you if you forget your code."
6. They are in. The device stays signed in.

### B. Signing in on another device (or after signing out)

1. Tap "I have a name already".
2. Type the class code, the first name and the 4-digit code.
3. They are in, with their progress. The device stays signed in.

Only for pupils who registered before the switch, the first time, in the same step: after their old code is accepted
they choose a **new** 4-digit code and their two pictures (A4, A5). Until that is done nothing is opened.

### C. Staying signed in

1. After A or B the device keeps a session. The pupil is not asked again on that device, also after closing the
   browser or restarting the phone.
2. The 4-digit code is **not kept on the device and is not sent again**. Saving progress uses the session only.
   (The first run of the new version deletes the code the old version kept on the device.)
3. "Sign out" ends it for that device only (used on a shared computer).
4. A pupil who clears the browser's data, or gets a new phone, signs in again as in B.

### D. Wrong code

1. A wrong code says "the name or the code is not right". It says the same thing when the name does not exist.
2. After 5 wrong codes that device or network has to wait: 5 minutes, then 15 minutes, then 1 hour, then 4 hours.
3. No more than 20 wrong codes a day are accepted for one name from unknown devices, and no more than 30 a day from
   one network for all the names of a class together.
4. **A pupil who is already signed in is never thrown out by this.** They keep playing and saving. The pupil's own
   phone, if it signed in correctly in the last month, keeps a few tries of its own even when the name is closed for
   strangers.

### E. "I forgot my code"

1. On the sign-in screen the pupil taps "I forgot my code".
2. They type the class code and their first name.
3. They tap their two secret pictures in order.
4. They choose a new 4-digit code and **two new pictures**.
5. If the pictures were right: the new code is set, they are in, and every other device signed in as them is signed
   out at once.
6. If they were wrong: "that is not it". After **3 wrong tries** recovery for that name is closed until the teacher
   reopens it (F). Signing in with the code, and devices already signed in, are not affected.
7. A pupil can recover by pictures once in 30 days. A second time inside 30 days goes through the teacher.

### F. The teacher resets a code (the fallback)

1. The pupil tells the teacher they cannot get in.
2. The teacher opens the teacher screen (she signs in with Google), finds the name and taps "reset code".
3. The old code stops working at once, every device signed in as that pupil is signed out, and the locks on the name
   are cleared. The screen shows a **one-time code of 6 digits**, once. It works for 48 hours.
4. The pupil taps "I forgot my code", types the class code and their name, taps "I have a code from the teacher" and
   types the 6 digits. **While a reset is waiting, only the teacher's code works; the pictures do not.**
5. They choose a new 4-digit code and two new pictures.
6. Until step 5 is done nobody can sign in with that name. (Today the first person to type that name after a reset
   sets the new code, whoever they are. That hole is closed.)

### What the teacher sees

Next to each name: "locked N times today", "waiting for a new code" after a reset, "recovery closed". For the class:
"many wrong codes today" and "many wrong pictures today, recovery is paused until tomorrow". She never sees a code or
a picture.

### The numbers behind this, plainly

All of these assume secrets chosen at random. Children pick favourites (the cat, a birthday), so read every figure
as a **lower bound** on the attacker's chance; what really protects a class is that tries are few, counted across the
whole class, and shown to the teacher.

- Two pictures in order out of 20 are 380 possibilities. Three tries on one name: 0.79%. (One picture was 15%; two
  without order 1.6%. A swapped order uses one try, not three.)
- Pictures across a class: 5 wrong a day from one network, 10 wrong a day in the whole class, then recovery pauses for
  everybody until the count drops and the teacher is told. At most 2.6% a day that one account in the class falls;
  24.2% if she ignored it for 11 days, after which every name is closed.
- One targeted random code: from one network 10 wrong a day (0.1% a day, 3.1% a month); from many networks 20 a day
  (6.25% a month, 76% a year). So a code is not a secret for a year against someone determined; the teacher's
  "locked N times today" is what ends it.
- Spraying popular codes over a class is **not stopped, it is capped**: one network gets 30 wrong codes a day for the
  class, any number of networks 100 a day (the class brake). The expected accounts opened in a day are
  `wrong tries allowed x share of pupils whose code is among the codes tried / number of codes tried`. With 3 codes
  and 3% of pupils on them: about 1 account a day expected at the brake; from one network 0.3 expected a day, which
  is a 26% chance a day that at least one account opens. The weak-code rule
  exists to push that 3% towards zero: it refuses 970 of the 10,000 codes (below).

## 4. How it works underneath

### 4.1 A session without an email

Supabase Auth issues sessions only to an auth user, and an auth user needs an email, a phone or to be anonymous.

**Chosen:** one auth user per pupil with a synthetic label, `p-<random uuid>@pupils.invalid`. `.invalid` is a
reserved top-level domain that can never receive mail; the label holds no name. The user is created by the function
(admin API), with no password. Public sign-up is off. To sign a pupil in, the function, after its own checks, asks
the admin API for a one-use sign-in token for that user (`generateLink`; nothing is sent anywhere), redeems it on the
server (`verifyOtp`) and returns the session. The browser refreshes the session by itself afterwards. These calls go
to Supabase Auth's HTTP API with plain `fetch` (`supabase/functions/_shared/gotrue.ts`): no client library to pin or
trust (pre-live review S10); a test checks each request against a stand-in, and section 10 against the project.

Rejected:

| Option | Why not |
|---|---|
| The 4-digit code as the Supabase password | Too short, and the public token endpoint would let anyone guess outside our lockout. |
| Password = code mixed with the pepper | Sign-in would also work straight at the public endpoint for anyone who ever gets the pepper. Our lock must be the only door. |
| A random password per pupil stored in `private` | Stores a live credential. Fallback only, if `generateLink` stops fitting. |
| Anonymous sign-in, then bind the anonymous user to the pupil | Anyone with the public key mints auth users; every device leaves one behind; every policy needs one more join. |
| A token signed by the function | The signing secret would live in the function; no refresh or revocation; Supabase is moving to asymmetric keys. |

**The auth user is not trusted to stay as we made it (review B3).** A pupil's session can call the Auth API directly
(change the email, set a password, enrol a second factor). Three layers:

1. **Project settings** make most of it impossible (section 9, the owner's checklist).
2. **A trigger on `auth.users`** refuses any change of email, phone or password on a `@pupils.invalid` user unless it
   comes from the server role, a trigger on `auth.mfa_factors` refuses a factor for such a user, and a trigger on
   `auth.identities` refuses any identity but its one email identity (no linked Google or GitHub: pre-live review
   S6). (Supabase allows triggers on `auth.users`; to be confirmed for updates, `mfa_factors` and `identities`,
   section 10.)
3. **Every sign-in checks** in the database that the auth user still has the label we gave it, no password, no phone,
   no second factor and no other identity. If not, that user is thrown away and a new one is made (tested with each
   trigger switched off).

**Signing out everywhere = a new auth user.** On every teacher reset and every recovery, `pupils.auth_user_id` is set
to null in the same transaction and the old auth user is deleted through the admin API; the next session belongs to a
brand-new user. This does not depend on an admin "sign out by user id" call existing, and it is immediate: the
policies find no pupil for the old user, so even an access token that has not expired yet reads and writes nothing
(tested). A password or factor someone managed to attach dies with the old user.

Sign-up being off, the teacher's auth user is **created by the owner beforehand** with her Google address; her first
Google sign-in then lands on it. No teacher-code bridge is built: teacher Google sign-in is a prerequisite of the
read switch (section 8).

Rate limits (review S1): all sign-ins reach Supabase Auth from the functions' addresses, so 35 pupils signing in
within a minute share one limit. The owner raises the token-verification limit (section 9) and the live test signs in
35 pupils in parallel (section 10).

### 4.2 How the code, the pictures and the one-time code are stored

```
inner  = HMAC-SHA256(key = pepper, message = purpose | pupil id | secret)     purpose: "code", "pic", "otc"
stored = PBKDF2-HMAC-SHA256(password = inner, salt = 16 random bytes, 600,000 rounds, 32 bytes)
```

The two pictures are one secret, `"7>12"` (first, then second).

Honest strength (review S6):

- **Table leaked, pepper not:** nothing can be tested. This is the case the design is built for. The pepper (32
  random bytes, `PUPIL_PEPPER`) lives only in the functions' secrets; never in the database, a backup, the repo, the
  migration tool or a chat.
- **Table and pepper both leaked:** PBKDF2 is not a defence at this size. 10,000 codes and 380 picture pairs per
  pupil fall to one GPU in well under a minute for a whole class. The response is fixed: rotate the pepper, the
  teacher issues one-time codes to everyone, every pupil sets a new code and pictures. `pepper_id` is stored per row.
- Measured locally: 600,000 rounds take 0.11 s. A sign-in is 1 derivation, the first sign-in of a migrated pupil 3
  (old code, new code, pictures), recovery 3. The function CPU limit and whether Web Crypto counts against it are
  checked on the real project (section 10); `kdf_iter` is a setting and is stored per row.
- Rejected: Argon2id or scrypt (a WebAssembly dependency, and memory hardness changes little at 10,000 values);
  bcrypt inside the database (the pepper would travel into SQL and its logs).
- The comparison happens in the database, so the stored hash never leaves it. The review suggests a timing-safe
  compare in the function instead; we keep it in the database because what is compared are two PBKDF2 outputs the
  caller cannot choose or see, so comparison time tells an attacker nothing, and moving the stored hash into the
  function would widen what a function bug can leak.

**Weak codes** are refused at registration and whenever a new code is set: four equal digits, ascending or descending
runs, also across 9-0 (`7890`, `8901`, `0987`), `abab`, `aabb`, `19xx` and `20xx` (408 codes), every code that reads
as a date (`DDMM` or `MMDD`, 588 codes: a classmate often knows the birthday; 40 of them are already in the first
group, so 956 together) and these 14 keypad lines, none of which is in the first two groups: `2580 0852 1470 0741
3690 0963 1357 2468 9753 8642 1379 7913 1397 2684`. Together 970 codes; 9,030 remain, so a pupil easily finds one.
The functions' list is this rule, and a test reads the keypad codes from this paragraph and counts 970
(`supabase/functions/tests`). The message is friendly: "pick one that is harder to guess".

**Hashes from the Sheet** (`SHA-256(salt + ":" + code)`, fast, so dangerous alone):

1. The migration tool runs on the owner's computer and never has the pepper. It writes the old salt and hash into
   `private.legacy_import`, which nothing but the server role can read.
2. A one-off admin function (`admin-wrap-legacy`, callable only with the server key) wraps each one as
   `PBKDF2(HMAC(pepper, "code-legacy" | pupil id | old hash))` into `pupil_secrets` (`code_algo = 'legacy-sha256'`)
   and deletes the staging row. The tool then checks the staging table is empty. Bare hashes exist in the new
   database for minutes, once.
3. First sign-in (**verify**): the function computes the old SHA-256 from the typed code, wraps it and compares.
   Right: the pupil must choose a new code and pictures in that same request (**upgrade**, 3B); the old form is then
   deleted. Nothing is opened before that, so nobody holding only a Sheet-era code that was left on a shared computer
   can enrol pictures quietly; and there is no "set my pictures" call for a signed-in session at all (review S5).
4. The CSV export stays outside the repo and is deleted after use; at retirement the Sheet's salt and hash columns
   are cleared (section 8).

### 4.3 The lockout

Every try is recorded **before** the slow hash is computed (`pending`), under a lock on that class and name, and
marked `ok` or `wrong` afterwards. Parallel guesses cannot slip past a limit; a try that crashes half way counts as
wrong. Names that do not exist go through the same steps, the same hash work and the same limits, and get the same
answer.

Who is asking (review S2, S3):

- **Known device:** after a correct sign-in the server hands the device a random token (256 bits). Only its HMAC is
  stored. A device counts as known for a pupil if it signed in correctly as that pupil in the last 30 days **and is
  not known for any other pupil** (a shared class computer is a stranger for everyone). A known device is judged
  only by its own wrong codes (10 a day), never by what strangers or unlocks did to the name, so the pupil's own phone
  always keeps its reserve (pre-live review S2; tested after strangers reached the ceiling of 29 through two unlocks).
- **Address:** `HMAC(today's random salt, address)`, 8 bytes kept; the raw address is never stored or logged by us
  and the salt is deleted after 2 days. The address is the **last** entry of `X-Forwarded-For` (the one the
  platform's proxy appends; the first is whatever the caller wrote), or a single-address header the platform sets,
  chosen with the function secret `CLIENT_IP_FROM` once section 10 item 10 shows which header the project uses
  (pre-live review S5). A request whose address cannot be read gets a bucket of its own, never one shared by all.
  No guarantee rests on the address alone: the per-name and per-class limits below hold even if every request claims
  a new address.
- **All at once** (pre-live review S1): every limit is a count followed by a write, so the counts are taken under
  database advisory locks held to the end of the request: the address first, then the class and kind, then the name.
  Tested with 35 tries at the same moment: exactly 10 wrong picture pairs compared for the class (17 without the
  locks) and exactly 30 wrong codes from one address.

| Limit | Value | Counts |
|---|---|---|
| Wrong codes before a bucket locks | 5; then 5 min, 15 min, 1 h, 4 h, 4 h … Back to the start after 24 quiet hours or a correct sign-in. | per known device; per address and name for strangers |
| Wrong codes in 24 h, one address, one name | 10 | strangers |
| Wrong codes in 24 h, one address, **all names of a class** | 30 | strangers (review B2) |
| Wrong codes in 24 h, one name, strangers | **20** | every address together |
| Wrong codes in 24 h, one name, strangers including lifted tries | **29**: the daily ceiling, whatever was unlocked | known devices are not counted here and keep their own 10 |
| Wrong codes in 24 h, one class, strangers | 60 → the teacher sees "many wrong codes today"; 100 → sign-in from unknown devices is paused for the class until the count drops **or the teacher lifts it** | class brake; known devices are never paused |
| Wrong picture pairs, one name | **3 → recovery closed until the teacher reopens it** (review B1) | no decay |
| Wrong picture pairs in 24 h, one address, all names | 5 | |
| Wrong picture pairs in 24 h, one class | 10 → recovery by pictures is paused for the class until the count drops, teacher sees it | class brake |
| Recovery by pictures | once per pupil in 30 days; not at all while a teacher reset is waiting | |
| Wrong one-time codes | 5 per address, then that address is refused for this code; 30 in total, then the code is cancelled and the teacher sees it (review S4) | a bully with one network cannot burn it |
| Wrong class codes per address | 30 an hour, kept as one counter per address and hour, not a row per try | |
| Wrong class codes, all addresses together | 2,000 an hour, then everyone waits for the next hour | so forged addresses cannot grow the database (pre-live review S3) |
| Calls per address, any kind | 120 an hour | |
| Registrations per address | 60 an hour (a class registering from the school's one address must fit) | |

The teacher has two remedies, both in `teacher-reset` (review N1, N2): **unlock a pupil** clears that name's locks
and counters without touching the code or the pictures (for the pupil kept off the school computers by someone's
wrong guesses), and **lift the class brake** does the same for the class-wide pauses, so wrong codes before school
cannot cost a lesson. Each use is on record and counted. A lift must not hand whoever caused the lock a fresh day:
after an unlock the name gets a smaller allowance (5 wrong codes from strangers until the next day, not 20) and the
wrong codes before the unlock still count towards the name's daily ceiling of 29; a name can be unlocked at most 2
times a day. After a brake lift the class gets 30 more wrong codes from strangers that day, not another 100, and
the brake can be lifted at most 2 times a day (pre-live review S7).
Exempting "addresses that signed in correctly for this class in the last 30 days", as the review suggests, would
need the address kept 30 days (a per-class keyed hash could do it); we chose not to keep addresses longer than two
days.

What this gives, and what it does not:

- A lock stops **new sign-ins only**. Nothing in the save path reads these tables, so an open session keeps playing
  and saving (tested: a name closed by a bully, the pupil keeps saving).
- A classmate burning tries from one phone locks that phone and that network first, then at most the name for
  unknown devices for a day. The pupil's own known phone still gets in.
- A hard ceiling means a determined person with several networks can keep new devices out of one name, or pause
  unknown-device sign-in for a class, for a day. Open sessions and known devices are not affected, the teacher sees
  it, and her reset clears a name.
- A bully with many networks can still cancel a one-time code with 30 wrong tries (review N3). That only denies: the
  teacher sees it and issues another. Tries arriving together cannot pass 30: the 30th ends the code, and nothing
  after it is compared (tested with 45 at once).
- The one-time code is consumed in the same transaction that sets the new code, and the auth user is replaced before
  the session is issued.

Answers of the functions: `ok`, `class`, `pin` (name or code not right; also "no such pupil" and "code was reset"),
`locked` (with seconds to wait, or -1 for "ask the teacher"), `setup` (old code right, now choose the new code and
pictures), `weak` (code on the deny-list), `picture`, `otc`, `taken`, `roster`, `full`, `input`, `forbidden`, and for
the teacher `limit` (a third unlock of a name, or a third brake lift, in a day). `teacher-reset` checks that the pupil
is hers before any slow hashing, so a stranger's token makes it do no work (pre-live review N3).

### 4.4 The functions

All: POST with JSON under 2 KB; every field validated (names, after NFC and squeezing spaces: an allow-list of Hebrew
letters, Latin letters including é, Ł, Ž (Latin-1 and Latin Extended-A), and space ' ’ ׳ ״ . - inside; 2 to 20;
starting with a letter and ending with a letter, a dot, or ' ’ ׳ right after a letter, so ג׳ורג׳ and ג'ורג' fit
(pre-live review S9). The
same rule is a CHECK on the tables, written with \u escapes, so markup, digits, emoji, other scripts' look-alikes and
invisible or direction characters never reach a row); CORS to the game's origin (hygiene, not protection); never log names, codes or addresses; names
never in a query string; the same amount of work on every path.

| Function | Caller | Does |
|---|---|---|
| `pupil-register` | anyone with the public key | class → class list, free name, class not full, weak-code rule → pupil, code hash, picture hash → session and device token. |
| `pupil-login` | anyone with the public key | limits → verify → (migrated pupil: require the new code and pictures in the same request) → check the auth user is untouched, create one if missing → session, device token, the `progress` blob. |
| `pupil-recover` | anyone with the public key | pictures (or the teacher's one-time code) + new code + new pictures → everything applied in one transaction → new auth user → session. |
| `teacher-reset` (actions `reset`, `unlock`, `unlock_class`) | a signed-in teacher; the function verifies her token with Supabase Auth and the database checks again that she teaches that pupil's class; nothing in the body decides who she is | clears the code, replaces the auth user, clears the name's locks, stores the one-time code's hash, returns the code once. |
| `admin-wrap-legacy` | the server key only; used once at migration | wraps the Sheet's hashes with the pepper (4.2). |
| `admin-class` | the server key only | creates a class and its 8-character code (the lookup needs the pepper), shows the code once; also rotates a class's code. |

Teacher sign-in is Google through Supabase. No bridge from today's teacher code (review S14).

## 5. Points and the board, computed in the database

The browser never sends points. It reports **typed events**; the database prices them with its own rules and caps.
Every way points are earned today is covered, so the number in the pupil's header can equal the board before reads
switch (the header then shows the server's total).

`record_events(batch_id, events)`, at most 200 a call, one transaction, one lock per pupil; a `batch_id` seen before
is ignored.

| Event | Today in the game | Server price | Hard cap (0 points and a flag beyond) | "Unusual" flag (points still given) |
|---|---|---|---|---|
| `answer` {game, item, correct, first_try, t} | 10 first try, 4 later | same | 20 a minute; 600 a day; the same item right 6 times a day; the item must be in the catalogue | 300 a day |
| `level` {game, level, stars} | 15 a star | same; also keeps the best stars per level | 20 levels a day; level in the catalogue; stars 0 to 3 | 12 a day |
| `read` {text} | 50 for a perfect text, once | 50, once per text ever | text in the catalogue | — |
| `exam` {paper, right} | 5 per right answer of a finished paper | same, `right` at most the paper's size | 3 papers a day | — |
| `run` {points} | Beach Run, at most 60 a day | the points sent | 60 a day | — |
| daily bonus | 20 on the first points of a day | 20, decided by the server (Israel time) | once a day | — |

Storage is finite (500 MB for everybody), so what one pupil's device can add in a day is capped too (re-check of
PR 12): 300 answer rows (honest play is about 80), 1,500 calls and 300 kept batch ids (a batch id is kept only when
the call stored something), one Beach Run ledger row a day grown in place; past that nothing is written but a counter
on one flag row, and a call over 64 KB is refused unread (tested: 50,000 answers from one pupil store at most 300
rows). The blob: `save_progress` writes nothing when the blob is unchanged, refuses a write within 5 seconds of the
last (`retry_after`), and stops at 300 writes or 4 MB a pupil a day (each write leaves a dead copy until vacuum;
tested: 5,000 saves of a 39 KB blob as fast as possible write 105 and grow the table by about 4 MB; before, 28,000
made it 428 MB). A refused save loses nothing: the device keeps its progress and the next save carries it.
The storage brake: when `maintenance()` finds the database at 350 MB it switches `storage_brake` on, and events are
then counted but not stored for everybody (saves still work) until the owner frees space; the teacher's
`backend_health` warns. `record_events` then answers `{ok: false, e: 'brake'}`, so the device keeps the batch and
sends it again later with the same id; nothing is lost silently (pre-live review S4). Under the brake the nightly
roll-up waits too: it writes new rows before vacuum can reuse the space of the deleted ones (S3). Nothing is bought. Housekeeping deletes devices not seen for 30 days, flags older than a
year, and folds daily-bonus and Beach Run rows older than the raw window into one row per pupil and reason; a text's
`read` row stays (it pays once, ever). At 35 pupils all at every cap the database still reaches the brake in weeks,
not days, and the brake holds it there.

Time (review S10): the client's `t` is used for the order of answers and the day they belong to (never in the
future, at most 48 hours back), so a pupil who played offline, also on a second device that delivers an earlier
hour late, is credited fairly and not flagged. But **every cap is also counted by the server's arrival time**: 600 answers with points per arrival day
whatever the client claims, so back-dating buys nothing.

Catalogue (review S9): `items`, `levels` and `texts` keys are generated from the repo's content files
(`tools/seed_catalog.mjs` → `supabase/seed/catalog.sql`; a test fails when it is stale). An unknown key earns nothing
and is flagged, and is not stored, so pupils cannot write free text into the database. New content must ship its seed
before the game that uses it.

What "cannot inflate the board" means, honestly: game logic runs in the browser, so a pupil with the console can
send events for answers they did not give. They cannot name a number, they cannot pass the caps (about 7,000 points
on a day of forging at full speed), reaching half of a cap already shows on the teacher screen, and nothing they send
can touch another pupil. Today one request sets 1,000,000.

The blob (`progress`, review S8): 40,000 characters as a table CHECK; every value the board or the teacher view
reads from it goes through a typed, clamped extraction, so one bad blob cannot break the class board (tested with
hostile blobs). `save_progress(state, base_updated_at)`: if the row changed since `base_updated_at` (another device),
nothing is written and the current row is returned; the client joins the two with its existing `merge()` and saves
again. The teacher's stars and levels come from the level ledger (`level_best`), not from the blob.

Points carried over from the Sheet enter as one `migrated` ledger row per pupil, capped at 50,000; the migration
prints every pupil above three times the class median for the teacher to look at.

## 6. Free-plan limits

Numbers as published for the free plan, to be re-read on the day the project is created. Assumptions: 35 pupils a
class, 80 answers per pupil per school day, 5 classes in the grade.

| Limit (free plan) | One class | Whole grade | Comment |
|---|---|---|---|
| Database 500 MB | about 12 MB a month raw; about 40 MB steady with the 90-day roll-up | about 60 MB a month; about 200 MB steady | The limit that matters. At 350 MB: stop and tell the owner. |
| Edge Function calls 500,000 a month | under 1,000 | under 5,000 | Saves and the board do not use functions. An outsider can burn the quota; signed-in pupils would not notice, new sign-ins would stop until the next month. Accepted, visible in the dashboard. |
| Auth users 50,000 monthly active | 36 | about 185 | |
| Egress 5 GB a month | under 100 MB | under 500 MB | |
| Database connections | a few | a few | Functions use the pooled port. |
| Pause after 7 days without activity | — | — | Keep-alive twice a week with the **public** key (`ping()`); the server key is never in GitHub Actions. What counts as activity is checked on the real project. |

Nothing here needs a card. If a limit is reached the project is restricted, not billed.

### Backup (review B4; a Phase 1 deliverable, before the Sheet is retired)

- The free plan has no backup we can restore from, a project paused for long may not come back, and an Actions
  artifact of a public repo can be downloaded by any signed-in GitHub user. So: the database itself produces an
  **encrypted** export. `backup_export()` returns every table as one document encrypted with pgcrypto to a public key
  whose private key only the owner holds (on his computer and one offline copy; never in GitHub, Supabase or a chat).
- Fetching it: `backup_export(p_token)` may be called with the public key. It compares `sha256(p_token)` with a hash
  stored in `private.settings` and returns ciphertext only. **One export** is one opening call (the table list) plus
  its parts, `backup_export(p_token, table, offset)`, all within 30 minutes of the opening; a new export can be
  opened at most once in 6 hours. Only a call with the right token opens one, so wrong-token calls block nothing
  and cost the caller a cheap refusal. Whoever holds a leaked token can take the slot (and gets ciphertext); the
  owner then stores a new hash. The token is a random
  string the owner generates; GitHub holds the token, the database holds its hash. A leaked token yields ciphertext
  and is revoked by storing a new hash. Supabase has no key type for this; it is our own function.
- The twice-weekly workflow keeps each export as an artifact for **7 days** (a public repository's artifacts can be
  downloaded by any signed-in GitHub user, and if the owner's private key ever leaked, every export still stored
  would open). The owner also saves one a month outside GitHub.
- The key is RSA 4096 with an encryption subkey (what pgcrypto's public-key encryption supports, to be confirmed,
  section 10). Each part is one table chunk (2,000 rows) so that no statement timeout cuts it; a table that changes
  between two parts may be a few rows off, and the restore's totals check says so.
- **Restore drill** before the switch: the owner decrypts one export and `tools/restore.py` loads it into a second
  free project; the totals check must pass there. Repeated once a term.
- **Summer:** GitHub switches schedules off after 60 days without repository activity and mails the owner; the
  checklist has a calendar reminder for the last school week to take one export by hand and to press "enable" if the
  mail comes. A paused project is restored from the dashboard within the period Supabase allows (to be read on the
  day, section 10); after it, the export is the only copy.

### Privacy notes (review S11)

- We store: first name, class, game events, hashes that need the pepper. No email, surname, birth date or photo.
- Supabase itself keeps the caller's address in `auth.sessions`, the Auth audit log and gateway logs. We cannot turn
  that off on the free plan; `maintenance()` deletes audit-log rows older than 30 days and reports `audit_purged:
  false` when the platform refuses (section 10), and sessions die with the rotated auth users. `maintenance()` runs
  every night from pg_cron inside the database, not from GitHub. This goes into the note for parents.
- Typed names of failed sign-ins stay 30 days in `private.auth_attempts` (needed for the limits), then are deleted.
- `teacher_delete_pupil` removes the pupil row and everything keyed by the pupil or by class and name (events,
  ledgers, blob, secrets, devices, one-time code, tries, locks) and the auth user. Tested table by table.

## 7. Threat model

| Who | What they try | What stops it | What is left |
|---|---|---|---|
| A curious 11-year-old with the console, signed in as themselves | Read or write another pupil's data | RLS: own rows only; no pupil id is ever taken from a request | Nothing. |
| | Give themselves points | No write grant on any ledger; the server prices typed events; caps and flags | Forged events up to the caps, visible to the teacher. |
| | Read codes or pictures | `private`: no grant, no API route; useless without the pepper | Nothing. |
| | Change their own auth user (password, email, second factor) to keep a back door | Project settings, triggers, a check at every sign-in, a new auth user at every reset and recovery | To be proven on the real project (section 10) before the switch. |
| | Reach the teacher screen | Teacher views return rows only for a user in `teachers`, added by the owner | Nothing. |
| | Find the code on a shared device | The code is never stored; the old version's copy is deleted on first run | An unlocked, signed-in phone can be played by whoever holds it. |
| A classmate who knows the class code and the names | Guess one pupil's code | 20 a day per name, growing locks | 6.25% a month against one name from many networks (76% a year); 3.1% a month from one network. Lower bounds. |
| | Try the popular codes on everybody | Weak-code rule; 30 a day per network for the class; class alarm at 60, brake at 100 | A code that is weak in a way the rule misses. |
| | Guess pictures, on one name or on all | 3 tries per name then closed; 5 a day per network; class pause at 10 a day; teacher told | 0.79% per name; at most 2.6% a day for the class, every day visible. Lower bounds: children pick favourites. |
| | Take over, then keep the account | Recovery forces new pictures; the real pupil's devices are signed out and they tell the teacher; reset gives a one-time code only the teacher hands out | Until the pupil or teacher notices. |
| | Lock a classmate out | Locks stop new sign-ins only; known devices exempt; one-time code cannot be burnt from one network | New devices kept out of a name for a day. |
| | Register under a classmate's name | Class list required; teacher can delete a wrong registration | A not-yet-registered pupil can be impersonated until noticed. Register in class, together. |
| An outsider with the public repo and the public key | Read anything | `anon` may only call `ping()` | Nothing. |
| | Find the class code | It is an identifier, not a secret: 8 characters, limits per address | It gives nothing without a listed name and that name's secrets. |
| | Learn first names | Sign-in and recovery answer the same for existing and missing names | "Name taken" at registration, for a class-code holder. |
| | Forge the address header to dodge per-address limits | Per-name and per-class limits do not depend on the address | Per-address limits may be weaker than written until verified. |
| | Steal the database or a backup | Hashes need the pepper; backups are encrypted to the owner's key | First names, class names, game results (database only). |
| | Steal the functions' secrets too | Nothing cryptographic at this size | Rotate, one-time codes for everyone (4.2). |
| | Burn the function quota | Early cheap refusals | New sign-ins stop until next month; signed-in pupils play on. |
| | Find a server key in the repo or CI | The server key is in the functions' secrets and on the owner's computer only; gitleaks and `secret_guard` on every push | Human error: rotate first. |
| The owner's own accounts taken over | Everything | 2FA on Supabase, GitHub and Google (section 9) | — |

## 8. Cutover (Phase 2), with the way back

1. **Shadow.** The game writes to the Sheet first, then to Supabase. Reads, sign-in, the teacher screen and reset
   stay on the Sheet. The server setting `shadow_mode` (default off) is on during this step only: a correct
   Sheet-era code then opens a session **without** a new code or pictures, under our lockout, so the copy has
   something to write with. A shadow session can only receive copies (`save_progress`, `record_events`): recovery,
   pictures, one-time codes and registration are refused while the setting is on, and nothing it writes is shown to
   a pupil. These rules live in the functions and the database, and are tested there (`tests/functions.py`).
   Turning the setting off replaces every pupil's `auth_user_id`, which ends every shadow session at once; after it a
   Sheet-era code opens nothing but the one upgrade step (new code and pictures, 4.2). A nightly, idempotent re-sync
   (`tools/migrate_sheet.py`) repairs anything a device missed: the Sheet's blob replaces the copy. What shadow
   sessions wrote is reconciled before the board switches: the per-source comparison (step 2) must be zero; any
   pupil whose ledger differs gets a `fix` row from the comparison tool, or the copy is discarded and re-imported.
2. **Compare daily**, per pupil: number of answers, stars per level, equality of the blob; and points **per source**
   (answers, stars, daily bonus, reading, exam, Beach Run), so a gap names its cause. Not point totals alone.
3. **Before the switch** (all must be true): section 10 green on the real project; the owner's checklist done; the
   teacher signed in with Google and saw her class; a restore drill done; the client reports every event type and
   the per-source gap is zero for 3 school days; the owner approved section 3.
4. **The switch** (the point of no return for sign-in): new class code (8 characters) handed out; the client's config
   points at Supabase; the Sheet backend starts answering every request with an error the old client already treats
   as "sign in again", so a stale tab cannot keep writing to the Sheet. Pupils sign in once with their old code and
   choose a new code and pictures.
5. **Way back.** Before step 4: turn dual-write off in the config; nothing else changes. After step 4, within the
   first days: point the config back at the Sheet and re-enable it; progress made meanwhile is pushed back from each
   device by the existing `merge()` (blobs), points earned meanwhile are in the blob too; new codes chosen in
   Supabase are lost and the old ones work again. After the Sheet's hash columns are cleared (a month later) there is
   no way back; the encrypted exports are then the only second copy.

## 9. Owner's manual checklist (in click order)

Steps 12 to 16 need a computer with the Supabase CLI, `openssl` and `gpg`; the rest can be done in a browser.

Accounts first:

1. Supabase: sign up with GitHub, no card. One project, EU region (Frankfurt), a generated database password kept in
   the password manager.
2. 2FA on the Supabase account, the GitHub account and the Google account. Recovery codes on paper.
3. GitHub → repository settings → Code security: secret scanning and push protection on.

Project settings (each has a test in section 10):

4. Authentication → Sign In / Providers: **Allow new users to sign up: off.** Anonymous sign-ins: off. Phone: off.
   Email provider: on (needed for the server-side token), "Confirm email": on, "Secure email change": on. Every
   OAuth provider off except Google.
5. Authentication → Google: client id and secret from the owner's own Google Cloud project (free).
6. Authentication → Advanced / Multi-factor: enrolment off for all factor types. Manual identity linking: off.
7. Authentication → Sessions: JWT expiry 3600; refresh-token rotation on, reuse interval 10 s.
8. Authentication → Rate limits: token verifications raised to at least 150 per 5 minutes for one class. The limit
   is per calling address and all our functions share theirs, so five classes signing in in the same five minutes
   need five times that; raise it again before a second class joins. Sign-ups and email sends at the minimum. No
   custom SMTP.
9. Authentication → URL configuration: site URL and redirect list = the game's address only.
10. API settings: exposed schemas = `public` only. `pg_graphql` extension off. Realtime: off for every table.
11. Database → Extensions: `pgcrypto` (the encrypted export) and `pg_cron` (the nightly clean-up) on.
12. Run the migrations (`supabase db push`), then `supabase/seed/catalog.sql`. The output must say
    "maintenance is scheduled: every night at 02:17 UTC"; if it says "maintenance is NOT scheduled", stop.
13. Secrets for the functions: `PUPIL_PEPPER` generated on the owner's computer (`openssl rand -base64 32`), set with
    `supabase secrets set`, never pasted anywhere else. `ALLOWED_ORIGINS`. Deploy the functions.
14. Backup: generate an RSA 4096 key pair with `gpg` on the owner's computer; store the **public** key in
    `private.settings`; the private key stays on the computer and on one offline copy. Generate the export token
    (`openssl rand -hex 32`) and store its sha256 in `private.settings`.
15. Create the class: call the admin function `admin-class` with the server key (it needs the pepper, so it cannot be
    done in the SQL editor); it prints the 8-character class code once. Load the class list (first names) with the
    SQL editor or, later, the teacher screen.
16. Migration, when Phase 2 starts: `docs/BACKEND.md` 4.2 steps 1 and 2 (`tools/migrate_sheet.py`, then
    `admin-wrap-legacy`), then `shadow_mode` on.
17. Authentication → Users: create the teacher's user with her Google address, auto-confirmed, with a password of 64
    random characters that is thrown away at once (the form asks for one; it must not be usable). Insert her row in
    `teachers` with the SQL editor.
18. GitHub → repository secrets: the project URL, the public key, the export token. **Not** the server key, not the
    database password, not the pepper, not the backup private key.
19. Send the lead: project URL and public key. Nothing else.
20. After the restore drill: delete the drill project.
21. Calendar: last school week, "take a backup export, check the keep-alive".

## 10. Verify on a real project before the switch

Each is a check in `tests/live_check.py` (PR E), run against the project URL with keys from the environment; the
same assertions as the local suites where a local version exists. None can be answered without a project.

| # | What must be true | How it is tested |
|---|---|---|
| 1 | `generateLink` + `verifyOtp` issue a session with sign-up off and an `.invalid` address; `email_confirm` works on create | sign a test pupil in through `pupil-login` |
| 2 | 35 sign-ins in a minute pass the Auth rate limits (and no per-user spacing blocks a second device) | 35 parallel sign-ins, then one pupil twice in 10 s |
| 3 | A pupil token cannot change its user: `PUT /auth/v1/user` with password, with email; `POST /auth/v1/factors`; identity linking; `/otp` and `/recover` for the label address | each must fail, and the user row must be unchanged |
| 4 | Triggers on `auth.users` (update) and `auth.mfa_factors` can be created and fire | migration applies; test 3 passes even with setting 5 of the checklist switched back on in a scratch project |
| 5 | Sign-up, anonymous and phone sign-in are refused with the public key | three calls |
| 6 | After a reset or recovery the old access token reads and writes nothing; the old refresh token is dead | use the old tokens right after |
| 7 | The server role (and the migrations' owner) may reference, read and delete `auth.users`, and delete old `auth.audit_log_entries` | `teacher_delete_pupil`, `maintenance()` |
| 8 | The owner-rights views return rows for a teacher and none for a pupil through the real API; RLS is on everywhere | the access tests of `tests/db.py`, run over HTTP |
| 9 | Only `public` is reachable: `private` and `app` through REST and GraphQL give nothing | calls with a pupil token |
| 10 | Which header holds the caller's address in a function, and that a client-sent copy does not win | call with a forged header, read the bucket |
| 11 | One PBKDF2 of 600,000 rounds, and three in one request, fit the function CPU limit | timing through the function, 20 runs |
| 12 | `verify_jwt = false` works with the project's key format, and `teacher-reset` refuses a pupil token, an expired token and no token | calls |
| 13 | Google sign-in lands on the pre-created teacher user | by hand, once |
| 14 | `ping()` with the public key counts as activity against the pause | read the docs on the day; watch the dashboard's activity over a quiet week in the holidays |
| 15 | `backup_export()` decrypts with the owner's key and restores into a second project with the totals check green | the restore drill |
| 16 | Free-plan numbers of section 6 and the restore window of a paused project | read on the day |
| 17 | Load: 35 pupils, 3 rounds, through the real API | the load test of `tests/db.py` over HTTP |
| 18 | pg_cron is available on the free plan and the nightly `maintenance()` is scheduled and runs | read `cron.job` and `cron.job_run_details` the next morning; `audit_purged` is true |
| 19 | pgcrypto encrypts to the owner's RSA 4096 public key, and a whole-class export finishes inside the statement timeout of the public role | `backup_export` with the token, decrypt, count rows |
| 20 | The local tests ran on PostgreSQL 16; the project's version behaves the same | `tests/db.py` and `tests/functions.py` assertions through the API |

## 11. What the local tests cannot prove

The local harness is a plain PostgreSQL with a stand-in for what Supabase provides (`tests/db/stub.sql`); Docker, and
with it the Supabase CLI's local stack, is not available where this is built. The stand-in proves the SQL: policies,
grants, limits, pricing, concurrency. It does not prove: anything in Supabase Auth (items 1 to 6, 13), the platform's
own grants on the `auth` schema (7), the API layer and what it exposes (8, 9), the function runtime (10 to 12), the
platform's limits (14, 16) or real network load (17). The suites are written so the same assertions run against a
project URL later: the test code asks a small driver to "run this as pupil A"; locally the driver sets the role and
the JWT claims in a transaction, on a project it calls the REST API with that pupil's token.

## 12. Review findings and where they are answered

| Finding | Answer |
|---|---|
| B1 picture recovery | 3 E, F; 4.3 (two pictures in order, closed after 3, per-address and class caps, one-time code only while a reset waits, new pictures forced, once in 30 days) |
| B2 code spraying, weak codes | 3 A, D; 4.2 weak codes; 4.3 (30 per address per class, class alarm and brake); migrated pupils choose a new code |
| B3 auth user, settings | 4.1; sections 9 and 10 |
| B4 backup | section 6 Backup; 8; 9 items 13, 17 |
| S1 | 4.1 rate limits; 9 item 7; 10 items 1, 2, 12 |
| S2 | 4.3 known device |
| S3 | 4.3 address; class code 8 characters, an identifier (3 A, 7, 8) |
| S4 | 4.3 one-time code row and last bullet |
| S5 | 4.2 step 3; 3 B, C |
| S6 | 4.2 |
| S7 | section 2: explicit revokes and default privileges, `search_path = ''`, functions raise without a pupil. **Not FORCE:** forcing RLS on the owner would make the owner-rights views depend on the platform owner role having BYPASSRLS, which is unverified; unforced, the only role that skips RLS is the owner, which no browser can be. Re-examined at 10 item 8. |
| S8 | section 5, the blob |
| S9 | section 5, catalogue (the seed tool, the seed file and its staleness test come with the client PR that fixes the event keys) |
| S10 | section 5, time, "unusual" column, migrated points |
| S11 | section 6, privacy notes |
| S12 | client (PR D): sign-out with local scope; on refresh failure keep local progress and ask to sign in; plain `fetch`, no vendored client; the project host in `connect-src` |
| S13 | section 8 |
| S14 | 4.4; 6 keep-alive; 9 item 15 |
| Nice to have | timing-safe compare: argued in 4.2; names Hebrew/Latin NFC: 4.4; masked input and picture layout: for the UI designer; Realtime off: 9; lock per pupil at first sign-in: 4.3 (one lock per class and name); EU region: 9 |
