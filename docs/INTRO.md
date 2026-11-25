# Welcome film (behind `?ds=1`)

A 30 s film shown once per device on the first open of the game page, only with the design flag on
(`js/intro.js`, `css/ds-intro.css`, `assets/al/intro/`). `?intro=1` shows it again. Automated browsers do not get it
unless `?intro=1` asks (so the other suites run as before); `tests/intro.py` checks it.

- Nothing plays by itself: the poster shows "צפייה בסרטון" (watch) and "דלגו" (skip, 48 px, from the first second).
  The film is requested only after the tap. Escape closes it. Closing stores `wi_intro=1` on the device.
- The narration is shown as live captions (text, not burned into the picture).
- With the flag off nothing of it is loaded.

## Name

The platform is called **ניצני אופק** (it will hold English, maths, Hebrew language and science). The film's closing title
is live text, "ברוכים הבאים, ניצני אופק!". Nothing else in the game is renamed here.

## Narration (written by us, **flagged for the teacher's review**)

| Time (s) | Text |
|---|---|
| 0.3 to 4.7 | בלילה, באמצע הים, מחכים לכם איים מיוחדים. |
| 5.5 to 8.3 | בכל אי מחכה עולם אחר לגלות. |
| 9.1 to 12.2 | פיצי הסרטן כבר מחכה לכם על החוף: |
| 12.8 to 15.1 | Hi! My name is Pitzi! |
| 16.4 to 19.4 | בוחרים דמות, ויוצאים לדרך. |
| 19.5 to 24.6 | משחקים, טועים, מתקנים, ומשתפרים כל יום עוד קצת. |
| 26.2 to 29.9 | ברוכים הבאים, ניצני אופק! |

Voice: ElevenLabs preset voice Kaia (generated, not a clone), take 1ec486fb-379a-4ec2-9613-83ddce779343. The text sent had
nikud on two words so they are read right: פִּיצִי and נִצָּנֵי אֹפֶק.

Sound: each sentence is cut from the take and placed at its shot; the pauses are true silence. One linear gain, no
compression and no denoising; encoded once as AAC-LC, mono, 48 kHz, 96 kbps target. Measured: -16.8 LUFS, peak
-1.0 dBTP (the take itself: noise floor -84 dB, its pauses below -45 dB). **A person must listen to the take before this ships**;
it was checked here only by length and pauses.
