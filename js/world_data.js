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
