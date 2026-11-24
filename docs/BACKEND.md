# Backend design: Supabase (Phase 1)

Status: design, 24.11.2026. Nothing here is live. The Google Sheet stays the only backend the class uses until the
owner approves section 3 (the login flow) and says "switch". No Supabase project exists yet; everything is built and
tested against a local PostgreSQL.

Read with `docs/PLAN.md` (Phase 1 and "Weaknesses of the Sheet backend that Phase 1 must close").

Words used below:

- **code**: the pupil's 4-digit secret code. **class code**: the join code of the class. **picture**: the secret
  picture a pupil picks at registration. **one-time code**: 6 digits the teacher hands over after a reset.
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
| `items` | `id int pk`, `game`, `item_key`, `skill`, unique (`game`,`item_key`) | Catalogue of things that can be answered. Rows are added by the server the first time an item is seen (key format checked, at most 50 new items per pupil per day). Keeps `answers` rows small. |
| `answers` | `id bigint pk`, `pupil_id`, `item_id`, `correct bool`, `first_try bool`, `pts smallint`, `flag smallint`, `at timestamptz` | Append only. One row per item answered. `pts` and `flag` are set by the server, never by the client. |
| `points` | `id bigint pk`, `pupil_id`, `delta int`, `reason` (`day`, `stars`, `migrated`, `fix`), `ref text`, `at` | Append only ledger for points that are not one answer: daily bonus, level stars, the total carried over from the Sheet, a teacher's correction. Written by the server only. |
| `pupil_totals` | `pupil_id pk`, `points int`, `answers int`, `first_try int`, `wrong int`, `last_at` | Kept up to date by the same server function that writes `answers` and `points`. The board reads this, so it never scans `answers`. A check function recomputes it from the two ledgers and must match (tested). |
| `progress` | `pupil_id pk`, `state jsonb` (at most 30,000 characters, as today), `updated_at` | Transitional: today's `pack()` blob, so the game changes little. `state.pts` is ignored by the board. |
| `flags` | `id bigint pk`, `pupil_id`, `kind` (`rate`, `repeat`, `daycap`, `marathon`, `items`, `levels`), `day date`, `n int`, unique (`pupil_id`,`kind`,`day`) | Sanity-check findings for the teacher. One row per pupil, kind and day with a counter, so a cheater cannot fill the table. |
| `answer_daily` | `pupil_id`, `day`, `item_id`, `tries`, `correct`, `first_try`, `pts` | Roll-up of `answers` older than 90 days (the raw rows are then deleted). Keeps the database inside the free 500 MB. |

Views (section 2 explains how they are protected):

- `class_board`: `display_name`, `points`, `words`, `streak`, `me bool` for the caller's own class. `points` comes
  from `pupil_totals`. `words` and `streak` are read from the pupil's `progress` blob for display only (self-reported,
  not used for the order).
- `teacher_view`: per pupil of the teacher's class: name, points, answers, first-try rate, error rate, stars and levels
  (from the blob, as today), last active day, `locked_today` (how many times the name was locked today), code status
  (`set`, `waiting for the pupil` after a reset), recovery status (`open`, `locked until …`, `closed`), open flags.
- `teacher_items`: the class's weakest items (at least 3 tries, highest error rate first), today's "hard words".

### private (never reachable from a browser)

| Table | Columns | Purpose |
|---|---|---|
| `class_codes` | `class_id pk`, `code_lookup bytea unique` | `code_lookup = HMAC-SHA256(pepper, upper-cased class code)`. Lets the function find the class from the code without storing the code. |
| `pupil_secrets` | `pupil_id pk`, `code_algo`, `code_salt`, `code_hash`, `code_iter`, `code_set_at`, `pic_salt`, `pic_hash`, `pic_iter`, `pepper_id` | The code and picture hashes (section 4). `code_hash` null = the teacher reset the code and the pupil has not set a new one yet. |
| `reset_codes` | `pupil_id pk`, `salt`, `hash`, `expires_at`, `fails`, `created_by` | The one-time code after a teacher reset, hashed like a code. Valid 48 hours, cancelled after 5 wrong tries. |
| `pupil_devices` | `pupil_id`, `device_hash`, `last_ok_at` | Devices that signed in correctly as this pupil since the code was last set. `device_hash = HMAC(pepper, device id)`. Emptied when the code changes. |
| `auth_attempts` | `id`, `class_id`, `name_key`, `kind` (`code`, `picture`, `otc`, `class`), `dev_bucket`, `ip_bucket`, `trusted bool`, `outcome` (`pending`, `ok`, `wrong`), `at` | One row per try. Keyed by class and name, not by pupil id, so a name that does not exist behaves exactly like one that does. Deleted after 30 days. |
| `auth_buckets` | `class_id`, `name_key`, `kind`, `bucket`, `fails`, `round`, `locked_until`, `last_fail_at` | The growing lock per device and per address (section 4). |
| `auth_lock_events` | `class_id`, `name_key`, `kind`, `at`, `until` | One row each time a lock starts. Feeds "locked N times today". |
| `ip_salts` | `day date pk`, `salt bytea` | A random salt per day for hashing addresses. Rows older than 2 days are deleted, after which the hashes cannot be linked to an address by anyone. |
| `answer_batches` | `pupil_id`, `batch_id uuid`, `at`, pk both | A batch of answers that is sent twice (retry on a bad network) is counted once. Deleted after 7 days. |
| `settings` | one row | The limits in sections 4 and 5, so they can be tuned without a migration. |

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
- `anon` (a visitor who is not signed in) has no right on any table, view or function. It can only call the four
  functions over HTTPS.
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
| `answers` | A pupil reads their own; a teacher reads her class. **No insert, update or delete grant for any browser role.** Rows are written only by `record_answers()`. | `create policy answers_read on answers for select to authenticated using (pupil_id = (select app.pupil_id()) or app.teaches_pupil(pupil_id));` |
| `points` | Same as `answers`: read own or own class (teacher). No client writes at all. | same shape as `answers_read` |
| `pupil_totals` | Read own, or own class as teacher. No client writes. Classmates' totals only through `class_board`. | same shape as `answers_read` |
| `answer_daily` | Same as `answers`. | same shape as `answers_read` |
| `progress` | A pupil reads only their own row; a teacher reads her class. Written only by `save_progress()`, which takes no pupil id. | same shape as `answers_read` |
| `flags` | Only the teacher of the class reads. A pupil cannot see or clear their own flags. | `create policy flags_teacher on flags for select to authenticated using (app.teaches_pupil(pupil_id));` |
| `class_board` (view) | A pupil sees name and points of every pupil **of their own class only**; a teacher sees her classes. | The view must show classmates, whom the `pupils` policy hides. So it runs with its owner's rights and carries the rule itself: `create view class_board with (security_barrier) as select … from pupils p join pupil_totals t … where p.class_id = app.class_id() or app.teaches(p.class_id);` It exposes four columns and no ids. |
| `teacher_view`, `teacher_items` (views) | Only a teacher, only her class. A pupil gets zero rows. | Same technique: `… where app.teaches(p.class_id)`. They also read the lock tables in `private`, which is why they are owner-rights views; only the listed columns leave. |

Database functions a signed-in pupil may call (each derives the pupil from `auth.uid()` and takes no pupil id):

- `record_answers(batch_id uuid, rows jsonb)`: section 5.
- `record_level(game text, level_key text, stars int)`: section 5.
- `save_progress(state jsonb)`: upsert of the caller's own `progress` row with the size check.

A teacher may call `teacher_delete_pupil(pupil uuid)` (her class only): deletes the pupil, their answers, points,
progress, secrets and their auth user. This is the "data a teacher or parent can ask to delete" path.

`maintenance()` (the roll-up, the deletions with a short life, a totals check; also the keep-alive query) runs for the
server role only.

Tests: `python3 tests/db.py` runs every policy as written on a throw-away local PostgreSQL with a stand-in for what
Supabase provides (`tests/db/stub.sql`: the `auth` schema, the three API roles, `auth.uid()` from the JWT claims, and
Supabase's open default grants): pupil A against pupil B's rows and against another class, the secret tables, direct
writes to `answers`/`points`/`pupil_totals`, the board, a teacher against another class, `anon` against everything,
whole-catalogue checks that catch a table or function added later without its lock, and the load test (35 pupils,
three rounds, plus one pupil from two devices at once).

## 3. The pupil's login, step by step (for the owner's approval)

What a pupil has to know: **the class code, their first name, a 4-digit code, and their secret picture.** Nothing
else. No email, no phone, no birth date.

### A. First time: register

1. The pupil opens the game and taps "I'm new".
2. They type the class code the teacher gave the class.
3. They type their first name (if the teacher uses a class list, the name must be on it).
4. They choose a 4-digit code and type it twice.
5. They are shown about 20 simple pictures (animals, fruit, objects; no characters, no brands) and tap one: "this is
   your secret picture, it helps you if you forget your code".
6. They are in. The device stays signed in.

### B. Signing in on another device (or after signing out)

1. Tap "I have a name already".
2. Type the class code, the first name and the 4-digit code.
3. They are in, with their progress. The device stays signed in.
4. Only for pupils who registered before the switch: the first time, they are asked to pick their secret picture
   (step A5). Their old code keeps working.

### C. Staying signed in

1. After A or B the device keeps a session. The pupil is not asked again on that device, also after closing the
   browser or restarting the phone.
2. The 4-digit code is **not kept on the device and is not sent again**. Saving progress uses the session only.
3. "Sign out" on the device ends it for that device (used on a shared computer).
4. A pupil who clears the browser's data, or gets a new phone, signs in again as in B.

### D. Wrong code

1. A wrong code says "the name or the code is not right". It says the same thing when the name does not exist, so
   nobody can fish for names.
2. After 5 wrong codes that device has to wait: 5 minutes, then 15 minutes, then 1 hour, then 4 hours.
3. No more than 20 wrong codes a day are accepted for one name from strangers' devices, whatever anyone does. After
   that, new sign-ins for that name are closed until the next day.
4. **A pupil who is already signed in is never thrown out by this.** They keep playing and saving. A phone or computer
   that signed in correctly before also keeps a few tries of its own, even when the name is closed for others.

### E. "I forgot my code"

1. On the sign-in screen the pupil taps "I forgot my code".
2. They type the class code and their first name.
3. They are shown the ~20 pictures and tap their secret picture.
4. They choose a new 4-digit code and type it twice.
5. If the picture was right: the new code is set, they are in, and every other device that was signed in as them is
   signed out (in case someone else knew the old code).
6. If the picture was wrong: "that is not it". After **3 wrong pictures** recovery for that name is locked for 24
   hours. After 3 more wrong pictures it is closed until the teacher reopens it (F). Signing in with the code, and
   devices already signed in, are not affected.

### F. The teacher resets a code (the fallback)

1. The pupil tells the teacher they cannot get in (forgot the code and the picture, or recovery is locked).
2. The teacher opens the teacher screen, finds the name and taps "reset code".
3. The old code stops working at once, every device signed in as that pupil is signed out, and all locks on the name
   are cleared. The screen shows a **one-time code of 6 digits**, once. It works for 48 hours.
4. The pupil taps "I forgot my code", types the class code and their name, and then **either** taps their secret
   picture (as in E) **or** taps "I have a code from the teacher" and types the 6 digits.
5. They choose a new 4-digit code. With the teacher's one-time code they also pick a secret picture again.
6. Until step 5 is done nobody can sign in with that name. (Today the first person to type that name after a reset
   sets the new code, whoever they are. That hole is closed.)

### What the teacher sees

Next to each name: "locked N times today" (sign-in or recovery), "waiting for a new code" after a reset, and
"recovery closed" when the pictures ran out. She never sees a code or a picture.

### Two things the owner should decide knowingly

- **One picture out of 20 is a weak secret.** A classmate who knows the class code and a first name has 3 tries: a
  15% chance to get in on the first day and 30% before recovery closes. Every such attempt shows on the teacher
  screen, and a successful one signs the real pupil out, so it is noticed. If that is too much: two secret pictures
  (about 3% instead of 30%) or a bigger grid. Both change what a pupil has to remember, so this is the owner's call,
  not ours. The design works with any of them (`settings`).
- **The class code is short** (`EN-` and 4 digits). Wrong class codes are limited per address, not in total, so a
  patient outsider can find it. It then gives nothing without a name on the class list and that name's code. Keep the
  class list on. A longer class code for new classes is recommended and costs the pupils nothing after the first day.

## 4. How it works underneath

### 4.1 A session without an email

Supabase Auth issues sessions only to an auth user, and an auth user needs an email, a phone or to be anonymous.

**Chosen:** one auth user per pupil with a synthetic identifier, `p-<random uuid>@pupils.invalid`. `.invalid` is a
reserved top-level domain that can never receive mail; it is a label, not anybody's email, and it contains no name.
The user is created by the function (admin API) the first time the pupil signs in, with no password. Public email
sign-up is switched off in the project. To sign a pupil in, the function, after it has checked the code itself, asks
the admin API for a one-use sign-in token for that auth user (`generateLink`, type magic link; nothing is sent
anywhere), redeems it at once on the server (`verifyOtp`) and returns the resulting session to the browser. From then
on the browser refreshes the session by itself; the code is not involved.

Why this one: real Supabase sessions (refresh, sign-out, revocation) with no credential stored anywhere, `auth.uid()`
works in every policy, and one auth user per pupil keeps the auth table tiny.

Rejected:

| Option | Why not |
|---|---|
| The 4-digit code as the Supabase password | Too short for the provider, and the public token endpoint would let anyone guess it with only the provider's own rate limit: our lockout would be bypassed. |
| Password = code mixed with the pepper, then normal password sign-in | Sign-in would also be possible straight at the public endpoint, outside our lockout, for anyone who ever gets the pepper. Our lock must be the only door. |
| A random password per pupil stored in `private`, the function signs in with it | Works, but stores a live credential at rest. Kept only as the fallback if `generateLink` ever stops fitting. |
| Anonymous sign-in on the device, then the function binds that anonymous user to the pupil | Anyone with the public key can mint auth users (abuse, monthly-user count, needs a captcha), every device and every re-login leaves a user behind, and every policy needs one more join. |
| A token signed by the function itself | The signing secret would live in the function, there is no refresh or revocation unless we write them, and Supabase is moving projects to asymmetric keys. |

Sign-out everywhere (after recovery or a reset): the function deletes the pupil's sessions through the admin API. A
stolen access token still works until it expires (1 hour at most); the refresh token is dead at once.

Not verifiable without a project (to check on the day one exists, before any pupil is moved): that `generateLink` +
`verifyOtp` behave as documented with sign-up disabled; which request header carries the caller's address; the time
one hash takes inside the function's CPU limit.

### 4.2 How the code and the picture are stored

A 4-digit code has 10,000 values and a picture 20. No hash, however slow, protects that by itself: if only a salted
slow hash were stored, a leaked table would give every code in under an hour. So the stored value depends on a secret
that is **not in the database**:

```
inner  = HMAC-SHA256(key = pepper, message = purpose | pupil id | secret)       purpose: "code", "pic", "otc"
stored = PBKDF2-HMAC-SHA256(password = inner, salt = 16 random bytes per pupil and purpose, 600,000 rounds, 32 bytes)
```

- The pepper is 32 random bytes in the functions' secrets (`PUPIL_PEPPER`). The database, its backups and the
  migration CSV never contain it. A leaked table without the pepper gives nothing, not in minutes and not in years.
- The slow part (PBKDF2, built into the function runtime, no dependency) is the second line: with table **and**
  pepper, each guess costs about 0.2 s of CPU, so one pupil's code falls in minutes to hours. That case is "the
  functions' secrets leaked": rotate the pepper and reset all codes (teacher reset, or everyone recovers with their
  picture after re-enrolment). `pepper_id` and `code_iter` are stored per row so both can be raised later.
- Rejected: Argon2id or scrypt (need a WebAssembly dependency; with 10,000 values memory hardness changes little, the
  pepper does the work); bcrypt inside the database (the pepper would travel into SQL and its logs).
- The comparison is done in the database in constant time on equal-length values; the stored hash never travels to
  the function, only the salt does.

**Hashes from the Sheet.** The Sheet stores `SHA-256(salt + ":" + code)`. That is weak alone, so it is never stored
bare in the new database. The migration tool wraps it on the way in:
`stored = PBKDF2(HMAC(pepper, "code-legacy" | pupil id | old hash))`, `code_algo = 'legacy-sha256'`, and keeps the old
salt. First sign-in: the function computes the old SHA-256 from the typed code and the old salt, wraps it the same
way and compares (**verify**). If it matches, it stores the code again in the new form above and forgets the old salt
(**upgrade**). Pupils notice nothing; codes keep working. A pupil who never signs in again keeps the wrapped form,
which is as safe as the new one against a leaked table.

### 4.3 The lockout

Every try is recorded **before** the slow hash is computed (`pending`), under a lock on that class and name, and
marked `ok` or `wrong` afterwards. So a burst of parallel guesses cannot slip past the limits, and a try that crashes
half way counts as wrong.

Each try belongs to two buckets for that name: the **device** (the random id the game keeps on the device) and the
**address** (`HMAC(today's random salt, IP address)`, 8 bytes kept; the raw address is never stored or logged, and the
salt is deleted after 2 days).

| Rule | Value |
|---|---|
| Wrong codes before a bucket locks | 5 |
| Lock length per round, per bucket | 5 min, 15 min, 1 h, 4 h, then 4 h each time. Back to the first round after 24 quiet hours or a correct sign-in from that bucket. |
| Wrong codes per bucket in any 24 hours | 10 |
| Wrong codes per name in any 24 hours, from devices that never signed in as that pupil | **20** |
| Wrong codes per name in any 24 hours, all devices together | **29** (the last 9 are reserved for the pupil's own known devices) |
| Wrong pictures | 3 → recovery locked 24 h; 3 more → closed until the teacher resets |
| Wrong one-time codes | 5 → that code is cancelled; the teacher issues another |
| Wrong class codes per address | 30 an hour, then that address waits an hour |
| Registrations per address | 60 an hour (a whole class registering from the school's one address must fit) |

What this gives:

- **Guessing a code:** at most 20 a day from outside, 29 in the worst case. All 10,000 codes take 500 days; the
  Sheet today gives 1,440 a day. Tested in PR C with a simulated day of guessing from many devices and addresses.
- **Bullying by lock:** the limits apply to **new sign-ins only**. Nothing in the save path looks at them, so an open
  session keeps playing and saving (tested in PR C: a locked name with an open session keeps saving). A classmate who
  burns the tries from one phone locks that phone and that address first, not the name. A device that has signed in
  correctly as the pupil is judged only by its own bucket and the 29 ceiling, so the pupil's own phone still gets in
  when the name is closed for strangers. In school everyone shares one address; that is why the pupil's own device is
  exempt from the address bucket.
- **What cannot be avoided:** a hard daily ceiling means someone determined, with several networks, can close new
  sign-ins for one name for a day. The pupil's open devices and known devices are not affected, the teacher sees
  "locked N times today", and her reset clears it.
- **Names that do not exist** go through the same steps, the same hash work and the same locks, and get the same
  answer, so the lock cannot be used to find out which names exist either.

The function returns one of: `ok`, `class` (wrong class code), `pin` (name or code not right), `locked` (with the
seconds to wait), `input`, `busy`. "No such pupil", "wrong code" and "code was reset, not set yet" are all `pin`.

### 4.4 The four functions

All four: accept only POST with JSON under 2 KB, validate every field with the same rules as today (`NAME_RE`, 4
digits), take the caller's address from the platform header, answer only to the game's origin (CORS; this is hygiene,
not protection), never log names, codes or addresses, and do the same amount of work on every path.

| Function | Caller | Does |
|---|---|---|
| `pupil-register` | anyone with the public key | class code → class; class list and "name taken" and "class full" checks; creates the pupil, the code hash and the picture hash; issues the session. |
| `pupil-login` | anyone with the public key | lockout → verify (new or legacy form) → upgrade a legacy hash → create the auth user if missing → mark the device as known → issue the session; returns the pupil's `progress` blob and `needs_picture` for migrated pupils. |
| `pupil-recover` | anyone with the public key; or a signed-in pupil for `set_picture` | picture or one-time code → new code (and new picture with a one-time code) → sign out the other devices → forget known devices → issue the session. `set_picture`: a signed-in pupil who has no picture yet sets it once. |
| `teacher-reset` | a signed-in teacher (the function checks the token and that she teaches that pupil's class; nothing from the request body is trusted for this) | clears the code, signs the pupil out everywhere, clears locks and reopens recovery, returns a new one-time code once. |

Teacher sign-in is Google through Supabase (the `teachers` table). Open point for the lead: `PLAN.md` puts teacher
Google sign-in in Phase 3, but the read switch at the end of Phase 2 already needs a signed-in teacher for the teacher
screen and for reset. Either teacher sign-in moves before the switch, or we add a small bridge that turns today's
class code + teacher code into a teacher session. The database design is the same for both.

## 5. Points and the board, computed in the database

The browser never sends points. It reports what happened, and the database decides what that is worth.

`record_answers(batch_id, rows)`: rows are `{game, item_key, skill, correct, first_try, t}` (at most 200 per call).
For the caller's pupil, in one transaction, under a per-pupil lock:

1. A `batch_id` seen before is ignored (a retry on a bad network does not count twice).
2. Each row gets a time: the client's `t`, but never in the future, never older than 48 hours and never earlier than
   the pupil's previous answer. So a pupil who played offline is credited fairly, and nobody can back-fill last week.
3. Points per answer, the same values the game uses today: right at the first try 10, right later 4, wrong 0.
4. Sanity checks. A row that fails one is **kept, gets 0 points and a flag**; nothing is deleted:
   - `rate`: more than 20 answers in one minute;
   - `daycap`: more than 600 answers with points in one day;
   - `repeat`: the same item right with points more than 6 times in one day (more often than it can be asked);
   - `items`: more than 50 never-seen item keys from one pupil in one day, or a key that does not look like one;
   - `marathon`: answers in 18 or more different hours of the last 24 (a session longer than a day).
5. The first answer with points of a day (Israel time) adds the daily bonus, 20, to the `points` ledger.
6. `pupil_totals` is updated in the same transaction.

`record_level(game, level_key, stars)`: stars 0 to 3, 15 points a star as today, at most 20 levels with points a day
(`levels` flag beyond that), written to the `points` ledger.

What "cannot inflate the board" means, honestly: all game logic runs in the browser, so a pupil with the console can
always send answers they did not give. What they can no longer do is name a number. The most a forged client can earn
in a day is what the fastest, most diligent real pupil could (600 answers and 20 levels, about 7,000 points), and
reaching that leaves flags on the teacher screen. Today one request sets 1,000,000.

Consequences to plan for:

- The board total will not equal the number in the pupil's own header (`S.pts`), which also counts things the server
  does not see yet (reading bonus, mock exam, Beach Run). During Phase 2 the adapter derives answers from the changes
  between two saves (`st`, level stars); the games should later report answers directly, and the header should show
  the server's total. Until then the two numbers differ a little. The points carried over from the Sheet enter as one
  `migrated` ledger row per pupil.
- `words` and `streak` on the board stay self-reported display values. Only `points` orders the board.

## 6. Free-plan limits

Numbers as published by Supabase for the free plan; to be re-read on the pricing page on the day the project is
created. Our numbers assume 35 pupils a class, 80 answers per pupil per school day, 5 classes in the grade.

| Limit (free plan) | One class | Whole grade (5 classes) | Comment |
|---|---|---|---|
| Database 500 MB | about 12 MB a month raw (2,800 answers a day at about 140 bytes with indexes); steady about 40 MB with the 90-day roll-up | about 60 MB a month; steady about 200 MB | This is the limit that matters. Hence small `answers` rows, the roll-up, and 30-day deletion of attempt logs. At 350 MB: stop and tell the owner (shorten the raw window to 30 days before anything else). |
| Edge Function calls 500,000 a month | under 1,000 (sign-ins are rare because devices stay signed in) | under 5,000 | Saves and the board do **not** use functions. Risk: an outsider can burn the quota by hammering a function; signed-in pupils would not notice, new sign-ins would stop until the next month. Accepted, visible in the dashboard. |
| Auth users 50,000 monthly active | 36 | about 185 | One per pupil and teacher. |
| Egress 5 GB a month | under 100 MB | under 500 MB | A save is 1 to 30 KB. |
| Direct database connections 60, pooled 200 | a few | a few | Saves go through the API, not through connections of ours. Functions use the pooled port. |
| Pause after 7 days without activity | — | — | `keepalive.yml` makes one query twice a week (weekly leaves no margin: GitHub may delay a scheduled run by hours, and one failed run would mean a pause). GitHub also switches scheduled workflows off after 60 days without repository activity; relevant in the summer. A paused project is restored by hand from the dashboard, data intact. |
| 2 projects, no automatic backups we can restore from | — | — | The weekly job can also export a dump as a private artifact later; not in Phase 1. Until the switch the Sheet is the backup. |

Nothing here needs a card. If any limit is reached the project is restricted, not billed.

## 7. Threat model

| Who | What they try | What stops it | What is left |
|---|---|---|---|
| A curious 11-year-old with the console, signed in as themselves | Read another pupil's progress or answers | RLS: own rows only; other pupils appear only as name + points on the board of their own class | Nothing. |
| | Write to another pupil's rows | No pupil id is ever taken from the request; every write derives it from the session | Nothing. |
| | Give themselves points, or edit the board | No write grant on `answers`, `points`, `pupil_totals`; points are computed by the server; `progress.state.pts` is ignored | They can forge answers up to the daily caps (section 5) and get flagged. |
| | Read codes or pictures | `private` has no grant and no API route; hashes need the pepper anyway | Nothing. |
| | Reach the teacher screen | Teacher views return rows only where `teachers` has their user id; the row is added by the owner by hand | Nothing. |
| | Find the code left on a shared device | The code is never stored; only a session is, and "sign out" removes it | A classmate who picks up an unlocked, signed-in phone can play as its owner. Same as any app. |
| A classmate who knows the class code and first names | Guess a code | 20 guesses a day per name, growing locks per device and address; 500 days for a full sweep | 0.2% a day per targeted name. |
| | Guess the picture | 3 tries, then 24 h, then closed; the teacher sees it; success signs the real pupil out | 15% to 30% for a determined classmate (section 3, owner's decision). |
| | Lock a classmate out (bullying) | Locks stop new sign-ins only; open sessions and the pupil's known devices keep working; teacher sees "locked N times today"; reset clears it | New sign-ins on a new device can be blocked for a day. |
| | Register under a classmate's name first | Class list on: only listed names; a taken name is refused; the teacher can delete a wrong registration | A pupil not yet registered can be impersonated until the teacher notices. Register in class, together. |
| | Use a reset to take over | After a reset nothing works without the picture or the teacher's one-time code | Whoever the teacher hands the one-time code to. |
| An outsider with the public repo and the public (anon) key | Read anything through the API | `anon` has no grant on any table, view or database function | Nothing. |
| | Create accounts | Email sign-up is off; registering needs a class code and, with the class list on, a listed free name | Finds the class code with enough addresses (section 3); it gives nothing by itself. |
| | Learn which first names are in a class | Sign-in and recovery answer the same for existing and missing names | "Name taken" at registration tells a class-code holder that a name exists. Needed for the pupils; first names only. |
| | Steal the database (leaked backup, SQL access) | Codes and pictures are useless without the pepper; no emails, no surnames, no addresses in the data | First names, class names and game results. |
| | Steal the functions' secrets as well | Slow hash only buys hours | Rotate the pepper and the keys, reset the codes. |
| | Exhaust the free quota (function calls) | Per-address limits answer early and cheaply, but a call is a call | New sign-ins stop until the next month; signed-in pupils keep playing. Accepted. |
| | Get a server key from the repo or the client | Only the public key is ever in the client; the server key lives in function secrets and GitHub Actions secrets; gitleaks and the repo guard run on every push | Human error; rotate first, then clean up. |
