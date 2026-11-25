/* The class backend, behind one call: api(action, data), the same calls the game has always made
   (register, login, save, board, teacher, reset) with the same answers.

   Which backend is chosen by window.BACKEND in config.js. With no such key (today) the mode is 'sheet' and this file
   does exactly what js/state.js did before it existed: one POST to the Google Sheet web app.
     window.BACKEND = {mode:'dual', url:'https://<project>.supabase.co', key:'<the public key>'}
   (optional: saveEveryS, how often at most a save goes to Supabase, 30 by default)
   'dual' (Phase 2 of docs/PLAN.md): the Sheet is asked first and its answer is the answer; afterwards, and only when
   the Sheet said ok, the same progress is copied to Supabase in the background. A failure there is never shown to
   the pupil, never slows the game, and is written to a small log on the device (shadowLog()).
   'supabase': the new backend alone. Not complete: it needs the sign-in screens with the secret pictures, so it is
   refused unless config.js also says unfinished: true.
   A mode that is not spelled exactly, or has no https project address and key, falls back to 'sheet'. */
const W=typeof window!=='undefined'?window:globalThis;
const SHEET=(W.API_URL||'').trim();
const B=W.BACKEND&&typeof W.BACKEND==='object'?W.BACKEND:{};
const URL_OK=typeof B.url==='string'&&/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(B.url)&&typeof B.key==='string'&&B.key.length>20;
// 'supabase' alone is not finished (see supa() below): it needs a second, deliberate key, so one mistyped word in
// config.js cannot switch the live class to it (review of #21, S-b)
export const MODE=URL_OK&&(B.mode==='dual'||(B.mode==='supabase'&&B.unfinished===true))?B.mode:'sheet';

/* exactly what js/state.js did: a failed request (no connection) throws; an answer that is not JSON (an Apps Script
   error page) gives {ok:false,e:'server'} */
async function sheet(a,d){const r=await fetch(SHEET,{method:'POST',body:JSON.stringify({a,...d}),keepalive:a==='save'});try{return await r.json()}catch(e){return{ok:false,e:'server'}}}

export async function api(a,d){
 if(MODE==='sheet')return sheet(a,d);
 if(MODE==='dual'){const r=await sheet(a,d);try{shadow(a,d,r)}catch(e){}return r}
 return supa(a,d)}

/* ---------- small storage helpers: everything Supabase-side lives under its own keys, never in the game's record ---------- */
const K={ses:'wi-sb-session',base:'wi-sb-base',pend:'wi-sb-pending',log:'wi-sb-log',stale:'wi-sb-stale',owner:'wi-sb-owner',stop:'wi-sb-stop'};
const get=k=>{try{return JSON.parse(localStorage.getItem(k))}catch(e){return null}};
const set=(k,v)=>{try{v==null?localStorage.removeItem(k):localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
/* what happened on the shadow side: time, a short kind, numbers. Never a name, a code or a token. */
function note(k,v){const l=get(K.log)||[];l.push({t:Date.now(),k,...(v||{})});set(K.log,l.slice(-80))}
export const shadowLog=()=>get(K.log)||[];
const uuid=()=>crypto.randomUUID?crypto.randomUUID():'10000000-1000-4000-8000-100000000000'.replace(/[018]/g,c=>(c^crypto.getRandomValues(new Uint8Array(1))[0]&15>>c/4).toString(16));

/* ---------- Supabase over plain fetch: no library to vendor ---------- */
const TIMEOUT=8000;
let hiding=false;      // a save sent while the page is being hidden goes with keepalive, so it survives the page
async function call(path,body,token){
 const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),TIMEOUT);
 // the new public key format (sb_publishable_) is not a JWT: it goes as apikey only; a bearer is a pupil's session
 const bearer=token||(B.key.startsWith('eyJ')?B.key:'');
 try{const r=await fetch(B.url+path,{method:'POST',signal:ctl.signal,keepalive:hiding,headers:{'content-type':'application/json',apikey:B.key,...(bearer?{authorization:'Bearer '+bearer}:{})},body:JSON.stringify(body)});
  let j=null;try{j=await r.json()}catch(e){}return{status:r.status,j}}
 finally{clearTimeout(t)}}
const fn=(name,body)=>call('/functions/v1/'+name,body);
/* the session: access token (an hour), refresh token, the device token the server handed out. The 4-digit code is never here. */
async function token(){
 const s=get(K.ses);if(!s||!s.refresh_token)return null;
 if(s.access_token&&s.expires_at&&s.expires_at*1000-Date.now()>60000)return s.access_token;
 let r;try{r=await call('/auth/v1/token?grant_type=refresh_token',{refresh_token:s.refresh_token})}catch(e){return s.access_token||null}   // offline: keep what we have
 if(r.status===200&&r.j&&r.j.access_token){set(K.ses,{...s,access_token:r.j.access_token,refresh_token:r.j.refresh_token,expires_at:r.j.expires_at||Math.floor(Date.now()/1000)+(r.j.expires_in||3600)});return r.j.access_token}
 if(r.status>=400&&r.status<500){set(K.ses,{device_token:s.device_token});return null}   // the session was ended on the server: sign in again; local progress is untouched
 return s.access_token||null}
async function rpc(name,args){const t=await token();if(!t)return{status:401,j:null};return call('/rest/v1/rpc/'+name,args,t)}
function keep(j){const old=get(K.ses)||{};const s=j.session||{};
 set(K.ses,{access_token:s.access_token,refresh_token:s.refresh_token,expires_at:s.expires_at||Math.floor(Date.now()/1000)+(s.expires_in||3600),device_token:j.device_token||old.device_token,at:j.updated_at||null})}
async function signIn(d,extra){const dev=(get(K.ses)||{}).device_token;
 const r=await fn('pupil-login',{class_code:d.c,name:d.n,code:d.p,...(dev?{device_token:dev}:{}),...(extra||{})});
 if(r.j&&r.j.ok)keep(r.j);return r.j||{ok:false,e:'net'}}
export function signOut(){const s=get(K.ses)||{};set(K.ses,s.device_token?{device_token:s.device_token}:null);set(K.base,null);set(K.pend,null);set(K.stale,null);queued=null}   // this device only
/* Review of #21, B1: on a shared device the session must belong to the pupil whose progress is being saved. The device
   keeps a hash of class code and name (never the name itself); when another pupil's request comes, the old session is
   revoked on the server (best effort) and forgotten here before anything is sent. */
async function ownerOf(d){const t=String(d&&d.c||'').trim().toUpperCase()+'|'+String(d&&d.n||'').normalize('NFC').trim().replace(/\s+/g,' ').toLowerCase();
 const h=await crypto.subtle.digest('SHA-256',new TextEncoder().encode('wi-owner|'+t));return Array.from(new Uint8Array(h).slice(0,12),b=>b.toString(16).padStart(2,'0')).join('')}
async function dropSession(keepProgress){const s=get(K.ses)||{};
 if(s.access_token){try{await call('/auth/v1/logout?scope=local',{},s.access_token)}catch(e){}}   // the refresh token dies with it
 if(keepProgress)set(K.ses,s.device_token?{device_token:s.device_token}:null);   // the same pupil: only the session goes
 else signOut()}
/* For js/state.js (review of #21, B1): logout forgets everything of this pupil on the device and revokes the session
   on the server; relogin (the Sheet refused the pupil) drops only the session, so the same pupil's pending progress
   waits for them. With no session on the device (the Sheet mode of today) nothing is sent anywhere. */
export function forget(all){dropSession(!all).catch(()=>{})}
async function sameOwner(d){if(!d||!d.c||!d.n)return true;const h=await ownerOf(d),cur=get(K.owner);
 if(cur&&cur!==h){await dropSession();set(K.stop,null)}
 set(K.owner,h);return h}

/* ---------- typed events out of two saves ----------
   The game still saves one record (pack() in js/state.js). Until every game reports its events itself, the adapter
   reads them off the difference between the last record the server took and this one. What it can see:
   word answers (st: [tries, wrong]), a level's stars going up (g.st, m.st), a text read perfectly (read + k.reads),
   a finished mock exam (x.tries). What it cannot see is listed in docs/BACKEND.md section 8 (the gap per source). */
const num=x=>+x||0,obj=x=>x&&typeof x==='object'&&!Array.isArray(x)?x:{};
export function events(prev,next){
 const ev=[],p=obj(prev),n=obj(next),now=Date.now();
 const ps=obj(p.st),ns=obj(n.st);
 for(const w in ns){const a=Array.isArray(ns[w])?ns[w]:[],b=Array.isArray(ps[w])?ps[w]:[];
  const tries=Math.min(50,Math.max(0,num(a[0])-num(b[0]))),wrong=Math.min(tries,Math.max(0,num(a[1])-num(b[1])));
  for(let i=0;i<tries;i++)ev.push({type:'answer',game:'en',item:w,correct:true,first_try:i>=wrong,t:now})}
 for(const[g,key]of[['en','g'],['math','m']]){const a=obj(obj(n[key]).st),b=obj(obj(p[key]).st);
  for(const l in a){const s=Math.min(3,Math.floor(num(a[l])));if(s>Math.floor(num(b[l])))ev.push({type:'level',game:g,level:l,stars:s})}}
 if(num(obj(n.k).reads)>num(obj(p.k).reads)){const a=obj(n.read),b=obj(p.read);for(const id in a)if(num(a[id])>num(b[id]))ev.push({type:'read',text:id})}
 const seen=new Set((Array.isArray(obj(p.x).tries)?p.x.tries:[]).map(t=>t&&t.at));
 for(const t of Array.isArray(obj(n.x).tries)?n.x.tries:[])if(t&&!seen.has(t.at)&&Array.isArray(t.total))ev.push({type:'exam',paper:'mock',right:Math.max(0,Math.floor(num(t.total[0])))});
 return ev.slice(0,200)}

/* ---------- writing a save to Supabase (shared by 'dual' and 'supabase') ----------
   Order matters for "never counted twice": the batch gets its id and is stored on the device BEFORE it is sent; if the
   answer is lost, the same batch with the same id goes again and the server ignores the repeat. */
async function writeSave(s,overwrite){
 let pend=get(K.pend);
 if(!pend){const base=get(K.base),ev=base?events(base,s):[];   // the first save on a device has nothing to compare with: it sets the base
  pend={id:uuid(),ev,next:s};set(K.pend,pend)}
 const ses=get(K.ses)||{};
 let r=await rpc('save_progress',{p_state:s,p_base:ses.at||null});
 if(r.status===200&&r.j&&r.j.conflict){
  if(!overwrite)return{ok:false,conflict:true,state:r.j.state,at:r.j.updated_at};
  set(K.ses,{...ses,at:r.j.updated_at});r=await rpc('save_progress',{p_state:s,p_base:r.j.updated_at})}   // shadow: the Sheet is the truth
 // the server rations saves (5 s apart, 300 a day): not a failure, a "later" with the seconds to wait. The events still
 // go now (review of #21, B2): they do not depend on the blob, and held back they would meet the next day's caps.
 const later_=r.status===200&&r.j&&!r.j.ok&&(r.j.e==='wait'||r.j.e==='daycap')?{e:r.j.e,retry:Math.max(1,num(r.j.retry_after))}:null;
 if(!later_&&(r.status!==200||!r.j||!r.j.ok))return{ok:false,status:r.status};
 if(!later_)set(K.ses,{...(get(K.ses)||{}),at:r.j.updated_at});
 let points=null;
 if(pend.ev.length){const e=await rpc('record_events',{p_batch:pend.id,p_events:pend.ev});
  if(e.status===200&&e.j&&e.j.e==='brake'){note('brake');return{ok:false,e:'brake',saved:!later_,retry:Math.max(BRAKE_RETRY,later_?later_.retry:0)}}   // the database is full for now: the batch waits on the device
  if(e.status!==200||!e.j||!e.j.ok)return later_?{ok:false,...later_}:{ok:false,status:e.status,saved:true};
  points=e.j.points;if(e.j.flagged)note('flagged',{n:e.j.flagged})}
 set(K.base,pend.next);set(K.pend,null);
 return later_?{ok:false,...later_,points,events:pend.ev.length}:{ok:true,points,events:pend.ev.length}}

/* ---------- pacing the saves (review S8) ----------
   The game saves 2.5 s after every change; the server takes one write every 5 s and 300 a day per pupil. So only the
   newest state is kept here and written at most every SAVE_EVERY (30 s), and at once when the page is hidden. When
   the server answers "wait" or "daycap" (or "brake" for the events), the state is kept and tried again after the time
   it names. Nothing is lost: the newest state carries all of it, and the events wait in the pending batch. */
const SAVE_EVERY=1000*Math.max(0,B.saveEveryS===undefined||!Number.isFinite(+B.saveEveryS)?30:+B.saveEveryS);
const BRAKE_RETRY=600;
let queued=null,qOverwrite=true,lastWrite=0,holdUntil=0,timer=null,flushing=false;
function later(){clearTimeout(timer);timer=null;if(!queued)return;
 timer=setTimeout(()=>{flush(false).catch(()=>{})},Math.max(0,Math.max(lastWrite+SAVE_EVERY,holdUntil)-Date.now()))}
async function flush(hidden){
 if(!queued||flushing)return null;
 const now=Date.now();if(now<holdUntil||(!hidden&&now<lastWrite+SAVE_EVERY)){later();return null}
 if(!(get(K.ses)||{}).refresh_token)return null;        // no session (yet): the state waits, nothing is sent
 const s=queued;queued=null;lastWrite=now;flushing=true;hiding=!!hidden;
 let w;try{w=await writeSave(s,qOverwrite)}catch(e){w={ok:false,status:0}}finally{flushing=false;hiding=false}
 if(w.retry){if(!queued)queued=s;holdUntil=Date.now()+w.retry*1000}             // told to wait: keep it and try again
 else if(w.conflict&&!qOverwrite)set(K.stale,{state:w.state,at:w.at});           // 'supabase': the game joins at its next save
 if(MODE==='dual')note('save',{ok:w.ok?1:0,st:w.status||0,ev:w.events||0,...(w.e?{e:w.e}:{}),...(w.points!=null?{server:w.points}:{})});
 later();return w}
if(MODE!=='sheet'&&typeof W.addEventListener==='function'){
 const away=()=>{flush(true).catch(()=>{})};
 W.addEventListener('pagehide',away);
 if(typeof document!=='undefined')document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')away()})}

/* ---------- 'dual': the shadow copy. Runs after the Sheet answered; nothing here can reach the pupil. ---------- */
/* Sign-in on the shadow side (review of #21, S-a): only when there is no session for this pupil; never again the
   same day after the server said no (a pupil Supabase does not know would otherwise count as wrong codes from the
   school's one address and could pause sign-in for the whole class); after a network error at most every 10 minutes. */
let busy=false,netFail=null,waiting=null;
const today=()=>new Date().toISOString().slice(0,10);
function shadow(a,d,r){
 if(!r||!r.ok)return;                                   // the Sheet refused: nothing to copy
 if(a!=='login'&&a!=='register'&&a!=='save')return;     // the board, the teacher screen and reset stay on the Sheet
 if(busy){if(a==='save')waiting=d;return}             // after the run in progress, and checked for its owner like any other
 busy=true;
 (async()=>{try{
  const owner=await sameOwner(d);                       // another pupil on this device: the old session is gone first
  if(a==='save'){queued=d.s;qOverwrite=true}            // the newest state waits here until it may go
  if(!(await token())){
   const stop=get(K.stop);if(stop&&stop.owner===owner&&stop.day===today())return;
   if(netFail&&netFail.owner===owner&&Date.now()-netFail.at<600000)return;
   await dropSession(true);set(K.owner,owner);
   const j=await signIn(d);note('signin',{e:j.ok?'ok':String(j.e||'net').slice(0,12)});
   if(!j.ok){const s0=get(K.ses)||{};set(K.ses,s0.device_token?{device_token:s0.device_token}:null);if(!j.e||j.e==='net'||j.e==='server')netFail={owner,at:Date.now()};else set(K.stop,{owner,day:today()});return}
   if(a==='save')queued=d.s}
  if(a==='save'){note('sheet',{pts:num(d.s&&d.s.pts)});await flush(false)}
 }catch(e){note('error',{e:String(e&&e.name||'x').slice(0,20)})}finally{busy=false;if(waiting){const w=waiting;waiting=null;shadow('save',w,{ok:true})}}})()}

/* ---------- 'supabase': the new backend alone ----------
   NOT COMPLETE. It needs screens the game does not have yet (two secret pictures at registration, at the first
   sign-in of a pupil who came from the Sheet, and in "I forgot my code"), a teacher signed in with Google, and
   js/state.js no longer keeping the code (cred()). It is here so those can be built against real calls. */
async function supa(a,d){
 try{
  if(a==='login'){const j=await signIn(d,d.np?{new_code:d.np,pictures:d.pics}:null);return j.ok?{ok:true,s:j.s||{}}:{ok:false,e:j.e||'net',wait:j.wait}}
  if(a==='register'){const r=await fn('pupil-register',{class_code:d.c,name:d.n,code:d.p,pictures:d.pics});if(r.j&&r.j.ok){keep(r.j);return{ok:true,s:{}}}return{ok:false,e:(r.j&&r.j.e)||'net'}}
  if(a==='login'||a==='register'||a==='save')await sameOwner(d);
  if(a==='save'){if(!(await token()))return{ok:false,e:'pin'};   // no session: the game asks to sign in again and keeps the progress
   const st=get(K.stale);if(st){set(K.stale,null);set(K.ses,{...(get(K.ses)||{}),at:st.at});return{ok:false,e:'stale',s:st.state}}   // a kept save met another device's
   queued=d.s;qOverwrite=false;
   const w=await flush(false);
   if(!w||w.ok||w.retry)return{ok:true};                 // written, or kept here and sent within SAVE_EVERY or when the page is hidden
   if(w.conflict){set(K.stale,null);set(K.ses,{...(get(K.ses)||{}),at:w.at});return{ok:false,e:'stale',s:w.state}}   // another device saved first: join and save again
   return{ok:false,e:w.status===401?'pin':'net'}}
  if(a==='board'){const t=await token();if(!t)return{ok:false,e:'pin'};
   const r=await fetch(B.url+'/rest/v1/class_board?select=display_name,points,words,streak&order=points.desc',{headers:{apikey:B.key,authorization:'Bearer '+t}});
   if(!r.ok)return{ok:false,e:'net'};return{ok:true,rows:(await r.json()).map(x=>({n:String(x.display_name),pts:num(x.points),words:num(x.words),streak:num(x.streak)}))}}
  return{ok:false,e:'teacher'}                           // teacher and reset: after Google sign-in exists
 }catch(e){return{ok:false,e:'net'}}}
