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
- **Storage:** `localStorage` key `wi_world`, one record per pupil on the device (`local`, or the class code and name
  when signed in). It is not in the progress record that `pack()` / `merge()` send to the sheet, and the file makes
  no request. `tests/world.py` checks all of this, including against the mock backend in class mode.
