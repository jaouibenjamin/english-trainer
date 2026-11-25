/* teacher.html: the teacher's page (docs/PHASE3.md). Step 1: sign in with Google, sign out. The logic is in
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
function clearScreen(){const sc=$('#screen');if(!sc)return;sc.hidden=true;$('main').classList.remove('wide');$('#class tbody').replaceChildren();$('#hard').replaceChildren();$('#health').hidden=true;$('#health').textContent='';$('#load').textContent=''}
function cell(tr,text,cls){const td=document.createElement('td');td.textContent=text;if(cls)td.className=cls;tr.append(td)}
function render(view,items,health){
 const body=$('#class tbody'),hard=$('#hard');body.replaceChildren();hard.replaceChildren();
 for(const r of view.slice().sort((a,b)=>txt(a.display_name).localeCompare(txt(b.display_name),'he'))){
  const tr=document.createElement('tr');cell(tr,txt(r.display_name),'name');cell(tr,num(r.points),'num');cell(tr,num(r.answers),'num');cell(tr,num(r.error_pct)+'%','num');cell(tr,num(r.stars),'num');cell(tr,STATUS(r));body.append(tr)}
 for(const it of items.slice().sort((a,b)=>(+b.error_pct-+a.error_pct)||(+b.tries-+a.tries)).slice(0,10)){
  const li=document.createElement('li'),w=document.createElement('span');w.className='en';w.textContent=txt(it.item_key);
  li.append(w,document.createTextNode(` · ${num(it.wrong)} טעויות מתוך ${num(it.tries)} (${num(it.error_pct)}%)`));hard.append(li)}
 const h=health[0],warn=$('#health');warn.hidden=!(h&&h.warn);
 warn.textContent=h&&h.warn?'שימו לב: המערכת צריכה בדיקה (התחזוקה של הלילה לא רצה, או שהמאגר מתמלא). ספרו למנהל המערכת.':'';
 $('#load').textContent=view.length?'':'אין עדיין תלמידים בכיתה הזאת, או שהחשבון הזה אינו חשבון של מורה.'}
let loading=0;
async function load(auth){
 if(!tsb||!auth.signedIn())return;
 const my=++loading;$('#screen').hidden=false;$('main').classList.add('wide');$('#load').textContent='טוען…';
 const[v,i,h]=await Promise.all([auth.read('/rest/v1/teacher_view?select=display_name,points,answers,error_pct,stars,locked_today,code_status,recovery_status,flags_week'),
  auth.read('/rest/v1/teacher_items?select=item_key,tries,wrong,error_pct'),auth.read('/rest/v1/backend_health?select=warn')]);
 if(my!==loading||!auth.signedIn()||!v||!i||!h)return;           // signed out, left or another load since: nothing of it is shown
 if(v.error||i.error||h.error){$('#load').textContent='לא הצלחנו לטעון. נסו שוב.';return}
 render(v.rows,i.rows,h.rows)}
function show(state,user,why){
 const msg=$('#msg'),who=$('#who'),note=$('#note');
 $('#in').hidden=state!=='out';$('#out').hidden=state!=='in';$('#in').disabled=false;
 msg.textContent=SAY[state]||SAY.out;
 who.textContent=state==='in'&&user?user.email:'';
 note.textContent=why&&SAY.e[why]||'';
 if(state!=='in'){loading++;clearScreen()}}
/* in a frame, or opened by another page that keeps a handle on it: the page refuses to run */
const framed=(()=>{try{return window.top!==window.self||!!window.opener}catch(e){return true}})();
/* the one address on the sign-in's redirect list is …/teacher.html; Pages also serves …/teacher */
if(/\/teacher$/.test(location.pathname))location.replace(location.pathname+'.html'+location.search);
else if(!P)show('off');
else if(framed)show('framed');
else{
 let store=null;try{store=window.sessionStorage}catch(e){}
 const auth=teacherAuth({url:P.url,key:P.key,fetch:(u,o)=>FETCH.call(window,u,o),crypto:window.crypto,location:window.location,history:window.history,
  store:store||{getItem:()=>null,setItem:()=>{throw new Error('no storage')},removeItem:()=>{}},
  now:()=>Date.now(),setTimeout:(f,ms)=>window.setTimeout(f,ms),clearTimeout:t=>window.clearTimeout(t),
  onOut:why=>show('out',null,why==='out'||why==='left'||why==='switch'?'':why)});
 $('#in').addEventListener('click',()=>{$('#in').disabled=true;auth.begin().then(r=>{if(r!=='going')show('out',null,r)})});
 $('#out').addEventListener('click',()=>{auth.signOut('out')});
 $('#reload').addEventListener('click',()=>{load(auth)});
 for(const t of['pointerdown','keydown'])window.addEventListener(t,()=>auth.touch(),{passive:true});
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')auth.wake()});
 window.addEventListener('pagehide',()=>{auth.left()});                       // leaving the page ends the session
 window.addEventListener('pageshow',e=>{if(e.persisted&&!auth.signedIn())show('out')});   // the back button shows nothing of her
 const back=new URLSearchParams(location.search).has('code');
 show(back?'going':'out');                                  // back from Google: no button until the exchange has answered
 auth.finish().then(r=>{show(r.state,r.user,r.e);if(r.state==='in')load(auth)})}
