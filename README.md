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

## Files

- `index.html`, `css/game.css`, `js/*.js`: the game. Static files, no build step, ES modules.
  - `js/data.js` holds all content and tuning constants (words, stories, sentences, star thresholds, points).
  - `js/state.js` progress, class backend client, speech. `js/audio.js` generated soundtrack and effects.
  - `js/main.js` screens and routing. `js/sling.js`, `listen.js`, `read.js`, `bridge.js` the four level types.
- `assets/`: illustrated backgrounds (`bg/`), sprites (`sp/`), app icons, and the Playpen Sans Hebrew font
  (SIL Open Font License, see `assets/font/OFL.txt`).
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
both sides. `tests/voice_map.py` writes `js/voice.js` from the generation log, which carries those measurements.

Playback (`say()` in `js/state.js`) is Web Audio: the clip is fetched and decoded once, the stretch is cut out with
30 ms before and 80 ms after it, levelled, cached (60 clips), and scheduled 80 ms ahead with a 12 ms fade-in and a
40 ms fade-out on the same audio context that plays the music, so the output is already awake and a phone does not
swallow the start of a word. A level preloads its clips and opens when its first one is ready (or after 3 s). If a
clip cannot be fetched or decoded within 3 s, the old `<audio>` element plays the same stretch, and after that the
browser's own voice speaks. The tests answer the clip host with a small generated WAV, so this path runs for real
in headless Chrome (`python3 tests/play.py --voice` runs only the speech checks).
