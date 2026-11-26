# Welcome film (behind `?ds=1`)

A 36 s film shown once per device on the first open of the game page, only with the design flag on
(`js/intro.js`, `css/ds-intro.css`, `assets/al/intro/`). `?intro=1` shows it again. Automated browsers do not get it
unless `?intro=1` asks (so the other suites run as before); `tests/intro.py` checks it.

- Nothing plays by itself: the poster shows "צפייה בסרטון" (watch) and "דלגו" (skip, 48 px, from the first second).
  The film is requested only after the tap. Escape closes it. Closing stores `wi_intro=1` on the device.
- The narration is shown as live captions (text, not burned into the picture).
- With the flag off nothing of it is loaded.

## Opening flow (spec, the owner's ask of 2026-11-26; replaces the offer card over the title)

One continuous flow on a device's first open, all behind `?ds=1`: **logo pops in → one tap → the film → a soft fade into
the game**. No credits: the logo is the film's closing lettering, rendered locally; the motion is CSS only. Mock:
`docs/mock/intro.html` (`?w=390|360|320`, `?auto=1` plays it all, `?step=splash|load|film|end|game`, `?ret=1`).

| Time | What the child sees | Notes for the build |
|---|---|---|
| 0 (first paint) | Navy `#050E22`, nothing else. Never the game behind | `js/dsflag.js` (a classic script in `<head>`) adds `html.wi-intro-pending` and one inline `<style>`: `html.wi-intro-pending{background:#050E22} html.wi-intro-pending body>*:not(#wi-intro){visibility:hidden}`. `js/intro.js` drops the class once its box is in the page. Safety: dsflag drops it after 4 s whatever happens (a failed load never leaves a blank page) |
| 0.15 to 0.75 s | **"ניצני אופק" pops in**, centred a little above the middle: scale 0.6 → 1.08 → 1 with a fade-in (0.6 s, `cubic-bezier(.34,1.56,.64,1)`), on a soft aqua glow; at 0.9 s one shine passes over it (brightness 1 → 1.25 → 1, 1.1 s) | `assets/al/intro/logo.webp` (built: a copy of the mock's render, 640 x 201, 44 KB; not in `assets/al/sources.tsv`, which lists Higgsfield files only): "ניצני אופק" in Rubik Moonrocks, gold gradient and glow, exactly the film's closing line, on transparency (rendered like `tools/intro_film.py` does the title; the mock's `docs/mock/intro-logo.webp`, 640 px, 44 KB, is that render). `alt="ניצני אופק"`. Width `min(84%, 330px)` |
| 0.65 s | Under it, the gold button **"▶ צפייה בסרטון"** (60 px high) rises in; under that, small and dim, the sound icon and **"עם קול"** | The one tap browsers require before sound. The button and the logo both start the film; the button has the focus. "דלגו" (48 px, top corner) is there from 0 s; Escape = skip |
| tap | The button and "עם קול" fade (0.15 s). The logo stays; after 0.6 s without a picture, three small aqua dots pulse under it | `src` set and `play()` called on the tap (as today). No black frame: the overlay stays navy |
| first frame (`playing`) | The logo grows a little and fades (scale 1.12, 0.35 s) while the film fades in over it (0.35 s): one cross-fade, no cut to black | Captions, light/full choice, hidden-tab pause: **unchanged** |
| end | The last frame holds (the title is in the film); **"מתחילים"** pops up at the bottom | As today |
| "מתחילים" / "דלגו" / Esc | The film layer fades out (0.45 s); the first screen of the game (today the sign-in; later the new sign-in) is already laid out behind it, and only its panel rises 10 px into place (0.35 s, transform only) | No flash, no layout jump: the game was laid out under the cover the whole time. Focus moves to the first screen's first control. The game's music may start only after this (`wi-intro-closed` event): never under the film |

**A device that has seen it** (`wi_intro=1`): **no splash**, straight to the first screen as today. The class opens it
every day; a logo on every open costs time and says nothing new. (Option if the owner wants it: the logo for 0.5 s,
fade only, no tap, no sound. Not recommended.) "צפייה שוב בסרטון" brings the whole flow back. It does not add a row to the settings (at 360 x 740 that pushed the account panel off): the row "איך משחקים?" says "ארבעת השלבים, והסרטון", and the film is the first card of that help screen (the poster, "▶ צפייה שוב בסרטון", "סרטון הפתיחה, 36 שניות, עם קול"). Mock: `docs/mock/rewatch.html`.

**Reduced motion or calm mode:** the logo and button fade in (0.2 s), no scale, no shine, no rise; the cross-fades stay
but shorter (0.15 s); the film still waits for the tap. **Failure:** if the film has not started 10 s after the tap,
or errors, "מתחילים" appears at once with "הסרטון לא נטען. ננסה שוב בפעם הבאה." (built: the spec said "אפשר לראות אותו אחר כך בהגדרות.", but the settings have no room for a replay row yet: a designer question), and `wi_intro` is not
stored (it is offered again next time). Never a trap: "דלגו" and Esc work in every state.

Fits 390 x 844, 360 x 740 and 320 x 568 (the logo and both buttons stay inside 320 px with 16 px gutters). Hebrew
strings: "צפייה בסרטון", "עם קול", "דלגו", "מתחילים" (existing), and the failure line (new).

## Name

The platform is **ניצני אופק**. The closing title, "ברוכים הבאים לניצני אופק!", is drawn into the film from about 32 s (rebuilt for free by the script below).

## Files and the build

- The master (the film without its closing title, with the final sound mix, 540 x 982) is **not in the repo** (it is
  not played, and git would keep 11 MB forever). Its sha256 is in `docs/ART_LEDGER.md` (batch k7); the owner keeps a copy.
- `tools/intro_film.py MASTER OUTDIR [--l1 ... --l2 ...]` renders the title and writes the two played files:
  `intro.*.mp4` (540 x 982, about 1.8 Mbit/s, the default) and `intro-light.*.mp4` (390 x 710, about 3 MB).
  A rename is a re-run of this script: no credits.
- A share version for the teacher or a presentation (704 x 1280, the clips' native size, about 20 MB) is built the same
  way from a native-size master; it is not in the repo (too large, not played).
- The player (`js/intro.js`) plays the light one by default, the full one only when the browser reports a 4G link with
  data saving off (Safari reports nothing, so iPhones get the light one).
- The sound starts with a 1 s fade-in (the school bell no longer jumps in at full level).
- A hidden tab pauses the film; it goes on only when the child taps "watch" again. While it is open the rest of the
  page is inert; on close, focus goes back where it was.
- Captions: one element per line, each with its own direction (an English line LTR, the Hebrew RTL), so a mixed
  caption is never laid out backwards.
- Escape closes it like "skip" and the device remembers that. The browser's Back (or closing the tab) during the offer
  leaves without a choice, so the film is offered again on the next open.

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