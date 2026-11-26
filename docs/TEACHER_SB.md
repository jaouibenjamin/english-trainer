# Spec: the teacher screen on Supabase (DRAFT, for the owner and the teacher)

Status: a design spec for `docs/PHASE3.md` steps 2 and 3 (read view, then the actions), behind `?tsb=1` on its own
page `teacher.html`, side by side with today's Sheet screen. Revised after an independent kids-UI review and the
backend engineer's answers. Nothing here is built. The data and actions are the ones on the server
(`teacher_view`, `teacher_items`, `backend_health`, `teacher-reset` with `reset` / `unlock` / `unlock_class`, the
roster table, remove and delete). Wireframes: `docs/mock/teacher.html` (static, no script, not linked from anything;
responsive: phone 360 and 390, laptop 1280).

For an adult, on a phone in a break between lessons and on the class computer (often on a projector). The look is
`css/ds-teacher.css`: navy shell and cards, white and dim text, numbers LTR, tags outlined in their colour (green for
good, warm `--wi-fix` for "look at this", never alarm red), every button 48 px.

## 1. Rules

- **She never sees a pupil's code or pictures.** The one-time code after a reset appears only after a second tap, is
  held in a variable (never in storage, the URL or history), and is removed from the page on close and on `pagehide`.
- **Projector safety:** anything secret (the class code, a one-time code) is hidden until tapped, and says so.
- Session in `sessionStorage`, signed out after 30 minutes idle. Google sign-in always shows the account chooser
  (`prompt=select_account`), so a shared computer never signs in as the last person by itself.
- Every write asks first, except "unlock". Confirmations name the pupil **with a second clue** (points and last
  activity), because a class can have two children with the same first name.
- **Names in the class list:** first name and one letter of the surname (`נועה כ.`); for two alike, a digit after the
  letter (`נועה כ2.`), never a second letter. The server refuses a dot or a second hyphen in the first name, but one
  hyphen is allowed (בת-אל), so a surname could still be written in (`דנה-כהן כ.`): the teacher's guide asks her to
  write first names only, and `roster_only` stays on so a child can register only a name from her list.
- Destructive actions are never next to everyday ones: "remove" and "delete" sit in a "עוד" menu, at least 24 px
  away from "reset" and "unlock".
- After every action a short status line (`role="status"`) and the row updates in place.
- Dialogs: `role="dialog"`, `aria-modal="true"`, focus trapped inside, Esc closes (except while the one-time code is
  shown: Esc asks first), focus returns to the button that opened it.
- Server text is never shown as is: each known warning has a fixed Hebrew string (section 3); anything unknown shows
  the generic one. Pupil names are drawn as text only.
- Impersonal Hebrew ("לאפס את הקוד?"), no gendered verbs.

## 2. Layout

**Phone:** header (class, class code, sign out) · banners · tabs **תלמידים / מילים קשות / רשימת הכיתה** · a chip
"דורשים טיפול" that filters to pupils with a lock, a waiting reset, closed recovery or a pattern to check · the list
as cards, **ordered by name** (alphabetical, so she finds a child fast) · a tap opens the pupil as a bottom sheet.

**Laptop (1024 and wider):** the same header and banners; pupils as a table, sortable (name, points, answers, right
the first time, last active), the selected pupil in a side panel with the same actions.

## 3. Screens and strings (for approval)

### Sign in and header

| Where | Text |
|---|---|
| Heading | כניסת מורה |
| Button | כניסה עם Google |
| Note | במחשב של הכיתה כדאי לצאת בסוף. החיבור נסגר לבד אחרי 30 דקות בלי פעילות. |
| Error: not a teacher of a class | החשבון הזה לא רשום כמורה של כיתה. {contact} |
| Header | {class} · יציאה |
| Sign-out note (under the button, once) | היציאה סוגרת את מסך המורה בלבד. החשבון של Google נשאר מחובר בדפדפן. |
| Class code (header, LTR, large when shown) | קוד הכיתה: ●●●●●●●● · הצגה / הסתרה |
| Under the code | ודאו שהמסך לא מוקרן לפני ההצגה. |

The class code and the class name come from the server at run time; neither is ever in the repo. `{contact}` is a
contact line the owner sets on the server (e.g. how to reach the site's manager), shown as text; it is not in the repo.

### Banners

| When (server kind) | Text | Action |
|---|---|---|
| many wrong codes today (class counter) | היום היו בכיתה הרבה ניסיונות כניסה עם קוד שגוי. מי שכבר מחובר ממשיך לשחק. | — |
| class brake reached (100 wrong a day; told at 60) | הכניסה לכיתה נעצרה עד מחר בגלל הרבה ניסיונות שגויים. אם אלה היו התלמידים, אפשר לשחרר. | שחרור הכניסה לכיתה |
| pictures paused for the class | היום היו הרבה ניסיונות שגויים עם תמונות. השחזור בתמונות מושהה לכל הכיתה עד מחר. | — |
| `unreadable_day` (the server cannot tell addresses apart) | יש תקלה טכנית בזיהוי המחשבים. התרגול ממשיך. {contact} | — |
| maintenance or backup late | הגיבוי האחרון לא הושלם. התרגול ממשיך. {contact} | — |
| any other warning | יש תקלה טכנית. התרגול ממשיך. {contact} | — |
| unlock-class used up (twice today) | הכניסה לכיתה נעצרה עד מחר ב-{HH:MM}. היום כבר שוחררה פעמיים, וזה המקסימום. מי שכבר מחובר ממשיך לשחק. {contact} | — (no button) |

The backend engineer confirms the list of server kinds; a new kind gets a string here before it is shown.

**Unlock class, confirm:** "לשחרר את הכניסה לכל הכיתה? כדאי רק אם ברור שהניסיונות השגויים היו של התלמידים עצמם.
אפשר לשחרר עד פעמיים ביום." · Buttons: **שחרור** / ביטול · Done: "הכניסה לכיתה שוחררה."

### Pupils (read)

| Where | Text |
|---|---|
| Search | חיפוש שם |
| Filter chip | דורשים טיפול ({n}) |
| Columns | שם · נקודות · תשובות · נכון בפעם הראשונה · כוכבים · פעילות אחרונה |
| Never played | "—" in every number column (never "0%"), and "עוד לא שיחק/ה" |
| Last active | היום · אתמול · לפני {n} ימים |
| Tag: locked | ננעל/ה {n} פעמים היום |
| Tag: reset waiting | מחכה לקוד חדש |
| Tag: recovery closed | שחזור בתמונות סגור |
| Tag: flag | דפוס תשובות לבדיקה (the kind, in one sentence, in the pupil's sheet) |
| Empty class | עוד אף תלמיד לא נרשם. השלב הבא: להוסיף את שמות הכיתה ב"רשימת הכיתה", ולכתוב את קוד הכיתה על הלוח. |

### A pupil

Numbers, tags, then the actions. Everyday actions as buttons; the rest in "עוד".

| Action | Shown when | Style | Text |
|---|---|---|---|
| Unlock | locked today, or recovery closed | gold | שחרור נעילה |
| Reset code | always | secondary (outlined) | איפוס קוד |
| New one-time code | a reset is waiting | secondary | קוד חדש במקום הקודם |
| Menu | always, 24 px below | quiet | עוד ▾ → הסרה מהכיתה · מחיקה לצמיתות |

**Unlock:** no question. Status: "הנעילה של {name} הוסרה."

**Reset, step 1:** "לאפס את הקוד של {name} ({points} נקודות, {last})?" · "הקוד הישן יפסיק לעבוד מיד, וכל מכשיר שמחובר
בשם הזה יתנתק. ההתקדמות נשמרת." · **איפוס** / ביטול.

**Reset, step 2 (hidden until asked):** "הקוד החד־פעמי מוכן." · "ודאו שהמסך לא מוקרן." · button **הצגת הקוד**.

**Reset, step 3 (the code):** big digits, LTR, in two groups of three (`482 913`).

| Where | Text |
|---|---|
| Heading | הקוד החד־פעמי של {name} |
| Line 1 | הקוד מוצג רק עכשיו. מסרו אותו לתלמיד בעל פה או בפתק. |
| How to read it | מקריאים בשתי קבוצות: "ארבע שמונה שתיים", "תשע אחת שלוש". |
| Line 2 | תקף 48 שעות. עד שהתלמיד יבחר קוד חדש, אי אפשר להיכנס בשם הזה. |
| What to tell the pupil | נכנסים ב"שכחתי את הקוד", מקלידים את קוד הכיתה ואת השם, מקישים "קיבלתי קוד מהמורה" ומקלידים את 6 הספרות. |
| Button | מסרתי, לסגור |
| Confirm on close (and on Esc) | לסגור? אי אפשר יהיה לראות את הקוד הזה שוב. (סגירה / חזרה) |

**Remove from the class** (can be undone for 14 days):
"להסיר את {name} ({points} נקודות, {last}) מהכיתה?" · "התלמיד לא יוכל להיכנס. אפשר להחזיר אותו עם כל ההתקדמות עד 14
יום; אחר כך הכול נמחק. השם נשאר תפוס עד אז." · **הסרה** / ביטול · Done: "{name} הוסר/ה מהכיתה. אפשר להחזיר עד
{date}." with a button **ביטול ההסרה** for 10 seconds.

**Delete for good** (immediate; also used for a parent's deletion request; also available on a removed pupil):
"למחוק את {name} לצמיתות?" · "כל ההתקדמות, הנקודות, התשובות והכוכבים יימחקו מיד. אי אפשר לבטל." · field "כדי
לאשר, הקלידו את השם הפרטי" (must match) · **מחיקה לצמיתות** (outlined in `--wi-fix`) / ביטול · Done: "{name} נמחק/ה."

### Removed pupils (a section at the bottom of "רשימת הכיתה")

| Where | Text |
|---|---|
| Heading | הוסרו לאחרונה |
| Row | {name} · יימחק ב-{date} · החזרה · מחיקה לצמיתות |
| Empty | (the section is hidden) |

### Hard words today

| Where | Text |
|---|---|
| Line | המילה · {n}% טעויות · {m} ניסיונות |
| Empty | עוד אין מספיק תשובות היום. |

### Roster

| Where | Text |
|---|---|
| Intro | רק שמות שברשימה יכולים להירשם. |
| Field | שם פרטי להוספה |
| Hint | שם פרטי או כינוי בלבד, בלי שם משפחה. לשני ילדים באותו שם: מוסיפים אות אחרי השם, למשל "{שם} ב". |
| Button | הוספה |
| Paste a list | הדבקת רשימה (one name per line; a preview shows what will be added and what is already there, then **הוספת {n} שמות**) |
| Error: already there | השם כבר ברשימה. |
| Row, not registered | {name} · עוד לא נרשם/ה · הסרה מהרשימה (confirm: "להסיר את {name} מהרשימה?") |
| Row, registered | {name} · נרשם/ה (removing goes through the pupil's "עוד" menu) |

### Privacy note (footer of the screen)

"השמות הם שמות פרטיים או כינויים בלבד. תלמיד שהוסר נשמר עד 14 יום ואז נמחק; מחיקה לצמיתות מוחקת מיד."

## 4. Open points

1. Two teachers on one class (a substitute): the table allows it; the screen is the same for both. Fine?
2. One sentence per flag kind (rate, repeat, daycap, marathon, items, levels, unusual, bonus) once the engineer
   fixes their definitions.
3. `{contact}`: the owner chooses what it says.
