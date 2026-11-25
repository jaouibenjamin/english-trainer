/* The new world's fixed lists, shared by the preview (world.html, js/world.js) and the live game behind ?ds=1
   (js/avatar.js). Moved here unchanged from js/world.js. */

/* The 20 characters. `open` is the energy level that opens one (1 = open from the start). Human kids are never locked. */
export const AVATARS=[
 {id:'fox',he:'שועל',open:1},{id:'owl',he:'ינשוף',open:1},{id:'turtle',he:'צב ים',open:1},{id:'shark',he:'כריש',open:1},
 {id:'girl-curls',he:'ילדה עם סרט צהוב',open:1},{id:'boy-cap',he:'ילד עם כובע',open:1},{id:'girl-braids',he:'ילדה עם צמות',open:1},{id:'boy-curls',he:'ילד עם מעיל צהוב',open:1},
 {id:'parrot',he:'תוכי',open:1},{id:'cat',he:'חתול',open:1},{id:'robot-box',he:'רובוט',open:1},{id:'diver',he:'צוללן',open:1},
 {id:'girl-glasses',he:'ילדה עם משקפיים',open:1},{id:'boy-blond',he:'ילד עם משקפיים',open:1},{id:'girl-ponytail',he:'ילדה עם קוקו',open:1},{id:'boy-scarf',he:'ילד עם צעיף',open:1},
 {id:'penguin',he:'פינגווין',open:3},{id:'octopus',he:'תמנון',open:4},{id:'robot-bell',he:'רובוט ירוק',open:5},{id:'pilot',he:'דמות עם קסדה',open:6}];

/* The two word lists of the name builder (no free text). `unit` marks a word and translation copied from the teacher's
   Unit 1 list in js/data.js; the others are ours. The describing words show both genders (her list has the masculine form
   only; the added ending is ours). Both lists are FLAGGED FOR THE TEACHER'S REVIEW before any pupil sees them. */
export const NAME_A=[
 {en:'Special',he:'מיוחד/ת',unit:1},{en:'Sweet',he:'מתוק/ה',unit:1},{en:'Ready',he:'מוכן/ה',unit:1},
 {en:'Happy',he:'שמח/ה'},{en:'Cool',he:'מגניב/ה'},{en:'New',he:'חדש/ה'},
 {en:'Brave',he:'אמיץ/ה'},{en:'Clever',he:'חכם/ה'},{en:'Kind',he:'טוב/ת לב'},
 {en:'Fast',he:'מהיר/ה'},{en:'Funny',he:'מצחיק/ה'},{en:'Lucky',he:'בר/בת מזל'}];
export const NAME_B=[
 {en:'Song',he:'שיר',unit:1},{en:'Guitar',he:'גיטרה',unit:1},{en:'Piano',he:'פסנתר',unit:1},{en:'Flower',he:'פרח',unit:1},
 {en:'Candy',he:'ממתק',unit:1},{en:'Goal',he:'שער',unit:1},{en:'Present',he:'מתנה',unit:1},{en:'Trip',he:'מסע, טיול',unit:1},
 {en:'Shark',he:'כריש'},{en:'Fox',he:'שועל'},{en:'Star',he:'כוכב'},{en:'Robot',he:'רובוט'}];
