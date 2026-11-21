/* The mock exam (מבחן דמו), built from the teacher's seven review stations ("Word Power", "Guess Who", "Be the Boss",
   "Birthday Time", "Reading Detective", "Mime It") and her Unit 1 word list. The four skills are the four lines of her
   "My Unit 1 check-in": words, grammar, reading, writing.
   An exam draws from these pools; the practice for a skill draws the items the exam did not use, so a retake is never the
   same paper. Items marked src:'ws' are copied from the worksheets word for word; the rest are written from the same words. */
import {WORDS} from './data.js';

export const XSKILL={
 words:{he:'מילים',en:'Words',icon:'📖',station:'תחנה 1'},
 grammar:{he:'דקדוק',en:'Grammar',icon:'🧩',station:'תחנה 2'},
 reading:{he:'קריאה',en:'Reading',icon:'🔎',station:'תחנה 3'},
 writing:{he:'כתיבה',en:'Writing',icon:'✏️',station:'תחנה 4'}};
export const XORDER=['words','grammar','reading','writing'];
export const XPLAN={words:6,grammar:5,reading:5,writing:4};    // 20 questions, about 12 minutes
export const XPASS=.8;                                            // below this a skill gets its own practice before the retake

/* the picture sheet (assets/x/pics.webp): 6 columns × 4 rows */
export const PIC=['guitar','bathroom','market','sofa','card','building','present','village','toilet','piano','flowers','candy',
 'dining room','classroom','cake','date','kick','throw','give','wait','play the piano','play the guitar','study'];

const R=(a,b)=>a+Math.floor(Math.random()*(b-a+1));
export const shuf=a=>{a=[...a];for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a};
const pick=(a,n)=>shuf(a).slice(0,n);
const he=en=>(WORDS.find(w=>w.en===en)||{}).he||'';

/* ---------- WORDS ---------- */
const PICWORDS=['guitar','bathroom','market','sofa','card','building','present','village','toilet','piano','flowers','candy','dining room','classroom','cake','date'];
const word_pic=PICWORDS.map(w=>({k:'pic:'+w,skill:'words',type:'choice',pic:w,q:'מה רואים בתמונה?',a:w,
 opts:()=>[w,...pick(PICWORDS.filter(x=>x!==w),3)],src:['guitar','bathroom','market','sofa','card','building','present','village','toilet'].includes(w)?'ws':'',
 tip:`בתמונה: ${w} (${he(w==='flowers'?'flower':w)||''})`}));
/* the exam has a vocabulary part from English to Hebrew: the teacher's own translations */
const HEPOOL=WORDS.filter(w=>w.p<=5&&!/,/.test(w.he.split(' / ')[0])&&w.he.length<16);
const word_he=HEPOOL.map(w=>({k:'he:'+w.en,skill:'words',type:'choice',en:w.en,q:'מה הפירוש בעברית?',big:w.en,a:w.he,
 opts:()=>[w.he,...pick(HEPOOL.filter(x=>x.p===w.p&&x.he!==w.he),3).map(x=>x.he)],tip:`${w.en} = ${w.he}`}));
const NUMS=[['16','sixteen','sixty'],['30','thirty','thirteen'],['50','fifty','fifteen'],['80','eighty','eighteen'],['14','fourteen','forty'],['40','forty','fourteen'],['13','thirteen','thirty'],['60','sixty','sixteen'],['18','eighteen','eighty'],['15','fifteen','fifty']];
const word_num=NUMS.map(([n,a,b])=>({k:'num:'+n,skill:'words',type:'choice',q:'איך כותבים את המספר?',big:n,a,opts:()=>[a,b],src:['16','30','50','80'].includes(n)?'ws':'',
 tip:`${n} = ${a}. מספרים שנגמרים ב־teen הם 13 עד 19, ומספרים שנגמרים ב־ty הם עשרות (30, 40, 50...)`}));
const FILLW=[['I ___ English at school.','study'],['Music is my favorite ___.','hobby'],['I can ___ the ball.','kick'],['There are twenty students in my ___.','classroom'],
 ['I ___ for the bus every morning.','wait'],['Please ___ me the ball.','throw'],['We ___ Grandma a present.','give'],['My favorite ___ is English.','subject'],['Happy birthday! Here is a ___ for you.','present'],['The ___ is far from the city.','village']];
const BANK=['study','hobby','kick','classroom','wait','throw','give','subject','present','village'];
const word_fill=FILLW.map(([s,a],i)=>({k:'fillw:'+i,skill:'words',type:'choice',q:'בחרו את המילה שמשלימה את המשפט',sent:s,a,opts:()=>[a,...pick(BANK.filter(x=>x!==a),3)],src:i<4?'ws':'',
 tip:`${s.replace('___',a)} (${he(a)})`}));
const MATCH=[['kick','a ball'],['play','the piano'],['give','a present'],['study','English'],['throw','a ball'],['wait for','a friend']];
const word_match=MATCH.map(([v,a],i)=>({k:'match:'+v,skill:'words',type:'choice',q:'מה מתאים להשלים?',sent:`${v} ___`,a,opts:()=>{const o=[a,...MATCH.filter(m=>m[1]!==a).map(m=>m[1])];return [a,...pick([...new Set(o.slice(1))],2)]},src:i<4?'ws':'',
 tip:`${v} ${a}`}));
const MAPS=[['HOME','🏠',['bathroom','sofa']],['BIRTHDAYS','🎂',['card','date']],['MUSIC','🎵',['song','guitar']]];
const word_map=MAPS.flatMap(([cat,ic,ws])=>ws.map(w=>({k:'map:'+w,skill:'words',type:'choice',q:`איזו מילה שייכת לקבוצה ${ic} ${cat}?`,a:w,
 opts:()=>[w,...pick(MAPS.filter(m=>m[0]!==cat).flatMap(m=>m[2]),2)],src:'ws',tip:`${cat}: ${ws.join(', ')}`})));
const ACTIONS=[['kick','Kick a ball.'],['throw','Throw a ball.'],['give','Give a present.'],['wait','Wait for a friend.'],['play the piano','Play the piano.'],['play the guitar','Play the guitar.'],['study','Study English.']];
const word_act=ACTIONS.map(([p,a])=>({k:'act:'+p,skill:'words',type:'choice',pic:p,q:'מה הילד/ה עושה?',a,opts:()=>[a,...pick(ACTIONS.filter(x=>x[1]!==a).map(x=>x[1]),2)],src:'ws',tip:a}));

/* ---------- GRAMMAR ---------- */
const BE=[['The market ___ far.','is','ws'],['I ___ from Israel.','am','ws'],['The flowers ___ pretty.','are','ws'],['We ___ outside.','are','ws'],
 ['She ___ a student.','is'],['They ___ ready.','are'],['My hobby ___ football.','is'],['The village ___ pretty.','is'],['You ___ my friend.','are'],
 ['It ___ a special present.','is'],['Her flat ___ new.','is'],['The students ___ in the classroom.','are'],['He ___ ten years old.','is'],['Dana and Noa ___ the same age.','are'],['I ___ eleven years old.','am']];
const WHO_BE={am:'I → am',is:'he / she / it, או דבר אחד → is',are:'we / you / they, או כמה דברים → are'};
const gram_be=BE.map(([s,a,src],i)=>({k:'be:'+i,skill:'grammar',type:'choice',q:'בחרו את הפועל הנכון',sent:s,a,opts:()=>['am','is','are'],fixed:1,src:src||'',
 tip:`${s.replace('___',a)} · ${WHO_BE[a]}`}));
const ORDER=[['Is the village far?',['far','the village','Is'],'ws'],['Is the candy sweet?',['Is','the candy','sweet'],'ws'],['Are they outside?',['outside','Are','they'],'ws'],
 ['Is the market far?',['far','Is','the market']],['Are you ready?',['ready','you','Are']],['Is she a student?',['a student','she','Is']],['Are the flowers pretty?',['pretty','the flowers','Are']],
 ['Is it a present?',['a present','Is','it']],['Are they on a trip?',['on a trip','they','Are']],['Is your flat big?',['big','your flat','Is']]];
const gram_order=ORDER.map(([a,tiles,src],i)=>({k:'order:'+i,skill:'grammar',type:'order',q:'סדרו את המילים לשאלה',tiles,a,src:src||'',
 tip:`בשאלה הפועל (Is / Are) עובר להתחלה: ${a}`}));
const SHORT=[['building','Is it a building?','Yes, it is.','ws'],['give','Are they on a trip?','No, they aren\'t.'],['bathroom','Is it a dining room?','No, it isn\'t.','ws'],
 ['piano','Is it a piano?','Yes, it is.'],['toilet','Is it a sofa?','No, it isn\'t.'],['flowers','Are they flowers?','Yes, they are.'],['candy','Are they flowers?','No, they aren\'t.'],
 ['classroom','Is it a classroom?','Yes, it is.'],['market','Is it a village?','No, it isn\'t.'],['give','Are they friends?','Yes, they are.'],['cake','Is it a cake?','Yes, it is.'],['guitar','Is it a piano?','No, it isn\'t.']];
const gram_short=SHORT.map(([pic,q,a,src],i)=>{const it=/^Is/.test(q);return{k:'short:'+i,skill:'grammar',type:'choice',pic,q:'הסתכלו ובחרו את התשובה הקצרה',sent:q,a,
 opts:()=>it?['Yes, it is.','No, it isn\'t.']:['Yes, they are.','No, they aren\'t.'],fixed:1,src:src||'',
 tip:`${it?'Is it…? → Yes, it is. / No, it isn\'t.':'Are they…? → Yes, they are. / No, they aren\'t.'}`}});

/* ---------- READING ---------- */
/* Guess Who (station 3): the four children and what the picture tells about them */
export const KIDS=[{n:'Maya',age:14,month:'',likes:['music','the guitar'],em:'🎸',note:'🎵 🎁'},{n:'Tom',age:13,month:'June',likes:['football'],em:'⚽'},
 {n:'Noa',age:14,month:'August',likes:['reading'],em:'📖'},{n:'Ben',age:13,month:'May',likes:['the piano','music'],em:'🎹'}];
const WHO=[[['I am thirteen years old.','My birthday is in August.','I like to play the piano.'],'none'],[['I am fourteen years old.','I like music.','I play the guitar.'],'Maya'],
 [['I am fourteen years old.','My birthday is in August.','I like to read.'],'Noa'],[['I like football.','I am thirteen years old.','My birthday is in June.'],'Tom'],
 [['I am thirteen years old.','My birthday is in May.','I play the piano.'],'Ben'],
 [['My birthday is in June.','I like football.'],'Tom'],[['I am fourteen.','I like books.'],'Noa'],[['I am thirteen.','I play the piano.','My birthday is in May.'],'Ben']];
const NONE='אף אחד';
const read_who=WHO.map(([lines,a],i)=>({k:'who:'+i,skill:'reading',type:'who',q:'מי מדבר/ת? (תיאור אחד לא מתאים לאף אחד)',lines,a:a==='none'?NONE:a,opts:()=>['Maya','Tom','Noa','Ben',NONE],fixed:1,src:i<5?'ws':'',
 tip:a==='none'?'Ben בן 13 ומנגן בפסנתר, אבל יום ההולדת שלו במאי (May), לא באוגוסט. Noa נולדה באוגוסט, אבל היא בת 14. אז אף אחד.':`בודקים כל פרט: גיל, חודש ותחביב. רק ${a} מתאים/ה לכולם.`}));
/* Reading Detective (station 6), the teacher's text */
export const TRIP={title:'A Special School Trip',lines:['Maya is a student. Her favorite subject is art.','Every Friday, her teacher takes the class outside.','Today they are on a special trip to a market.','There are a lot of pretty things at the market.','Maya can hear music, too.','At the end of the trip, the students are tired but happy.']};
const TQ=[['Maya\'s favorite subject is ___.',['art','music'],'art',0,'ws'],['When does the class go outside? Every ___.',['Friday','Sunday','day'],'Friday',1,'ws'],['Where are they today?',['school','market','home'],'market',2,'ws'],
 ['True or False: Maya can hear music.',['True','False'],'True',4,'ws'],['How do the students feel at the end?',['tired but happy','sad','ready'],'tired but happy',5,'ws'],
 ['Who takes the class outside?',['Maya','the teacher','the students'],'the teacher',1],['What is at the market?',['a lot of pretty things','a classroom','a piano'],'a lot of pretty things',3],
 ['True or False: The trip is to a village.',['True','False'],'False',2],['Is Maya a teacher?',['Yes, she is.','No, she isn\'t.'],'No, she isn\'t.',0]];
const read_trip=TQ.map(([q,opts,a,line,src],i)=>({k:'trip:'+i,skill:'reading',type:'read',text:'trip',q:'קראו את הקטע וענו',sent:q,a,opts:()=>opts,fixed:1,line,src:src||'',
 tip:`התשובה בשורה: “${TRIP.lines[line]}”`}));

/* ---------- WRITING ---------- */
/* the invitation (station 5): what the picture shows, written in the exam's words */
export const INVITE={name:'Lia',age:12,date:'October 14',time:'4 o\'clock',where:'8 Rose Street'};
const norm=s=>String(s||'').toLowerCase().replace(/[’']/g,"'").replace(/[.,!?]/g,' ').replace(/\s+/g,' ').trim();
export const WRITE_CHECK={
 /* plain answers: case and punctuation do not matter, a few spellings are accepted */
 plain:(v,acc)=>acc.some(x=>norm(x)===norm(v)),
 /* a full sentence: the words, then a capital letter at the start and a full stop at the end, each told apart */
 sentence:(v,a)=>{const t=String(v||'').trim().replace(/\s+/g,' ');
  if(norm(t)!==norm(a))return{ok:false,why:'words'};
  const caps=a.match(/\b[A-Z][a-z']*/g)||[];const miss=caps.filter(w=>!new RegExp('\\b'+w+'\\b').test(t));
  if(!/^[A-Z]/.test(t))return{ok:false,why:'cap'};
  if(miss.length)return{ok:false,why:'name',w:miss[0]};
  if(!/[.?!]$/.test(t))return{ok:false,why:'stop'};
  return{ok:true}}};
const write_inv=[['age','It\'s my birthday! I\'m ___ years old.',['12','twelve'],'הגיל כתוב על העוגה'],['date','Date: ___',['October 14','14 October','October 14th','14th October','the 14th of October','14th of October','October fourteenth'],'מה כתוב בלוח השנה?'],
 ['time','Time: ___',['4 o\'clock','four o\'clock','4:00','4','four','at 4 o\'clock','at four o\'clock','4 oclock','four oclock'],'מה השעה בשעון?'],['where','Where: ___',['8 Rose Street','8 rose street','Rose Street 8','eight Rose Street'],'מה כתוב על השלט ליד הבית?'],
 ['from','From: ___',['Lia'],'מי מזמינה למסיבה?']].map(([f,s,acc,hint])=>({k:'inv:'+f,skill:'writing',type:'type',card:'invite',q:'השלימו את ההזמנה לפי התמונה',sent:s,acc,a:acc[0],src:'ws',hint,
 tip:`${s.replace('___',acc[0])}`}));
const SPELL=['guitar','sofa','card','cake','piano','market','present','toilet','village','building'];
const write_spell=SPELL.map(w=>({k:'spell:'+w,skill:'writing',type:'type',pic:w,q:'כתבו באנגלית מה רואים בתמונה',acc:[w],a:w,src:['guitar','sofa','card','market','building'].includes(w)?'ws':'',
 tip:`כותבים: ${w.split('').join(' ')}`}));
const SENTS=[['maya is a student','Maya is a student.'],['i am from israel','I am from Israel.'],['tom is thirteen years old','Tom is thirteen years old.'],['we are outside','We are outside.'],
 ['the market is far','The market is far.'],['her favorite subject is art','Her favorite subject is art.'],['the flowers are pretty','The flowers are pretty.'],['ben plays the piano','Ben plays the piano.'],
 ['my birthday is in june','My birthday is in June.'],['noa likes to read','Noa likes to read.']];
const write_sent=SENTS.map(([w,a],i)=>({k:'sent:'+i,skill:'writing',type:'sentence',q:'כתבו את המשפט נכון: אות גדולה בהתחלה ונקודה בסוף',raw:w,a,
 tip:`${a}  ·  אות גדולה בהתחלה, I תמיד גדולה, שמות (Maya, Israel, June) באות גדולה, ונקודה בסוף.`}));
const write_num=[['16','sixteen'],['30','thirty'],['50','fifty'],['80','eighty'],['13','thirteen'],['14','fourteen'],['12','twelve'],['40','forty']].map(([n,a])=>({k:'wnum:'+n,skill:'writing',type:'type',big:n,q:'כתבו את המספר במילים באנגלית',acc:[a],a,tip:`${n} = ${a}`}));

/* ---------- pools and papers ---------- */
export const POOL={words:{pic:word_pic,he:word_he,num:word_num,fill:word_fill,match:[...word_match,...word_map],act:word_act},
 grammar:{be:gram_be,order:gram_order,short:gram_short},
 reading:{who:read_who,trip:read_trip},
 writing:{inv:write_inv,spell:write_spell,sent:write_sent,num:write_num}};
/* how many of each kind go into one paper */
const PAPER={words:{pic:2,he:1,num:1,fill:1,match:1},grammar:{be:2,order:1,short:2},reading:{who:2,trip:3},writing:{spell:1,sent:1,inv:2}};
/* first paper: the worksheet items first; later papers: what this pupil has not seen yet first */
export function paper(seen=new Set(),first=false){
 const out=[];for(const sk of XORDER){for(const [kind,n] of Object.entries(PAPER[sk])){const pool=POOL[sk][kind];
  const fresh=shuf(pool.filter(it=>!seen.has(it.k))),old=shuf(pool.filter(it=>seen.has(it.k)));
  const ordered=first?[...fresh.filter(i=>i.src==='ws'),...fresh.filter(i=>i.src!=='ws'),...old]:[...fresh,...old];
  out.push(...ordered.slice(0,n))}}
 return out.map(prep)}
/* practice for one skill: 8 items, the ones missed in the exam first, then ones not seen */
export function practice(sk,missed=[],seen=new Set()){
 const all=Object.values(POOL[sk]).flat(),miss=all.filter(i=>missed.includes(i.k));
 const rest=shuf(all.filter(i=>!missed.includes(i.k)&&!seen.has(i.k))),more=shuf(all.filter(i=>!missed.includes(i.k)&&seen.has(i.k)));
 /* mix the kinds so a practice is not eight of the same thing */
 const byKind={};for(const it of [...rest,...more]){const kk=it.k.split(':')[0];(byKind[kk]=byKind[kk]||[]).push(it)}
 const mixed=[],ks=Object.keys(byKind);for(let r=0;mixed.length<16&&r<20;r++)for(const kk of ks){const it=byKind[kk][r];if(it)mixed.push(it)}
 return [...miss,...mixed].slice(0,8).map(prep)}
/* fix the order of the options once, so they do not jump around if the screen is drawn again */
const prep=it=>({...it,o:it.opts?(it.fixed?it.opts():shuf(it.opts())):null});

/* the rule card shown before a skill's practice: one short idea, in Hebrew, with examples from the unit */
export const RULES={
 words:{t:'איך זוכרים מילים',lines:[['מסתכלים על התמונה ואומרים את המילה בקול',''],['מספרים שנגמרים ב־teen הם 13 עד 19','thirteen · sixteen · eighteen'],['מספרים שנגמרים ב־ty הם עשרות','thirty · fifty · sixty · eighty'],['פעלים הולכים עם מילים קבועות','kick a ball · play the piano · give a present']]},
 grammar:{t:'am · is · are',lines:[['עם I משתמשים ב־am','I am ten.'],['עם he, she, it או דבר אחד משתמשים ב־is','The market is far.'],['עם we, you, they או כמה דברים משתמשים ב־are','The flowers are pretty.'],['בשאלה, Is או Are עוברים להתחלה','The village is far. → Is the village far?'],['תשובה קצרה',"Yes, it is. · No, it isn't. · Yes, they are."]]},
 reading:{t:'בלש קריאה',lines:[['1. קוראים את השאלה ומוצאים בה מילה חשובה','Friday · market · music'],['2. מחפשים את המילה בקטע',''],['3. קוראים את כל המשפט שבו היא נמצאת. התשובה שם',''],['ב־Guess Who בודקים כל פרט: גיל, חודש ותחביב. פרט אחד לא מתאים? זה לא הוא','']]},
 writing:{t:'משפט נכון באנגלית',lines:[['אות גדולה בהתחלה','The market is far.'],['I תמיד באות גדולה, גם באמצע המשפט','Maya and I are friends.'],['שמות של אנשים, מקומות וחודשים באות גדולה','Maya · Israel · June'],['נקודה בסוף המשפט','We are outside.'],['מספרים במילים','12 twelve · 13 thirteen · 30 thirty']]}};
