# Welcome film (behind `?ds=1`)

A 38 s film shown once per device on the first open of the game page, only with the design flag on
(`js/intro.js`, `css/ds-intro.css`, `assets/al/intro/`). `?intro=1` shows it again. Automated browsers do not get it
unless `?intro=1` asks (so the other suites run as before); `tests/intro.py` checks it.

- Nothing plays by itself: the poster shows "צפייה בסרטון" (watch) and "דלגו" (skip, 48 px, from the first second).
  The film is requested only after the tap. Escape closes it. Closing stores `wi_intro=1` on the device.
- The narration is shown as live captions (text, not burned into the picture).
- With the flag off nothing of it is loaded.

## Name

The platform is **ניצני אופק**. The closing title is live text, "ברוכים הבאים לניצני אופק!".

## Files and the build

- `master.*.mp4`: the film without its closing title, with the final sound mix (not played).
- `tools/intro_film.py MASTER OUTDIR [--l1 ... --l2 ...]` renders the title and writes the two played files:
  `intro.*.mp4` (540 x 982, about 1.8 Mbit/s, the default) and `intro-light.*.mp4` (390 x 710, about 3 MB).
  A rename is a re-run of this script: no credits.
- A share version for the teacher or a presentation (704 x 1280, the clips' native size, about 20 MB) is built the same
  way from a native-size master; it is not in the repo (too large, not played).
- The player (`js/intro.js`) plays the light one when the connection reports saved data or 2G/3G, the full one otherwise.

## Story (version 7, the owner's notes)

1. A generic illustrated school gate at sunset: the four (girl with braids, boy with cap, fox, penguin: our avatars) wave
   goodbye to friends and walk toward the camera.
2. The camera circles to their side on the seaside path; sunset turns to dusk.
3. They sit on the grass above the sea and laugh, each in their own way (a bright giggle, a hearty laugh, a sly
   chuckle, a squeaky honk), no words; behind them small Pitzi peeks out of the sea and ducks back, unnoticed.
4. At "ופתאום" the laughter stops and, in the same move, they turn in shock as the camera swings round to the sea:
   a huge island rises slowly out of the water straight in front of them.
5. Small Pitzi leaps out of the sea toward them with a splash, lands at the water's edge and calls: "Hey kids! Are you ready for an adventure?"
6. "Yeah, let's go!": they run with Pitzi toward that same island; the picture freezes and the title flies in from the front
   ("ברוכים הבאים לניצני אופק!", in the film itself: the letters pop in one by one, "ברוכים הבאים" in aqua
   Rubik Bubbles, "לניצני אופק!" in gold Rubik Moonrocks with moon craters, then a glint passes over them).

## Narration (written by us, **flagged for the teacher's review**)

| Time (s) | Text |
|---|---|
| 0.3 to 4.9 | הצלצול האחרון. נפרדים מהחברים, ויוצאים לדרך. |
| 5.9 to 9.2 | הולכים יחד לאורך הים, כמו בכל יום. |
| 11.2 to 14.6 | יושבים על הדשא, מדברים, צוחקים... |
| 16.3 to 17.7 | ופתאום... |
| 18.5 to 21.8 | מתוך הים עולה אי ענק! |
| 25.2 to 28.6 | Pitzi: "Hey kids! Are you ready for an adventure?" (caption: היי ילדים! מוכנים להרפתקה?) |
| 29.0 to 31.0 | The four: "Yeah, let's go!" (caption: כן, יאללה!) |
| 34.4 to 37.9 | ברוכים הבאים לניצני אופק! (the title is in the picture, so no caption) |

The kids' chatter, laughter and cheering are the shots' own generated sound, wordless, ducked under the narration
(the narration stays 8 to 13 dB above it). A person should check that no word can be made out.

Pitzi's line is ours, not from the unit: simple English, with a Hebrew caption under it.

Voices, generated, never clones: ElevenLabs preset voice Kaia for the narration (takes dd64b78b-db60-4e55-9e97-e908bb1cd35a,
9e3d099a-f624-4dfb-a1b1-52a711fa9798 and, for the closing line, b1e4b4c4-8238-4bd1-9f4b-be1a9e838dd5: the first take of it said
"לנתני"; the plain spelling reads right, checked by speech recognition); Pitzi's line and the four's "Yeah, let's go!" are generated with their video
shots (91f4e24c, 30220de2), so mouths match. A person must check both lines are clear and the laughs have no words.

Sound: each sentence is cut from the take and placed at its shot; one linear gain on the voice, no compression and no
denoising (the pauses between lines are true silence). Under it a music bed, original and
instrumental (ElevenLabs Music, job c9f440f8-64c5-4dfe-ac0c-db1ae20e57bd; calm, warm, a little adventurous: plucked
arpeggios over pads, about 84 bpm). It fades in over the first 4 s, sits about 12 dB under the speech, and fades out on
the title (33.5 to 37 s). Encoded once: AAC-LC, stereo, 48 kHz, 128 kbps. Measured: -15.7 LUFS, peak -1.5 dBTP; picture 540 x 982, about 1.8 Mbit/s (8.3 MB), so the foam and water stay clean; the narration take's noise floor -70 dB.

The music is meant to become the platform's own theme (the map too). The generated piece ends with a short decay at
28 s; a clean loop can be cut at its phrase boundary near 23.2 s for no credits when the map needs it.