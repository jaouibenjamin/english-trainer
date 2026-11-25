# The new world in the live game (behind `?ds=1`)

On a device with the design flag (`?ds=1`, see `js/dsflag.js`), the English map gets a dock along the bottom, and
`#avatar` opens the character picker. Without the flag nothing of it is fetched, drawn or stored: `js/avatar.js` and
`css/avatar.css` are loaded only when the flag is on, and `#avatar` is an unknown address as before.

- **Character:** one of the 20 in `assets/al/av` (list in `js/world_data.js`, shared with the `world.html` preview).
  **Rule: the eight human kids are always open.** Every child can pick a kid who looks like them from the first
  minute; no child's look is ever locked behind a level (the owner's lead, 25.11.2026). The other twelve (animals,
  robots, the diver, the pilot) open one per energy level, from level 2 to 13: the fox first, the most exciting last
  (see the ladder below). A locked tile shows the whole character at 0.7, a small lock in its top corner and "רמה N"
  in one line at the bottom; it cannot be chosen, and a tap (and the screen reader's name for it) says "(name): אפשר
  לפתוח ברמה N (עוד N רמות)". A character a pupil already chose stays theirs even if it would be locked at their
  level. When a level opens a character, the map says once "דמות חדשה נפתחה!" with its portrait and a button to the
  picker; when several came at once, "דמויות חדשות נפתחו!" with the newest three portraits and "ועוד N". The notice
  never covers the character on the map (or the "?" badge): it sits above the dock, or under the map's header when the
  character stands there; on a short screen where neither fits, it drops its sentence (the heading says it). A device
  that first opens the map at a high level is not told about old news.
- **Its name:** a describing word and an animal, one from each of two fixed lists (`NAME_A`, `NAME_B` in
  `js/world_data.js`), stored as two indexes and the lists' version (`nv: 2`). No free text. A name stored from the
  earlier lists (no version) reads as "no name yet", so nobody gets a different name silently. All 144 names fit on
  one line in the picker and one word per line on the map at 320 and 360 px (`tests/world.py`).
- **Energy:** only goes up. Worked out from what was learned (10 per star, 5 per word known, 5 per story read) and
  kept as the highest value seen. Levels: 0, 40, 90, 150, 220, 300, 380, 460, 540, 620, 700, 760, 820, then +250
  each. The most a pupil can earn today is 980 (66 stars, 59 words, 5 stories), so all 13 levels fit; every threshold
  is at or below the earlier ones (0, 120, 220, 340, 480, 640, 820, 1020), so no device ever shows a lower level.
  These numbers are ours, for the owner and designer to tune (`WORTH` and `LEVELS` in `js/avatar.js`).
- **Today's focus:** the open island with the most words the pupil got wrong and does not know yet; up to 5. The
  button goes to that island. Hidden when there is none.
- **Storage:** `localStorage` key `wi_world`, one record per pupil on the device. A signed-in pupil's record is
  filed under a SHA-256 digest of `wi|` + the class code in upper case + `|` + the name (trimmed, spaces collapsed),
  never under the code or the name; a device that is not signed in uses `local`. The record holds only a character
  id, two indexes, the names' version, the energy, the last level announced and the island the character last stood
  on. Stored energy above 100000 is read as
  100000.
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
  the level opens at once and nothing pulses. If the backdrop cannot load (or takes over 2.5 s), or a stone picture fails, today's list stays (never a blank screen). The path and stones are shared with the world.html preview
  (`js/worldpath.js`, `css/worldpath.css`). Same routes, order and unlock rules as the list.

## The ladder (energy level → character)
| Level | Energy from | Opens |
|---|---|---|
| 1 | 0 | the 8 human kids (always open) |
| 2 | 40 | fox |
| 3 | 90 | cat |
| 4 | 150 | sea turtle |
| 5 | 220 | owl |
| 6 | 300 | parrot |
| 7 | 380 | robot |
| 8 | 460 | diver |
| 9 | 540 | penguin |
| 10 | 620 | shark |
| 11 | 700 | octopus |
| 12 | 760 | green robot |
| 13 | 820 | pilot (helmet) |

Pace, roughly: 15 minutes a day is about two levels played, worth about 100 energy while the stars are new (up to 30
for three stars, about 25 for words learned), so a new character every day or two at first; later the stars are
already earned and energy comes mostly from words, so it slows down. The last one asks for about 84% of all there is.

The maximum (980) is computed in `js/avatar.js` (`MAX_ENERGY`, next to `LEVELS`), and `tests/world.py` fails if the
level that opens the last character is above it. When content adds energy, the ladder is to be revisited.

**Open decision for the owner:** Fraction Bay (math) progress gives no energy today: stars and levels in math do not
count. Counting them would raise the maximum (and open characters sooner for a pupil who plays math); not done here.

## For the teacher's review: the name words (ours, not from Unit 1)
None of these words is in the teacher's Unit 1 list; the words and their Hebrew are ours. The describing words show
both genders.

| Describing word | Hebrew | Animal | Hebrew |
|---|---|---|---|
| Brave | אמיץ/ה | Fox | שועל |
| Happy | שמח/ה | Lion | אריה |
| Clever | חכם/ה | Tiger | טיגריס |
| Fast | מהיר/ה | Eagle | נשר |
| Funny | מצחיק/ה | Wolf | זאב |
| Strong | חזק/ה | Dolphin | דולפין |
| Kind | טוב/ת לב | Panda | פנדה |
| Lucky | בר/בת מזל | Shark | כריש |
| Golden | זהוב/ה | Owl | ינשוף |
| Cool | מגניב/ה | Bear | דוב |
| Mighty | אדיר/ה | Dragon | דרקון |
| Wild | פראי/ת | Rabbit | ארנב |

All 144 pairs were read for an unkind or silly meaning, in English and in the Hebrew under each word; none found.
For her attention: "Wild" (פראי/ת) is meant as "full of energy"; she may prefer to drop it. "Golden" replaced "Super" (its Hebrew "סופר" reads as a writer or a supermarket; "Smart" would have the same Hebrew as "Clever") and "Rabbit" replaced "Falcon" (בז is unknown to many children).
Also ours and to be checked: "דמות חדשה נפתחה!", "דמויות חדשות נפתחו!", "(name) מחכה לכם. רוצים להחליף?", "לבחירת דמות",
"אחר כך", "N דמויות חדשות מחכות לכם. רוצים להחליף?", "ועוד N", "רמה N" (the badge on a locked tile),
"(name): אפשר לפתוח ברמה N (עוד N רמות). מרוויחים אנרגיה כשלומדים, ואף פעם לא מפסידים אותה.",
"בכל רמה חדשה נפתחת דמות חדשה. עכשיו אתם ברמה N."
