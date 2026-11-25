# Spec: the teacher screen on Supabase (DRAFT, for the owner and the teacher)

Status: a design spec for `docs/PHASE3.md` steps 2 and 3 (read view, then the actions), behind `?tsb=1` on its own
page `teacher.html`, side by side with today's Sheet screen. Nothing here is built. The data and the actions are the
ones that already exist on the server (`teacher_view`, `teacher_items`, `backend_health`, `teacher-reset` with
`reset` / `unlock` / `unlock_class`, the roster table, `teacher_delete_pupil`). Wireframes: `docs/mock/teacher.html`
(static, no script, not linked from anything).

For an adult, on a phone (390 wide, in a break between lessons) and on a laptop (the class computer). The look is
`css/ds-teacher.css`: navy shell and cards, white and dim text, numbers LTR, tags outlined in their colour (green for
good, warm `--wi-fix` for "look at this", never alarm red), every button 48 px.

## 1. Rules

- **She never sees a pupil's code or pictures.** The one-time code after a reset is shown once, then gone from the
  page (not kept in the DOM, storage or history).
- Session in `sessionStorage`, signed out after 30 minutes idle, a visible "יציאה" (sign out) in the header. The
  header says which class is open.
- Every write asks first, except "unlock" (harmless, undo is not needed). The two that cannot be undone (delete a
  pupil, and a reset that throws devices out) say so in plain words.
- After every action a short status line (`role="status"`), and the row updates in place; no full reload.
- Pupil names come from the server and are drawn as text only (as today).
- Addressing: impersonal or infinitive Hebrew ("לאפס את הקוד?"), no gendered verbs.

## 2. Layout

**Phone:** header (class, sign out) · alert banners · three tabs **תלמידים / מילים קשות / רשימת הכיתה** · the list as
cards (name, points, last active, tags) · a tap opens the pupil as a bottom sheet with the numbers and the actions.

**Laptop (1024 and wider):** the same header and banners; the pupils as a table on the right (RTL start), sortable by
name, points, answers, first-try rate and last active; the selected pupil in a side panel on the left with the same
actions. "Hard words" and "roster" are tabs above the table.

## 3. Screens and strings (for approval)

### Sign in

| Where | Text |
|---|---|
| Heading | כניסת מורה |
| Button | כניסה עם Google |
| Note | במחשב של הכיתה כדאי לצאת בסוף. החיבור נסגר לבד אחרי 30 דקות בלי פעילות. |
| Error: not a teacher of a class | החשבון הזה לא רשום כמורה של כיתה. כדאי לפנות למנהל האתר. |
| Header | {class} · יציאה |

### Banners (from `backend_health` and the class counters; only when they apply)

| When | Text | Action |
|---|---|---|
| many wrong codes today | היום היו בכיתה הרבה ניסיונות כניסה עם קוד שגוי. | — |
| pictures paused | היום היו הרבה ניסיונות שגויים עם תמונות. השחזור בתמונות מושהה לכל הכיתה עד מחר. | שחרור הכיתה |
| a server warning | יש תקלה בשרת: {text}. התרגול ממשיך; כדאי לעדכן את מנהל האתר. | — |

"שחרור הכיתה" (unlock_class) asks: **"לשחרר את כל הנעילות בכיתה? מומלץ רק אם ברור שאלה היו התלמידים עצמם."**
Buttons: שחרור / ביטול. Done: "הנעילות בכיתה שוחררו."

### Pupils (read)

| Where | Text |
|---|---|
| Tab | תלמידים |
| Search | חיפוש שם |
| Sort (laptop headers) | שם · נקודות · תשובות · נכון בפעם הראשונה · כוכבים · פעילות אחרונה |
| Last active | היום / אתמול / לפני {n} ימים / עוד לא שיחק |
| Tag: locked | ננעל {n} פעמים היום |
| Tag: reset waiting | מחכה לקוד חדש |
| Tag: recovery closed | שחזור בתמונות סגור |
| Tag: a flag | תשובות חריגות (with the kind on hover / in the sheet) |
| Empty | עוד אף תלמיד לא נרשם. |

### A pupil (sheet on the phone, side panel on the laptop)

Numbers: points, answers, first-try rate, error rate, stars and levels, last active, flags. Actions:

| Action | Shown when | Text |
|---|---|---|
| Reset code | always | איפוס קוד |
| Reset again | a reset is waiting | קוד חדש במקום הקודם |
| Unlock | the name is locked today, or recovery is closed | שחרור נעילה |
| Delete | always, at the bottom, quiet style | מחיקת התלמיד |

**Reset, step 1 (ask):** "לאפס את הקוד של {name}?" · "הקוד הישן יפסיק לעבוד מיד, וכל מכשיר שמחובר בשם הזה יתנתק.
ההתקדמות נשמרת." · Buttons: **איפוס** / ביטול.

**Reset, step 2 (the code, once):** big digits, LTR, spaced (`482 913`).

| Where | Text |
|---|---|
| Heading | הקוד החד־פעמי של {name} |
| Line 1 | הקוד מוצג רק עכשיו. מסרו אותו לתלמיד בעל פה או בפתק. |
| Line 2 | תקף 48 שעות. עד שהתלמיד יבחר קוד חדש, אי אפשר להיכנס בשם הזה. |
| What to tell the pupil | נכנסים ב"שכחתי את הקוד", מקלידים את קוד הכיתה ואת השם, מקישים "קיבלתי קוד מהמורה" ומקלידים את 6 הספרות. |
| Button | מסרתי, לסגור |
| Confirm on close | לסגור? אי אפשר יהיה לראות את הקוד הזה שוב. (סגירה / חזרה) |

**Unlock:** no question. Status: "הנעילה של {name} הוסרה."

**Delete:** "למחוק את {name}?" · "יימחקו כל ההתקדמות, הנקודות, התשובות והכוכבים. אי אפשר לבטל." · A tick box
"הבנתי שאי אפשר לבטל" enables **מחיקה לצמיתות** (gold is not used here: the button is outlined in `--wi-fix`) ·
ביטול. Done: "{name} נמחק/ה מהכיתה."

### Hard words today (`teacher_items`)

| Where | Text |
|---|---|
| Tab | מילים קשות |
| Line | המילה · {n}% טעויות · {m} ניסיונות |
| Empty | עוד אין מספיק תשובות היום. |

### Roster

| Where | Text |
|---|---|
| Tab | רשימת הכיתה |
| Intro | רק שמות שברשימה יכולים להירשם. |
| Field | שם פרטי להוספה |
| Hint | שם פרטי או כינוי בלבד, בלי שם משפחה. |
| Button | הוספה |
| Error: already there | השם כבר ברשימה. |
| Row of a name not registered yet | {name} · עוד לא נרשם · הסרה |
| Row of a registered pupil | {name} · נרשם · (removing goes through "מחיקת התלמיד" above) |
| Remove (not registered) | להסיר את {name} מהרשימה? (הסרה / ביטול) |

## 4. Open points

1. Two teachers on one class (a substitute): the table allows it; the screen shows the same for both. Fine as is?
2. The class name in the header comes from `classes.name`; the repo never holds it.
3. "תשובות חריגות" needs one sentence per flag kind for the teacher (rate, repeat, daycap, marathon, ...). The
   engineer has the definitions; I will word them once they are fixed.
