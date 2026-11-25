# Welcome film (behind `?ds=1`)

A 34 s film shown once per device on the first open of the game page, only with the design flag on
(`js/intro.js`, `css/ds-intro.css`, `assets/al/intro/`). `?intro=1` shows it again. Automated browsers do not get it
unless `?intro=1` asks (so the other suites run as before); `tests/intro.py` checks it.

- Nothing plays by itself: the poster shows "צפייה בסרטון" (watch) and "דלגו" (skip, 48 px, from the first second).
  The film is requested only after the tap. Escape closes it. Closing stores `wi_intro=1` on the device.
- The narration is shown as live captions (text, not burned into the picture).
- With the flag off nothing of it is loaded.

## Name

The platform is **ניצני אופק**. The closing title is live text, "ברוכים הבאים לניצני אופק!".

## Story (version 2, the owner's, one continuous camera)

1. A generic illustrated school gate at sunset: the four (girl with braids, boy with cap, fox, penguin: our avatars) wave
   goodbye to friends and walk toward the camera.
2. The camera circles to their side on the seaside path; sunset turns to dusk.
3. They step onto the grass above the sea (a short dissolve while the camera moves).
4. Push in to their faces: talking, laughing.
5. A fast pull-back and up: far across the sea a huge island lights up.
6. A flight across the sea onto the island's lantern path, into Pitzi waving on the beach.
7. The four small on the hill, the island lit; title.

## Narration (written by us, **flagged for the teacher's review**)

| Time (s) | Text |
|---|---|
| 0.3 to 4.9 | הצלצול האחרון. נפרדים מהחברים, ויוצאים לדרך. |
| 5.9 to 9.2 | הולכים יחד לאורך הים, כמו בכל יום. |
| 11.2 to 14.6 | יושבים על הדשא, מדברים, צוחקים... |
| 15.5 to 16.6 | ופתאום... |
| 17.5 to 20.3 | באופק נדלק אי ענק! |
| 26.4 to 29.2 | Pitzi: "Hey kids! Are you ready for an adventure?" (caption: היי ילדים! מוכנים להרפתקה?) |
| 29.9 to 33.6 | ברוכים הבאים לניצני אופק! |

Pitzi's line is ours, not from the unit: simple English, with a Hebrew caption under it.

Voices: ElevenLabs preset voices, generated, never clones: Kaia for the narration (take dd64b78b-db60-4e55-9e97-e908bb1cd35a, nikud on
לְנִצָּנֵי אֹפֶק), Archie for Pitzi (7e57dcd5-6db4-4210-b861-97ad87358c78).

Sound: each sentence is cut from the take and placed at its shot; one linear gain on the voice, no compression and no
denoising (the pauses between lines are true silence). Under it a music bed, original and
instrumental (ElevenLabs Music, job c9f440f8-64c5-4dfe-ac0c-db1ae20e57bd; calm, warm, a little adventurous: plucked
arpeggios over pads, about 84 bpm). It fades in over the first 4 s, sits about 12 dB under the speech, and fades out on
the title (29.5 to 31.7 s). Encoded once: AAC-LC, stereo, 48 kHz, 128 kbps. Measured: -16.7 LUFS, peak -1.2 dBTP; the narration take's noise floor -70 dB.

The music is meant to become the platform's own theme (the map too). The generated piece ends with a short decay at
28 s; a clean loop can be cut at its phrase boundary near 23.2 s for no credits when the map needs it.