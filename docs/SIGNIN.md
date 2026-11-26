# Spec: the pupil's sign-in screens for Supabase mode (DRAFT, for the owner's and the teacher's approval)

Status: a design spec, revised after an independent kids-UI review and the backend engineer's answers. Nothing here is
built or switched on. The flows are `docs/BACKEND.md` section 3 (A, B, E, F); the step in the plan is
`docs/PHASE3.md` step 5. **These screens change how children sign in: they need the owner's explicit yes (and the
teacher's) before they are ever switched on.** Every string a child sees is listed below for that approval.

Wireframes: `docs/mock/signin.html` (the identity row and the "who is playing" pill at 390, 360 and 320 included), a static page in the new look, not linked from the game, not wired to anything,
no script, no requests. It is responsive: each screen is shown at 390 x 844, and the picture screens also at
360 x 740 and 320 x 568, so the smallest phones can be judged. The picture tiles there are labelled placeholders.

## 1. Rules every screen follows

- One question per screen. On top: a back arrow (48 px, keeps what was typed) and the step, "שלב 2 מתוך 5". Steps are
  numbered per flow and always count the same screens (section 3 lists them).
- The main action is the gold button in a **bottom bar that stays on screen** (sticky, above the keyboard and the safe
  area). Only the middle scrolls. Nothing a child needs is below the fold at 360 x 740.
- Headings are one short line, 22 px. Body text 18 px. Every target 48 px or more.
- Errors sit under the field in `--wi-fix` (warm, never alarm red), are read out (`role="alert"`), never blame, and
  always say what to do next. A wrong answer never ends anything.
- Plural "אתם" as the game already speaks; no gendered verbs to the child.
- Reduced motion and calm mode: no pop, no shake, no slide.

### The 4-digit code field

One real `<input inputmode="numeric" pattern="[0-9]*" maxlength="4" autocomplete="off">` (a password manager must not
offer to save it), shown as four boxes with dots, LTR, with a "הצגה" toggle, **and** a big on-screen keypad of 48 px
keys (1 to 9, 0, delete) under it for a child who cannot find the digits on a laptop keyboard. Both feed the same
field. Nothing is kept after the screen closes.

**Placement:** on the register flow it is its own step (A2), the keypad right under the four boxes. On the sign-in
screen (B) it sits directly under the name row, with "הצגה" on the same line. The on-screen keypad shows only on a
fine pointer (a laptop, `@media (pointer:fine)`); on a phone the system's number keyboard does the job, so two
keypads never stack and the bar with "כניסה" stays above the keyboard.

### Identity: first name and one letter (the owner's decision, 2026-11-26)

A pupil is **a first name plus the first letter of the surname**, shown as "נועה כ." (letter, then a full stop).

- **Fields (A1, B, E1):** one row, the first name (wide) and the letter (a 1-character box, 88 px, label "אות
  משפחה", `aria-label="האות הראשונה של שם המשפחה"`). Under them one hint: "השם הפרטי והאות הראשונה של שם המשפחה, כמו
  ברשימה של המורה." In A1 a live preview: "כך יופיע במשחק: נועה כ.".
- **Input rules:** `maxlength=1`, one letter only, no full stop typed (the game adds it). A Hebrew final letter is
  stored as its plain form (ך ם ן ף ץ become כ מ נ פ צ); a Latin letter is stored upper case. The letter takes the
  name's script (Hebrew name, Hebrew letter); if not, the hint turns into "האות צריכה להיות באותה שפה של השם."
- **Not on the list:** "השם הזה לא ברשימת הכיתה. בדקו את השם ואת האות, או בקשו מהמורה." (replaces the A1 message.)
  Two pupils with the same name and letter: the teacher adds a digit to the letter on her list ("כ2"), the only case
  where the box takes two characters; this replaces the old "{שם} ב" rule.
- **Display:** always `<bdi>` around the whole name (a Latin name stays LTR inside Hebrew text): first name, a
  no-break space, the letter and the full stop. When space is short, **only the first name is cut** with "…"; the
  letter is never cut ("Alexandri… K."). The full name is the `aria-label`.
- **Where it shows:** the "who is playing" chip (title and map), the settings account panel, the class board
  ("נועה כ."), the grade board ("נועה כ." and a separate class tag "ה׳2", never one string). Nowhere a surname.

### Who is playing (title and map)

A pill at the top of the title screen and in the map header: the avatar (36 px), the name as above, a dot, and a
button **"זה לא אני · יציאה"** (48 px tall target). At 320 px the first name gives way first (see Display); the
button never shrinks. The button asks the confirm of "Shared device" below.


### The picture screen (choose, recall)

- **Two big slots on top, "1" and "2"**, side by side (first on the right, RTL). Each tap on a tile fills the next
  empty slot with that picture and its name. Tapping a filled slot empties it. The order lives in the slots, nothing
  else marks the tiles, so the child sees "first, then second".
- **The grid scrolls under the slots**; the slots and the bottom bar stay. Tiles about 76 px on a 360 wide screen
  (`repeat(auto-fill, minmax(72px, 1fr))` with an 8 px gap: 4 across at 360 and 390, 3 across at 320), the picture
  56 to 64 px inside, its Hebrew word under it. Each tile is a button labelled by its word.
- **Shuffled on every visit**, a different order in the repeat step (A5) than in the choose step (A3), and a new order
  on every recovery attempt (E2), so nobody can learn a pair by where a finger went.
- **Sound** (recorded clips, preset voice Kaia, never browser speech): the first time the screen opens, one line plays
  once: "קודם תמונה אחת, אחר כך עוד אחת". A tap on a tile also says its name. A mute button sits with the others in
  the game's settings; calm mode keeps sound off.
- Screen reader: "תפוח, נבחרה ראשונה"; a filled slot reads "תמונה ראשונה: תפוח. הקישו כדי להוריד".
- **In recovery (E2) the slots show filled dots, not the pictures**, like the code's dots, and tapped tiles get no ring
  or mark: a neighbour must not read the pair off the screen.

## 2. The picture set (20, new art; cap A of the art budget)

The art under `assets/al` cannot give a good grid (9 of the 13 usable images are avatars every classmate sees on the
board; the icons already mean something in the game). The art brief for 20 new pictures:

- One style: painted, Arcade Lagoon palette, one object, thick flat shapes (thin lines vanish at 64 px), centred on a
  plain navy tile, readable at 56 px. **No characters, no faces, no letters or numbers, no brands.**
- **Nothing that is also part of the game:** no avatar animal, no Pitzi or any crab, and nothing from the sea and the
  islands (no boat, moon, star, sun, shell, anchor, fish, lighthouse, palm, island), no game icon (gear, lock, bolt,
  key, star).
- **Nothing everybody would pick** (a football, a birthday cake), and no confusable pair: every picture differs from
  every other in silhouette *and* main colour; only one round red thing.
- Each one word, the same spelling everywhere (this file, the art's file name in `sources.tsv`, the clips).

| | | | | |
|---|---|---|---|---|
| תפוח (apple, red, round) | בננה (banana, yellow, crescent) | אבטיח (watermelon slice, green and red, wedge) | קקטוס (cactus in a pot, green, upright) | ענבים (grapes, purple, bunch) |
| פרח (flower, pink, petals) | מטריה (umbrella, blue, open) | עפיפון (kite, orange, diamond) | תוף (drum, red and white, cylinder) | כובע (hat, brown, wide brim) |
| נעל (shoe, light blue) | פיל (elephant, grey) | ג׳ירפה (giraffe, yellow with brown spots, tall) | בית (house, cream with a red roof) | עיפרון (pencil, blue, straight) |
| ספר (book, blue-green, closed) | פעמון (bell, gold) | מכונית (car, yellow, from the side) | מספריים (scissors, silver and orange) | פטרייה (mushroom, smooth orange-brown cap, no spots) |

Pairs checked for confusion: apple and mushroom (round vs stalk and cap), banana and pencil (yellow curve vs blue straight), banana and the carrot (dropped: two long yellow-orange shapes at 56 px, replaced by a cactus),
umbrella and mushroom (blue vs orange-brown, handle vs stalk), elephant and giraffe (wide vs tall).

**Cost estimate (cap A, 25 credits):** pictures as 5 sheets of 4, gpt_image_2_5 high, 1.25 each: **6.25**, with a
retake of two sheets 8.75. Sound: 22 clips (20 names, "קודם תמונה אחת, אחר כך עוד אחת", "אמרו את זה בקול"),
text2speech_v2 with the Kaia preset, quoted 0.75 each = **16.5** quoted (the account has charged 0.15 a take so far,
about 3.3). Together 22.75 quoted, inside the cap. Nothing has been generated yet.

## 3. The flows, screen by screen, with every string

### Entry

| Where | Text |
|---|---|
| Title | ניצני אופק |
| Main button | נרשמים בפעם הראשונה |
| Second button | כבר נרשמתי |
| Link | שכחתי את הקוד |
| Tick box (on every sign-in screen) | מחשב משותף: לא לזכור אותי |

The tick box keeps the session for this tab only (it ends when the tab closes). Unticked, the device stays signed in.

### A. Register (5 steps)

| Step | Where | Text |
|---|---|---|
| A1 1/5 | Heading | מי אתם? |
| | Label, hint | קוד הכיתה · 8 תווים, אותיות ומספרים. הוא על הלוח. |
| | Labels, hint | השם הפרטי · אות משפחה · השם הפרטי והאות הראשונה של שם המשפחה, כמו ברשימה של המורה. |
| | Preview | כך יופיע במשחק: {שם} {אות}. |
| | Button | המשך |
| | Error: class code | קוד הכיתה לא נכון. בדקו שוב מול הלוח. |
| | Error: name not on the list | השם הזה לא ברשימת הכיתה. בדקו את השם ואת האות, או בקשו מהמורה. |
| | Error: name already taken | מישהו כבר נרשם בשם הזה. אם זה אתם, הקישו "כבר נרשמתי". אם יש בכיתה שני ילדים בשם הזה, בקשו מהמורה. |
| A2 2/5 | Heading | בוחרים קוד סודי |
| | Text | 4 ספרות שרק אתם יודעים. לא הקוד של הטלפון! |
| | Label | הקוד הסודי שלי (4 ספרות) |
| | Label | שוב את אותו הקוד |
| | Toggle | הצגה / הסתרה |
| | Error: weak code | קל מדי לנחש. לא 1234 ולא ספרות חוזרות. נסו קוד אחר. |
| | Error: the two differ | שני הקודים לא זהים. נסו שוב. |
| A3 3/5 | Heading | בוחרים שתי תמונות סודיות |
| | Line (sound, once) | קודם תמונה אחת, אחר כך עוד אחת |
| | Slots | 1 · 2 |
| | Hint (under the slots) | הקישו על תמונה כדי לבחור. הקישו על משבצת כדי להחליף. |
| | Button (after two) | המשך |
| A4 4/5 | Heading | זוכרים בעזרת סיפור |
| | (note) | the pair and the story below are a **sample**; the screen shows the child's own two pictures |
| | The pair, large | תפוח, ואחר כך עפיפון |
| | Text (no sound) | אמרו את זה בלב. (was "בקול": a secret is not said aloud in a classroom; the Kaia clip of the old line is not played. For the teacher's review) |
| | Text | מצאו סיפור קצר שמחבר אותן. למשל: התפוח עף על עפיפון. אל תספרו אותו לאף אחד. |
| | Button | זכרתי |
| A5 5/5 | Heading | עכשיו מהזיכרון |
| | Text | הקישו על שתי התמונות, באותו הסדר. |
| | Error: other pictures or order | לא בדיוק. נסו שוב, אתם קרובים. |
| | After 3 misses | אפשר לבחור תמונות חדשות. (returns to A3, new shuffle) |
| Done | Heading | נרשמתם! |
| | Text | המכשיר הזה יזכור אתכם. אם תשכחו את הקוד, התמונות יעזרו. |
| | Button | יוצאים לדרך |

A4 and A5 are client-side only (nothing extra is sent). A5 comes **after** the code (A2) and the story (A4) so it is
real recall, not copying. **After this the pair is never shown again**, anywhere.

**Two pupils with the same first name:** the surname letter tells them apart (section 1, Identity); with the same letter too, the teacher adds a digit ("כ2").

### B. Sign in

| Where | Text |
|---|---|
| Heading | נכנסים |
| Labels | קוד הכיתה · השם הפרטי · אות משפחה · הקוד הסודי שלי (4 ספרות) |
| Button | כניסה |
| Error: name or code (the same for both, BACKEND D1) | השם או הקוד לא נכונים. נסו שוב. |
| Link | שכחתי את הקוד |

### B'. First sign-in of a pupil from the Sheet (one time)

| Step | Where | Text |
|---|---|---|
| B'1 | Screen B | as above; the old code is typed here |
| B'2 1/4 | Heading | כניסה חדשה: בוחרים קוד ותמונות |
| | Text | פעם אחת בלבד. הנקודות והכוכבים שלכם נשמרים. |
| | Button | בואו נתחיל |
| B'3 to B'5 2/4 to 4/4 | | A2 (new code), A3 (pictures), A4 and A5 (story, recall), numbered 2/4, 3/4, 4/4 (A4 and A5 count as one step) |
| Error: new code equals the old (if the server refuses it) | | בחרו קוד חדש, לא את הקוד הקודם. |
| If the tab closes before the end | (next time, after B'1) | עוד לא סיימתם לבחור קוד ותמונות. אפשר להמשיך עכשיו. |

Nothing opens before the end of B'5 (BACKEND 3B). If the tab closes in the middle nothing has changed on the server:
the **old code still works**, and the next sign-in starts B'2 again with the line above.

A pupil from the Sheet who **forgot the old code** has no pictures yet: "שכחתי את הקוד" → E1 → straight to E3 with
"עוד לא בחרתם תמונות. בקשו מהמורה קוד חדש." (the server answers E1 with "no pictures"; it says nothing an attacker can
use that the teacher's list does not already show).

### E. "I forgot my code"

| Step | Where | Text |
|---|---|---|
| E1 1/3 | Heading | שכחתם את הקוד? זה קורה. |
| | Labels | קוד הכיתה · השם הפרטי שלכם |
| | Button | המשך |
| E2 2/3 | Heading | התמונות הסודיות, לפי הסדר |
| | Slots | filled dots, not pictures |
| | Wrong, 2 left | לא התאים. אפשר לנסות עוד 2 פעמים. |
| | Wrong, 1 left | ניסיון אחרון. קחו רגע לחשוב על הסדר. |
| | After the 3rd | הפעם התמונות לא עבדו. המורה תעזור לכם עם קוד חדש. |
| | Used in the last 30 days | כבר החלפתם קוד החודש. המורה תעזור לכם עם קוד חדש. |
| | Paused for the class today | היום אי אפשר לשחזר עם תמונות. המורה תעזור לכם עם קוד חדש, או נסו מחר. |
| | Link | קיבלתי קוד מהמורה |
| E3 2/3 | Heading | הקוד מהמורה |
| | Label | 6 ספרות (LTR, the same keypad) |
| | Error | הקוד לא נכון או שפג תוקפו. בקשו מהמורה קוד חדש. |
| | When a reset is waiting (E1 goes straight here) | יש לכם קוד חדש מהמורה. הקלידו אותו כאן. |
| E4 3/3 | | a new code (A2) and **two new pictures** (A3, A4, A5) |
| Done | Heading | הקוד החדש מוכן! |
| | Text | בטלפונים ובמחשבים אחרים תצטרכו להיכנס שוב עם הקוד החדש. |
| | Button | יוצאים לדרך |

### Waits (the server's answer carries `by`, `help` and the wait; PR #93)

On a school Wi-Fi 25 children share one address, so the screen says **whose** wait it is, and promises the teacher's
help only when `help` is `teacher`. When the scope is wider than the child (address, class, everyone) the copy says it
is not their fault. Unknown values read as `wait`. A wait of −1 means "until the teacher": no time is shown. Every
message ends with what the child can do meanwhile; a pupil already signed in is never stopped (BACKEND D4).

| `by` / `help` | When (backend rules) | Text |
|---|---|---|
| name / teacher | 5 wrong codes for this name from here: 5, then 15, 60, 240 minutes; resets after 24 hours without a mistake | הכניסה בשם הזה נעצרה ל-{N} דקות. בינתיים אפשר ללחוץ "שכחתי את הקוד", או לבקש מהמורה לשחרר. |
| name / teacher, wait −1 | recovery by pictures closed for this name | הכניסה בשם הזה נעצרה. בקשו מהמורה לשחרר אותה. |
| device / teacher | a device where only this child signed in, past its own 10 a day | הכניסה מהמכשיר הזה נעצרה עד {HH:MM}. אפשר להיכנס ממכשיר אחר, או לבקש מהמורה לשחרר. |
| address / teacher | wrong codes or pictures across the class from this network | זה לא בגללכם: הכניסה מהמחשבים כאן עוצרת לכולם עד {HH:MM}. אפשר לבקש מהמורה לשחרר. מי שכבר מחובר ממשיך לשחק. |
| address / wait | too many calls, class codes or registrations in an hour from this network | זה לא בגללכם: הכניסה מכאן עוצרת לכולם עד {HH:MM}. נסו שוב אז. |
| class / teacher | the class brake (100 wrong a day) | זה לא בגללכם: הכניסה לכיתה עוצרת עד {HH:MM}. אפשר לבקש מהמורה לשחרר. |
| everyone / wait | the service is busy | יש עכשיו עומס. נסו שוב ב-{HH:MM}. |
| system / wait | registration closed for now | אי אפשר להירשם כרגע. נסו שוב מאוחר יותר. מי שכבר רשום יכול להיכנס. |
| (unknown) | anything else | הכניסה עוצרת לכמה דקות. נסו שוב ב-{HH:MM}. |

The picture counts for a name (3 tries) are the E2 messages above.

### Shared device and switching

| Where | Text |
|---|---|
| The "who is playing" pill, title and map | {avatar} {name} · זה לא אני · יציאה |
| Settings button | יציאה מהמכשיר הזה |
| Confirm | לצאת? ההתקדמות נשמרת. בפעם הבאה תצטרכו את השם ואת הקוד. |
| Buttons | כן, לצאת · נשארים |
| Hint | במחשב משותף, תמיד יוצאים בסוף. |

"זה לא אני" asks the same confirm and then shows the Entry screen.

## 4. Questions for the owner

1. The 20 pictures and 22 clips under cap A (22.75 quoted): go?
2. The tick box "מחשב משותף: לא לזכור אותי": off by default (as written) or on by default at school?
3. The story step (A4): keep it? It adds about 15 seconds once and is what makes the pair stick after two weeks.

## 5. Boards (class and grade)

Mock: `docs/mock/boards.html` (390, 360, 320). One screen, two tabs "הכיתה" / "השכבה". A row: rank, avatar, the
name (first name and letter, as above), on the grade board a class tag ("ה׳2", outlined aqua, its own element), the
points (LTR, gold). The pupil's own row has a gold outline. Under the list: "נקודות השבוע. מתחילים מחדש בכל יום
ראשון." Up to 10 rows; if the pupil is not in them, their row is added under a thin line with its rank. No surname,
no code, nothing else about another child.

## 6. A trial device (`?new=1`)

Mock: `docs/mock/trial.html`. Today the question is a plain paper box; it becomes a screen of the game: Pitzi waving,
the heading **"רגע, זה מכשיר ניסיון"**, the text "כאן בודקים את המערכת החדשה של המשחק. הגעתם לכאן בטעות? אין
בעיה: חוזרים למשחק הרגיל, וכל מה שעשיתם בו נשמר." The **big gold button is the safe one, "חזרה למשחק הרגיל"**, and
it has the focus; "להמשיך לניסיון" is the quiet button under it (a child who arrived by mistake only has to press
the obvious button). Plural "אתם", no "שלך". On the sign-in screens of a trial device: a small dashed aqua tag "מצב
ניסיון" above the title, and "חזרה למשחק הרגיל" as a quiet 48 px button in the bottom bar (it replaces the
underlined link "מצב ניסיון · חזרה למשחק הרגיל").
