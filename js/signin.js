/* The pupil's sign-in screens for 'supabase' mode (docs/SIGNIN.md, docs/BACKEND.md section 3, PHASE3 step 5).
   Shown only when js/api.js runs in 'supabase' mode, which config.js cannot reach by accident (a project, the exact
   mode, and a ?new=1 device until `everyone: true`). With today's config nothing here is loaded.

   Flows: Entry, A register (5 steps), B sign in, E "I forgot my code" (the pictures or the teacher's one-time code,
   then a new code and new pictures, one request), and the waits the server answers with (by / help / wait). There is no
   "first sign-in of a Sheet pupil" flow: the move to Supabase is a fresh start (docs/PHASE4.md A).
   What this module needs from the page (mount's second argument):
     enter(kind, f)      js/state.js enter() (the seam with PHASE3 step 6): 'register' {c, n, code, pics}, 'login'
                         {c, n, code}, 'recover' {c, n, newCode, newPics, pics | otc}. It resolves {ok:true} (the game
                         holds the pupil, no code is kept) or {ok:false, e, wait?, by?, help?}, and never throws.
     done()              leave to the game (the title). There is no way out without signing in: the game shows
                         nothing else to a pupil who is not signed in
     sound()             true when sound may play (the game's sfx on, calm mode off)
     lastC               the class code this device used last, if any
   Secrets: the 4-digit code, the one-time code and the pictures live in this module's memory only, while the flow
   runs; nothing is written to storage, the address or the console, and everything is wiped when the flow ends.
   DOM: built from strings with every outside value escaped (esc); events by delegation on data-si, so the game's own
   data-a handler never sees these buttons. No inline handler (CSP). */

/* THE PICTURE NUMBERS ARE A CONTRACT WITH THE SERVER: a pupil's pair is stored as these numbers (1 to 20, in order;
   supabase/functions/_shared/validate.ts isPictures, settings.pic_choices = 20). Never reorder, insert or remove: every
   pupil's pictures would change meaning. A new picture can only be added at the end, with pic_choices raised. */
export const PICS=[
 ['apple','תפוח','041323_3bedd33e-537f-445d-9b2f-a2de6c83f3d4','041501_6e989b5b-457d-413a-b052-91c5d415333a'],
 ['banana','בננה','041323_3bedd33e-537f-445d-9b2f-a2de6c83f3d4','041501_1749fdd7-d81e-4ff5-8802-4c9a12cbc35c'],
 ['watermelon','אבטיח','041323_3bedd33e-537f-445d-9b2f-a2de6c83f3d4','041501_f13d943c-abd0-4057-aa17-fa2aaaffb883'],
 ['cactus','קקטוס','041323_3bedd33e-537f-445d-9b2f-a2de6c83f3d4','041501_305fd88d-103c-4868-a8ce-6576188890be'],
 ['grapes','ענבים','041322_4b04d8ff-8ca0-47fd-a5ea-62a29b8c9dd8','062550_d4547c12-54e9-4053-a70b-52ce41dddcdc'],
 ['flower','פרח','041322_4b04d8ff-8ca0-47fd-a5ea-62a29b8c9dd8','041822_d3ae8b43-4946-4375-8390-56b2d11d86b8'],
 ['umbrella','מטריה','041322_4b04d8ff-8ca0-47fd-a5ea-62a29b8c9dd8','041501_66667285-eef1-48cd-a8d5-4ebe3b5f7307'],
 ['kite','עפיפון','041322_4b04d8ff-8ca0-47fd-a5ea-62a29b8c9dd8','041501_5ddd60a1-6a59-4b8f-8ba9-634847123e63'],
 ['drum','תוף','041323_f033b30a-5de8-4534-aa9f-1b61ac24e09b','041501_3639ff18-963e-4fa3-94c9-e345a6fc4541'],
 ['hat','כובע','041323_f033b30a-5de8-4534-aa9f-1b61ac24e09b','041820_b2c05453-5cf8-481e-9e3e-f03442827454'],
 ['shoe','נעל','041323_f033b30a-5de8-4534-aa9f-1b61ac24e09b','041945_22708831-06e1-4ac9-8977-63bbde8ec217'],
 ['elephant','פיל','041323_f033b30a-5de8-4534-aa9f-1b61ac24e09b','041503_8c39ba93-5a31-430e-9033-14834c89b24d'],
 ['giraffe','ג׳ירפה','041324_98e7de0d-19d1-4079-b408-10392bd66467','041820_4a431c47-503b-4a2e-852c-53493f881296'],
 ['house','בית','041324_98e7de0d-19d1-4079-b408-10392bd66467','041503_4da55548-bad7-4392-bfb2-e845ff116845'],
 ['pencil','עיפרון','041324_98e7de0d-19d1-4079-b408-10392bd66467','041521_e7bdb3ef-ccd9-4101-b0dc-b8df78a1e34f'],
 ['book','ספר','041324_98e7de0d-19d1-4079-b408-10392bd66467','044253_e88faa03-fd09-4dff-908d-e1d6fcdd0ae3'],
 ['bell','פעמון','041323_04bbaf2a-1abe-45cc-837b-ccffb8d58a23','041503_54a0ec08-1f0a-49c4-a020-b9db1af31528'],
 ['car','מכונית','041323_04bbaf2a-1abe-45cc-837b-ccffb8d58a23','041503_7d6ec7c6-a168-4438-8fac-5bc91cf8ff55'],
 ['scissors','מספריים','041323_04bbaf2a-1abe-45cc-837b-ccffb8d58a23','041520_bac811c6-d9c5-4946-a09f-361bc9daa58d'],
 ['mushroom','פטרייה','041323_04bbaf2a-1abe-45cc-837b-ccffb8d58a23','041820_c0c6aef4-ba22-4f70-9fc5-4b7dfa845a8c']
].map(([en,he,img,vox],i)=>({no:i+1,en,he,img:`assets/al/secret/${en}.hf_20261126_${img}.webp`,vox:`assets/al/voice/${en}.hf_20261126_${vox}.mp3`}));
const LINE={order:'assets/al/voice/line-order.hf_20261126_041501_1b46e76f-b879-483e-bea7-15c82072397a.mp3'};

/* Every string a child sees: docs/SIGNIN.md section 3, copied exactly. The ones marked NEW are not in the spec yet and
   are on the teacher-review list. */
const T={
 title:'ניצני אופק',reg:'נרשמים בפעם הראשונה',have:'כבר נרשמתי',forgot:'שכחתי את הקוד',
 step:(a,b)=>`שלב ${a} מתוך ${b}`,back:'חזרה',next:'המשך',
 a1h:'מי אתם?',classL:'קוד הכיתה',classH:'8 תווים, אותיות ומספרים. הוא על הלוח.',
 // the name: first name + one letter of the surname (docs/SIGNIN.md section 1 "Identity", docs/GRADES_V1.md 0011)
 firstL:'השם הפרטי',letterL:'אות משפחה',letterA:'האות הראשונה של שם המשפחה',nameH:'השם הפרטי והאות הראשונה של שם המשפחה, כמו ברשימה של המורה.',
 asIs:'כך יופיע במשחק: ',eScript:'האות צריכה להיות באותה שפה של השם.',
 // NEW, not in the spec (on the teacher-review list): the server says the class takes the letter, or the name's form
 eLetter:'חסרה האות הראשונה של שם המשפחה. אות אחת, למשל כ.',
 eForm:'כתבו את השם כמו ברשימה של המורה: השם הפרטי, ואות אחת משם המשפחה.',
 eClass:'קוד הכיתה לא נכון. בדקו שוב מול הלוח.',eRoster:'השם הזה לא ברשימת הכיתה. בדקו את השם ואת האות, או בקשו מהמורה.',
 eTaken:'מישהו כבר נרשם בשם הזה. אם זה אתם, הקישו "כבר נרשמתי". אם יש בכיתה שני ילדים בשם הזה, בקשו מהמורה.',
 a2h:'בוחרים קוד סודי',a2t:'4 ספרות שרק אתם יודעים. לא הקוד של הטלפון!',codeL:'הקוד הסודי שלי (4 ספרות)',code2L:'שוב את אותו הקוד',
 show:'הצגה',hide:'הסתרה',eWeak:'קל מדי לנחש. לא 1234 ולא ספרות חוזרות. נסו קוד אחר.',eDiff:'שני הקודים לא זהים. נסו שוב.',
 a3h:'בוחרים שתי תמונות סודיות',a3line:'קודם תמונה אחת, אחר כך עוד אחת',a3hint:'הקישו על תמונה כדי לבחור. הקישו על משבצת כדי להחליף.',
 a4h:'זוכרים בעזרת סיפור',pair:(a,b)=>`${a}, ואחר כך ${b}`,a4say:'אמרו את זה בלב.',a4t:'מצאו סיפור קצר שמחבר אותן. למשל: התפוח עף על עפיפון. אל תספרו אותו לאף אחד.',a4b:'זכרתי',
 a5h:'עכשיו מהזיכרון',a5t:'הקישו על שתי התמונות, באותו הסדר.',a5miss:'לא בדיוק. נסו שוב, אתם קרובים.',a5new:'אפשר לבחור תמונות חדשות.',
 regDone:'נרשמתם!',regDoneT:'המכשיר הזה יזכור אתכם. אם תשכחו את הקוד, התמונות יעזרו.',go:'יוצאים לדרך',
 bh:'נכנסים',enter:'כניסה',ePin:'השם או הקוד לא נכונים. נסו שוב.',
 e1h:'שכחתם את הקוד? זה קורה.',e2h:'התמונות הסודיות, לפי הסדר',
 e2wrong:'לא התאים. קחו רגע לחשוב על הסדר ונסו שוב.',e2end:'הפעם התמונות לא עבדו. המורה תעזור לכם עם קוד חדש.',
 e2month:'כבר החלפתם קוד החודש. המורה תעזור לכם עם קוד חדש.',e2paused:'היום אי אפשר לשחזר עם תמונות. המורה תעזור לכם עם קוד חדש, או נסו מחר.',
 gotOtc:'קיבלתי קוד מהמורה',e3h:'הקוד מהמורה',otcL:'6 ספרות',eOtc:'הקוד לא נכון או שפג תוקפו. בקשו מהמורה קוד חדש.',
 recDone:'הקוד החדש מוכן!',recDoneT:'בטלפונים ובמחשבים אחרים תצטרכו להיכנס שוב עם הקוד החדש.',
 // NEW (not in docs/SIGNIN.md; for the teacher's review)
 eNet:'אין חיבור כרגע. בדקו את האינטרנט ונסו שוב.',
 // review of #117: the project answered 404 (its sign-in is not set up yet), and the way back from a trial device
 eUnset:'המערכת החדשה עוד לא מוכנה. אפשר לחזור למשחק הרגיל ולנסות שוב בהמשך.',trial:'מצב ניסיון · חזרה למשחק הרגיל',eFull:'אי אפשר להירשם לכיתה הזאת כרגע. בקשו מהמורה.',busy:'רגע…',
 slot:(k,w)=>w?`תמונה ${k===1?'ראשונה':'שנייה'}: ${w}. הקישו כדי להוריד`:`משבצת ${k}, ריקה`,picked:(w,k)=>`${w}, נבחרה ${k===1?'ראשונה':'שנייה'}`,
 dot:k=>`תמונה ${k===1?'ראשונה':'שנייה'} נבחרה. הקישו כדי להוריד`,del:'מחיקה',
 waitTeacher:'הכניסה עוצרת. בקשו מהמורה לשחרר אותה.',sysRec:'אי אפשר לשחזר את הקוד כרגע. נסו שוב מאוחר יותר, או בקשו מהמורה קוד חדש.',
 namesOff:'🔈 להשמיע את שמות התמונות',namesOn:'🔊 שמות התמונות נשמעים (באוזניות)'
};
/* the waits (docs/SIGNIN.md "Waits"): by / help from the server; anything unknown reads as the last line. {N} minutes,
   {T} the clock time (HH:MM). wait −1 means "until the teacher": no time is shown. */
const WAITS={
 'name/teacher':'הכניסה בשם הזה נעצרה ל-{N} דקות. בינתיים אפשר ללחוץ "שכחתי את הקוד", או לבקש מהמורה לשחרר.',
 'name/teacher/-1':'הכניסה בשם הזה נעצרה. בקשו מהמורה לשחרר אותה.',
 'device/teacher':'הכניסה מהמכשיר הזה נעצרה עד {T}. אפשר להיכנס ממכשיר אחר, או לבקש מהמורה לשחרר.',
 'address/teacher':'זה לא בגללכם: הכניסה מהמחשבים כאן עוצרת לכולם עד {T}. אפשר לבקש מהמורה לשחרר. מי שכבר מחובר ממשיך לשחק.',
 'address/wait':'זה לא בגללכם: הכניסה מכאן עוצרת לכולם עד {T}. נסו שוב אז.',
 'class/teacher':'זה לא בגללכם: הכניסה לכיתה עוצרת עד {T}. אפשר לבקש מהמורה לשחרר.',
 'everyone/wait':'יש עכשיו עומס. נסו שוב ב-{T}.',
 'system/wait':'אי אפשר להירשם כרגע. נסו שוב מאוחר יותר. מי שכבר רשום יכול להיכנס.',
 '':'הכניסה עוצרת לכמה דקות. נסו שוב ב-{T}.'
};
const BY=['name','device','address','class','everyone','system'];
export function waitText(r,now=Date.now(),flow=''){
 const w=Number(r&&r.wait),by=BY.includes(r&&r.by)?r.by:'',help=r&&r.help==='teacher'?'teacher':'wait';   // anything else reads as the generic line
 let t=w<0&&WAITS[`${by}/${help}/-1`]||WAITS[`${by}/${help}`]||WAITS[''];
 if(t===WAITS['system/wait']&&flow==='rec')t=T.sysRec;
 if(w<0&&/\{[NT]\}/.test(t))return help==='teacher'?T.waitTeacher:flow==='rec'?T.sysRec:WAITS['system/wait'];   // no time to show
 const s=Number.isFinite(w)&&w>0?w:300,at=new Date(now+s*1000);
 return t.replace('{N}',String(Math.max(1,Math.ceil(s/60)))).replace('{T}',String(at.getHours()).padStart(2,'0')+':'+String(at.getMinutes()).padStart(2,'0'))}

/* the same rule as the server (supabase/functions/_shared/validate.ts isWeakCode, docs/BACKEND.md 4.2), so a weak
   code is caught on A2 and not after the whole registration. The server checks again. */
const KEYPAD=new Set(['2580','0852','1470','0741','3690','0963','1357','2468','9753','8642','1379','7913','1397','2684']);
const DAYS=[31,29,31,30,31,30,31,31,30,31,30,31],isDate=(d,m)=>m>=1&&m<=12&&d>=1&&d<=DAYS[m-1];
export function weak(code){const d=[...code].map(Number),step=(d[1]-d[0]+10)%10;
 const run=(step===1||step===9)&&(d[2]-d[1]+10)%10===step&&(d[3]-d[2]+10)%10===step,a=+code.slice(0,2),b=+code.slice(2);
 return(d[0]===d[1]&&d[1]===d[2]&&d[2]===d[3])||run||(d[0]===d[2]&&d[1]===d[3])||(d[0]===d[1]&&d[2]===d[3])||code.startsWith('19')||code.startsWith('20')||isDate(a,b)||isDate(b,a)||KEYPAD.has(code)}
const normC=x=>String(x||'').trim().toUpperCase(),normN=x=>String(x||'').normalize('NFC').trim().replace(/\s+/g,' ');
/* the name in a 'first_initial' class is `${first} ${letter}.` (docs/GRADES_V1.md 0011); a 'first' class (the trial)
   takes the first name alone, so the letter goes only when one was typed. The box: one Hebrew letter (a final form is
   written as its plain one: an initial is never final) or one Latin letter, as a capital; then, only as the teacher's
   list has it for two pupils of the same name and letter, one digit 2-9 ("כ2"). Never a second letter: one letter of
   the surname is the owner's rule */
const FINAL={'ך':'כ','ם':'מ','ן':'נ','ף':'פ','ץ':'צ'};
const LET=ch=>{if(FINAL[ch])return FINAL[ch];if(ch>='א'&&ch<='ת')return ch;const u=ch.toUpperCase();return u.length===1&&u>='A'&&u<='Z'?u:''};
export function letter(s){let l='',d='';for(const c of String(s??'').normalize('NFC')){const L=LET(c);
 if(!l){if(L)l=L}else if(c>='2'&&c<='9'){d=c;break}}return l+d}
const isHe=c=>c>='א'&&c<='ת';
/* the letter takes the name's script (a Hebrew name, a Hebrew letter): false when they differ */
export function sameScript(first,l){const f=[...String(first||'')].find(c=>isHe(c)||LET(c)),k=[...String(l||'')][0];return!f||!k||isHe(f)===isHe(k)}
/* first name and letter as they will be sent: a two-word first name is written with a hyphen (בת-אל); a letter typed
   into the first name ("נועה כ." with the letter field empty) moves to its field */
export function whoName(first,let1){let f=normN(first),l=letter(let1);
 if(!l){const w=f.split(' '),t=w.length>1?w[w.length-1]:'',u=t.endsWith('.')?t.slice(0,-1):t;
  const cs=[...u];if((cs.length===1||(cs.length===2&&cs[1]>='0'&&cs[1]<='9'))&&letter(u).length===u.length){l=letter(u);f=w.slice(0,-1).join(' ')}}
 while(f.endsWith('.'))f=f.slice(0,-1).trim();
 let h='';for(const c of f)h+=c===' '?'-':c;
 return{f:h,l,n:l?`${h} ${l}.`:h}}
/* no regular expression ever runs on a code, a one-time code or a class code (docs/LESSONS.md 17: it would stay in
   RegExp.$_): escaping and the digit filter go character by character */
const ESC={'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
const esc=s=>{let o='';for(const c of String(s??''))o+=ESC[c]||c;return o};
const digits=(s,n)=>{let o='';for(const c of String(s)){if(c>='0'&&c<='9'&&o.length<n)o+=c}return o};
const classOk=c=>{if(c.length<4||c.length>16)return false;for(const ch of c)if(!((ch>='A'&&ch<='Z')||(ch>='0'&&ch<='9')||ch==='-'))return false;return true};
function shuffle(){const a=PICS.map(p=>p.no),r=new Uint32Array(a.length);crypto.getRandomValues(r);
 for(let i=a.length-1;i>0;i--){const j=r[i]%(i+1);[a[i],a[j]]=[a[j],a[i]]}return a}
const P=no=>PICS[no-1];

/* the screens of each flow, in order; a step number is the place in this list */
// A: 5 steps. E: 3 steps (E2 the pictures or E3 the teacher's code is step 2; the new code and pictures are step 3)
const STEPNO={reg:{a1:1,a2:2,a3:3,a4:4,a5:5},rec:{e1:1,e2:2,e3:2,a2:3,a3:3,a4:3,a5:3}};
const STEPS={reg:5,rec:3};

/* "זה לא אני": on the title and the map of a signed-in pupil in 'supabase' mode, whose device this is and a way out in
   one tap (docs/SIGNIN.md "Shared device and switching"). The device stays signed in after the browser is closed (a
   class computer included), so the next child sees the previous one's name here and signs them out. out() is the
   game's own sign-out (it refuses while progress is not saved yet, and says so). */
const NM={notMe:'זה לא אני · יציאה',q:'לצאת?',t:'ההתקדמות נשמרת. בפעם הבאה תצטרכו את השם ואת הקוד.',yes:'כן, לצאת',no:'נשארים',hint:'במחשב משותף, תמיד יוצאים בסוף.'};
export function notMe(host,o){
 for(const h of['css/ds.css','css/signin.css'])if(!document.querySelector(`link[href="${h}"]`)){const l=document.createElement('link');l.rel='stylesheet';l.href=h;document.head.appendChild(l)}
 const old=host.querySelector('.si-who');if(old)old.remove();
 const box=document.createElement('div');box.className='si-who wi-root'+(o.inline?' si-who--in':'');box.dir='rtl';
 /* the pill of docs/SIGNIN.md "Who is playing": (the avatar,) the name, a dot, the button. The name in one <bdi> (a Latin
    name stays LTR); when space is short only the first name is cut, never the letter ("Alexandri… K.") */
 const n=String(o.name??''),k=n.lastIndexOf(' '),tail=k>0&&n.endsWith('.')&&[...n.slice(k+1)].length<=3?n.slice(k+1):'';
 const nm=tail?`<span class="si-fn">${esc(n.slice(0,k))}</span><span class="si-ln">&nbsp;${esc(tail)}</span>`:`<span class="si-fn">${esc(n)}</span>`;
 box.innerHTML=`${o.av?`<img class="si-av" src="${esc(o.av)}" alt="" width="36" height="36">`:''}<bdi class="si-hi">${nm}</bdi><span class="si-sep" aria-hidden="true">·</span><button type="button" class="wi-btn wi-btn--quiet si-nm" data-sw="ask">${NM.notMe}</button>`;
 let ov=null;const close=()=>{if(ov){ov.remove();ov=null}};
 box.addEventListener('click',e=>{const b=e.target.closest('[data-sw]');if(!b)return;
  if(b.dataset.sw==='ask'){close();ov=document.createElement('div');ov.className='si-ov wi-root';ov.dir='rtl';
   ov.innerHTML=`<div class="wi-card si-card" role="dialog" aria-modal="true" aria-labelledby="si-q"><h3 class="si-h" id="si-q" tabindex="-1">${NM.q}</h3><p class="si-txt">${NM.t}</p>
    <div class="si-row"><button type="button" class="wi-btn" data-sw="yes">${NM.yes}</button><button type="button" class="wi-btn wi-btn--secondary" data-sw="no">${NM.no}</button></div><p class="si-hint">${NM.hint}</p></div>`;
   box.appendChild(ov);ov.querySelector('.si-h').focus()}
  else if(b.dataset.sw==='no')close();
  else if(b.dataset.sw==='yes'){close();try{o.out()}catch(x){}}});
 host.appendChild(box);return box}

export function mount(root,o){
 // pics: the pair being chosen (A3); rec: the taps of the recall step (A5); proof: the old pair typed in recovery (E2)
 const st={flow:'',scr:'entry',c:o.lastC||'',n:'',l:'',needL:false,p:'',p2:'',pics:[],rec:[],proof:[],otc:'',err:'',hint:'',busy:false,
  shown:{},order:null,misses:0,closed:false,saidOrder:false,names:false};
 let alive=true,audio=null;
 const css=['css/ds.css','css/signin.css'].filter(h=>!document.querySelector(`link[href="${h}"]`)).map(h=>{const l=document.createElement('link');l.rel='stylesheet';l.href=h;document.head.appendChild(l);return l});
 const say=src=>{if(!o.sound||!o.sound())return;try{if(audio)audio.pause();audio=new Audio(src);audio.play().catch(()=>{})}catch(e){}};
 const wipe=()=>{st.p=st.p2=st.otc='';st.pics=[];st.rec=[];st.proof=[]};
 /* ---------- parts ---------- */
 const top=()=>{const f=st.flow,n=f&&STEPNO[f][st.scr];
  return`<div class="si-top"><button type="button" class="wi-btn wi-btn--quiet si-back" data-si="back" aria-label="${T.back}">→</button>${n?`<span class="si-prog">${T.step(n,STEPS[f])}</span>`:''}</div>`};
 const head=t=>`<h2 class="si-h" tabindex="-1">${t}</h2>`;
 const err=()=>st.err?`<p class="si-err" role="alert">${esc(st.err)}</p>`:'';
 const bar=(label,act,on=true,extra='')=>`<div class="si-bar">${extra}<button type="button" class="wi-btn wi-btn--block" data-si="${act}" ${on&&!st.busy?'':'disabled'}>${st.busy?T.busy:label}</button></div>`;
 /* the name: two fields side by side (first name; one letter of the surname), and on A1 the name as it will appear */
 const nrow=as=>{const w=whoName(st.n,st.l);
  return`<div class="si-nrow"><div class="si-f si-fn"><label for="si-n">${T.firstL}</label><input id="si-n" data-sin="n" value="${esc(st.n)}" autocomplete="off" maxlength="20" aria-describedby="si-n-h"></div><div class="si-f si-lt"><label for="si-l">${T.letterL}</label><input id="si-l" data-sin="l" value="${esc(st.l)}" autocomplete="off" autocapitalize="characters" spellcheck="false" maxlength="2" aria-label="${T.letterA}" ${st.needL?'aria-required="true"':''} aria-describedby="si-n-h"></div></div><span class="si-hint" id="si-n-h">${sameScript(w.f,w.l)?T.nameH:T.eScript}</span>${as?`<p class="si-as" ${w.f?'':'hidden'}>${T.asIs}<b><bdi>${esc(w.n)}</bdi></b></p>`:''}`};
 const field=(id,label,hint,val,attrs='')=>`<div class="si-f"><label for="si-${id}">${label}</label>${hint?`<span class="si-hint" id="si-${id}-h">${hint}</span>`:''}<input id="si-${id}" data-sin="${id}" value="${esc(val)}" autocomplete="off" ${hint?`aria-describedby="si-${id}-h"`:''} ${attrs}></div>`;
 /* a code never goes into the screen's HTML (a string that may outlive the screen): the fields and boxes are drawn empty
    and filled through the DOM (fill) */
 const boxes=n=>'<span class="si-d"></span>'.repeat(n);
 const fill=id=>{const el=root.querySelector('#si-'+id);if(!el)return;if(el.value!==st[id])el.value=st[id];const v=st[id];
  const box=root.querySelector(`[data-box="${id}"]`);if(box)box.querySelectorAll('.si-d').forEach((s,i)=>{s.textContent=i<v.length?(st.shown[id]?v.charAt(i):'●'):''})};
 /* a code: one real input (numeric, LTR, nothing to save) drawn as boxes; and the keypad under it */
 const code=(id,label,n,val)=>`<div class="si-f"><label for="si-${id}">${label}</label><div class="si-pinrow" dir="ltr">
   <div class="si-pin" data-box="${id}"><input id="si-${id}" data-sin="${id}" class="si-pinin" inputmode="numeric" pattern="[0-9]*" maxlength="${n}" autocomplete="off" autocorrect="off" spellcheck="false" value="">${boxes(n)}</div>
   <button type="button" class="wi-btn wi-btn--quiet si-show" data-si="show" data-id="${id}" aria-pressed="${!!st.shown[id]}">${st.shown[id]?T.hide:T.show}</button></div></div>`;
 const keypad=()=>`<div class="si-pad" dir="ltr">${['1','2','3','4','5','6','7','8','9','','0','⌫'].map(k=>k?`<button type="button" class="si-key" data-si="key" data-k="${k}" ${k==='⌫'?`aria-label="${T.del}"`:''}>${k}</button>`:'<span></span>').join('')}</div>`;
 const tile=(no,secret)=>{const p=P(no),k=st.pics.indexOf(no)+1;
  return`<button type="button" class="si-tile" data-si="pick" data-no="${no}" aria-label="${p.he}" ${!secret&&k?`aria-describedby="si-picked-${no}"`:''}><img src="${p.img}" alt="" width="64" height="64" draggable="false"><span class="si-w">${p.he}</span>${!secret&&k?`<span class="si-vh" id="si-picked-${no}">${T.picked(p.he,k)}</span>`:''}</button>`};
 const slots=(arr,secret,big)=>`<div class="si-slots${big?' big':''}">${[1,2].map(k=>{const no=arr[k-1],p=no&&P(no);
  return`<button type="button" class="si-slot${no?' on':''}" data-si="slot" data-k="${k}" ${big?'disabled':''} aria-label="${no?(secret?T.dot(k):T.slot(k,p.he)):T.slot(k)}">${no?(secret?'<span class="si-dot"></span>':`<img src="${p.img}" alt="" width="56" height="56" draggable="false"><span class="si-w">${p.he}</span>`):`<span class="si-num">${k}</span>`}</button>`}).join('<span class="si-arr" aria-hidden="true">←</span>')}</div>`;
 const grid=secret=>`<div class="si-grid">${st.order.map(no=>tile(no,secret)).join('')}</div>`;
 /* ---------- screens ---------- */
 const S={
  entry:()=>`<div class="si-mid si-center"><h1 class="si-logo" tabindex="-1">${T.title}</h1></div>
   <div class="si-bar"><button type="button" class="wi-btn wi-btn--block" data-si="start" data-f="reg">${T.reg}</button>
   <button type="button" class="wi-btn wi-btn--block wi-btn--secondary" data-si="start" data-f="in">${T.have}</button>
   <button type="button" class="wi-btn wi-btn--quiet" data-si="start" data-f="rec">${T.forgot}</button>
   ${o.trial?`<a class="si-trial" href="?new=0#login">${T.trial}</a>`:''}</div>`,
  a1:()=>`${top()}${head(T.a1h)}<div class="si-mid">${field('c',T.classL,T.classH,st.c,'dir="ltr" class="si-en" autocapitalize="characters" maxlength="16"')}${nrow(true)}${err()}</div>${bar(T.next,'a1')}`,
  a2:()=>`${top()}${head(T.a2h)}<div class="si-mid"><p class="si-txt">${T.a2t}</p>${code('p',T.codeL,4,st.p)}${code('p2',T.code2L,4,st.p2)}${err()}${keypad()}</div>${bar(T.next,'a2',st.p.length===4&&st.p2.length===4)}`,
  a3:()=>`${top()}${head(T.a3h)}<button type="button" class="wi-btn wi-btn--quiet si-names" data-si="names" aria-pressed="${st.names}">${st.names?T.namesOn:T.namesOff}</button>${slots(st.pics)}<p class="si-hint si-c">${st.hint?esc(st.hint):T.a3hint}</p><div class="si-mid">${grid(false)}</div>${bar(T.next,'a3',st.pics.length===2)}`,
  a4:()=>{const[a,b]=st.pics.map(P);return`${top()}${head(T.a4h)}<div class="si-mid si-center">${slots(st.pics,false,true)}<p class="si-pair">${T.pair(a.he,b.he)}</p><p class="si-txt si-c">${T.a4say}</p><p class="si-txt si-c">${T.a4t}</p></div>${bar(T.a4b,'a4')}`},
  a5:()=>`${top()}${head(T.a5h)}<p class="si-txt">${T.a5t}</p>${slots(st.rec)}${err()}<div class="si-mid">${grid(true)}</div>${bar(T.next,'a5',st.rec.length===2)}`,
  done:()=>`<div class="si-mid si-center"><h2 class="si-h si-c" tabindex="-1">${st.flow==='rec'?T.recDone:T.regDone}</h2><p class="si-txt si-c">${st.flow==='rec'?T.recDoneT:T.regDoneT}</p></div>${bar(T.go,'go')}`,
  b:()=>`${top()}${head(T.bh)}<div class="si-mid">${field('c',T.classL,'',st.c,'dir="ltr" class="si-en" autocapitalize="characters" maxlength="16"')}${nrow(false)}${code('p',T.codeL,4,st.p)}${err()}${keypad()}
   <button type="button" class="wi-btn wi-btn--quiet si-link" data-si="start" data-f="rec">${T.forgot}</button></div>${bar(T.enter,'b')}`,
  e1:()=>`${top()}${head(T.e1h)}<div class="si-mid">${field('c',T.classL,'',st.c,'dir="ltr" class="si-en" autocapitalize="characters" maxlength="16"')}${nrow(false)}${err()}</div>${bar(T.next,'e1')}`,
  e2:()=>`${top()}${head(T.e2h)}${slots(st.proof,true)}${err()}<div class="si-mid">${st.closed?'':grid(true)}
   <button type="button" class="wi-btn wi-btn--quiet si-link" data-si="otc">${T.gotOtc}</button></div>${st.closed?'':bar(T.next,'e2',st.proof.length===2)}`,
  e3:()=>`${top()}${head(T.e3h)}<div class="si-mid">${code('otc',T.otcL,6,st.otc)}${err()}${keypad()}</div>${bar(T.next,'e3',st.otc.length===6)}`
 };
 let focusId='';
 function draw(){if(!alive)return;
  root.innerHTML=`<section class="si wi-root" dir="rtl" lang="he" data-scr="${st.scr}">${S[st.scr]()}</section>`;
  for(const id of['p','p2','otc'])fill(id);
  const f=focusId&&root.querySelector('#si-'+focusId)||root.querySelector('.si-h,.si-logo');if(f)f.focus({preventScroll:true})}
 /* a picture screen gets a new order each time it is entered (and each recovery try) */
 function to(scr,keep,fid){if(!keep){st.err='';st.hint=''}focusId=fid||'';
  st.scr=scr;if(scr==='a3'||scr==='a5'||scr==='e2')st.order=shuffle();
  if(scr==='a3'&&!st.saidOrder){st.saidOrder=true;say(LINE.order)}
  // A4 says nothing aloud: "אמרו את זה בלב" (a secret is not said aloud in a classroom); the old clip said the opposite
  draw()}
 const fail=(msg,scr,fid)=>{st.busy=false;st.err=msg;if(scr&&scr!==st.scr){to(scr,true,fid)}else{if(fid)focusId=fid;draw()}};
 /* the class takes first name + letter and the name sent was not in that form: back to the name, the letter field asked
    for, everything else kept (the server says so only once the class code is right) */
 const nameForm=(r,scr)=>{if(r.form==='first_initial')st.needL=true;return fail(st.needL&&!st.l?T.eLetter:T.eForm,scr,st.needL&&!st.l?'l':'n')};
 const nm=()=>whoName(st.n,st.l).n;
 const flowDone=()=>{st.busy=false;wipe()};
 /* the back arrow: the screen before this one in its flow (what was typed is kept) */
 function prev(){const s=st.scr,f=st.flow;
  if(s==='a1'||s==='b'||s==='e1')return'entry';
  if(s==='a2')return f==='reg'?'a1':st.otc?'e3':'e2';if(s==='e2')return'e1';if(s==='e3')return'e2';
  return{a3:'a2',a4:'a3',a5:'a4'}[s]||'entry'}
 /* ---------- the requests: one per flow, at its end ---------- */
 async function send(kind,f){st.busy=true;draw();let r;try{r=await o.enter(kind,f)}catch(e){r={ok:false,e:'net'}}
  if(!alive)return null;return r&&typeof r==='object'?r:{ok:false,e:'net'}}
 async function register(){const r=await send('register',{c:normC(st.c),n:nm(),code:st.p,pics:st.pics.slice()});if(!r)return;
  if(r.ok){flowDone();return to('done')}
  if(r.e==='locked')return fail(waitText(r));
  if(r.e==='weak'){st.p=st.p2='';return fail(T.eWeak,'a2')}
  if(r.e==='name')return nameForm(r,'a1');
  const m={class:[T.eClass,'a1'],roster:[T.eRoster,'a1'],taken:[T.eTaken,'a1'],full:[T.eFull,'a1'],input:[T.eRoster,'a1']}[r.e];
  return m?fail(m[0],m[1]):fail(r.e==='unset'?T.eUnset:T.eNet)}
 async function login(){const r=await send('login',{c:normC(st.c),n:nm(),code:st.p});if(!r)return;
  if(r.ok){flowDone();draw();return o.done()}
  if(r.e==='locked'){st.p='';return fail(waitText(r))}
  if(r.e==='class')return fail(T.eClass);
  if(r.e==='name')return nameForm(r);
  if(r.e==='pin'||r.e==='input'){st.p='';return fail(T.ePin)}
  return fail(r.e==='unset'?T.eUnset:T.eNet)}
 async function recover(){const byOtc=!!st.otc;
  const r=await send('recover',{c:normC(st.c),n:nm(),...(byOtc?{otc:st.otc}:{pics:st.proof.slice()}),newCode:st.p,newPics:st.pics.slice()});if(!r)return;
  if(r.ok){flowDone();return to('done')}
  if(r.e==='weak'){st.p=st.p2='';return fail(T.eWeak,'a2')}
  if(r.e==='otc'){st.otc='';return fail(T.eOtc,'e3')}
  // how many tries are left is the server's to know (it answers locked by name when the pictures are closed)
  if(r.e==='picture'){st.proof=[];return fail(T.e2wrong,'e2')}
  if(r.e==='locked'&&!byOtc&&(r.by==='name'||r.by==='class')){st.proof=[];st.closed=true;   // the pictures are closed for this name or paused for the class
   return fail(r.by==='class'?T.e2paused:Number(r.wait)<0?T.e2end:T.e2month,'e2')}
  if(r.e==='locked')return fail(waitText(r,Date.now(),'rec'));
  if(r.e==='class')return fail(T.eClass,'e1');
  if(r.e==='name')return nameForm(r,'e1');
  if(r.e==='input')return fail(T.eRoster,'e1');
  return fail(r.e==='unset'?T.eUnset:T.eNet)}
 /* ---------- what each button does ---------- */
 /* the fields are tidied to what will be sent (the hyphen, a letter moved to its field), so the child sees it */
 const nameOk=()=>{const c=normC(st.c),w=whoName(st.n,st.l);if(!classOk(c)){st.err=T.eClass;focusId='c';return false}
  st.n=w.f;st.l=w.l;
  if([...w.f].length<2){st.err=T.eRoster;focusId='n';return false}
  if(st.needL&&!w.l){st.err=T.eLetter;focusId='l';return false}
  if(!sameScript(w.f,w.l)){st.err=T.eScript;focusId='l';return false}return true};
 const A={
  start(d){st.flow=d.f==='in'?'':d.f;st.closed=false;st.misses=0;wipe();to(d.f==='reg'?'a1':d.f==='in'?'b':'e1')},
  back(){if(st.scr==='entry')return;const p=prev();if(p==='entry'){st.flow='';wipe()}to(p)},
  a1(){if(!nameOk())return draw();to('a2')},
  a2(){if(st.p!==st.p2){st.p2='';focusId='p2';st.err=T.eDiff;return draw()}
   if(weak(st.p)){st.p=st.p2='';focusId='p';st.err=T.eWeak;return draw()}
   to('a3')},                                             // pictures already chosen stay (the back arrow and a refusal keep what was done)
  a3(){if(st.pics.length===2){st.rec=[];st.misses=0;to('a4')}},
  a4(){st.rec=[];to('a5')},
  a5(){if(st.rec.length!==2)return;
   if(st.rec[0]===st.pics[0]&&st.rec[1]===st.pics[1]){st.err='';return st.flow==='reg'?register():recover()}
   st.rec=[];st.misses++;if(st.misses>=3){st.misses=0;st.pics=[];to('a3');st.hint=T.a5new;return draw()}
   st.order=shuffle();st.err=T.a5miss;draw()},
  b(){st.flow='';if(!nameOk())return draw();if(st.p.length!==4){st.err=T.ePin;focusId='p';return draw()}login()},
  e1(){if(!nameOk())return draw();st.proof=[];st.otc='';to('e2')},
  e2(){if(st.proof.length===2){st.otc='';to('a2')}},              // a new code typed on an earlier try stays
  otc(){st.proof=[];to('e3')},
  e3(){if(st.otc.length===6)to('a2')},
  go(){o.done()},
  names(){st.names=!st.names;draw()},
  show(d){st.shown[d.id]=!st.shown[d.id];focusId=d.id;draw()},
  key(d){const id=focusId&&['p','p2','otc'].includes(focusId)?focusId:['p','p2','otc'].find(k=>root.querySelector('#si-'+k)&&st[k].length<(k==='otc'?6:4))||['p','p2','otc'].find(k=>root.querySelector('#si-'+k));
   if(!id)return;const n=id==='otc'?6:4;st[id]=d.k==='⌫'?st[id].slice(0,-1):(st[id]+d.k).slice(0,n);
   if(d.k!=='⌫'&&st[id].length===n&&id==='p'&&root.querySelector('#si-p2'))focusId='p2';else focusId=id;st.err='';draw()},
  // a picture's name is said only when the child turned the names on (A3 only): said aloud in a classroom, the pair is no secret
  pick(d){const no=+d.no,secret=st.scr!=='a3',arr=st.scr==='a3'?st.pics:st.scr==='e2'?st.proof:st.rec;if(!secret&&st.names)say(P(no).vox);
   if(arr.includes(no)||arr.length>=2)return;arr.push(no);if(st.scr==='a5'||st.scr==='e2')st.err='';draw()},
  slot(d){const arr=st.scr==='a3'?st.pics:st.scr==='e2'?st.proof:st.rec,k=+d.k-1;if(arr[k]==null)return;arr.splice(k,1);draw()}
 };
 const onClick=e=>{const el=e.target.closest('[data-si]');if(!el||!root.contains(el)||el.disabled)return;const f=A[el.dataset.si];if(f&&!st.busy)f(el.dataset)};
 const onInput=e=>{const el=e.target,id=el.dataset&&el.dataset.sin;if(!id)return;
  if(id==='p'||id==='p2'||id==='otc'){const n=id==='otc'?6:4,v=digits(el.value,n);if(v!==el.value)el.value=v;st[id]=v;
   fill(id);
   const btn=root.querySelector('.si-bar [data-si]');if(btn&&(st.scr==='a2'||st.scr==='e3'))btn.disabled=!(st.scr==='a2'?st.p.length===4&&st.p2.length===4:st.otc.length===6);
   if(id==='p'&&v.length===4&&root.querySelector('#si-p2')&&!st.p2)root.querySelector('#si-p2').focus();return}
  if(id==='l'){const v=letter(el.value);if(v!==el.value)el.value=v}
  st[id]=el.value;
  if(id==='n'||id==='l'){const w=whoName(st.n,st.l),as=root.querySelector('.si-as'),h=root.querySelector('#si-n-h');
   if(as){as.hidden=!w.f;as.querySelector('bdi').textContent=w.n}if(h)h.textContent=sameScript(w.f,w.l)?T.nameH:T.eScript}};
 const onFocus=e=>{const id=e.target.dataset&&e.target.dataset.sin;if(id)focusId=id};
 const onKey=e=>{if(e.key!=='Enter'||!e.target.dataset||!e.target.dataset.sin)return;e.preventDefault();const b=root.querySelector('.si-bar .wi-btn--block:not([disabled])');if(b)b.click()};
 /* the page is left (a link, Back, closing the tab) or hidden for a minute: every secret is forgotten and the flow starts
    again, so Back from the back-forward cache, or the next child at the screen, finds no code typed and no picture
    chosen ("הצגה" has nothing to show) */
 let hidT=0;
 const forget=()=>{clearTimeout(hidT);if(!alive)return;wipe();st.n=st.l='';st.needL=false;st.shown={};st.flow='';st.err='';st.hint='';st.closed=false;st.busy=false;focusId='';
  root.querySelectorAll('input').forEach(i=>{i.value=''});st.scr='entry';draw()};
 const onHide=()=>forget();
 const onVis=()=>{clearTimeout(hidT);if(document.visibilityState==='hidden')hidT=setTimeout(forget,60000)};
 addEventListener('pagehide',onHide);document.addEventListener('visibilitychange',onVis);
 root.addEventListener('click',onClick);root.addEventListener('input',onInput);root.addEventListener('change',onInput);root.addEventListener('focusin',onFocus);root.addEventListener('keydown',onKey);
 draw();
 /* the flow ends (the game moves on): every secret is wiped and the listeners go */
 return{destroy(){clearTimeout(hidT);removeEventListener('pagehide',onHide);document.removeEventListener('visibilitychange',onVis);
  root.querySelectorAll('input').forEach(i=>{i.value=''});alive=false;wipe();st.c=st.n=st.l='';if(audio){try{audio.pause()}catch(e){}}audio=null;
  root.removeEventListener('click',onClick);root.removeEventListener('input',onInput);root.removeEventListener('change',onInput);root.removeEventListener('focusin',onFocus);root.removeEventListener('keydown',onKey);
  css.forEach(l=>l.remove())}}}
