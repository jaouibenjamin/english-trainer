# Spec: the pupil's sign-in screens for Supabase mode (DRAFT, for the owner's and the teacher's approval)

Status: a design spec. Nothing here is built or switched on. The flows are `docs/BACKEND.md` section 3 (A, B, E, F);
the step in the plan is `docs/PHASE3.md` step 5. **These screens change how children sign in: they need the owner's
explicit yes (and the teacher's) before they are ever switched on.** Every string a child sees is listed below for
that approval.

Wireframes: `docs/mock/signin.html` (a static page in the new look; not linked from the game, not wired to anything,
no requests). Portrait 390x844 first; the same column centred on a laptop.

## 1. The picture grid: the existing art cannot give a good one (stop here; it needs credits)

I checked everything under `assets/al` (no generation). The usable candidates are 13: cat, fox, octopus, owl,
parrot, penguin, shark, turtle (avatars), Pitzi (the crab), one robot, and the bolt, gear and lock icons. The 8
children's portraits, the pilot and the diver are out (they look like classmates). That set fails on three counts:

1. **9 of the 13 are avatars, and a pupil's avatar is shown to the whole class** (board, map). A child who picks "my
   fox" as a secret picture hands every classmate half the secret. This alone rules them out.
2. **Too few.** `docs/BACKEND.md` section 3 counts on about 20 pictures: two in order out of 20 are 380 pairs, 3
   tries 0.79%. With 13 it is 156 pairs and 1.9% (with 16, 240 and 1.25%). The security numbers would have to be
   re-done and re-approved.
3. **The icons already mean something** in the game (gear = settings, lock = a closed island, bolt = energy), so they
   confuse, and the two robots are too alike to keep both.

**What is missing:** 20 new pictures, one style (painted, the Arcade Lagoon palette, one object on a plain navy
tile, no text, no characters, no brands), none of them used anywhere else in the game, each nameable in one Hebrew
word and different in shape *and* colour from the others:

| | | | | |
|---|---|---|---|---|
| תפוח (apple, red) | בננה (banana, yellow) | אבטיח (watermelon slice) | עוגה (cake, pink) | כדור (ball, blue and white) |
| מטריה (umbrella, purple) | אופניים (bicycle) | עפיפון (kite, orange) | תוף (drum) | גיטרה (guitar) |
| כובע (hat) | נעל (shoe) | שעון (clock) | ירח (moon) | עץ (tree) |
| פרח (flower) | בית (house) | סירה (sailboat) | פיל (elephant, grey) | ג׳ירפה (giraffe) |

Left out on purpose: a key or a lock (they read as "password"), two red fruits (apple and strawberry are confused at
72 px), anything on an avatar, Pitzi, the islands, numbers and letters.

Estimate: one sheet of 20 on a 4 x 5 grid, cut into tiles (one style for free), gpt_image_2_5 high, 1.25 a take; with
a retake or two **about 2.5 to 5 credits**; 20 single images would be about 25 to 30. The art budget is at 448.69 of
450, so either needs the owner to set a new cap. **Nothing has been generated.** The wireframes use labelled
placeholder tiles.

## 2. The rules every screen follows

- One question per screen, a progress line on top ("שלב 2 מתוך 4"), a back arrow (48 px) that keeps what was typed.
- Buttons and tiles 48 px or more; the main action is the gold button at the bottom, inside the thumb's reach.
- Fields: a visible label above (never only a placeholder), `inputmode="numeric"` for codes, `autocomplete="off"`
  and no autofill of the 4-digit code; class code `autocapitalize="characters"`, Latin, LTR inside the RTL page.
- The 4-digit code shows as 4 boxes with dots, with a "הצגה" (show) toggle; nothing is kept after the screen closes.
- Errors appear under the field in `--wi-fix` (warm, never alarm red), in words a child can act on, and are read
  out (`role="alert"`). Wrong answers never blame: "לא נכון" is followed by what to do.
- The pictures: a 4 x 5 grid, tiles about 76 px with an 8 px gap on a 390 wide screen, each a button with its Hebrew
  word under it and as its label. Tapping marks it with a gold ring and a badge "1" or "2"; tapping a marked tile
  unmarks it (and the "2" becomes "1"). The grid order is fixed (the same everywhere, so memory by place helps; a
  shuffle would not hide what is tapped anyway). Screen reader: "תפוח, נבחרה ראשונה".
- Reduced motion and calm mode: no pop on the badge, no shake on an error.
- Gendered Hebrew is avoided with the plural "אתם" the game already uses.

## 3. The screens and every string (for approval)

### Entry (sign-in screen, Supabase mode)

| Where | Text |
|---|---|
| Title | ניצני אופק |
| Main button | נרשמים בפעם הראשונה |
| Second button | כבר נרשמתי |
| Link | שכחתי את הקוד |

### A. Register (4 steps)

| Step | Where | Text |
|---|---|---|
| A1 | Heading | מי אתם? |
| | Label | קוד הכיתה |
| | Hint | 8 אותיות ומספרים. הוא כתוב על הלוח. |
| | Label | השם הפרטי שלכם |
| | Button | המשך |
| | Error: class code | קוד הכיתה לא נכון. בדקו שוב מול הלוח. |
| | Error: name not on the list | השם הזה לא ברשימת הכיתה. בקשו מהמורה להוסיף אותו. |
| | Error: name already registered | כבר נרשמו עם השם הזה. אם זה אתם, הקישו "כבר נרשמתי". |
| A2 | Heading | בוחרים קוד סודי |
| | Text | 4 ספרות שרק אתם יודעים. לא הקוד של הטלפון! |
| | Label | הקוד הסודי שלי (4 ספרות) |
| | Label | שוב את אותו הקוד |
| | Toggle | הצגה / הסתרה |
| | Error: weak code | קל מדי לנחש את הקוד הזה. בחרו קוד אחר. |
| | Error: the two differ | שני הקודים לא זהים. נסו שוב. |
| A3 | Heading | בוחרים שתי תמונות סודיות |
| | Text | קודם אחת, ואחריה עוד אחת. הן יעזרו לכם אם תשכחו את הקוד. |
| | Hint | אל תגלו אותן לאף אחד, גם לא לחברים. |
| | Status | נבחרה 1 מתוך 2 / נבחרו 2 מתוך 2 |
| | Button (after two) | המשך |
| A4 | Heading | עוד פעם, כדי לזכור |
| | Text | הקישו שוב על שתי התמונות, באותו הסדר. |
| | Error: other pictures or order | זה לא אותו הדבר. נסו שוב, או חזרו לבחור מחדש. |
| | Link | לבחור תמונות אחרות |
| Done | Heading | נרשמתם! |
| | Text | המכשיר הזה יזכור אתכם. אם תשכחו את הקוד, התמונות יעזרו. |
| | Button | יוצאים לדרך |

A4 is new (not in BACKEND.md): a check on the device only, so a child remembers what they tapped. Nothing extra is
sent.

### B. Sign in

| Where | Text |
|---|---|
| Heading | נכנסים |
| Labels | קוד הכיתה / השם הפרטי שלכם / הקוד הסודי שלי (4 ספרות) |
| Button | כניסה |
| Error: name or code (the same for both, BACKEND D1) | השם או הקוד לא נכונים. נסו שוב. |
| Error: wait | היו יותר מדי ניסיונות. אפשר לנסות שוב בעוד 5 דקות. (15 דקות / שעה / 4 שעות) |
| Link | שכחתי את הקוד |

### B'. First sign-in of a pupil from the Sheet (one time; nothing opens before it is done)

| Where | Text |
|---|---|
| Heading | יש לנו כניסה חדשה ובטוחה יותר |
| Text | פעם אחת בלבד: בוחרים קוד סודי חדש ושתי תמונות סודיות. הנקודות והכוכבים שלכם נשמרים. |
| Button | בואו נתחיל |
| Then | A2, A3 and A4 as above, progress "שלב 1 מתוך 3" ... |
| Error: new code equals the old (only if the server refuses it) | בחרו קוד חדש, לא את הקוד הקודם. |

### E. "I forgot my code"

| Step | Where | Text |
|---|---|---|
| E1 | Heading | שכחתם את הקוד? זה קורה. |
| | Labels | קוד הכיתה / השם הפרטי שלכם |
| | Button | המשך |
| E2 | Heading | הקישו על שתי התמונות הסודיות שלכם, לפי הסדר |
| | Error: wrong (tries left) | זה לא זה. נשארו עוד 2 ניסיונות. (עוד ניסיון אחד) |
| | After the 3rd wrong try | השחזור עם תמונות נסגר לשם הזה. בקשו מהמורה קוד חדש. |
| | Already used in the last 30 days | כבר החלפתם קוד החודש. בקשו מהמורה קוד חדש. |
| | Class paused for the day | אי אפשר לשחזר עם תמונות היום. נסו מחר, או בקשו מהמורה קוד. |
| | Link | קיבלתי קוד מהמורה |
| E3 | Heading | הקוד מהמורה |
| | Label | 6 ספרות |
| | Button | המשך |
| | Error | הקוד לא נכון או שפג תוקפו. בקשו מהמורה קוד חדש. |
| E4 | Then | A2, A3 and A4: a new code and **two new pictures** |
| Done | Heading | הקוד החדש מוכן! |
| | Text | בטלפונים ובמחשבים אחרים תצטרכו להיכנס שוב עם הקוד החדש. |
| | Button | יוצאים לדרך |

While a reset is waiting (BACKEND F4) the pictures do not work. If the server answers E1 with "a teacher's code is
waiting", E1 goes straight to E3 with the text "המורה הכינה לכם קוד. הקלידו אותו כאן." Whether the server may say
that (it tells anyone with the class code and the name that a reset is waiting) is the engineer's call; if not, E2's
wrong-picture message is shown and the link to E3 is enough.

### Signing out (settings)

| Where | Text |
|---|---|
| Button | יציאה מהמכשיר הזה |
| Confirm | לצאת? בפעם הבאה תצטרכו את השם ואת הקוד. |
| Buttons | כן, לצאת / נשארים |
| Hint | במחשב משותף, תמיד יוצאים בסוף. |

## 4. Questions for the owner

1. The 20 pictures (section 1): a new cap of about 5 credits for one sheet, or about 30 for single images?
2. Should the device remember the class code (not the name or the code), so a child types it once? It saves typing
   on a shared computer but leaves the class code on that computer. My suggestion: no, it is on the board.
3. A4 (tap the pictures again to confirm): keep it? It costs 10 seconds and saves a forgotten pair.
