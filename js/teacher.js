/* teacher.html: the teacher's page (docs/PHASE3.md). Step 1: sign in with Google, sign out. The logic is in
   js/teacher_auth.js; this file only wires it to the page. Without a project in config.js the page says so and does
   nothing else: no request, no listener. The words are ours, for the teacher's review. */
import {teacherAuth,projectOf} from './teacher_auth.js';
const P=projectOf(window.BACKEND);
const $=s=>document.querySelector(s);
const SAY={
 off:'כניסת המורים עוד לא פועלת: המערכת החדשה עוד לא מחוברת.',
 out:'כניסה למורים בלבד, עם חשבון Google.',
 in:'מחוברים בתור',
 e:{flow:'הכניסה לא הושלמה. נסו שוב.',code:'הכניסה לא הושלמה. נסו שוב.',denied:'הכניסה בוטלה.',net:'אין חיבור לאינטרנט. נסו שוב.',
    idle:'יצאנו אוטומטית אחרי 30 דקות בלי פעילות.',expired:'החיבור פג. היכנסו שוב.',storage:'הדפדפן לא מאפשר כניסה (אחסון חסום).'}};
function show(state,user,why){
 const msg=$('#msg'),who=$('#who'),note=$('#note');
 $('#in').hidden=state!=='out';$('#out').hidden=state!=='in';
 msg.textContent=state==='off'?SAY.off:state==='in'?SAY.in:SAY.out;
 who.textContent=state==='in'&&user?user.email:'';
 note.textContent=why&&SAY.e[why]||''}
if(!P)show('off');
else{
 let store=null;try{store=window.sessionStorage}catch(e){}
 const auth=teacherAuth({url:P.url,key:P.key,fetch:(u,o)=>window.fetch(u,o),crypto:window.crypto,location:window.location,history:window.history,
  store:store||{getItem:()=>null,setItem:()=>{throw new Error('no storage')},removeItem:()=>{}},
  now:()=>Date.now(),setTimeout:(f,ms)=>window.setTimeout(f,ms),clearTimeout:t=>window.clearTimeout(t),
  onOut:why=>show('out',null,why==='out'||why==='left'||why==='switch'?'':why)});
 $('#in').addEventListener('click',()=>{auth.begin().then(r=>{if(r==='storage')show('out',null,'storage')})});
 $('#out').addEventListener('click',()=>{auth.signOut('out')});
 for(const t of['pointerdown','keydown'])window.addEventListener(t,()=>auth.touch(),{passive:true});
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')auth.wake()});
 window.addEventListener('pagehide',()=>{auth.left()});                       // leaving the page ends the session
 window.addEventListener('pageshow',e=>{if(e.persisted&&!auth.signedIn())show('out')});   // the back button shows nothing of her
 show('out');
 auth.finish().then(r=>show(r.state,r.user,r.e))}
