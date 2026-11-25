# Welcome film (behind `?ds=1`)

A 30 s film shown once per device on the first open of the game page, only with the design flag on
(`js/intro.js`, `css/ds-intro.css`, `assets/al/intro/`). `?intro=1` shows it again. Automated browsers do not get it
unless `?intro=1` asks (so the other suites run as before); `tests/intro.py` checks it.

- Nothing plays by itself: the poster shows "צפייה בסרטון" (watch) and "דלגו" (skip, 48 px, from the first second).
  The film is requested only after the tap. Escape closes it. Closing stores `wi_intro=1` on the device.
- The narration is shown as live captions (text, not burned into the picture).
- With the flag off nothing of it is loaded.

## Name

The platform is **ניצני אופק**. The closing title is live text, "ברוכים הבאים לניצני אופק!".

## Story (version 4, the owner's notes)

1. A generic illustrated school gate at sunset: the four (girl with braids, boy with cap, fox, penguin: our avatars) wave
   goodbye to friends and walk toward the camera.
2. The camera circles to their side on the seaside path; sunset turns to dusk.
3. They step onto the grass above the sea (a short dissolve while the camera moves); push in to their faces, laughing.
4. At "ופתאום" they turn around, the camera swings behind them, and a huge island rises out of the sea.
5. Pitzi is suddenly on a rock beside them and calls to them (his line is spoken in the shot, so his mouth matches);
   the four cheer.
6. The closing title flies in from the front (live text, still with reduced motion or calm mode).

## Narration (written by us, **flagged for the teacher's review**)

| Time (s) | Text |
|---|---|
| 0.3 to 4.9 | הצלצול האחרון. נפרדים מהחברים, ויוצאים לדרך. |
| 5.9 to 9.2 | הולכים יחד לאורך הים, כמו בכל יום. |
| 11.2 to 14.6 | יושבים על הדשא, מדברים, צוחקים... |
| 16.5 to 17.9 | ופתאום... |
| 18.2 to 21.4 | מתוך הים עולה אי ענק! |
| 21.9 to 24.6 | Pitzi: "Hey kids! Are you ready for an adventure?" (caption: היי ילדים! מוכנים להרפתקה?) |
| 26.5 to 30.0 | ברוכים הבאים לניצני אופק! |

The kids' chatter, laughter and cheering are the shots' own generated sound, wordless, ducked under the narration
(the narration stays 8 to 13 dB above it). A person should check that no word can be made out.

Pitzi's line is ours, not from the unit: simple English, with a Hebrew caption under it.

Voices, generated, never clones: ElevenLabs preset voice Kaia for the narration (takes dd64b78b-db60-4e55-9e97-e908bb1cd35a
and 9e3d099a-f624-4dfb-a1b1-52a711fa9798, nikud on לְנִצָּנֵי אֹפֶק); Pitzi's line is generated with his video shot (fdd4513c), so his
mouth matches. A person must check he says the line clearly.

Sound: each sentence is cut from the take and placed at its shot; one linear gain on the voice, no compression and no
denoising (the pauses between lines are true silence). Under it a music bed, original and
instrumental (ElevenLabs Music, job c9f440f8-64c5-4dfe-ac0c-db1ae20e57bd; calm, warm, a little adventurous: plucked
arpeggios over pads, about 84 bpm). It fades in over the first 4 s, sits about 12 dB under the speech, and fades out on
the title (26.4 to 28.9 s). Encoded once: AAC-LC, stereo, 48 kHz, 128 kbps. Measured: -15.6 LUFS, peak -1.6 dBTP; the narration take's noise floor -70 dB.

The music is meant to become the platform's own theme (the map too). The generated piece ends with a short decay at
28 s; a clean loop can be cut at its phrase boundary near 23.2 s for no credits when the map needs it.