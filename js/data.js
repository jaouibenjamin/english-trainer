/* Word Islands: all learning content and tuning constants live here (one source of truth for the game).
   RAW, TEXTS, GL, BUILD, TOBE are copied verbatim from the classic trainer (trainer.html). */

export const PARTS=[
 {id:1,en:'Meet Emma'},{id:2,en:'Cool Schools'},{id:3,en:'The New Flat'},
 {id:4,en:'A Birthday in Brazil'},{id:5,en:'A Special Present'},
 {id:6,en:'Months'},{id:7,en:'Numbers'}];

export const RAW={
1:'goal|שער;a lot of|הרבה;kick|לבעוט;song|שיר;also|גם;hobby|תחביב;piano|פסנתר;subject|מקצוע לימוד;far|רחוק;Israel|ישראל;play|לנגן / לשחק',
2:'about|על;every|כל;special|מיוחד;their|שלהם;classroom|כיתה;forty|40;student|תלמיד;trip|מסע, טיול;dining room|חדר אוכל;other|אחר;study|ללמוד;wait|להמתין, לחכות',
3:'age|גיל;flat|דירה;soon|בקרוב;bathroom|חדר אמבטיה;guitar|גיטרה;same|אותו הדבר;teach|ללמד;building|בניין;her|שלה;sofa|ספה;toilet|אסלה;like|כמו',
4:'candy|ממתק;everyone|כולם;July|יולי;sweet|מתוק;date|תאריך;flour|קמח;outside|בחוץ, החוצה;then|אז;do|לעשות;give|לתת;ready|מוכן;throw|לזרוק',
5:"card|כרטיס ברכה;for|למשך, עבור, ל-;market|שוק;sell|למכור;end|סוף;hear|לשמוע;present|מתנה;thing|דבר;flower|פרח;I'm sorry|אני מצטער;pretty|יפה;village|כפר",
6:'January|ינואר;February|פברואר;March|מרץ;April|אפריל;May|מאי;June|יוני;July|יולי;August|אוגוסט;September|ספטמבר;October|אוקטובר;November|נובמבר;December|דצמבר',
7:'eleven|11;twelve|12;thirteen|13;fourteen|14;fifteen|15;sixteen|16;eighteen|18;twenty|20;thirty|30;fifty|50;sixty|60;seventy|70;eighty|80;ninety|90;a hundred|100;twenty-five|25;thirty-seven|37;sixty-two|62'};

export const WORDS=[];
for(const p in RAW)RAW[p].split(';').forEach(s=>{const[en,he]=s.split('|');WORDS.push({en,he,p:+p})});
export const wordsOf=p=>WORDS.filter(w=>w.p===p);

export const TEXTS=[
{id:1,p:1,title:"Maya's Hobbies",text:'Hi! My name is Maya. I am ten years old. I am from Israel. I have a lot of hobbies. I play football with my friends. I kick the ball and I get a goal! I also play the piano. My favorite song is "Happy Birthday". My favorite subject at school is English. My school is not far from my home.',
 qs:[['How old is Maya?',['She is ten.','She is eleven.','She is forty.'],0],['Where is Maya from?',['She is from Israel.','She is from Brazil.','She is from a village.'],0],['What does Maya play?',['Football and the piano.','The guitar.','Football and the guitar.'],0],['What is her favorite subject?',['English.','Music.','Football.'],0],['Is her school far from her home?',['No, it is not far.','Yes, it is far.','She has no school.'],0]]},
{id:2,p:2,title:'A Special School',text:'This is a story about a special school. There are forty students in the school. Their classroom is big. Every day the students study English and music. At one o\'clock they eat in the dining room. Every year the students go on a trip. Some students go to the sea. The other students wait for the bus and go to a farm.',
 qs:[['How many students are in the school?',['Forty.','Fourteen.','Ten.'],0],['Where do the students eat?',['In the dining room.','In the classroom.','On the bus.'],0],['What do the students study every day?',['English and music.','Football and music.','English and piano.'],0],['What do the students do every year?',['They go on a trip.','They eat in the dining room.','They wait for a story.'],0]]},
{id:3,p:3,title:"Dana's New Home",text:'Dana is eleven. Her friend Noa is the same age. Dana has a new flat. The flat is in a big building. There is a blue sofa in the living room. There is a small bathroom and a toilet. Dana plays the guitar in her room. Noa plays the guitar like Dana. Dana\'s mother is a teacher. She teaches music. Noa is coming soon to see the new flat.',
 qs:[['How old is Noa?',['She is eleven.','She is ten.','She is twelve.'],0],['Where is the flat?',['In a big building.','In a small village.','In a school.'],0],['What is in the living room?',['A blue sofa.','A guitar.','A piano.'],0],['What does Dana\'s mother teach?',['Music.','English.','Football.'],0],['Who plays the guitar?',['Dana and Noa.','Dana\'s mother.','The teacher.'],0]]},
{id:4,p:4,title:'A Birthday Party',text:'Tom\'s birthday is in July. The date is July 15. Everyone is ready for the party. Tom\'s dad makes a cake. He has flour, eggs and sugar. The cake is very sweet. Then the children go outside. They throw a ball and play games. Tom\'s friends give him candy. What do you do on your birthday?',
 qs:[['When is Tom\'s birthday?',['In July.','In June.','In January.'],0],['Who makes the cake?',['Tom\'s dad.','Tom\'s friends.','Everyone.'],0],['Where do the children play games?',['Outside.','In the classroom.','In the bathroom.'],0],['What do Tom\'s friends give him?',['Candy.','Flour.','A ball.'],0]]},
{id:5,p:5,title:'A Present for Grandma',text:'Lia lives in a small village. Today is her grandma\'s birthday. Lia goes to the market. A man sells pretty flowers there. Lia buys red flowers and a card for her grandma. The flowers are a present. At the end of the day, Lia is late. "I\'m sorry, Grandma," she says. She gives Grandma the flowers and the card. Then Lia sings a song. Grandma can hear the song. She is happy. "This is a special thing," says Grandma.',
 qs:[['Where does Lia live?',['In a small village.','In a big building.','In a market.'],0],['Where does Lia go?',['To the market.','To the school.','To the sea.'],0],['What does Lia buy?',['Flowers and a card.','Candy and a cake.','A guitar.'],0],['Why does Lia say "I\'m sorry"?',['She is late.','She has no present.','She is not happy.'],0]]}];

/* Which sentences of each passage hold the answer to each question (index into the passage's sentences).
   Used only by the reading hint, which opens the story with those sentences highlighted. */
export const EVIDENCE={1:[[2],[3],[5,7],[9],[10]],2:[[1],[4],[3],[5]],3:[[0,1],[3],[4],[9],[6,7]],4:[[0],[3],[6,7],[8]],5:[[0],[2],[4],[6]]};

export const GL={hi:'היי',my:'שלי',name:'שם',is:'הוא / היא (is)',maya:'מאיה (שם)',i:'אני',am:'(אני) am',ten:'עשר','years old':'בן / בת (גיל)',from:'מ-',israel:'ישראל',have:'יש לי',has:'יש לו / לה','a lot of':'הרבה',hobbies:'תחביבים',play:'לנגן / לשחק',plays:'מנגנת / משחקת',football:'כדורגל',with:'עם',friends:'חברים',friend:'חבר / חברה',kick:'לבעוט',the:'ה-',ball:'כדור',and:'ו-',get:'להשיג, לקבל',a:'(מילת יידוע)',goal:'שער',also:'גם',piano:'פסנתר',favorite:'אהוב ביותר',song:'שיר',subject:'מקצוע לימוד',at:'ב-',school:'בית ספר',english:'אנגלית',not:'לא',far:'רחוק',home:'בית',happy:'שמח',birthday:'יום הולדת',how:'איך / כמה',old:'ישן, בן כמה',where:'איפה',what:'מה',does:'(מילת שאלה)',do:'לעשות',her:'שלה',she:'היא',he:'הוא',it:'זה',no:'לא',yes:'כן',to:'אל, ל-',in:'ב-',brazil:'ברזיל',village:'כפר',guitar:'גיטרה',eleven:'אחת עשרה',forty:'ארבעים',music:'מוזיקה',this:'זה',story:'סיפור',about:'על',special:'מיוחד',there:'שם / יש',are:'הם / הן (are)',students:'תלמידים',their:'שלהם',classroom:'כיתה',big:'גדול',every:'כל',day:'יום',study:'ללמוד',one:'אחת',"o'clock":'בשעה',they:'הם',eat:'לאכול','dining room':'חדר אוכל',year:'שנה',go:'ללכת, לנסוע',goes:'הולכת',on:'על, ב-',trip:'טיול',some:'כמה, חלק',sea:'ים',other:'אחר',wait:'לחכות',for:'בשביל, ל-',bus:'אוטובוס',farm:'חווה','how many':'כמה',fourteen:'ארבע עשרה',dana:'דנה (שם)',noa:'נועה (שם)',same:'אותו הדבר',age:'גיל',new:'חדש',flat:'דירה',building:'בניין',blue:'כחול',sofa:'ספה','living room':'סלון',small:'קטן',bathroom:'חדר אמבטיה',toilet:'אסלה',room:'חדר',like:'כמו',mother:'אמא',teacher:'מורה',teaches:'מלמדת',teach:'ללמד',coming:'באה',soon:'בקרוב',see:'לראות',twelve:'שתים עשרה',who:'מי',tom:'תום (שם)',july:'יולי',june:'יוני',january:'ינואר',date:'תאריך',everyone:'כולם',ready:'מוכן',party:'מסיבה',dad:'אבא',makes:'מכין',cake:'עוגה',flour:'קמח',eggs:'ביצים',sugar:'סוכר',very:'מאוד',sweet:'מתוק',then:'אז, אחר כך',children:'ילדים',outside:'בחוץ',throw:'לזרוק',games:'משחקים',give:'לתת',gives:'נותנת',him:'לו',candy:'ממתק',you:'אתה / את',your:'שלך',when:'מתי',lia:'ליה (שם)',lives:'גרה',live:'לגור',today:'היום',grandma:'סבתא',market:'שוק',man:'איש',sells:'מוכר',pretty:'יפה',flowers:'פרחים',buys:'קונה',buy:'לקנות',red:'אדום',card:'כרטיס ברכה',present:'מתנה',end:'סוף',of:'של',late:'מאחרת',"i'm sorry":'אני מצטער/ת',says:'אומרת',say:'לומר',sings:'שרה',can:'יכולה',hear:'לשמוע',thing:'דבר',why:'למה'};

export const BUILD=[['I am ten years old.','אני בן / בת עשר.'],['My hobby is music.','התחביב שלי הוא מוזיקה.'],['She is a student.','היא תלמידה.'],['My birthday is in July.','יום ההולדת שלי ביולי.'],['We are in the classroom.','אנחנו בכיתה.'],['The flat is in a big building.','הדירה נמצאת בבניין גדול.'],['I play the guitar every day.','אני מנגן/ת בגיטרה כל יום.'],['They are from Israel.','הם מישראל.'],['The flowers are pretty.','הפרחים יפים.'],['My favorite subject is English.','המקצוע האהוב עליי הוא אנגלית.'],['He is my friend.','הוא חבר שלי.'],['The market is far.','השוק רחוק.']];
export const TOBE=[['I ___ eleven.','am'],['She ___ a student.','is'],['They ___ ready.','are'],['My hobby ___ football.','is'],['We ___ in the dining room.','are'],['The village ___ pretty.','is'],['You ___ my friend.','are'],['The flowers ___ for Grandma.','are'],['It ___ a special present.','is'],['I ___ from Israel.','am'],['Her flat ___ new.','is'],['The students ___ outside.','are'],['He ___ ten years old.','is'],['Dana and Noa ___ the same age.','are']];

export const TOKRE=/(a lot of|dining room|living room|I'm sorry|years old|how many|o'clock|[A-Za-z]+(?:'[a-z]+)?|[^A-Za-z]+)/gi;
export function glossKey(t){let k=t.toLowerCase();if(GL[k])return k;k=k.replace(/'s$/,'');return GL[k]?k:null}
export const VOC=new Set(WORDS.filter(w=>w.p<6).map(w=>w.en.toLowerCase()));

/* Bridge sentences per island: A1 level, at most 6 planks including the full stop and short enough for large plank lettering, built from each part's words.
   Some come from BUILD above, the rest were written for the game. */
export const SENT={
1:[['I play the piano.','אני מנגן/ת בפסנתר.'],['My hobby is music.','התחביב שלי הוא מוזיקה.'],['I am from Israel.','אני מישראל.'],['The goal is far.','השער רחוק.'],['I kick the ball.','אני בועט/ת בכדור.'],['I also play football.','אני גם משחק/ת כדורגל.']],
2:[['She is a student.','היא תלמידה.'],['We are in the classroom.','אנחנו בכיתה.'],['The trip is special.','הטיול מיוחד.'],['I study every day.','אני לומד/ת כל יום.'],['Their classroom is big.','הכיתה שלהם גדולה.'],['We wait for the bus.','אנחנו מחכים לאוטובוס.']],
3:[['The flat is new.','הדירה חדשה.'],['Her sofa is blue.','הספה שלה כחולה.'],['I play the guitar.','אני מנגן/ת בגיטרה.'],['We are the same age.','אנחנו באותו הגיל.'],['The building is big.','הבניין גדול.'],['She is coming soon.','היא באה בקרוב.']],
4:[['My birthday is in July.','יום ההולדת שלי ביולי.'],['The candy is sweet.','הממתק מתוק.'],['Everyone is ready.','כולם מוכנים.'],['We are outside.','אנחנו בחוץ.'],['I throw the ball.','אני זורק/ת את הכדור.'],['They give me candy.','הם נותנים לי ממתק.']],
5:[['The flowers are pretty.','הפרחים יפים.'],['The market is far.','השוק רחוק.'],['The village is pretty.','הכפר יפה.'],['This is a present.','זאת מתנה.'],['I hear a song.','אני שומע/ת שיר.'],['The card is for you.','הכרטיס בשבילך.']]};
export const TOBE_BY={
1:[['I ___ from Israel.','am'],['My hobby ___ football.','is'],['The goal ___ far.','is'],['I ___ eleven.','am'],['You ___ my friend.','are']],
2:[['She ___ a student.','is'],['We ___ in the dining room.','are'],['The students ___ outside.','are'],['Their classroom ___ big.','is']],
3:[['Her flat ___ new.','is'],['Dana and Noa ___ the same age.','are'],['He ___ ten years old.','is'],['The sofa ___ blue.','is']],
4:[['They ___ ready.','are'],['The candy ___ sweet.','is'],['I ___ outside.','am'],['We ___ ready.','are']],
5:[['The village ___ pretty.','is'],['The flowers ___ for Grandma.','are'],['It ___ a special present.','is'],['I ___ sorry.','am']]};

/* ---------- game structure ---------- */
export const LEVEL_INFO={
 sling:{name:'קלע המילים',sub:'פוגעים במילה הנכונה',exam:'אוצר מילים',icon:'fork',bg:null},
 listen:{name:'תופסים צלילים',sub:'שומעים מילה ותופסים אותה',exam:'הבנת הנשמע',icon:'conch',bg:'listen'},
 read:{name:'בקבוק הסיפור',sub:'קוראים סיפור ועונים',exam:'הבנת הנקרא',icon:'bottle',bg:'read'},
 bridge:{name:'גשר המשפטים',sub:'בונים משפט וחוצים',exam:'כתיבת משפטים',icon:'ic_bridge',bg:'bridge'}};

export const ISLANDS=[
 {id:1,he:'אי התחביבים',en:'Meet Emma',need:0,bg:'sling1',pos:[67,83],levels:[['sling',1],['listen',1],['read',1],['bridge',1]]},
 {id:2,he:'אי בית הספר',en:'Cool Schools',need:6,bg:'sling2',pos:[32,70.5],levels:[['sling',2],['listen',2],['read',2],['bridge',2]]},
 {id:3,he:'אי הבית החדש',en:'The New Flat',need:14,bg:'sling3',pos:[68,58],levels:[['sling',3],['listen',3],['read',3],['bridge',3]]},
 {id:4,he:'אי יום ההולדת',en:'A Birthday in Brazil',need:22,bg:'sling4',pos:[32,45.5],levels:[['sling',4],['listen',4],['read',4],['bridge',4]]},
 {id:5,he:'אי המתנות',en:'A Special Present',need:30,bg:'sling5',pos:[68,33],levels:[['sling',5],['listen',5],['read',5],['bridge',5]]},
 {id:6,he:'אי האוצר',en:'Months and Numbers',need:36,bonus:true,bg:'sling1',pos:[32,21],levels:[['sling',6],['listen',7]]}];
export const MAX_STARS=ISLANDS.reduce((a,i)=>a+i.levels.length*3,0);
export const levelKey=(isl,type)=>isl+'-'+type;

/* unlockable slingshot balls, by total stars */
export const BALLS=[{name:'קוקוס',need:0},{name:'כדור ים',need:5},{name:'שבלול',need:12},{name:'כדורגל',need:20},{name:'תפוז',need:30},{name:'כדור הזהב',need:45}];

/* ---------- tuning ---------- */
export const T={
 slingWords:7, listenWords:7, bridgeBuild:3, bridgeTobe:2,
 gravity:.19, launchK:.165, maxPull:112, minPull:16, hitPad:12, ballR:16,
 ptsFirst:10, ptsLater:4, ptsStar:15, ptsReadPerfect:50, ptsDay:20,
 ttsRate:.85};
/* one star rule for every level type: share of items answered right on the first try; a hint caps the level at 2 */
export const STAR3=.85,STAR2=.6;
export function starsFor(first,total,hint){const acc=total?first/total:0;return Math.min(hint?2:3,acc>=STAR3?3:acc>=STAR2?2:1)}
