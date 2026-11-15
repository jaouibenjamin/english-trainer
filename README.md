# איי המילים (Word Islands)

A mobile web game for a 5th-grade English exam (Fantastic 5, Unit 1 "All About Me"). Five islands, one per part of
the unit, each with four levels that match the four exam sections:

| Level | Exam section | What you do |
| --- | --- | --- |
| קלע המילים | vocabulary | pull the slingshot and pop the balloon with the English word that matches the Hebrew meaning |
| תופסים צלילים | listening | a word is spoken from the conch; tap the bubble with that word (later rounds: its meaning) |
| בקבוק הסיפור | reading | read a short story (tap any word for its meaning), then pick the bottle with the right answer |
| גשר המשפטים | sentence writing | lay the word planks in order; am / is / are rounds; capital letter first, full stop last |

A sixth bonus island practises months and numbers. Stars open the next islands and new slingshot balls.
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

- Pupils open the site, type the class code, their first name and a 4-digit code they choose. No email.
- The teacher screen is under settings ("כניסת מורה"), or at the bottom of the login screen, and needs the teacher code from the `config` tab.
- To reset a pupil's forgotten code, delete their row in the `kids` tab; they register again.
- Points: 10 for a correct answer on the first try (4 after a mistake), 15 per star when a level is finished,
  50 for a story answered without mistakes, 20 for each day of practice.

## Tests

Needs Python Playwright and Chrome, plus Node for the mock backend.

```
python3 tests/play.py            # every level of every island, two phone sizes, class mode, audio levels (about 10 minutes)
python3 tests/play.py --quick    # island 1 only in each mode (about 3 minutes)
python3 tests/play.py --shots out/   # also save a screenshot of every screen
```

The script starts its own static server. Class mode runs against `tests/mock.js`, a small Node stand-in for the Apps Script
runtime that executes `backend/Code.gs` unchanged (`node tests/mock.js unit` runs the backend checks on their own).
`CHROME` overrides the browser path.
