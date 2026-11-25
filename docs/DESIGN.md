# Design system v1: Arcade Lagoon

Night sea, dark glass panels, aqua and gold accents. Files: `css/ds.css` (tokens + components, all classes prefixed `wi-`), `ds.html` (live preview, noindex, not linked). Nothing in the live game loads either file yet.

## Principles
- One main action per screen, targets at least 48px, text never below 16px (14px only for tags).
- Mistakes explain and come back. Warm coral "fix" colour, never alarm red. Nobody shown last.
- Energy is earn-only: never drains, never blocks, replaying anything open is free. No copy may say "lost", "not enough", "out of".
- Glow lives in image assets. CSS uses solid edges and flat rings only: no blur, no backdrop-filter, no animated shadow.
- Exam and anything printed use the light "paper" card inside the dark shell.
- Nothing leans on the art behind it. Whatever sits on a picture brings its own solid backing: a filled disc with a dark keyline (`--wi-scrim`) outside its ring, or a `wi-plate` under text, labels and star rows. Bare text on art is not allowed, because the real sea glows and no ratio measured on a placeholder would hold.

## Tokens (contrast measured, WCAG 2.x)
| Token | Hex | Use | Pair and ratio |
|---|---|---|---|
| navy-900 | #0B1E3F | page background | white 16.51, dim 8.56, aqua 10.41, gold 11.44 |
| navy-800 | #11295A | card, panel | white 14.11, dim 7.31, aqua 8.89, gold 9.77, good 8.40, fix 6.16, locked 4.53 |
| navy-700 | #18376B | raised, disabled button | white 11.68, dim 6.05, aqua 7.37, gold 8.09; disabled ring (locked) 3.75 |
| text / dim | #FFFFFF / #A9BCD9 | text on dark | see above |
| aqua | #2EE6C5 | energy, current stone, links | navy-900 on aqua 10.41 (aqua-press #25C9AD: 7.89) |
| gold | #FFD23F | main button, stars, done | navy-900 on gold 11.44 (gold-press #E8B91F: 8.96) |
| azure | #134B8A | secondary button | white 8.75 (press #0F3B6E: 11.22) |
| magenta | #C7367A | special, rare only | white 4.96, fine for 18px bold; press #A22660: 7.04 |
| good / fix | #5BE08F / #FF8A7A | right / let's fix it, on dark | 8.40 / 6.16 on navy-800 |
| locked | #7F93B5 | lock icon, locked label, locked stone ring, disabled button ring | text: 4.53 on navy-800, 5.30 on navy-900 (plate). Shape only on navy-700 (3.75). Ring against its scrim keyline: 6.17 |
| line | #5C8AC6 | borders, control outlines | 4.64 / 3.97 / 3.29 on 900 / 800 / 700 (needs 3) |
| locked-line | #5F76A0 | quiet outline inside a panel: empty star, locked avatar | 3.08 on navy-800, 3.61 on navy-900. Never on art (2.24 on the light sea) and never on navy-700 (2.55) |
| gold-deep | #5A4300 | fill of a done stone | gold on it 6.50 |
| scrim | #050E22 | dialog scrim, solid edges, keyline around stones | locked 6.17, gold 13.31, aqua 12.12 against it |
| sea-hi | #14407A | reference: lightest placeholder sea | white 10.27, dim 5.32; locked 3.30 and line 2.89 fail, hence plates and keylines |
| paper / paper-2 | #FFF4DE / #F3E3C0 | exam, print | ink #1B2A41: 13.24 / 11.39 |
| ink-2 | #4A5568 | secondary on paper | 6.90 on paper, 5.93 on paper-2 |
| good-ink / fix-ink | #1A6B3D / #A8402B | right / fix on paper | 5.99 / 5.61 on paper, 5.15 / 4.82 on paper-2 |
| focus | #FFFFFF (dark), #134B8A (paper) | focus-visible ring 3px, offset 3px | 14.11 / 8.02 |

The ratios are also computed live in `ds.html` from the CSS variables, so the table cannot drift. The live table lists every pair `ds.css` and the preview put together and prints a one-line total: 56 measured pairs, 2 pairs marked "fails by design, needs a plate" (locked and line on bare light sea, counted on their own), and 2 decoration rows. A new component adds its pairs there in the same change.
Review fixes after v1: disabled button ring uses `locked` (was `locked-line`, 2.55 on navy-700); locked stones got the `locked` ring, a scrim keyline and plated labels (were 2.24 / 3.30 on the light sea); `good-ink` darkened from #1E7A46 (4.22 on paper-2); the energy "?" is a real 48px target (`wi-bar__help`).
Adjusted from the starting palette: `line` (first try #3C6AA8 gave only 2.57 on cards), and added `dim`, `locked`, paper and ink sets. The five approved pairs are unchanged and pass.

Type scale: 14, 16, 18 (body), 22, 28, 36. Line height 1.45 (1.2 for titles). Spacing 4, 8, 12, 16, 24, 32, 48. Radii 8, 12, 16, 24, pill. Elevation: e1/e2/e3 are solid 2/4/6px edges in #050E22; "ring" is a 3px flat translucent ring. Motion: 120 / 200 / 360ms, one easing, only transform and opacity.

## Fonts
Only self-hosted files in `assets/font`, declared in `ds.css` as `WI Hebrew` and `WI Latin` (no new file, no new host).
- Hebrew: Fredoka (`fredoka-hebrew.woff2`). Round, friendly, clear, not cursive. Kept.
- English: **Rubik** (`rubik-latin.woff2`, variable weight, SIL OFL 1.1), owner's decision. It replaced Playpen Sans in the new look: the handwriting read childish next to Fredoka, and English is what pupils must read most carefully for spelling. Rubik's a, g, I and l are plain and distinct.
- The live game (`css/game.css`) still uses Playpen Sans. It changes only when a screen moves to the new system.

## Components (all `wi-` prefixed)
| Component | Do | Don't |
|---|---|---|
| `btn` primary (gold), `--secondary` (azure+aqua ring), `--quiet`, `--special` (magenta) | One primary per screen. Verb first: "משחקים". Pressed sinks 3px. Disabled shows a lock or reason nearby. | Two gold buttons. Red buttons. Disabled without saying why. |
| `card` dark / `--paper` | Dark for game, paper for exam and print. | Paper card inside the game flow for decoration. |
| `chip` (HUD), `--btn` | Energy, stars, avatar, settings. Tappable chips use `--btn` (48px). | Numbers without icon. Chips over the road or the question. |
| `bar` (energy, progress), `bar__help` | Fills from the inline-start side. Has `role=progressbar`. The "?" at its end is `wi-bar__help`, 48px. | Showing it empty as a warning. It only goes up. |
| `stone` done / current / locked + `stars` | 1 to 3 stars under done stones. Current stone has aqua ring. Locked shows lock and a hint on tap. | Hiding locked stones. Showing a grey star row on a stone never played. |
| `av` avatar tile | Default, selected (gold ring + check badge), locked (dimmed + lock). `aria-pressed`. | Locking by name or gender. |
| `tag` | Short status. `--btn` for filters (48px). | Tags as the only way to tap. |
| `banner` (today's focus, fix, good) | In the layout flow, with one action button. | Floating over the answers. Auto-hiding the only explanation. |
| `plate` | Solid navy backing under a title, sentence or icon row that sits on art. | Text straight on a picture. Translucent plates. |
| `dialog` in `scrim` | Title, one sentence, one button. Esc and button close. | Two destructive-looking choices. |

## RTL rules
- Logical properties only in the system (`margin-inline`, `inline-size`, `inset-inline-end`, `border-inline-start`). The one exception is map art in mocks, which is a picture and is not mirrored.
- Page is `dir=rtl lang=he`. Every English word or phrase sits in `<bdi dir="ltr">` (or `.wi-en`). Never put English at the start of a Hebrew string without it.
- Icons drawn pointing right. In Hebrew, right means "back" (unmirrored) and "next/forward" needs `wi-icon--mirror`. Never mirrored: star, bolt, lock, check, gear, person, focus, close, question mark, play, speaker, clock, bar fill icon.
- Star rows are always left to right (1-2-3), also in RTL. Numbers stay LTR.
- Bars fill from the inline-start edge (right in Hebrew).

## Motion
- Allowed: stone press, bar fill, banner entrance (8px fade), character bob on the current stone.
- Not allowed: shaking, flashing, red pulses, spinning on mistakes. Wrong answers get a soft fade and the explanation.
- `html.calm` and `prefers-reduced-motion` turn off every animation and transition inside `.wi-root`.

## Strings (Hebrew)
| Where | Text |
|---|---|
| Picker title | בוחרים דמות |
| Picker subtitle | אפשר להחליף אותה מתי שרוצים. |
| Picker confirm | זאת הדמות שלי |
| Picker locked note | דמויות נוספות נפתחות כשמרוויחים אנרגיה. |
| Energy, one sentence | מרוויחים אנרגיה כשלומדים, והיא אף פעם לא נגמרת. |
| Energy dialog | מה זו אנרגיה? / מתקנים טעות, חוזרים למילה קשה או משחקים עוד קצת. כשעולים רמה נפתחים דברים חדשים. מה שכבר נפתח נשאר פתוח תמיד. / הבנתי. (Not "באים כל יום": it can read as pressure to keep a streak.) |
| Locked stone hint | עוד נעולה. משחקים את משימה 4 והיא נפתחת. |
| Today's focus | המיקוד להיום / יש 5 מילים שכדאי לחזק. זה ייקח כמה דקות. / מתחילים |
| Stars | כוכב אחד: קל. שני כוכבים: בינוני. שלושה כוכבים: מאתגר. (legend: כל כוכב נוסף, משחק קשה יותר) |
| Coming soon | בקרוב |
| Fix toast | כמעט! המילה X תחזור עוד מעט, ושם תצליחו. / תיקנתם טעות, קיבלתם אנרגיה |

Mission names and "5 words" are placeholders. Plural address is used so it works for boys and girls.

## Rollout (each behind a flag, default off; the class keeps the current look)
Flag mechanism: `?ds=1` or a `localStorage` key `wi_ds`, adding `class="wi-root"` and loading `css/ds.css`. Teacher turns the class on later by config. Ship one screen at a time, test with `tests/*.py` in both modes.
1. **Title / login** (low risk, first impression, no learning state). Needs the character picker.
2. **Island map** (world map + island path, with energy and today's focus). The new structure; needs the engineer for energy rules and the weak-item recommender.
3. **Level screens** (English games). Dark shell, answers keep high contrast; the road and question are never covered.
4. **Fraction Bay** (math). Same shell; island of the world map.
5. **Mock exam**. Paper card inside the dark shell. Last among learner screens because calm matters and the class uses it for real prep.
6. **Beach Run HUD**. Chips and bar over the WebGL canvas; check phone performance (no blur).
7. **Teacher screen**. Dark or paper; it is data-heavy. Last, lowest kid impact.

## Not done here / needs art
Real island, stone, character and sea images (glow is baked in). The 20 characters and their gender/skin variety. Sounds.

## New-world screens: `world.html` (static preview)

Three screens built from `css/ds.css` and the art in `assets/al/`: character picker (two steps: choose, then name), world map, island mission path. Files: `world.html`, `css/world.css`, `js/world.js`, `js/world_art.js` (label to file, written from `assets/al/sources.tsv`).
- Not linked from the game, `noindex`. Shows only with `?ds=1` or when `localStorage.wi_ds` is `1` (read only); otherwise a short "still being built" card with a link back to the game.
- Static: nothing is saved, no backend call, no speech, no music file. A reload starts over.
- For review: `?ds=1&screen=name`, `screen=map`, `screen=island`, `screen=island&island=math`.
- Layout: the world map background has no fixed features, so it covers the screen and islands sit in percent of the free area. An island backdrop has a painted path, so it keeps its 752:1344 shape, scales to the free height, and stones sit in percent of the picture (`PATHS` in `js/world.js`). A new backdrop needs its own eight points.

### Data each screen needs (for the engineer who wires state)
The demo values live in `DEMO` in `js/world.js`; this is the contract.

| Field | Type | Used by | Notes |
|---|---|---|---|
| `avatar` | id string, or null | all three | One of the 20 ids in `AVATARS`. Null sends a pupil to the picker first. |
| `name` | `[a, b]`, two indexes | name step, map greeting | Indexes into the two word lists, never text. No free text anywhere, so nothing a pupil types is stored or shown to the class. Store the lists' version if they ever change order. |
| `energy.points` | integer, only goes up | island bar | Never shown as a cost and never spent. |
| `energy.level`, `energy.from`, `energy.next` | integers | map chip, island bar, picker locks | Level and this level's two thresholds. The bar shows progress inside the level. Thresholds are a rule for the engineer; the demo uses 120 and 220 for level 2. |
| `energy.opens` | short Hebrew text | island bar line | What the next level opens ("נפתחת דמות חדשה"). |
| `AVATARS[].open` | level | picker | The level that opens a character. Human kids are open from the start, so no pupil is short of a girl or a boy to pick; only four non-human characters are level rewards. |
| `stars` | integer | map chip | Sum of mission stars. |
| `focus` | `{island, mission, count}` or null | map banner only | Today's focus. Null hides the banner. Shown on the map only. |
| `islands[id].missions[].stars` | 0 to 3 | island path | Per mission. 0 on a played mission still counts as done. |
| `islands[id].current` | index | island path, main button | The first mission not done yet. Everything before it is done, everything after it is locked. |

Not in the data on purpose: other pupils (no ranking on these screens), any loss or spend of energy, and a reason a mission is locked other than "play the one before it".

### Name word lists (flagged for the teacher's review)
Two lists of 12, picked with arrows or the "הפתעה" button; 144 names. Words marked * and their translations are copied from the teacher's Unit 1 list in `js/data.js`. The rest are ours and need her OK, like any text we write.
- First word: Special*, Sweet*, Ready*, Happy, Cool, New, Brave, Clever, Kind, Fast, Funny, Lucky.
- Second word: Song*, Guitar*, Piano*, Flower*, Candy*, Goal*, Present*, Trip*, Shark, Fox, Star, Robot.
- Hebrew under each describing word shows both genders (מתוק/ה, אמיץ/ה, טוב/ת לב, בר/בת מזל). Her list gives the masculine form only, so the added ending is ours and needs her OK. Nouns are as in her list.
- For her attention: "Special". It is her word (מיוחד) and is meant kindly here ("Special Star"), but she should decide whether it is comfortable as part of a pupil's name in her class.
- Every one of the 144 pairs was read for an unkind or silly meaning; none found.
- Also ours and to be checked: the maths mission names in the demo (placeholders, not from `js/mdata.js`).

### Strings added
| Where | Text |
|---|---|
| Gate | המסך הזה עוד בבנייה / בינתיים משחקים במשחק הרגיל. / חזרה למשחק |
| Picker, next | הלאה: בוחרים שם / קודם בוחרים דמות. |
| Picker, locked character | (שם): נפתחת ברמת אנרגיה 3. עכשיו אתם ברמה 2. |
| Name step | איך קוראים לדמות? / בוחרים מילה אחת מכל רשימה. השם באנגלית. / מילה ראשונה / מילה שנייה / הפתעה / זה השם שלי / חזרה לדמויות |
| Map greeting | שלום, (name)! לאן מפליגים היום? |
| Map, island not open | בקרוב / האי הזה עוד בבנייה. הוא ייפתח בהמשך השנה. No subject is named on these islands until a teacher has given material for it. |
| Today's focus | המיקוד להיום / (N) מילים מ־(mission) שכדאי לחזק. כמה דקות וזהו. / מתחילים. The preview shows "דוגמה: 5 מילים שכדאי לחזק" with no mission name, so it cannot be taken for real content. |
| Island, energy line | רמה 2 / עוד 90 אנרגיה לרמה 3: נפתחת דמות חדשה. |
| Island, stone hints | משימה 5 עוד נעולה. משחקים את משימה 4 והדרך נפתחת. / משימה 2: שני כוכבים. אפשר לשחק שוב ולאסוף עוד. / כאן אתם עכשיו. לוחצים על הכפתור למטה ומתחילים. |
| Island, main button | משחקים: משימה 4 |
| Settings | מצב רגוע: בלי תנועה ובלי מוזיקה / אפשר להפעיל ולכבות מתי שרוצים. |
| Sound button | מוזיקה (a toggle: pressed means on). In calm mode it is disabled and reads: מוזיקה כבויה במצב רגוע |
