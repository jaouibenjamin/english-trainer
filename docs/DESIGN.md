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
1. **Title / login** (low risk, first impression, no learning state). Needs the character picker. *Built behind the flag: see "Rollout step 1" below.*
2. **Island map** (world map + island path, with energy and today's focus). The new structure; needs the engineer for energy rules and the weak-item recommender. *First the skin: the existing English map and level list behind the flag, see "Rollout step 2" below.*
3. **Level screens** (English games). Dark shell, answers keep high contrast; the road and question are never covered. *Built behind the flag: see "Rollout step 3" below.*
4. **Fraction Bay** (math). Same shell; island of the world map. *Built behind the flag: see "Rollout step 4" below.*
5. **Mock exam**. Paper card inside the dark shell. Last among learner screens because calm matters and the class uses it for real prep. *A light touch behind the flag: see "Rollout step 5" below.*
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

## Rollout step 1: title, login and settings of the live game, behind the flag
Files: `js/dsflag.js` (the flag), `css/ds-game.css` (the skin), one `<script>` line in `index.html`. Default off.
- `index.html?ds=1` turns the new look on for that device and remembers it (`localStorage.wi_ds`); `?ds=0` turns it off. With the flag off, `dsflag.js` adds nothing and writes nothing, and the two stylesheets are not requested.
- With it on, `<html>` gets the class `ds` and every rule in `ds-game.css` sits under `html.ds #stage[data-scr=title|login|settings]` or the matching screen class. All other screens keep today's look.
- Styling only. No element is added, removed or reordered; the login form keeps its fields, ids, labels, validation, messages and requests. Pitzi's new picture is drawn as the background of the existing `<img>` (its own picture is squeezed to zero height), so no script or markup changes.
- Backdrop: `bg/world` (night sea with the moon). Title: the three subjects are three tiles of equal weight; the mock exam tile is paper, because the exam stays light. Login: one dark card with a keyline; fields are navy-900 with a line border and white text; the main button is the only gold one. Settings: dark cards, aqua switches.
- Targets: the two login tabs and the three fields are 48px tall with the flag on (44 to 47px today).
- Known seams, on purpose for step 1: the map, help, class table and teacher screens are still in the old look, so moving from the title to the map changes style. The old painted icons in settings are kept.
- Checked: `tests/play.py --quick` gives the same 170 checks on `game`, on this branch with the flag off, and with the flag on (class login against the mock backend included); `math.py --quick` 21 and `mock.py --quick` 12 are unchanged with the flag off.

## Rollout step 2: the English island map and an island's level list, behind the same flag
Skin only, in `css/ds-game.css` under `html.ds #stage[data-scr=map|island]`. No script, markup, route, saving or request changes. Default off.
- Map: backdrop `bg/sea` (sea from above). Top row: round glass buttons with a plate under each name, the star count as a gold-edged chip, "מקצועות" as a 48px plated button (moved down 14px so it no longer covers the "הגדרות" label). Route: aqua dashes. Island names on dark plates; locked: dashed, dimmed, grey island, new lock; the next island to play: gold ring and soft aqua glow; full: green edge. The all-played banner is a dark card with the starry Pitzi.
- Level list (`#island/N`): `bg/english` dimmed behind; four dark rows with a colour edge each (aqua, gold, magenta, green); stars and Pitzi in the new art.
- New art used (all from `assets/al`, nothing generated): sea, english backdrop, star, lock, gear, Pitzi wave and star. Swapped pictures keep their `<img>` and size; the old picture is pushed out of its box with `object-position` and the new one drawn as the background.
- Known seams: the six painted islands, the boat, the whale, the compass, the chest and trophy icons and the level icons keep today's art (day-light painting on the night sea). New island art would need a generation; not done. Pressing a level row opens the level in today's look.
- Other switches with the flag on: the toast (locked island, hints, sign-out notes) is a dark card with a gold edge on all five screens in the new look; with `?games=1` the extra-game buttons are navy pills, 48px, and their label sits on a plate; with `?sheet=1` the worksheet link is 48px; empty stars at half strength.
- Checked: flag off, the 27 screenshots (map, island 1, island 6 × three progress states × three sizes) match `game` byte for byte. Flag on, alone and with every other switch (`games`, `sheet`, `help`, `card`, `tmock`), tapping a locked island: `tests/play.py --quick` 170 pass, no page errors, no text under 4.5:1 against its own backing, and every button on the title, settings, map and level list is 48px or more. Not covered by this step: the login screen at 360x640 is taller than the screen in today's look too (its teacher button sits partly below).
- For every next screen: test the flag on together with every other switch, not only alone.

### Painted art for the map and frames (batch h, see `docs/ART_LEDGER.md`)
- The six English islands are redrawn in the night-sea style, each keeping its theme (hobbies, school, new home, birthday, presents, treasure), with a locked version of each made from the same picture (grey, darker, cool mist). Behind the flag they replace the old pictures on the map and the level list; the `<img>` keeps its place, its box is 7:6 (4:3 on phones 700px tall or less) so the trees fit.
- The map sea now carries quiet details near the edges (whale, two lantern boats, lighthouse, jellyfish); the old boat and whale sprites are hidden. The route is round aqua dots, drawn as a stroke, no blur.
- Painted frames as `border-image` (9-slice), text stays live on top: panel (login card, settings panels, the all-played banner; in `world.html` the cards and the focus banner), gold button (the login button; the primary buttons of `world.html`), HUD pill (the star count, the island chip; the HUD chips of `world.html`). Disabled and secondary buttons keep their flat look, so "not yet" still reads differently.

## Rollout step 3: the English level screens and the result card, behind the same flag
Skin only, in `css/ds-game.css` under `html.ds #stage[data-scr=play|result]`. No script, markup, route, saving or request changes. Default off.
- The painted scenes stay (the slingshot, the beach and the bridge cliffs are part of each picture, and the levels place things on them) under a night tint: a blue layer in multiply over the picture, no blur.
- The game pieces (balloons, bubbles, the story scroll, bottle notes, planks) keep their painted backing and dark ink, so the answers keep their contrast.
- HUD: glass buttons with name plates, the level's stars in a gold-edged chip with the new star, progress dots navy (to do), aqua (done) and gold (now).
- The hanging wooden sign is the painted panel frame with white text, in the same box, so every level places things exactly as before.
- Tips, rules and feedback lines are dark plates; right is green, a slip coral, the gap on the bridge gold. The score caption over the balloons has a dark keyline.
- Buttons: the main one gold, the others navy with an aqua edge (the "listen again" button too).
- Result card: the painted panel, the heading on a gold-edged plate, the new star and the new Pitzi (star, happy, wave), review words on gold with dark text. The result card is shared with Fraction Bay.
- Checked: flag on, `tests/play.py --quick` 170 pass with every level played to its result; screenshots of every state (aim, miss, wrong bubble, star lost, hint, story, gloss, wrong bottle, bridge build, snap, to-be, every result) at 390x844 and 360x740, and the four levels at 1366x768. Flag off: `ds-game.css` is not loaded, so nothing changes.
- Not in this step: the extra games (`?games=1`), Fraction Bay, the mock exam.

### The extra games (`?games=1`) in the new look
Under `html.ds #stage[data-scr=extra]`. The light cards (true or not, pairs, letters) are dark cards with white text; right is a green edge, wrong a coral edge, and the game's own words and marks stay, so colour is never the only sign. Face-down pairs show an aqua "?". The explain block, the pairs list and the end screen sit on dark cards; the counters and one-line notes on plates. Backdrop: the English island picture, dimmed. Checked: `tests/extra.py` 253 pass with the flag on, screenshots of card, explain, wrong, board and end for all three games at 390x844, 360x640 and 1366x768.

## Rollout step 4: Fraction Bay behind the same flag
Skin only, in `css/ds-game.css` under `html.ds #stage[data-scr=math|misland|mplay]`. No script, markup, route, saving or request changes. Default off.
- The maths screens reuse the English classes (`.map`, `.island`, `.lv`, `.result`), so the rules of steps 2 and 3 reach them; this step adds the screen-level rules for the three maths screens and the maths pieces.
- Bay map: the sea with details, the new island pictures (the bay uses the same six pictures as the English map, locked versions included), the bay's name on a plate under the star chip.
- Island screen: the maths backdrop (`bg/math`), dimmed, under the level rows of step 2.
- Levels: the same night tint and HUD as the English levels. Keypad keys navy with white digits, the check key gold; choice cards navy with a green or coral edge for right and wrong; the pizza footer notes on plates. The worksheet paper and the pizza task note stay light, like the mock exam: they are written work.
- The level rules of step 3 are scoped to `#stage[data-scr=play|mplay]`, so the maths levels get all of them (with #44 alone they reach only the English levels). The slingshot's caption keeps its paper label with dark ink, as in step 3.
- Checked: flag on, `tests/math.py --quick` 21 pass, screenshots of every state (map, island, pizza ask, build, cut, eat, merge, wholes, count; sling aim and miss; sheet question, form, solution; every result) at 390x844, 360x740 and 1366x768. Flag off: `ds-game.css` is not loaded.

## Rollout step 5: the mock exam, a light touch, behind the same flag
Under `html.ds #stage[data-scr=mock|mockrun|mockprac]`. The exam stays on paper and keeps its calm: the question cards, answers, stations trail, report bars and their colours are today's. Only the shell matches the other screens: the dark surround on wide screens, the heading on a navy plate, the round back and quit buttons, the gold main button (no pulse), the navy toast, the paper focus ring (`--wi-focus-paper`), the fonts.
- The exam's quit button: its icon was missing (`ico('x')`, not in the set) and is fixed in #60 (`ico('close')`). With the flag on it is a navy disc with a white X, drawn as a background on a square 48 px hit box (Chrome does not hit-test rounded-off corners, so a `border-radius` would let corner taps fall through to the trail); the stations trail's inline padding is 60 px, which leaves a real gap of 12 to 17 px between the X and the writing-station circle.
- Checked: flag on, `tests/mock.py --quick` 12 pass, screenshots of every state (intro, the four stations, each question type, report, practice, hub) at 390x844, and the hub and a question at 1366x768.

## Rollout step 6: Beach Run HUD and menus, behind the same flag
Files: `css/run-ds.css` (the skin), a seven-line block at the top of `js/run.js` (the same switch as `js/dsflag.js`: `?ds=1` on and remembered in `localStorage.wi_ds`, `?ds=0` off). `run.html` is unchanged, so with the flag off the page makes exactly the same requests as before and stores nothing new. Default off.
- Styling only. The 3D scene, the signs drawn in it, the runner models, the questions, the scoring and every element, id and handler are untouched.
- HUD: hearts, the question count and the shells as navy chips with a gold (count, shells) or line (hearts) edge and a scrim keyline, so they read on sky and sand. The hit shake is off in the new look.
- Question card: navy-800 with a keyline, still compact so the road stays in view. Lane answers are navy tiles; the current lane has an aqua ring; an empty lane is a dashed "—". Right: green edge and title; wrong: the warm "fix" edge and title, the right answer in gold, "השאלה הזאת תחזור עוד מעט" in aqua. The speaker is a 48px target (negative margin, so the card is not taller).
- "נכון!" / "כמעט!" over the road: green / fix colour with a solid dark edge; a miss only fades, it does not pop.
- Touch pad and "יודע/ת!": solid navy and azure, no blur (the old pad used `backdrop-filter`), 48px or more.
- Start, pause and end menus: the painted panel frame, the painted gold button for the one main action, "חזרה למשחק" as an azure secondary button (48px), pace choice with an aqua ring, scores in gold.
- Checked: `tests/run.py` plays the whole run with the flag on at 390x844 (and 1366x768 in the full form): same scoring checks, every visible button and link 48px or more on the start menu, the HUD, the question card and the end menu; with the flag off it checks no class, nothing stored and only `css/run.css` requested. Computed styles of the start menu with the flag off match `game` at both sizes.
- Follow-up (review of #42): every text in the runner's new look is 16px or more (lanes, question line, hint, the "how to play" tiles, pace); "נכון!" / "כמעט!" sit on a navy plate with an edge in their colour (never bare on the 3D picture); with reduced motion the card does not slide and those two only fade; the menu stays hidden until both stylesheets are in (or failed, or 4 s), so the old look never flashes; a menu taller than a small phone starts at the top and scrolls (the picture above the card stays whole). At 360x740 the question card ends at 197px or higher, as in today's look (195).
- Known seams: the signs on the gate are drawn in the 3D scene in today's hand font and colours; the copy "נגמרו הלבבות" is unchanged (copy is the designer's).

## Rollout step 7: the teacher screen, behind the same flag
Files: `css/ds-teacher.css` (the skin), one more entry in the stylesheet list of `js/dsflag.js`. Styling only, every rule under `html.ds #stage[data-scr=teacher]` or `.teacher`. No markup, script, request or saving change; pupil names still come from the backend at run time, escaped by `js/main.js`.
- Dark shell, flat navy cards with a line edge (the painted frame is not used: many cards, small data). No paper picture behind.
- Sign-in form: fields 48px, navy-900 with a line border; "כניסה" is the one gold button. Pitzi listens in the new art.
- Hard words: the share of wrong answers and its bar in the warm "fix" colour.
- A pupil's card: name, status tag outlined in its colour (green "מוכן/ה", warm "fix" for a nudge, dim "בדרך"; the word carries the meaning), stars bar in aqua, data rows in dim text, mock exam rows (with `?tmock=1`) under a quiet divider.
- "איפוס קוד" is a 48px azure secondary button (was 30px); armed for the second tap it turns warm "fix", never red.
- Data rows, tags and the footnote are 14px (were 12.5px): below the 16px body rule, on purpose for a data-heavy adult screen. Designer to confirm.
- Toasts on this screen ("the code was reset", an error) are the same dark card with a gold edge as on the other new-look screens. A pupil name with no space (up to 20 letters) wraps inside its card.
- Not behind the flag (teacher view only): after a confirmed reset, the 4 s disarm timer no longer writes "איפוס קוד" back over "הקוד אופס", and a tap on a disabled reset button does nothing; a pupil's name sits in a `<bdi>` (an English name keeps the card's right alignment) and may wrap, so a 20-letter name with no space stays inside its card in today's look too.
- Checked (`tests/teacher_mock.py`, mock backend, 390x844 and 1366x768): toasts after a reset that worked and one that failed are 4.5:1 or more in both looks; with the flag on, the same cards and rows as without it, no card wider than its box, every button and field 48px or more, every text 4.5:1 or more against its own backing, the first tap on "reset code" sends nothing; `?ds=0` takes the look away.

## Character animations (behind the flag)
One 2 s animated WebP per character (`assets/al/avanim/`, 192 px, under 150 KB, batch i in `docs/ART_LEDGER.md`), played once by `js/avanim.js` when a character is tapped or chosen, and on hover where there is a mouse. The still portrait shows the rest of the time; the animation ends on it (the penguin and fox retakes play forward and back, the others fade their last frames back to the first). The owl has no file: two takes changed its expression, so its still portrait does one 0.9 s CSS tilt-and-bounce (`.wi-av__art--bob` in `css/ds.css`), off with reduced motion and calm mode.
- The file is requested only at that moment, never preloaded. With `prefers-reduced-motion` or calm mode nothing moves and nothing is requested.
- Wired in `world.html`'s picker (`js/world.js`). For the live game's picker (`js/avatar.js`, behind `?ds=1`): `import {playAv} from './avanim.js'` and call `playAv(img, id)` with the character's `<img>` when it is chosen.
- Checked by `tests/avanim.py`: every character has one, each is an animated WebP under 150 KB listed with its sha256; nothing is requested before a tap; a tap requests that one file and the portrait comes back; nothing with reduced motion or calm mode; nothing without the flag.

