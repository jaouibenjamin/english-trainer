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

Sound: each sentence is cut from the take and placed at its shot; one linear gain on the voice, no compression and no
denoising (the take's own noise floor is -84 dB and its pauses are true silence). Under it a music bed, original and
instrumental (ElevenLabs Music, job c9f440f8-64c5-4dfe-ac0c-db1ae20e57bd; calm, warm, a little adventurous: plucked
arpeggios over pads, about 84 bpm). It fades in over the first 4 s, sits about 12 dB under the speech, and fades out on
the title (25.4 to 27 s). Encoded once: AAC-LC, stereo, 48 kHz, 128 kbps. Measured: -16.0 LUFS, peak -1.6 dBTP.

The music is meant to become the platform's own theme (the map too). The generated piece ends with a short decay at
28 s; a clean loop can be cut at its phrase boundary near 23.2 s for no credits when the map needs it.