# Welcome film (behind `?ds=1`)

A 32 s film shown once per device on the first open of the game page, only with the design flag on
(`js/intro.js`, `css/ds-intro.css`, `assets/al/intro/`). `?intro=1` shows it again. Automated browsers do not get it
unless `?intro=1` asks (so the other suites run as before); `tests/intro.py` checks it.

- Nothing plays by itself: the poster shows "צפייה בסרטון" (watch) and "דלגו" (skip, 48 px, from the first second).
  The film is requested only after the tap. Escape closes it. Closing stores `wi_intro=1` on the device.
- The narration is shown as live captions (text, not burned into the picture).
- With the flag off nothing of it is loaded.

## Name

The platform is **ניצני אופק**. The closing title is live text, "ברוכים הבאים לניצני אופק!".

## Story (version 3, the owner's notes)

1. A generic illustrated school gate at sunset: the four (girl with braids, boy with cap, fox, penguin: our avatars) wave
   goodbye to friends and walk toward the camera.
2. The camera circles to their side on the seaside path; sunset turns to dusk.
3. They step onto the grass above the sea (a short dissolve while the camera moves); push in to their faces, laughing.
4. A rumble: the camera pulls back as a huge island rises out of the sea, water pouring off it, lanterns lighting up.
5. Pitzi leaps onto a rock at the water's edge and calls to them; the four cheer and wave.
6. The frame opens to the whole scene; title.

## Narration (written by us, **flagged for the teacher's review**)

| Time (s) | Text |
|---|---|
| 0.3 to 4.9 | הצלצול האחרון. נפרדים מהחברים, ויוצאים לדרך. |
| 5.9 to 9.2 | הולכים יחד לאורך הים, כמו בכל יום. |
| 11.2 to 14.6 | יושבים על הדשא, מדברים, צוחקים... |
| 16.3 to 17.7 | ופתאום... |
| 18.1 to 21.3 | מתוך הים עולה אי ענק! |
| 22.3 to 25.0 | Pitzi: "Hey kids! Are you ready for an adventure?" (caption: היי ילדים! מוכנים להרפתקה?) |
| 28.1 to 31.9 | ברוכים הבאים לניצני אופק! |

The kids' chatter, laughter and cheering are the shots' own generated sound, wordless, ducked under the narration
(the narration stays 8 to 13 dB above it). A person should check that no word can be made out.

Pitzi's line is ours, not from the unit: simple English, with a Hebrew caption under it.

Voices: ElevenLabs preset voices, generated, never clones: Kaia for the narration (take dd64b78b-db60-4e55-9e97-e908bb1cd35a, nikud on
לְנִצָּנֵי אֹפֶק), Archie for Pitzi (7e57dcd5-6db4-4210-b861-97ad87358c78).

Sound: each sentence is cut from the take and placed at its shot; one linear gain on the voice, no compression and no
denoising (the pauses between lines are true silence). Under it a music bed, original and
instrumental (ElevenLabs Music, job c9f440f8-64c5-4dfe-ac0c-db1ae20e57bd; calm, warm, a little adventurous: plucked
arpeggios over pads, about 84 bpm). It fades in over the first 4 s, sits about 12 dB under the speech, and fades out on
the title (28 to 30.5 s). Encoded once: AAC-LC, stereo, 48 kHz, 128 kbps. Measured: -15.7 LUFS, peak -1.5 dBTP; the narration take's noise floor -70 dB.

The music is meant to become the platform's own theme (the map too). The generated piece ends with a short decay at
28 s; a clean loop can be cut at its phrase boundary near 23.2 s for no credits when the map needs it.