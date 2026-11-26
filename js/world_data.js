/* The new world's fixed lists, shared by the preview (world.html, js/world.js) and the live game behind ?ds=1
   (js/avatar.js).
   NOTE for the preview (js/world.js): its DEMO energy uses the old thresholds (level 2 from 120); the live levels are
   in js/avatar.js. */

/* The 20 characters, in the order the picker shows them. `open` is the energy level that opens one (1 = open from the
   start). The eight human kids are always open: every child can pick a kid who looks like them from the first minute,
   and no child's look is ever locked behind a level. The other twelve (animals, robots, the diver, the pilot) open one
   per level from 2 to 13 (js/avatar.js LEVELS): the fox first (level 2 comes within the first session), the most
   exciting last. */
export const AVATARS=[
 {id:'girl-curls',he:'ילדה עם סרט צהוב',open:1},{id:'boy-cap',he:'ילד עם כובע',open:1},{id:'girl-braids',he:'ילדה עם צמות',open:1},{id:'boy-curls',he:'ילד עם מעיל צהוב',open:1},
 {id:'girl-glasses',he:'ילדה עם משקפיים',open:1},{id:'boy-blond',he:'ילד עם משקפיים',open:1},{id:'girl-ponytail',he:'ילדה עם קוקו',open:1},{id:'boy-scarf',he:'ילד עם צעיף',open:1},
 {id:'fox',he:'שועל',open:2},{id:'cat',he:'חתול',open:3},{id:'turtle',he:'צב ים',open:4},{id:'owl',he:'ינשוף',open:5},
 {id:'parrot',he:'תוכי',open:6},{id:'robot-box',he:'רובוט',open:7},{id:'diver',he:'צוללן',open:8},{id:'penguin',he:'פינגווין',open:9},
 {id:'shark',he:'כריש',open:10},{id:'octopus',he:'תמנון',open:11},{id:'robot-bell',he:'רובוט ירוק',open:12},{id:'pilot',he:'דמות עם קסדה',open:13}];

/* The ten characters of levels 14 to 23 (docs/ART_QUEUE.md, docs/AVATAR_CHARACTER.md), approved by the owner with the
   waist-up set: a list of its own, not in AVATARS, so a phone that still holds the last ship's js/avatar.js or
   js/world_art.js (no picture for them yet) never asks for one; js/avatar.js shows a character only where its picture
   is known. The Hebrew names are ours, FLAGGED FOR THE TEACHER'S REVIEW. The "griffin" was drawn as an eagle and is the
   eagle (נשר) everywhere. */
export const MORE=[
 {id:'hedgehog',he:'קיפוד',open:14},{id:'koala',he:'קואלה',open:15},{id:'raccoon',he:'דביבון',open:16},{id:'capybara',he:'קפיברה',open:17},
 {id:'otter',he:'לוטרה',open:18},{id:'flamingo',he:'פלמינגו',open:19},{id:'zebra',he:'זברה',open:20},{id:'badger',he:'גירית',open:21},
 {id:'kangaroo',he:'קנגורו',open:22},{id:'eagle',he:'נשר',open:23}];

/* Energy, in one table (the new world, behind the flag): what each thing learned is worth, and the level thresholds.
   Option A of docs/features/energy-math.md, chosen 2026-11-26 (switching to B is a change to this table only):
   10 per English star, 5 per word known, 5 per story read, 20 per Fraction Bay star (best stars per level, so energy
   is always worked out from the progress already saved, never a second counter). Level n runs from levels[n-1] to
   levels[n]; past the table, one level per `after`. Levels 1 to 13 are where they always were, so no pupil's level
   ever goes down; 14 to 23 were added for the ten characters the designer is making (SOON until their art lands).
   The most a pupil can earn: 980 in English + 660 in math = 1640; the last level, 1480, is 90% of it. */
export const ENERGY={
 worth:{star:10,word:5,story:5,mstar:20},
 levels:[0,40,90,150,220,300,380,460,540,620,700,760,820, 890,950,1020,1080,1150,1220,1280,1350,1410,1480],
 after:250};
/* The levels whose character is still being drawn: shown in the picker as "בקרוב" (no picture, opens nothing) until
   the art lands and the character joins AVATARS with that `open`. */
export const SOON=[14,15,16,17,18,19,20,21,22,23];

/* The two word lists of the name builder (no free text): a describing word and an animal, picked with arrows or the
   surprise button and stored as two indexes. None of these words is in the teacher's Unit 1 list: they are all ours,
   with our Hebrew (the describing words in both genders), and FLAGGED FOR THE TEACHER'S REVIEW before any pupil sees them
   (docs/features/new-world.md). Version 2 of the names: a name stored from the earlier lists reads as "no name yet". */
export const NAME_V=2;
export const NAME_A=[
 {en:'Brave',he:'אמיץ/ה'},{en:'Happy',he:'שמח/ה'},{en:'Clever',he:'חכם/ה'},{en:'Fast',he:'מהיר/ה'},
 {en:'Funny',he:'מצחיק/ה'},{en:'Strong',he:'חזק/ה'},{en:'Kind',he:'טוב/ת לב'},{en:'Lucky',he:'בר/בת מזל'},
 {en:'Golden',he:'זהוב/ה'},{en:'Cool',he:'מגניב/ה'},{en:'Mighty',he:'אדיר/ה'},{en:'Wild',he:'פראי/ת'}];
export const NAME_B=[
 {en:'Fox',he:'שועל'},{en:'Lion',he:'אריה'},{en:'Tiger',he:'טיגריס'},{en:'Eagle',he:'נשר'},
 {en:'Wolf',he:'זאב'},{en:'Dolphin',he:'דולפין'},{en:'Panda',he:'פנדה'},{en:'Shark',he:'כריש'},
 {en:'Owl',he:'ינשוף'},{en:'Bear',he:'דוב'},{en:'Dragon',he:'דרקון'},{en:'Rabbit',he:'ארנב'}];
