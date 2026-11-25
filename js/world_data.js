/* The new world's fixed lists, shared by the preview (world.html, js/world.js) and the live game behind ?ds=1
   (js/avatar.js).
   NOTE for the preview (js/world.js): its DEMO energy uses the old thresholds (level 2 from 120); the live levels are
   in js/avatar.js. */

/* The 20 characters, in the order the picker shows them. `open` is the energy level that opens one (1 = open from the
   start). Eight are open from the start, a fair mix: two girls, two boys, three animals and a robot. The other twelve
   open one per level from level 2 to 13 (js/avatar.js LEVELS), the remaining kids first, the most exciting last. */
export const AVATARS=[
 {id:'girl-curls',he:'ילדה עם סרט צהוב',open:1},{id:'boy-cap',he:'ילד עם כובע',open:1},{id:'girl-braids',he:'ילדה עם צמות',open:1},{id:'boy-curls',he:'ילד עם מעיל צהוב',open:1},
 {id:'fox',he:'שועל',open:1},{id:'cat',he:'חתול',open:1},{id:'turtle',he:'צב ים',open:1},{id:'robot-box',he:'רובוט',open:1},
 {id:'girl-glasses',he:'ילדה עם משקפיים',open:2},{id:'boy-blond',he:'ילד עם משקפיים',open:3},{id:'girl-ponytail',he:'ילדה עם קוקו',open:4},{id:'boy-scarf',he:'ילד עם צעיף',open:5},
 {id:'owl',he:'ינשוף',open:6},{id:'parrot',he:'תוכי',open:7},{id:'penguin',he:'פינגווין',open:8},{id:'shark',he:'כריש',open:9},
 {id:'diver',he:'צוללן',open:10},{id:'octopus',he:'תמנון',open:11},{id:'robot-bell',he:'רובוט ירוק',open:12},{id:'pilot',he:'דמות עם קסדה',open:13}];

/* The two word lists of the name builder (no free text): a describing word and an animal, picked with arrows or the
   surprise button and stored as two indexes. None of these words is in the teacher's Unit 1 list: they are all ours,
   with our Hebrew (the describing words in both genders), and FLAGGED FOR THE TEACHER'S REVIEW before any pupil sees them
   (docs/features/new-world.md). Version 2 of the names: a name stored from the earlier lists reads as "no name yet". */
export const NAME_V=2;
export const NAME_A=[
 {en:'Brave',he:'אמיץ/ה'},{en:'Happy',he:'שמח/ה'},{en:'Clever',he:'חכם/ה'},{en:'Fast',he:'מהיר/ה'},
 {en:'Funny',he:'מצחיק/ה'},{en:'Strong',he:'חזק/ה'},{en:'Kind',he:'טוב/ת לב'},{en:'Lucky',he:'בר/בת מזל'},
 {en:'Super',he:'סופר'},{en:'Cool',he:'מגניב/ה'},{en:'Mighty',he:'אדיר/ה'},{en:'Wild',he:'פראי/ת'}];
export const NAME_B=[
 {en:'Fox',he:'שועל'},{en:'Lion',he:'אריה'},{en:'Tiger',he:'טיגריס'},{en:'Eagle',he:'נשר'},
 {en:'Wolf',he:'זאב'},{en:'Dolphin',he:'דולפין'},{en:'Panda',he:'פנדה'},{en:'Shark',he:'כריש'},
 {en:'Owl',he:'ינשוף'},{en:'Bear',he:'דוב'},{en:'Dragon',he:'דרקון'},{en:'Falcon',he:'בז'}];
