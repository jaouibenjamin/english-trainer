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
