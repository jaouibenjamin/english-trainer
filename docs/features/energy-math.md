# Energy from Fraction Bay, and the ladder past level 13 (proposal, no code yet)

The owner's decisions (2026-11-25): Fraction Bay gives energy too, with the same rule (energy only ever goes up), and
the unlock ladder grows past level 13 for ten new characters the designer is making. English plus math should reach
about 23 levels. This page is the proposal; the code follows once the owner and the lead pick an option.

## What exists today
- Energy (js/avatar.js): 10 per English star, 5 per word known, 5 per story read. The most: 66 stars, 59 words,
  5 stories = **980**. Levels 1 to 13 at 0, 40, 90, 150, 220, 300, 380, 460, 540, 620, 700, 760, 820; past 820, one
  level per 250. The 12 characters open at levels 1 to 13.
- Fraction Bay (js/mdata.js): 4 islands, 11 levels, **33 stars** at most (S.m.st, the best stars per level).
  Exercises are not counted per pupil (only each level's best stars are kept), so **stars are the only fair unit**:
  a math star costs about the same effort as an English one (a level of 4 to 6 exercises).

## Two options

| | A: 20 per math star (recommended) | B: 15 per math star |
|---|---|---|
| Most energy (English + math) | 980 + 660 = **1640** | 980 + 495 = **1475** |
| Levels 14 to 23 (new characters) | 890, 950, 1020, 1080, 1150, 1220, 1280, 1350, 1410, 1480 | 870, 920, 970, 1020, 1080, 1130, 1180, 1230, 1280, 1330 |
| The last character (level 23) at | 90% of everything | 90% of everything |
| All English, no math | level 15 | level 16 |
| All math, no English | level 10 | level 8 |
| All English + half of math | level 20 | level 20 |
| Everything | level 23 | level 23 |

Both keep:
- levels 1 to 13 exactly where they are (no pupil's level ever goes down; the existing 12 characters open as today);
- the last new character reachable only with both subjects, at 90% of everything, so it is not trivial and not
  impossible;
- past level 23, one level per 250, as today past 13;
- energy only ever goes up: math stars are best-ever stars, and a stored energy is never lowered.

**Why A:** math is half of what the class practises, but it has half as many stars (33 against 66). At 20 a math star
weighs what an English star plus its words weigh (980 / 66 is about 15), so a pupil who loves maths is not held back,
and a pupil who does only English still reaches level 15 (two new characters).

## The code once an option is picked (small)
- `WORTH.mstar` and `earned()` adding the math stars (from S.m, the same record the class already syncs).
- `LEVELS` gets ten more thresholds; `MAX_ENERGY` adds `WORTH.mstar * M_MAX`.
- The ten new characters in js/world_data.js with `open: 14 .. 23` (the designer's art; until it lands, the ladder
  can ship with the thresholds and no character at those levels).
- tests/world.py's reachability check covers the new ladder: the level that opens the last character is at or below
  `MAX_ENERGY`, and above the English-only maximum (so it needs both subjects); levels 1 to 13 unchanged; a math star
  raises energy and the level never goes down after a sync.
- Nothing new is sent to the backend: energy is computed on the device from progress that is already saved.
