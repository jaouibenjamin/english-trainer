/* teacher.html: the teacher's page (docs/PHASE3.md). Step 1: sign in with Google, sign out. Step 2: her class, read
   only. Step 3: her actions (a new code, unlock, the class list), each asked first and checked again by the server. The logic is in
   js/teacher_auth.js; this file only wires it to the page. Without a project in config.js the page says so and does
   nothing else: no request, no listener. The words are ours, for the teacher's review. */
import {teacherAuth,projectOf} from './teacher_auth.js';
/* captured as the module loads, before anything else on the page could replace it (pages of the owner's other
   projects share this origin) */
const FETCH=window.fetch,P=projectOf(window.BACKEND);
const $=s=>document.querySelector(s);
const SAY={
 off:'כניסת המורים עוד לא פועלת: המערכת החדשה עוד לא מחוברת.',
 framed:'פתחו את הדף הזה ישירות, בלשונית משלו.',
 out:'כניסה למורים בלבד, עם חשבון Google. במחשב משותף: היכנסו בחלון גלישה בסתר, ובסוף לחצו "יציאה" וסגרו את החלון (היציאה מכאן לא מוציאה מחשבון Google).',
 going:'מתחברים…',
 in:'מחוברים בתור',
 e:{flow:'הכניסה לא הושלמה. נסו שוב.',code:'הכניסה לא הושלמה. נסו שוב.',denied:'הכניסה בוטלה.',net:'אין חיבור לאינטרנט. נסו שוב.',
    idle:'יצאנו אוטומטית אחרי 30 דקות בלי פעילות.',expired:'החיבור פג. היכנסו שוב.',storage:'הדפדפן לא מאפשר כניסה (אחסון חסום).',
    path:'הכניסה פועלת רק מהכתובת של דף המורים.',stale:'',forbidden:'השרת סירב לחשבון הזה, ולכן יצאנו. אם זו טעות, פנו למנהל המערכת.'}};
/* the screen (docs/PHASE3.md step 2): read only for now, behind a switch this device gets with ?tsb=1 and loses with
   ?tsb=0. Every value is put in with textContent: pupils' names are text a child typed, never HTML. */
let tsb=false;
try{const q=new URLSearchParams(location.search).get('tsb');if(q==='1')localStorage.setItem('wi_tsb','1');else if(q==='0')localStorage.removeItem('wi_tsb');tsb=localStorage.getItem('wi_tsb')==='1'}catch(e){}
const STATUS=r=>[r.locked_today>0?`ננעל היום ${r.locked_today} פעמים`:'',r.code_status==='waiting'?'מחכה לקוד חדש':'',r.recovery_status==='closed'?'השחזור סגור':r.recovery_status==='locked'?'השחזור נעול לזמן קצר':'',r.flags_week>0?'לבדיקה':''].filter(Boolean).join(' · ');
const num=x=>Number.isFinite(+x)?String(Math.round(+x)):'0';
const txt=x=>x==null?'':String(x);                          // a missing name is empty, never "null"
function clearScreen(){const sc=$('#screen');if(!sc)return;sc.hidden=true;$('main').classList.remove('wide');$('#class tbody').replaceChildren();$('#hard').replaceChildren();$('#roster').replaceChildren();$('#removed').replaceChildren();$('#health').hidden=true;$('#health').textContent='';$('#quota').textContent='';$('#load').textContent='';$('#act').textContent=''}
function cell(tr,text,cls){const td=document.createElement('td');td.textContent=text;if(cls)td.className=cls;tr.append(td);return td}
function btn(text,onClick,cls){const b=document.createElement('button');b.type='button';b.className='small act'+(cls?' '+cls:'');b.textContent=text;b.disabled=busy;b.addEventListener('click',onClick);return b}
const byName=(a,b)=>txt(a).localeCompare(txt(b),'he');
function render(view,items,health,classes,roster,removed){
 const body=$('#class tbody'),hard=$('#hard');body.replaceChildren();hard.replaceChildren();
 for(const r of view.slice().sort((a,b)=>byName(a.display_name,b.display_name))){
  const tr=document.createElement('tr'),name=txt(r.display_name),id=String(r.pupil_id);
  cell(tr,name,'name');cell(tr,num(r.points),'num');cell(tr,num(r.answers),'num');cell(tr,num(r.error_pct)+'%','num');cell(tr,num(r.stars),'num');cell(tr,STATUS(r));
  const td=cell(tr,'','acts');td.append(btn('קוד חדש',()=>reset(id,name)));
  if(r.locked_today>0||r.recovery_status==='locked')td.append(btn('שחרור נעילה',()=>unlock(id,name)));
  td.append(btn('הוצאה מהכיתה',()=>takeOut(id,name)));
  body.append(tr)}
 renderRoster(classes,roster);renderRemoved(removed);
 for(const it of items.slice().sort((a,b)=>(+b.error_pct-+a.error_pct)||(+b.tries-+a.tries)).slice(0,10)){
  const li=document.createElement('li'),w=document.createElement('span');w.className='en';w.textContent=txt(it.item_key);
  li.append(w,document.createTextNode(` · ${num(it.wrong)} טעויות מתוך ${num(it.tries)} (${num(it.error_pct)}%)`));hard.append(li)}
 const h=health[0],warn=$('#health');warn.hidden=!(h&&h.warn);
 $('#quota').textContent=h&&Number.isFinite(+h.resets_cap)&&+h.resets_cap>0?`קודים חדשים ב־24 השעות האחרונות: ${num(h.resets_day)} מתוך ${num(h.resets_cap)}`:'';
 warn.textContent=h&&h.warn?'שימו לב: המערכת צריכה בדיקה (התחזוקה של הלילה לא רצה, או שהמאגר מתמלא). ספרו למנהל המערכת.':'';
 $('#load').textContent=view.length?'':'אין עדיין תלמידים בכיתה הזאת, או שהחשבון הזה אינו חשבון של מורה.'}
/* the class list (roster): who may register. Per class she teaches: the names, "remove" on each, a field to add one,
   and "unlock the whole class". Removing a name does not remove a pupil who already registered. */
function renderRoster(classes,roster){
 const box=$('#roster');box.replaceChildren();
 for(const c of classes.slice().sort((a,b)=>byName(a.name,b.name))){
  const cid=String(c.id),cname=txt(c.name),sec=document.createElement('section');sec.className='cls';
  const bar=document.createElement('div'),h=document.createElement('h3');bar.className='bar';h.textContent=`רשימת הכיתה ${cname}`;
  bar.append(h,btn('שחרור נעילות לכל הכיתה',()=>unlockClass(cid,cname)));
  const ul=document.createElement('ul');ul.className='names';
  for(const n of roster.filter(x=>String(x.class_id)===cid).sort((a,b)=>byName(a.display_name,b.display_name))){
   const li=document.createElement('li'),s=document.createElement('span'),name=txt(n.display_name),k=txt(n.name_key);
   s.textContent=name;li.append(s,btn('הסרה',()=>remove(cid,cname,k,name)));ul.append(li)}
  const add=document.createElement('div'),inp=document.createElement('input'),lab=document.createElement('label');add.className='add';
  inp.type='text';inp.maxLength=20;inp.autocomplete='off';inp.spellcheck=false;inp.id='add-'+cid;lab.htmlFor=inp.id;lab.textContent='שם פרטי או כינוי:';
  add.append(lab,inp,btn('הוספה לרשימה',()=>addName(cid,cname,inp)));
  sec.append(bar,ul,add);box.append(sec)}}
/* pupils taken out of the class: back with one tap for 14 days, then deleted for good by the server; or deleted for
   good now (a parent's request), after she types the name */
const day=t=>{const d=new Date(t);return Number.isFinite(d.getTime())?d.toLocaleDateString('he-IL',{timeZone:'Asia/Jerusalem',day:'numeric',month:'numeric'}):''};
function renderRemoved(rows){
 const box=$('#removed');box.replaceChildren();if(!rows.length)return;
 const h=document.createElement('h2');h.textContent='הוצאו מהכיתה';const ul=document.createElement('ul');ul.className='gone';
 for(const r of rows.slice().sort((a,b)=>byName(a.display_name,b.display_name))){
  const li=document.createElement('li'),s=document.createElement('span'),id=String(r.pupil_id),name=txt(r.display_name);
  s.textContent=`${name} · יימחק/תימחק לצמיתות ב־${day(r.purge_at)}`;
  li.append(s,btn('החזרה לכיתה',()=>bringBack(id,name)),btn('מחיקה לצמיתות',()=>forGood(id,name),'danger'));ul.append(li)}
 box.append(h,ul)}
let loading=0,auth=null;
async function load(){
 if(!tsb||!auth||!auth.signedIn())return;
 const my=++loading;$('#screen').hidden=false;$('main').classList.add('wide');$('#load').textContent='טוען…';
 const[v,i,h,c,ro,rm]=await Promise.all([auth.read('/rest/v1/teacher_view?select=pupil_id,class_id,display_name,points,answers,error_pct,stars,locked_today,code_status,recovery_status,flags_week'),
  auth.read('/rest/v1/teacher_items?select=item_key,tries,wrong,error_pct'),auth.read('/rest/v1/backend_health?select=warn,resets_day,resets_cap'),
  auth.read('/rest/v1/classes?select=id,name'),auth.read('/rest/v1/roster?select=class_id,name_key,display_name'),auth.read('/rest/v1/rpc/teacher_removed')]);
 if(my!==loading||!auth.signedIn()||!v||!i||!h||!c||!ro||!rm)return;   // signed out, left or another load since: nothing of it is shown
 if(v.error||i.error||h.error||c.error||ro.error||rm.error){$('#load').textContent='לא הצלחנו לטעון. נסו שוב.';return}
 render(v.rows,i.rows,h.rows,c.rows,ro.rows,rm.rows)}

/* Her actions (docs/PHASE3.md step 3). Each one: asked first (a dialog, "yes" or "cancel"), one at a time (busy), and
   sent with her token; the server checks again that the pupil or the class is hers (teacher-reset, row-level
   security on the class list). epoch is raised whenever the screen forgets her (sign-out, leaving, idle): an answer
   that comes back to another epoch is dropped, so nothing of hers reaches whoever is at the computer next. */
let epoch=0,busy=false;
const ERR={input:'הפעולה לא התקבלה. רעננו ונסו שוב.',forbidden:'הפעולה לא אושרה (התלמיד לא בכיתה שלך, או שהמערכת עוד בשלב הניסיון).',
 limit:'הנעילה כבר שוחררה פעמיים היום. אפשר לתת קוד חדש.',net:'אין חיבור לאינטרנט. נסו שוב.',server:'משהו השתבש. נסו שוב.'};
const fail=r=>r.status===0?ERR.net:r.j&&typeof r.j.e==='string'&&ERR[r.j.e]||ERR.server;
const say=t=>{$('#act').textContent=t};
function setBusy(b){busy=b;for(const x of document.querySelectorAll('button.act'))x.disabled=b}
/* typed: for what cannot be undone, "yes" waits until she has typed the pupil's name */
function ask(text,yes,typed){
 const d=$('#ask'),inp=$('#ask-type'),y=$('#ask-yes');$('#ask-text').textContent=text;y.textContent=yes;d.returnValue='';
 inp.value='';inp.hidden=!typed;$('#ask-type-label').hidden=!typed;y.disabled=!!typed;
 inp.oninput=typed?()=>{y.disabled=clean(inp.value)!==typed}:null;
 return new Promise(res=>{d.addEventListener('close',()=>{inp.oninput=null;inp.value='';res(d.returnValue==='yes'&&(!typed||!y.disabled))},{once:true});d.showModal();(typed?inp:$('#ask-no')).focus()})}
async function act(question,yes,run,typed){
 if(busy||!auth||!auth.signedIn())return;
 const e=epoch;setBusy(true);
 try{if(!await ask(question,yes,typed)||e!==epoch||!auth.signedIn())return;
  say('שולחים…');await run(e)}
 finally{if(e===epoch)setBusy(false)}}
/* a new code: the old one stops working. The six digits are shown once, in a dialog, and are kept nowhere else: not in
   storage, the address bar or the console, and no variable keeps them once the dialog is filled; closing the dialog,
   signing out, leaving the page or 10 minutes wipe them from the screen. */
/* six digits, checked without a regular expression: a regexp run on the code leaves it in the page's RegExp statics
   (RegExp.$_, RegExp.lastMatch) until the next match, readable from the console after the dialog is closed
   (review of #86, B4; docs/LESSONS.md entry 14) */
const sixDigits=x=>{if(typeof x!=='string'||x.length!==6)return false;for(let i=0;i<6;i++){const c=x.charCodeAt(i);if(c<48||c>57)return false}return true};
const CODE_MS=10*60000;
let shown=0,shownAt=0;
/* the 10 minutes are counted by the clock too: a timer sleeps with the laptop (S8) */
function codeClock(){if(shownAt&&Date.now()-shownAt>=CODE_MS)hideCode()}
function hideCode(){shown++;shownAt=0;const d=$('#code');$('#code-digits').textContent='';$('#code-name').textContent='';$('#code-exp').textContent='';if(d.open)d.close()}
function showCode(name,otc,exp){
 const my=++shown;shownAt=Date.now();$('#code-name').textContent=`הקוד החדש של ${name}:`;$('#code-digits').textContent=otc.slice(0,3)+' '+otc.slice(3);
 const t=new Date(exp);$('#code-exp').textContent=Number.isFinite(t.getTime())?'תקף עד '+t.toLocaleString('he-IL',{timeZone:'Asia/Jerusalem',weekday:'long',hour:'2-digit',minute:'2-digit'})+'. הקוד מוצג רק עכשיו: רשמו אותו ומסרו לתלמיד/ה.':'';
 $('#code').showModal();$('#code-done').focus();
 setTimeout(()=>{if(my===shown)hideCode()},CODE_MS)}
const reset=(id,name)=>act(`לתת ל${name} קוד חדש? הקוד הישן יפסיק לעבוד, והקוד החדש יוצג פעם אחת בלבד.`,'כן, קוד חדש',async e=>{
 const r=await auth.write('/functions/v1/teacher-reset',{action:'reset',pupil_id:id});
 if(!r||e!==epoch)return;
 if(r.status===200&&r.j&&r.j.ok===true&&sixDigits(r.j.otc)){say('');showCode(typeof r.j.name==='string'?r.j.name:name,r.j.otc,r.j.expires_at);r.j.otc='';load()}
 else say(r.j&&r.j.e==='limit'?'הגעתם למספר הקודים החדשים שמותר ב־24 שעות. אפשר שוב מחר (או לבקש ממנהל המערכת להגדיל אותו).':fail(r))});
const unlock=(id,name)=>act(`לשחרר את הנעילה של ${name}? אפשר לשחרר עד פעמיים ביום.`,'כן, לשחרר',async e=>{
 const r=await auth.write('/functions/v1/teacher-reset',{action:'unlock',pupil_id:id});
 if(!r||e!==epoch)return;
 if(r.status===200&&r.j&&r.j.ok===true){say(`הנעילה של ${name} שוחררה.`);load()}else say(fail(r))});
const unlockClass=(cid,cname)=>act(`לשחרר את הנעילות של כל הכיתה ${cname}?`,'כן, לכל הכיתה',async e=>{
 const r=await auth.write('/functions/v1/teacher-reset',{action:'unlock_class',class_id:cid});
 if(!r||e!==epoch)return;
 if(r.status===200&&r.j&&r.j.ok===true){say(`הנעילות של הכיתה ${cname} שוחררו.`);load()}else say(fail(r))});
/* out of the class, back, or deleted for good: hers only, checked again by the database (0009_soft_delete.sql) */
const rpc=(fn,id)=>auth.write('/rest/v1/rpc/'+fn,{p_pupil:id});
const takeOut=(id,name)=>act(`להוציא את ${name} מהכיתה? הוא/היא יוצא/ת מהמשחק מיד ולא יופיע/תופיע בטבלה. אפשר להחזיר תוך 14 יום, ואחר כך הכול נמחק לצמיתות.`,'כן, להוציא',async e=>{
 const r=await rpc('teacher_remove_pupil',id);
 if(!r||e!==epoch)return;
 if(r.status===200&&r.j&&r.j.ok===true){say(`${name} הוצא/ה מהכיתה. אפשר להחזיר עד ${day(r.j.purge_at)}.`);load()}
 else say(r.j&&r.j.e==='taken'?`כבר יש ברשימת המוצאים תלמיד/ה בשם ${name}. אפשר להחזיר או למחוק אותו/ה קודם.`:fail(r))});
const bringBack=(id,name)=>act(`להחזיר את ${name} לכיתה? כל הנקודות וההתקדמות חוזרות, והקוד הישן עובד.`,'כן, להחזיר',async e=>{
 const r=await rpc('teacher_restore_pupil',id);
 if(!r||e!==epoch)return;
 if(r.status===200&&r.j&&r.j.ok===true){say(`${name} חזר/ה לכיתה.`);load()}
 else say(r.j&&r.j.e==='taken'?`אי אפשר להחזיר: השם ${name} תפוס עכשיו בכיתה (נרשם/ה תלמיד/ה חדש/ה בשם הזה). הרשומה של מי שהוצא/ה נשארת ברשימת המוצאים עד ${day(r.j.purge_at)}, ואז נמחקת לצמיתות. אפשר גם למחוק אותה עכשיו.`
  :r.j&&r.j.e==='full'?'אי אפשר להחזיר: הכיתה מלאה.':r.j&&r.j.e==='gone'?`הרשומה של ${name} כבר נמחקה לצמיתות.`:fail(r))});
const forGood=(id,name)=>act(`למחוק את ${name} לצמיתות? כל מה ששמור עליו/עליה נמחק עכשיו, ואי אפשר לבטל. כדי לאשר, כתבו את השם:`,'מחיקה לצמיתות',async e=>{
 const r=await rpc('teacher_delete_pupil',id);
 if(!r||e!==epoch)return;
 if(r.status===200&&r.j===true){say(`${name} נמחק/ה לצמיתות.`);load()}else say(fail(r))},name);
/* the class list, through the database's own rules: a name she adds or removes is checked there (her class only, a
   valid first name, the key the database computes the same way: trimmed, inner spaces squeezed, lower-cased) */
const clean=n=>String(n).replace(/^ +| +$/g,'').replace(/\s+/g,' ');
function addName(cid,cname,inp){
 const name=clean(inp.value);if(!name){say('כתבו שם קודם.');return}
 return act(`להוסיף את "${name}" לרשימת הכיתה ${cname}? רק שמות שברשימה יכולים להירשם למשחק.`,'כן, להוסיף',async e=>{
  const r=await auth.write('/rest/v1/roster',{class_id:cid,name_key:name.toLowerCase(),display_name:name},'POST','return=minimal');
  if(!r||e!==epoch)return;
  if(r.status===201){inp.value='';say(`"${name}" נוסף/ה לרשימה.`);load()}
  else say(r.status===409?`"${name}" כבר ברשימה.`:r.status===400?'השם לא התקבל: רק אותיות (עברית או אנגלית), בלי ספרות וסימנים, עד 20 תווים.':r.status===403?ERR.forbidden:fail(r))})}
const remove=(cid,cname,key,name)=>act(`להסיר את "${name}" מרשימת הכיתה ${cname}? מי שכבר נרשם/ה ממשיך/ה לשחק, אבל השם לא יוכל להירשם מחדש.`,'כן, להסיר',async e=>{
 const r=await auth.write('/rest/v1/roster?class_id=eq.'+encodeURIComponent(cid)+'&name_key=eq.'+encodeURIComponent(key),undefined,'DELETE','return=representation');
 if(!r||e!==epoch)return;
 if(r.status===200&&Array.isArray(r.j)&&r.j.length===1){say(`"${name}" הוסר/ה מהרשימה.`);load()}
 else say(r.status===200?'השם כבר לא ברשימה.':fail(r))});
function show(state,user,why){
 const msg=$('#msg'),who=$('#who'),note=$('#note');
 $('#in').hidden=state!=='out';$('#out').hidden=state!=='in';$('#in').disabled=false;
 msg.textContent=SAY[state]||SAY.out;
 who.textContent=state==='in'&&user?user.email:'';
 note.textContent=why&&SAY.e[why]||'';
 if(state!=='in'){loading++;epoch++;setBusy(false);hideCode();const a=$('#ask');if(a&&a.open)a.close();clearScreen()}}
/* in a frame, or opened by another page that keeps a handle on it: the page refuses to run */
const framed=(()=>{try{return window.top!==window.self||!!window.opener}catch(e){return true}})();
/* the one address on the sign-in's redirect list is …/teacher.html; Pages also serves …/teacher */
if(/\/teacher$/.test(location.pathname))location.replace(location.origin+location.pathname+'.html'+location.search);
else if(!P)show('off');
else if(framed)show('framed');
else{
 let store=null;try{store=window.sessionStorage}catch(e){}
 auth=teacherAuth({url:P.url,key:P.key,fetch:(u,o)=>FETCH.call(window,u,o),crypto:window.crypto,location:window.location,history:window.history,
  store:store||{getItem:()=>null,setItem:()=>{throw new Error('no storage')},removeItem:()=>{}},
  now:()=>Date.now(),setTimeout:(f,ms)=>window.setTimeout(f,ms),clearTimeout:t=>window.clearTimeout(t),
  onOut:why=>show('out',null,why==='out'||why==='left'||why==='switch'?'':why)});
 $('#in').addEventListener('click',()=>{$('#in').disabled=true;auth.begin().then(r=>{if(r!=='going')show('out',null,r)})});
 $('#out').addEventListener('click',()=>{auth.signOut('out')});
 $('#reload').addEventListener('click',()=>{load()});
 $('#ask-yes').addEventListener('click',()=>$('#ask').close('yes'));
 $('#ask-no').addEventListener('click',()=>$('#ask').close('no'));
 $('#code-done').addEventListener('click',hideCode);
 $('#code').addEventListener('cancel',e=>{e.preventDefault()});     // Escape does not hide the code by accident: the button does
 for(const t of['pointerdown','keydown'])window.addEventListener(t,()=>{codeClock();auth.touch()},{passive:true});
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'){codeClock();auth.wake()}});
 /* and every 30 seconds: a laptop that wakes up with the page in front fires no event; neither the class nor a code may
    stay on the screen until the next person's first tap (re-review of #82 and #86) */
 window.setInterval(()=>{codeClock();auth.wake()},30000);
 window.addEventListener('pagehide',()=>{auth.left()});                       // leaving the page ends the session
 window.addEventListener('pageshow',e=>{if(e.persisted&&!auth.signedIn())show('out')});   // the back button shows nothing of her
 const back=new URLSearchParams(location.search).has('code');
 show(back?'going':'out');                                  // back from Google: no button until the exchange has answered
 auth.finish().then(r=>{show(r.state,r.user,r.e);if(r.state==='in')load()})}
