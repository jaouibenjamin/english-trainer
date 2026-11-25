# The new world in the live game (behind `?ds=1`)

On a device with the design flag (`?ds=1`, see `js/dsflag.js`), the English map gets a dock along the bottom, and
`#avatar` opens the character picker. Without the flag nothing of it is fetched, drawn or stored: `js/avatar.js` and
`css/avatar.css` are loaded only when the flag is on, and `#avatar` is an unknown address as before.

- **Character:** one of the 20 in `assets/al/av` (list in `js/world_data.js`, shared with the `world.html` preview).
  Penguin, octopus, the green robot and the pilot open at energy levels 3 to 6; the children and the other animals are
  open from the start.
- **Its name:** one word from each of two fixed lists (`NAME_A`, `NAME_B` in `js/world_data.js`), stored as two
  indexes. No free text. Both lists are flagged for the teacher's review (see `docs/DESIGN.md`).
- **Energy:** only goes up. Worked out from what was learned (10 per star, 5 per word known, 5 per story read) and
  kept as the highest value seen. Levels: 0, 120, 220, 340, 480, 640, 820, 1020, then +250 each. These numbers are
  ours, for the owner and designer to tune (`WORTH` and `LEVELS` in `js/avatar.js`).
- **Today's focus:** the open island with the most words the pupil got wrong and does not know yet; up to 5. The
  button goes to that island. Hidden when there is none.
- **Storage:** `localStorage` key `wi_world`, one record per pupil on the device. A signed-in pupil's record is
  filed under a SHA-256 digest of `wi|` + the class code in upper case + `|` + the name (trimmed, spaces collapsed),
  never under the code or the name; a device that is not signed in uses `local`. The record holds only a character
  id, two indexes and a number. Stored energy above 100000 is read as 100000.
- It is not in the progress record that `pack()` / `merge()` send to the sheet, and the file makes no request.
  `tests/world.py` checks all of this, including against the mock backend in class mode, a damaged or edited record,
  and the class code typed in another case.
- **A browser without `crypto.subtle`** (an insecure page) cannot make the key: a signed-in pupil reads in the dock
  "במכשיר הזה אין דמויות. משחקים כרגיל!" (our words, flagged for the teacher's review), and nothing is stored. A write keeps only well-formed keys (`local`,
  `h:` + 64 hex) and drops any other.
- **The map with the flag:** the islands are sized so that a picture and its label fit between two islands of one
  column, with the dock's 76 px kept free (`worldIw` in `js/main.js`); without the flag the map is unchanged.
- **Deleting it:** the records stay on the device after sign-out, one per pupil who chose a character there. Clearing
  the site's data in the browser (or `localStorage.removeItem('wi_world')`) deletes them all; nothing is kept anywhere
  else.
- **Today's focus** leaves out the bonus island (months and numbers): it is about the unit's five word lists.
- **The character on the map** (docs/DESIGN.md spec): the chosen character stands, as a 44 px framed portrait token with
  a small shadow on the ground, on the island played now (the one marked "ממשיכים כאן"; when every island is full, the
  last one), in the crab's place at the island's lower edge, beside the tag and never over it. When that island changes
  it hops once from the island it stood on before (`at` in the record): an arc, 0.9 s, a squash on landing; any tap or
  key ends it and still does what it would have done; none with reduced motion or calm mode. On a small island (a short
  phone) the token is at most 60% of the island's picture. With no character yet, Pitzi stands there as today with a
  small "?" badge (a 48 px tap area) that opens the picker; on a device that cannot keep one, Pitzi alone. A remembered
  island that is not open is no position. With the flag, the island played now also says "ממשיכים כאן" (or "מתחילים
  כאן") to a screen reader; without it the island's label is as today.
- **An island as a path** (docs/DESIGN.md spec): with the flag, an island's levels are stones along the painted path
  of the English island backdrop, in their order, joined by a dotted line (gold up to the next stone, dim after it).
  Each stone has a label on a dark plate with the level's name and sub-line, exactly as in today's list (it wraps on a
  narrow screen, never below 15 px), and stone and label are one button. Played stones are lit with their stars, the
  first not played glows and pulses softly, the others are open (as today, every level of an open island can be
  played). The character, a 52 px token, stands on the glowing stone and glides to a tapped one (0.45 s, ease-out)
  before the level opens; a second tap ends the glide and goes at once (two quick taps open the level once), the back
  button is never held up, and with reduced motion or calm, with no character, or on a device that cannot keep one,
  the level opens at once and nothing pulses. The path and stones are shared with the world.html preview
  (`js/worldpath.js`, `css/worldpath.css`). Same routes, order and unlock rules as the list.
