# Word help and slow playback (behind a switch, off by default)

Not part of the game the class sees unless a device is given it: open the game once with `?help=1` (`?help=0` takes it
away again). That device then also has a fourth switch in the settings, "עזרה במילים". With the switch off, or on a
device that never got it, every screen is drawn exactly as before.

- **A tap on an English word** in a sentence or a question shows its Hebrew meaning in a small bubble (`js/help.js`).
  It works by touch, mouse and keyboard (the words are buttons; Escape closes), is announced to screen readers, and
  never lies over an answer, the question's picture or the line it explains. It sits next to its word with a small
  pointer. The help words of a line are one stop for the Tab key; the arrow keys move along the line. Where it works: the am / is / are sentence on the bridge and the
  mock exam's practice. The story level keeps its own line of meanings. The mock exam's paper has no help: it is the
  rehearsal of the real test. A word that is an answer button, or the answer itself, is never a help word; inside the
  text it is drawn like the other help words but is not a button, so it does not stand out. In "who is it?" the number
  words are treated the same way, because they would give the age on the card away.
- **Where the meanings come from** (`js/helpdata.js`): only from the teacher's Unit 1 word list. No machine translation
  and nothing written for this feature; a word that is not in her list is simply not a button. The reading glossary
  that the story level shows is not used (`GLOSSARY=false`): it was written for the game's own stories and several of
  its meanings are wrong outside them. `docs/WORD_HELP_COVERAGE.md` (built by `node tests/help_coverage.mjs --write`)
  lists every glossary entry with the sentences it would appear in, and what has no meaning at all, for the teacher.
- **"המשפט בעברית"** shows the Hebrew of a whole sentence only when the data already holds it, and only where it does
  not give the answer away.
- **The 🐢 button** next to "say it again" (listening) and "read to me" (story) plays the same recorded clip at 0.75 of
  its pace with the pitch kept: through Web Audio with `js/stretch.js`, and through the `<audio>` element's own slow
  playback when Web Audio is not available. A slow replay is the recorded voice or nothing: if the recording cannot be
  played it stays silent, and while the recordings are out of reach the button is hidden. `node tests/stretch_check.mjs` measures the
  result on real clips (length, no clipping, loudness, pitch). The Hebrew narration of the mock exam has no slow
  button: its words appear on screen in time with the voice, and it is not learning material.
- **Help costs nothing.** No points, no star, no mistake. Each use is noted on the device only, in its own
  `localStorage` entry (`wi-help-v1`: per question, which words were looked up, whether the sentence was shown, how
  often it was heard slowly). It is not part of the progress that is saved to the class, so nothing new is sent to the
  backend. Signing out clears it, so the next pupil on a shared device starts empty. Showing it to the teacher is a
  later step that needs the owner's approval.
- **The switch in the address** (`?help=1`, `?help=0`) is taken out of the address once it was read, so a copied link
  does not carry it to another device. `?help=0` on a device that never had the switch changes nothing.

`python3 tests/help.py` checks all of this with the switch off and on.
