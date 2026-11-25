# איי המילים (Word Islands)

A mobile web game for a 5th-grade English exam (Fantastic 5, Unit 1 "All About Me"). Five islands, one per part of
the unit, each with four levels that match the four exam sections:

| Level | Exam section | What you do |
| --- | --- | --- |
| קלע המילים | vocabulary | pull the slingshot and pop the balloon with the English word that matches the Hebrew meaning |
| תופסים צלילים | listening | a word is spoken (never printed); tap the bubble with that word (later rounds: its meaning). Without a voice on the device the word is flashed on the sign instead, and the level says so |
| בקבוק הסיפור | reading | read a short story (tap any word for its meaning), then pick the bottle with the right answer |
| גשר המשפטים | sentence writing | lay the word planks in order; am / is / are rounds; capital letter first, full stop last |

A sixth bonus island practises months and numbers. Stars open the next islands and new slingshot balls.
One star rule everywhere: no mistake or a single slip gives 3 stars, at least 60% right on the first try gives 2,
otherwise 1; using the hint (the lantern) caps the level at 2 and the result screen says so.
The interface is Hebrew (RTL); all English content comes from the teacher's word list.

Motion and sound are kept gentle: nothing on screen flashes more than about once a second, there are no full-screen
flashes, and effects play well under the voice. Settings has a "תצוגה רגועה" (calm display) switch that stops the
looping animations, confetti and shaking; the device's own "reduce motion" setting does the same.

## Files

- `index.html`, `css/game.css`, `js/*.js`: the game. Static files, no build step, ES modules.
  - `js/data.js` holds all content and tuning constants (words, stories, sentences, star thresholds, points).
  - `js/state.js` progress, class backend client, speech. `js/audio.js` generated soundtrack and effects.
  - `js/main.js` screens and routing. `js/sling.js`, `listen.js`, `read.js`, `bridge.js` the four level types.
- `assets/`: illustrated backgrounds (`bg/`), sprites (`sp/`), app icons, voice, 3D models, pictures and the fonts
  (Playpen Sans Hebrew, Fredoka, Rubik: SIL Open Font License, texts in `assets/font/`). `assets/CREDITS.md` lists
  every file with its origin.
- `trainer.html`: the earlier quiz-style trainer ("תרגול קלאסי" in the game's settings). It shares the same progress
  record and class login as the game.
- `config.js`: the backend URL. `backend/Code.gs`: Google Apps Script that stores names, salted PIN hashes and scores
  in a Google Sheet. No pupil data is stored in this repository.
- `tests/play.py`: automated play-through (see below).

## Connect the class (one time, about 10 minutes)

1. Create a new Google Sheet in your own Google account.
2. In the Sheet: **Extensions > Apps Script**. Delete the sample code, paste all of `backend/Code.gs`, save.
3. In the script editor choose the function `setup` and press **Run**. Approve the permission prompt. The Sheet now has two tabs: `config` (class code and teacher code, editable) and `kids`.
4. **Deploy > New deployment > Web app**. Execute as: **Me**. Who has access: **Anyone**. Deploy and copy the web-app URL (it ends in `/exec`).
5. Put that URL in `config.js` between the quotes and commit.

With `config.js` empty the game still works, without login, and progress stays on each device.

## For the teacher

- Pupils open the site, type the class code, their first name and a 4-digit code they choose (the first time they pick
  "פעם ראשונה" at the top of the form, afterwards "יש לי קוד"). No email.
- The teacher screen is at the bottom of the login screen ("כניסת מורה") or at `#teacher`, and needs the teacher code from the `config` tab.
  Each pupil's card leads with stars (out of 66) and levels played; words learned and stories without a mistake are secondary.
  A pupil gets the red tag when 30% or more of their answers were wrong, or after 3 days without practice.
  Class list: first names in column A of the `roster` tab (from row 2). With at least one name there, only listed names can register.
  The teacher code locks for 5 minutes after 5 wrong tries, like a pupil's code.
  Forgotten code: the teacher taps "איפוס קוד" on the pupil's card (or the parent clears the hash cell, column C, in the `kids` tab).
  The pupil then signs in with their name and any 4 digits, which become the new code. Progress stays.
  After changing `backend/Code.gs`, paste it into the script again and deploy a new version (Deploy > Manage deployments > edit > Version: New version).
- The leaderboard shows the podium, the top five and the pupil's own place; nobody is listed as last.
- To reset a pupil's forgotten code, delete their row in the `kids` tab; they register again.
- A pupil can play on more than one device: when the game opens or comes back to the front it joins the record on the
  server with the one on the device (the higher stars, word knowledge and points win), so nothing earned is lost.
  A save that fails is tried again by itself, and signing out waits until progress is saved.
- Ten wrong teacher codes close the teacher screen for 5 minutes (the counter lives in `config`, cells C2:D2).
- Points: 10 for a correct answer on the first try (4 after a mistake), 15 per star when a level is finished,
  50 for a story answered without mistakes, 20 for each day of practice.

## Tests

Needs Python Playwright and Chrome, plus Node for the mock backend.

`python3 tests/all.py --quick` runs every suite (one line each; `--list` shows them, `--jobs 3` runs three at a time,
each with its own servers). The commands below run the main play-through on its own.

```
python3 tests/play.py            # every level of every island, two phone sizes, class mode, audio levels (about 10 minutes)
python3 tests/play.py --quick    # island 1 only in each mode (about 3 minutes)
python3 tests/play.py --laptop   # island 1 with a mouse at three laptop window sizes
python3 tests/play.py --shots out/   # also save a screenshot of every screen
```

The script starts its own static server. Headless Chrome has no speech engine, so the pages get a small stand-in that
"speaks" (the listening level runs in its real, spoken mode); one separate run uses an engine that always fails, to
check the no-voice fallback. Class mode runs against `tests/mock.js`, a small Node stand-in for the Apps Script
runtime that executes `backend/Code.gs` unchanged (`node tests/mock.js unit` runs the backend checks on their own).
`CHROME` overrides the browser path.

### Recorded voice

`js/voice.js` maps every English text the game can speak to a recorded clip and to the stretch of that clip that
holds the words (start and end in milliseconds). The files themselves are not trustworthy at their edges: the speech
generator often starts a word at the very first sample, lets it run into the end of the file, or says it twice. So
every file was measured (speech = above 5% of the peak, blips under 20 ms ignored), words and short phrases were
recorded again as a repetition ("Piano. Piano. Piano.") and one clean repetition was chosen, the one with silence on
both sides. `tests/voice_map.py` writes those measurements from the generation log into `assets/voice/sources.tsv`.

The files are ours and are served with the game (relative URLs, no other host): `tests/voice_local.py build --cache DIR`
downloads each original once into DIR (outside the repo), mixes it to mono, keeps the measured stretch plus 150 ms on
each side, encodes it as mono MP3 (64 kbps, 24 kHz; plays on old iPhones and cheap Androids) into `assets/voice/en/`,
and writes `js/voice.js` with the stretch as offsets into the new file. The Hebrew narration of the mock exam is copied
byte for byte into `assets/voice/he/`. `assets/voice/sources.tsv` lists every local file with the
sha256 of its original, its own sha256 and its text (for the credits); `tests/play.py` fails when a file on disk differs from its sha256. `tests/voice_local.py verify --cache DIR` decodes every local file and checks that the stretch
the player plays sits exactly where the offsets say (waveform cross-correlation against the original).

Playback (`say()` in `js/state.js`) is Web Audio: the clip is fetched and decoded once, the stretch is cut out with
30 ms before and 80 ms after it, levelled, cached (60 clips), and scheduled 80 ms ahead with a 12 ms fade-in and a
40 ms fade-out on the same audio context that plays the music, so the output is already awake and a phone does not
swallow the start of a word. A level preloads its clips and opens when its first one is ready (or after 3 s). If a
clip cannot be fetched or decoded within 3 s, the old `<audio>` element plays the same stretch, and after that the
browser's own voice speaks. The tests fetch and decode the real clip files in headless Chrome, and check that no clip
URL points to another host and that every file the game can ask for is on disk (`python3 tests/play.py --voice` runs
only the speech checks).

## Fraction Bay (מפרץ השברים): math

A second subject in the same game and under the same class login, for the math exam on Friday 20.11.26 (from the teachers' notice):
adding and subtracting fractions and mixed numbers with the same denominator, with regrouping (פריטה), and mixed number ↔ improper fraction.

- Four islands: conversion, addition, subtraction, and an exam island that mixes everything. 11 levels, 33 stars.
- Three level types: the pizza table (build and see the fractions, cut a whole pizza to regroup), the fraction slingshot,
  and the exam sheet (answers typed digit by digit, wrong twice shows the worked solution).
- Every exercise is generated (`js/mdata.js`), so replays are new. `node tests/mdata_check.mjs` checks 30,000 of them:
  right answer, right form, no distractor equal to the answer.
- Progress is saved in the same record as English (`S.m`), so it needs no backend change. Math points count on the class board;
  the teacher screen still shows English only.
- `python3 tests/math.py` plays every math level at two phone sizes and a laptop size (`--quick`: a short run).

## Mock exam (מבחן דמו)

Built from the teacher's seven review stations (Word Power, Guess Who, Be the Boss, Birthday Time, Reading Detective, Mime It)
and her "My Unit 1 check-in". 20 questions in four stations (words, grammar, reading, writing), one try per question.
The report fills in the check-in card per skill; every skill under 80% gets a practice (a rule card and 8 items with
explanations and a second try). A new paper opens only after that practice, drawn mostly from items the pupil has not seen.

- Content: `js/xdata.js` (about 200 items; `src:'ws'` marks items copied from the worksheets). Screens: `js/mock.js`, `css/mock.css`.
- Pictures: `assets/x/pics.webp`, one sheet of 23 drawings in the game's style (made with Higgsfield, `tools/sheet.html` lays them out for capture
  from our own small copies in `assets/x/src/`).
- Progress: `S.x` in the account record (papers, practice times, items seen). No backend change.
- `python3 tests/mock.py` plays exam, report, practice and a second paper at two phone sizes and a laptop size.

## 3D models and pictures: our own copies

Nothing the game shows is loaded from another host. `assets/CREDITS.md` lists every file under `assets/`
and `vendor/` with what it is, where it came from and its job id (`python3 tests/credits.py write` rebuilds it from the
lists; the tests fail when it is out of date or a file is missing from it). `assets/sources.tsv` lists every 3D model and generated picture
kept in the repo: its kind, the local file, the sha256 of the original
and of the local file, and what was done to it. Every file keeps the generator's job id in its name (for the credits).

- `assets/3d/`: the two Beach Run runners (GLB). Only the texture inside each file was made smaller (2048 px to 1024 px
  JPEG); mesh, rig and animation are the original bytes. Each file stays under 3 MB.
- `assets/x/hf_*.webp`: the runners' pictures on the Beach Run menu (512 px).
- `assets/x/src/`: the 23 word-picture sources as 512 px WebP, used only by `tools/sheet.html`.

The address of the storage that holds the originals is private and is written nowhere in the repo (the tests fail if it
appears). An original has the name of its local file, with its own extension; the build scripts get the folder's address
when they have to download: `--base https://HOST/FOLDER/` or the environment variable `WI_STORAGE_BASE`
(`tests/storage.py`). Everything else works without it: the checks, the tests, and a build or verify whose originals are
already in the cache.

`python3 tests/assets_local.py build --cache DIR` downloads the originals once into DIR (outside the repo) and rebuilds
the files and their sha256 (needs Pillow); `verify --cache DIR` compares every file with its original again (for a
model: every byte range except the texture is identical); `check` needs no download. `python3 tests/remote_guard.py`
(also run by `tests/run.py`) fails on any URL of another host in `js/`, `css/`, the pages and the tools, the voice files included: no file is
excused. Exactly one thing is allowed: the class backend URL in `config.js`.

## Features behind a switch

Each feature that is off by default (a device gets it with a parameter in the address) is described in its own file
in [`docs/features/`](docs/features/): what it does, how a device gets the switch, and which test checks it. A new
feature adds a new file there, not a section here.
