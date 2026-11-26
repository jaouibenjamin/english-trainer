/* The class backend, behind one call: api(action, data), the same calls the game has always made
   (register, login, save, board, teacher, reset) with the same answers.

   Which backend is chosen by window.BACKEND in config.js. With no such key (today) the mode is 'sheet' and this file
   does exactly what js/state.js did before it existed: one POST to the Google Sheet web app.
     window.BACKEND = {mode:'dual', url:'https://<project>.supabase.co', key:'<the public key>'}
   BEFORE switching it on: add that same https://<project>.supabase.co to connect-src in the Content-Security-Policy of
   every page (index, run, trainer, worksheet, world, ds). Without it the browser refuses every call to Supabase, and
   in 'dual' the refusals only reach shadowLog(), so nothing would look wrong. tests/csp_check.py fails until it is there.
   (optional: saveEveryS, how often at most a save goes to Supabase, 30 by default)
   'dual' (Phase 2 of docs/PLAN.md): the Sheet is asked first and its answer is the answer; afterwards, and only when
   the Sheet said ok, the same progress is copied to Supabase in the background. A failure there is never shown to
   the pupil, never slows the game, and is written to a small log on the device (shadowLog()).
   'supabase': the new backend alone (docs/PHASE3.md step 6): sign-in with the code once, then the session only; the
   record and the board from Supabase. Still refused unless config.js also says unfinished: true, until the pupil
   sign-in screens (step 5) are in; whichever of the two lands second removes that key.
   A mode that is not spelled exactly, or has no https project address and key, falls back to 'sheet'. */
const W=typeof window!=='undefined'?window:globalThis;
const SHEET=(W.API_URL||'').trim();
const B=W.BACKEND&&typeof W.BACKEND==='object'?W.BACKEND:{};
const URL_OK=typeof B.url==='string'&&/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(B.url)&&typeof B.key==='string'&&B.key.length>20;
// 'supabase' alone is not finished (see supa() below): it needs a second, deliberate key, so one mistyped word in
// config.js cannot switch the live class to it (review of #21, S-b)
/* One test device first, then the class (docs/LIVE_STAGE.md D3, F1). With a project in config.js, the default is a
   trial: only a device that opened the game once with ?dual=1 copies to Supabase; ?dual=0 turns it off again and ends
   that device's session. The class is turned on by one explicit key, everyone: true (exactly that name, exactly the
   value true). Anything else, a misspelt, cased or nested key or a value like 'true' or 1, keeps the class on the Sheet
   (K2b, review of #73: no typo can switch every pupil over); an old trial key changes nothing. Without a BACKEND key
   nothing is read. */
const EVERYONE=Object.prototype.hasOwnProperty.call(B,'everyone')&&B.everyone===true;
let tryOn=true,tryOff=false;
// the device switch: ?dual=1 for 'dual', ?new=1 for 'supabase' (docs/PHASE4.md A, "a plain trial switch")
const SW=B.mode==='supabase'?'new':'dual';
if(URL_OK&&!EVERYONE){tryOn=false;
 try{const q=new URLSearchParams(W.location&&W.location.search||'').get(SW);
  if(q==='1')W.localStorage.setItem('wi_'+SW,'1');else if(q==='0'){tryOff=true;W.localStorage.removeItem('wi_'+SW)}
  tryOn=W.localStorage.getItem('wi_'+SW)==='1'}catch(e){}}
export const MODE=URL_OK&&tryOn&&(B.mode==='dual'||(B.mode==='supabase'&&B.unfinished===true))?B.mode:'sheet';

/* exactly what js/state.js did: a failed request (no connection) throws; an answer that is not JSON (an Apps Script
   error page) gives {ok:false,e:'server'} */
async function sheet(a,d){const r=await fetch(SHEET,{method:'POST',body:JSON.stringify({a,...d}),keepalive:a==='save'});try{return await r.json()}catch(e){return{ok:false,e:'server'}}}

export async function api(a,d){
 if(MODE==='sheet')return sheet(a,d);
 if(MODE==='dual'){
  /* X1 (review of #50): the Sheet may answer late (a cold Apps Script); if the pupil logged out meanwhile (forget()
     raises epoch at once), the answer goes to the game as always but nothing is copied: the shadow would sign the
     pupil in again with this request's code and end the next pupil's session */
  /* G1 (review of #55): the game keeps and edits the objects it hands over and gets back (S.st is the answer's s.st,
     mark() adds to it), so the shadow works on copies taken now: what was sent, and what the Sheet answered */
  const e=epoch,dc=copy(d),save=a==='save'&&dc&&dc.c&&dc.n&&dc.s&&typeof dc.s==='object';
  const id=save?sending(dc):null,n=a==='save'?JSON.stringify({a,...d}).length:0;
  let r;keepBytes+=n;
  try{r=await sheet(a,d)}catch(x){if(id)sentDone(id,false);throw x}finally{keepBytes-=n}
  const rc=copy(r);
  if(id)sentDone(id,!!(rc&&rc.ok),e);
  try{if(e===epoch)shadow(a,dc,rc)}catch(x){}
  return r}
 return supa(a,d)}

/* ---------- small storage helpers: everything Supabase-side lives under its own keys, never in the game's record ---------- */
const K={ses:'wi-sb-session',base:'wi-sb-base',pend:'wi-sb-pending',log:'wi-sb-log',stale:'wi-sb-stale',owner:'wi-sb-owner',stop:'wi-sb-stop',netfail:'wi-sb-netfail',sent:'wi-sb-sent',sending:'wi-sb-sending'};
/* the page's storage and fetch, taken once (they never change in a browser; in the tests each copy keeps its own) */
const LS=(()=>{try{return W.localStorage||null}catch(e){return null}})(),FETCH=typeof W.fetch==='function'?W.fetch.bind(W):null;
const get=k=>{try{return JSON.parse(LS.getItem(k))}catch(e){return null}};
const set=(k,v)=>{try{v==null?LS.removeItem(k):LS.setItem(k,JSON.stringify(v))}catch(e){}};
const copy=x=>{try{return x==null?x:JSON.parse(JSON.stringify(x))}catch(e){return null}};   // raw: only op(), keep(), signOut() and note() call it
/* what happened on the shadow side: time, a short kind, numbers. Never a name, a code or a token. */
function note(k,v){const l=get(K.log)||[];l.push({t:Date.now(),k,...(v||{})});set(K.log,l.slice(-80))}
export const shadowLog=()=>get(K.log)||[];
const uuid=()=>crypto.randomUUID?crypto.randomUUID():'10000000-1000-4000-8000-100000000000'.replace(/[018]/g,c=>(c^crypto.getRandomValues(new Uint8Array(1))[0]&15>>c/4).toString(16));

/* ---------- Supabase over plain fetch: no library to vendor ---------- */
const TIMEOUT=8000;
// body undefined: a GET. keep: sent while the page is being hidden, with keepalive, so it survives the page
async function call(path,body,token,keep){
 const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),TIMEOUT);
 // the new public key format (sb_publishable_) is not a JWT: it goes as apikey only; a bearer is a pupil's session
 const bearer=token||(B.key.startsWith('eyJ')?B.key:'');
 try{const r=await FETCH(B.url+path,{method:body===undefined?'GET':'POST',signal:ctl.signal,keepalive:!!keep,headers:{...(body===undefined?{}:{'content-type':'application/json'}),apikey:B.key,...(bearer?{authorization:'Bearer '+bearer}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
  let j=null;try{j=await r.json()}catch(e){}return{status:r.status,j}}
 finally{clearTimeout(t)}}
const fn=(name,body)=>call('/functions/v1/'+name,body);   // the public key only, never a session

/* ---------- the one guard (reviews of #41 and #50) ----------
   Who the device belongs to is three things: gen, raised in this page whenever a session is let go (another pupil,
   logout); sid, a random id keep() writes into the stored session (a refresh keeps it; every tab sees it); and own,
   the owner mark (a hash of class code and name, wi-sb-owner; every tab sees it). An operation takes an op() when it
   starts, which remembers all three; sid alone is not enough, since "no session yet" (null) is the same for every
   pupil (X3). Every read of the token, every call made with it, and every write of the session, the base, the pending
   batch, the stale record, the sent record, the owner marks and the queue goes through that op, which refuses (writes
   nothing, sends nothing, its token is null) once any of the three changed. The data is bound to the pupil as well:
   the queue holds the owner it was queued for and is handed only to an op of the same owner (X2); the sent record
   holds its owner too. The only other writers are keep() (called by op.keep), signOut() (called by op.end) and note(),
   the device log (numbers only). Sign-in and the copy take turns between tabs (navigator.locks, where there is one).
   The list of every await, timer and listener and the guard of each is in the PR of gate 5. */
const sidNow=()=>(get(K.ses)||{}).sid||null;
let gen=0;
function op(){
 const g=gen,sid=sidNow(),own=get(K.owner),live=()=>g===gen&&sidNow()===sid&&get(K.owner)===own;
 let tk=null;                                           // one token per operation, taken once
 let budget=null;                                       // keepalive requests of a hidden page share 64 KiB, the Sheet's save included
 const o={sid,own,live,hidden:false,ended:false,
  put(k,v){if(!live())return false;set(k,v);return true},
  queue(s,ow){if(!live())return false;queued={s,own};qOverwrite=ow;return true},
  // the queued state only for an op of the pupil it was queued for; another pupil's is dropped (X2)
  take(){if(!live())return null;const q=queued;queued=null;return q&&q.own===own?q.s:null},
  keep(j){if(!live()){const t=j&&j.session&&j.session.access_token;if(t)call('/auth/v1/logout?scope=local',{},t).catch(()=>{});return false}   // not kept: ended on the server at once (best effort)
   keep(j);return true},                                // a new session: the op that made it is done with the old one
  /* the access token (an hour), refreshed when it is about to end */
  async token(){
   if(!live())return null;if(!sid){o.ended=true;return null}if(tk)return tk;
   const s=get(K.ses);if(!s||!s.refresh_token){o.ended=true;return null}
   if(s.access_token&&s.expires_at&&s.expires_at*1000-Date.now()>60000)return tk=s.access_token;
   let r;try{r=await call('/auth/v1/token?grant_type=refresh_token',{refresh_token:s.refresh_token})}catch(e){r=null}
   if(!live())return null;                              // B1: a late refresh never writes over the session that came meanwhile
   if(r&&r.status===200&&r.j&&r.j.access_token){set(K.ses,{...get(K.ses),access_token:r.j.access_token,refresh_token:r.j.refresh_token,expires_at:r.j.expires_at||Math.floor(Date.now()/1000)+(r.j.expires_in||3600)});return tk=r.j.access_token}
   if(r&&r.status>=400&&r.status<500){set(K.ses,{device_token:s.device_token});o.ended=true;return null}   // ended on the server: sign in again; progress stays
   return tk=s.access_token||null},                      // offline: keep what we have
  /* a call with the session's token; aborted when the session changed before or while it ran */
  async call(path,body){const t=await o.token();if(!live())return{status:0,j:null,aborted:true};if(!t)return{status:401,j:null};
   if(o.hidden&&body!==undefined){if(budget==null)budget=60000-keepBytes;const n=JSON.stringify(body).length;if(n>budget)return{status:0,j:null};budget-=n}   // the rest goes at the next visit
   const r=await call(path,body,t,o.hidden);return live()?r:{...r,aborted:true}},
  /* let go of this op's session: revoked on the server, forgotten here. all: everything of the pupil goes (logout,
     another pupil); otherwise only the session (the same pupil signs in again). Nothing at all if the device's
     session is already another one (S2). */
  async end(all){
   const t=await o.token();                             // a fresh token: revoking with an expired one is refused (review of #39, 4)
   if(g!==gen||(sidNow()&&sidNow()!==sid)||get(K.owner)!==own)return false;   // another session or pupil is the device's now: not this op's to end
   if(all)signOut();else{const s=get(K.ses)||{};set(K.ses,s.device_token?{device_token:s.device_token}:null)}
   if(t){try{await call('/auth/v1/logout?scope=local',{},t)}catch(e){}}   // the refresh token dies with it
   return true}};
 return o}
/* the session: access token, refresh token, the device token the server handed out, sid. The 4-digit code is never here. */
function keep(j){const old=get(K.ses)||{};const s=j.session||{};
 set(K.ses,{sid:uuid(),access_token:s.access_token,refresh_token:s.refresh_token,expires_at:s.expires_at||Math.floor(Date.now()/1000)+(s.expires_in||3600),device_token:j.device_token||old.device_token,at:j.updated_at||null})}
async function signIn(o,d,extra){return turn(async()=>{
 if(!o.live())return{ok:false,e:'net'};
 const dev=(get(K.ses)||{}).device_token;
 const r=await fn('pupil-login',{class_code:d.c,name:d.n,code:d.p,...(dev?{device_token:dev}:{}),...(extra||{})});
 if(r.j&&r.j.ok&&!o.keep(r.j))return{ok:false,e:'net'}; // the device was signed out meanwhile: this session is not kept, and ended
 return r.j||{ok:false,e:'net'}})}
/* tabs take turns for sign-in and the copy (review of #50, X3 and S-b): the Web Locks API where the browser has it,
   otherwise as before (the guard above still holds). Not at hide time: the page may not live to be given the lock. */
function turn(f,now){let L=null;try{L=!now&&W.navigator&&W.navigator.locks&&typeof W.navigator.locks.request==='function'?W.navigator.locks:null}catch(e){}
 if(!L)return f();
 // a tab frozen while it holds the lock (a phone in a pocket) does not stop the others for long: after 20 s, this one gives up and keeps its state
 const sig=typeof AbortSignal!=='undefined'&&typeof AbortSignal.timeout==='function'?AbortSignal.timeout(20000):null;
 return sig?L.request('wi-sb',{signal:sig},()=>f()):L.request('wi-sb',()=>f())}
/* everything of the pupil on this device, at once (op.end only): saves in flight stop, the next pupil starts with
   nothing of the last one (no session, base, batch, queue, wait, or waiting save with its code) */
function signOut(){gen++;const s=get(K.ses)||{};set(K.ses,s.device_token?{device_token:s.device_token}:null);
 for(const k of[K.base,K.pend,K.stale,K.owner,K.stop,K.netfail,K.sent,K.sending])set(k,null);
 queued=null;waiting={};holdUntil=0;lastWrite=0;clearTimeout(timer);timer=null}
/* Review of #21, B1: on a shared device the session must belong to the pupil whose progress is being saved. The device
   keeps a hash of class code and name (never the name itself); when another pupil's request comes, the old session is
   revoked on the server (best effort) and forgotten here before anything is sent. */
const ownerKey=d=>String(d&&d.c||'').trim().toUpperCase()+'|'+String(d&&d.n||'').normalize('NFC').trim().replace(/\s+/g,' ').toLowerCase();
const owners=new Map();                                 // this page's hashes, so a save can be marked as sent at once
async function ownerOf(d){const t=ownerKey(d);if(owners.has(t))return owners.get(t);
 const h=await crypto.subtle.digest('SHA-256',new TextEncoder().encode('wi-owner|'+t));
 const x=Array.from(new Uint8Array(h).slice(0,12),b=>b.toString(16).padStart(2,'0')).join('');owners.set(t,x);return x}
/* the owner of the request; null when the device was signed out while it was being worked out */
async function sameOwner(d){if(!d||!d.c||!d.n)return true;const g=gen,h=await ownerOf(d);if(g!==gen)return null;
 const cur=get(K.owner);
 if(cur&&cur!==h){await op().end(true);if(get(K.owner))return null}   // another pupil: the old session and all of theirs go first
 return op().put(K.owner,h)?h:null}
/* For js/state.js. logout (all): what was played since the last copy goes first, all within 8 s (review of #41, S1),
   then the session is revoked and everything of the pupil leaves the device. relogin (the Sheet refused the pupil):
   only the session goes; the same pupil's pending progress waits for them. Another pupil who signs in meanwhile waits
   for the logout to finish (leaving), and a logout that comes late never ends their session (S2). */
let leaving=null,epoch=0,keepBytes=0;
export function forget(all){if(MODE==='sheet')return;
 epoch++;                                               // X1: a Sheet answer still on its way is not copied
 const p=(async()=>{
  const g=gen;let owner=get(K.owner);
  if(all){const w=waiting.save;waiting={};
   await Promise.race([new Promise(r=>setTimeout(r,8000)),(async()=>{
    if(busy)await busy;                                 // the copy of the last answer may be on its way: sameOwner, sign-in
    if(g!==gen)return;
    if(owner===null)owner=get(K.owner);                 // the pupil's first run had not claimed the device yet
    const o=op();                                       // the pupil's session as it is now; another tab's sign-in ends it
    if(w&&owner&&o.own===owner&&await ownerOf(w.d)===owner)o.queue(w.d.s,true);   // the save that was waiting behind it
    if(flushP)await flushP;                             // a copy in flight finishes first
    if(o.live()&&get(K.owner)===owner)await flush(false,true)})()]).catch(()=>{})}
  if(owner===null)owner=get(K.owner);
  if(g!==gen||get(K.owner)!==owner)return;              // another pupil came meanwhile (this tab or another): theirs is left alone
  await op().end(all)})().catch(()=>{}).finally(()=>{if(leaving===p)leaving=null});
 if(all)leaving=p}

/* ---------- typed events out of two saves ----------
   The game still saves one record (pack() in js/state.js). Until every game reports its events itself, the adapter
   reads them off the difference between the last record the server took and this one. What it can see:
   word answers (st: [tries, wrong]), a level's stars going up (g.st, m.st), a text read perfectly (read + k.reads),
   a finished mock exam (x.tries). What it cannot see is listed in docs/BACKEND.md section 8 (the gap per source). */
const num=x=>+x||0,obj=x=>x&&typeof x==='object'&&!Array.isArray(x)?x:{};
/* After a long wait (the server said wait, daycap or brake) many answers build up. They are all kept (review of #39,
   3) and sent in batches of BATCH; the caps only stop a counter that jumped absurdly (a broken or edited record). */
const BATCH=200,MAX_PER_WORD=600,MAX_EVENTS=4000;
export function events(prev,next){
 const ev=[],p=obj(prev),n=obj(next),now=Date.now();
 const ps=obj(p.st),ns=obj(n.st);
 for(const w in ns){const a=Array.isArray(ns[w])?ns[w]:[],b=Array.isArray(ps[w])?ps[w]:[];
  const tries=Math.min(MAX_PER_WORD,Math.max(0,num(a[0])-num(b[0]))),wrong=Math.min(tries,Math.max(0,num(a[1])-num(b[1])));
  for(let i=0;i<tries;i++)ev.push({type:'answer',game:'en',item:w,correct:true,first_try:i>=wrong,t:now})}
 for(const[g,key]of[['en','g'],['math','m']]){const a=obj(obj(n[key]).st),b=obj(obj(p[key]).st);
  for(const l in a){const s=Math.min(3,Math.floor(num(a[l])));if(s>Math.floor(num(b[l])))ev.push({type:'level',game:g,level:l,stars:s})}}
 if(num(obj(n.k).reads)>num(obj(p.k).reads)){const a=obj(n.read),b=obj(p.read);for(const id in a)if(num(a[id])>num(b[id]))ev.push({type:'read',text:id})}
 const seen=new Set((Array.isArray(obj(p.x).tries)?p.x.tries:[]).map(t=>t&&t.at));
 for(const t of Array.isArray(obj(n.x).tries)?n.x.tries:[])if(t&&!seen.has(t.at)&&Array.isArray(t.total))ev.push({type:'exam',paper:'mock',right:Math.max(0,Math.floor(num(t.total[0])))});
 return ev.slice(0,MAX_EVENTS)}
/* the id of part i of a pending batch: the batch's own id for part 0, then ids derived from it, so a part that is
   sent again keeps its id and the server counts it once */
const partId=(id,i)=>i?id.slice(0,-4)+((parseInt(id.slice(-4),16)+i)&0xffff).toString(16).padStart(4,'0'):id;

/* the larger of two records, field by field, for what events() reads: a base never goes down */
const arr=x=>Array.isArray(x)?x:[];
function mx(a,b){a=obj(a);b=obj(b);const r={...a};
 r.st={...obj(a.st)};for(const w in obj(b.st)){const x=arr(r.st[w]),y=arr(b.st[w]);if(num(y[0])>num(x[0])||num(y[1])>num(x[1]))r.st[w]=[Math.max(num(x[0]),num(y[0])),Math.max(num(x[1]),num(y[1]))]}
 for(const k of['g','m']){const st={...obj(obj(a[k]).st)};for(const l in obj(obj(b[k]).st))st[l]=Math.max(num(st[l]),num(b[k].st[l]));r[k]={...obj(a[k]),st}}
 r.read={...obj(a.read)};for(const id in obj(b.read))r.read[id]=Math.max(num(r.read[id]),num(b.read[id]));
 r.k={...obj(a.k),reads:Math.max(num(obj(a.k).reads),num(obj(b.k).reads))};
 const ta=arr(obj(a.x).tries),at=new Set(ta.map(t=>t&&t.at));r.x={...obj(a.x),tries:[...ta,...arr(obj(b.x).tries).filter(t=>t&&!at.has(t.at))]};
 return r}
/* S3 (review of #41): a pupil with two devices. A Sheet sign-in answers with the record joined from every device; the
   game takes it in and its next save carries what the other device played, which that device has already copied. So
   what the Sheet has beyond what this device itself knows (ref: its last save, or else its batch or base) is added to
   the base: counted once, by the device it was played on. */
function lift(b,sh,ref){b=obj(b);sh=obj(sh);ref=obj(ref);const r={...b},up=(x,y,z)=>num(x)+Math.max(0,num(y)-num(z));
 r.st={...obj(b.st)};for(const w in obj(sh.st)){const y=arr(sh.st[w]),z=arr(obj(ref.st)[w]),x=arr(r.st[w]);if(num(y[0])>num(z[0]))r.st[w]=[up(x[0],y[0],z[0]),up(x[1],y[1],z[1])]}
 for(const k of['g','m']){const st={...obj(obj(b[k]).st)},y=obj(obj(sh[k]).st),z=obj(obj(ref[k]).st);for(const l in y)if(num(y[l])>num(z[l]))st[l]=Math.max(num(st[l]),num(y[l]));r[k]={...obj(b[k]),st}}
 r.read={...obj(b.read)};for(const id in obj(sh.read))r.read[id]=up(r.read[id],sh.read[id],obj(ref.read)[id]);
 r.k={...obj(b.k),reads:up(obj(b.k).reads,obj(sh.k).reads,obj(ref.k).reads)};
 const known=new Set([...arr(obj(ref.x).tries),...arr(obj(b.x).tries)].map(t=>t&&t.at));
 r.x={...obj(b.x),tries:[...arr(obj(b.x).tries),...arr(obj(sh.x).tries).filter(t=>t&&!known.has(t.at))]};
 return r}

/* ---------- writing a save to Supabase (shared by 'dual' and 'supabase') ----------
   Order matters for "never counted twice": the batch gets its id and is stored on the device BEFORE it is sent; if the
   answer is lost, the same batch with the same id goes again and the server ignores the repeat. Everything goes
   through the op of the flush: the moment the device's session changes, nothing more is sent or kept. */
const ABORT={ok:false,aborted:true};
async function writeSave(o,s,overwrite){
 const t=await o.token();                               // one token for this whole save, taken once
 if(!o.live())return ABORT;
 if(!t)return{ok:false,status:401};
 let pend=get(K.pend);
 if(!pend){const base=get(K.base);                      // the first save on a device has nothing to compare with: it sets the base
  pend={id:uuid(),ev:base?events(base,s):[],next:base?mx(s,base):s,sent:0,size:BATCH};if(!o.put(K.pend,pend))return ABORT}
 const size=Math.max(1,num(pend.size)||BATCH);          // a batch keeps the part size it was cut with
 let r=await o.call('/rest/v1/rpc/save_progress',{p_state:s,p_base:(get(K.ses)||{}).at||null});
 if(r.aborted)return ABORT;
 if(r.status===200&&r.j&&r.j.conflict){
  if(!overwrite)return{ok:false,conflict:true,state:r.j.state,at:r.j.updated_at};
  o.put(K.ses,{...get(K.ses),at:r.j.updated_at});r=await o.call('/rest/v1/rpc/save_progress',{p_state:s,p_base:r.j.updated_at})   // shadow: the Sheet is the truth
  if(r.aborted)return ABORT}
 // the server rations saves (5 s apart, 300 a day): not a failure, a "later" with the seconds to wait. The events still
 // go now (review of #21, B2): they do not depend on the blob, and held back they would meet the next day's caps.
 const later_=r.status===200&&r.j&&!r.j.ok&&(r.j.e==='wait'||r.j.e==='daycap')?{e:r.j.e,retry:Math.max(1,num(r.j.retry_after))}:null;
 if(!later_&&(r.status!==200||!r.j||!r.j.ok))return{ok:false,status:r.status};
 if(!later_)o.put(K.ses,{...get(K.ses),at:r.j.updated_at});
 let points=null;
 const mine=()=>{const c=get(K.pend);return c&&c.id===pend.id?c:pend};   // as stored: a Sheet sign-in may have lifted its next (S3)
 for(let i=num(pend.sent);i*size<pend.ev.length;i++){   // in parts; each part done is remembered
  const e=await o.call('/rest/v1/rpc/record_events',{p_batch:partId(pend.id,i),p_events:pend.ev.slice(i*size,(i+1)*size)});
  if(e.aborted)return ABORT;
  if(e.status===200&&e.j&&e.j.e==='brake'){note('brake');return{ok:false,e:'brake',saved:!later_,retry:Math.max(BRAKE_RETRY,later_?later_.retry:0)}}   // the database is full for now: the rest waits on the device
  if(e.status!==200||!e.j||!e.j.ok)return later_?{ok:false,...later_}:{ok:false,status:e.status,saved:true};
  points=e.j.points;if(e.j.flagged)note('flagged',{n:e.j.flagged});
  if(!o.put(K.pend,{...mine(),sent:i+1}))return ABORT}
 // the base never goes down: another tab of the same pupil may have moved it further meanwhile (S-b)
 if(!o.put(K.base,mx(mine().next,get(K.base)||{})))return ABORT;const c=get(K.pend);if(c&&c.id===pend.id)o.put(K.pend,null);
 return later_?{ok:false,...later_,points,events:pend.ev.length}:{ok:true,points,events:pend.ev.length}}

/* ---------- pacing the saves (review S8) ----------
   The game saves 2.5 s after every change; the server takes one write every 5 s and 300 a day per pupil. So only the
   newest state is kept here and written at most every SAVE_EVERY (30 s), and at once when the page is hidden. When
   the server answers "wait" or "daycap" (or "brake" for the events), the state is kept and tried again after the time
   it names. Nothing is lost: the newest state carries all of it, and the events wait in the pending batch. */
const SAVE_EVERY=1000*Math.max(0,B.saveEveryS===undefined||!Number.isFinite(+B.saveEveryS)?30:+B.saveEveryS);
const BRAKE_RETRY=600;
let queued=null,qOverwrite=true,lastWrite=0,holdUntil=0,timer=null,flushP=null,flushOp=null;
function later(){clearTimeout(timer);timer=null;if(!queued)return;
 timer=setTimeout(()=>{flush(false).catch(()=>{})},Math.max(0,Math.max(lastWrite+SAVE_EVERY,holdUntil)-Date.now()))}
/* hidden: the page is being hidden (keepalive, no waiting for SAVE_EVERY). force: logout, the server's "wait" too is
   not waited for (the save is refused again, the events still go) */
/* hidden: the page is being hidden or closed (keepalive within its 64 KiB budget, no lock, no pacing). force: logout
   (no pacing, and the server's "wait" is not waited for: the save is refused again, the events still go); a logout is
   not a closing page, so no keepalive and no budget (G3, review of #55) */
function flush(hidden,force){
 if(!queued||displaced)return Promise.resolve(null);
 if(flushP&&flushOp.live()){later();return Promise.resolve(null)}   // one at a time; a flush of a session that is gone holds nothing back
 const now=Date.now();if(!force&&(now<holdUntil||(!hidden&&now<lastWrite+SAVE_EVERY))){later();return Promise.resolve(null)}
 const o=op();if(!o.sid)return Promise.resolve(null);   // no session (yet): the state waits, nothing is sent
 const ow=qOverwrite;o.hidden=!!hidden;let s=null;
 const p=(async()=>{
  let w;
  // the newest state, taken once the lock is this tab's (not before: another tab may have copied meanwhile)
  try{w=await turn(()=>{if(!o.live())return ABORT;s=o.take();if(s==null)return ABORT;lastWrite=Date.now();return writeSave(o,s,ow)},hidden)}
  catch(e){w=e&&(e.name==='TimeoutError'||e.name==='AbortError')?{ok:false,retry:5}:{ok:false,status:0}}   // the lock did not come in 20 s: the state stays queued
  if(!o.live()||w.aborted){later();return w}            // the session changed meanwhile: nothing of this save is kept
  if(w.retry){if(!queued&&s!=null)o.queue(s,ow);holdUntil=Date.now()+w.retry*1000}   // told to wait: keep it and try again
  else if(w.conflict&&!ow)o.put(K.stale,{state:w.state,at:w.at});                 // 'supabase': the game joins at its next save
  if(MODE==='dual')note('save',{ok:w.ok?1:0,st:w.status||0,ev:w.events||0,...(w.e?{e:w.e}:{}),...(w.points!=null?{server:w.points}:{})});
  later();return w})().finally(()=>{if(flushP===p){flushP=null;flushOp=null}});
 flushP=p;flushOp=o;return p}
/* G4 (review of #55): two tabs of one device with two pupils would take the device from each other at every save (a
   stream of sign-ins from the school's one address). A tab whose pupil is no longer the device's owner, because another
   tab signed someone else in, stops copying; the page then reloads to show the device's pupil, after the child's tap
   (D1, js/state.js). Not in sheet mode. */
let mine=null,displaced=false;
if(MODE!=='sheet'&&typeof W.addEventListener==='function'){
 const away=()=>{flush(true).catch(()=>{})};
 W.addEventListener('pagehide',away);
 if(typeof document!=='undefined')document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')away()});
 W.addEventListener('storage',ev=>{
  if(!ev||ev.key!==K.owner||!ev.newValue||displaced)return;
  let h=null;try{h=JSON.parse(ev.newValue)}catch(e){}
  if(!mine||!h||h===mine)return;
  displaced=true;waiting={};note('displaced');
  /* D1 (review of #63): the page decides when to reload. js/state.js takes the event (preventDefault), sends the
     pupil's last save to the Sheet and shows a calm message; the reload waits for the child's tap and for this tab's
     own work in flight (a sign-in whose session is then refused and ended). A page without js/state.js reloads now. */
  const ready=Promise.race([settled(),new Promise(r=>setTimeout(r,8000))]);
  let ev2=null;try{ev2=new CustomEvent('wi-displaced',{cancelable:true,detail:{ready}})}catch(e){}
  const taken=ev2&&typeof W.dispatchEvent==='function'&&!W.dispatchEvent(ev2);
  if(!taken)try{W.location.reload()}catch(e){}})}
/* for the tests: resolves when no shadow run and no flush is in progress */
export async function settled(){for(let i=0;i<20&&(busy||flushP||leaving);i++){try{await Promise.all([busy,flushP,leaving])}catch(e){}}}

/* ---------- 'dual': the shadow copy. Runs after the Sheet answered; nothing here can reach the pupil. ---------- */
/* Sign-in on the shadow side (review of #21, S-a): only when there is no session for this pupil; never again the
   same day after the server said no (a pupil Supabase does not know would otherwise count as wrong codes from the
   school's one address and could pause sign-in for the whole class); after a network error at most every 10 minutes.
   One run at a time (busy, its promise); what comes meanwhile waits (the newest save, the newest sign-in) and runs
   after it, checked for its owner like any other. */
let busy=null,waiting={};
const today=()=>new Date().toISOString().slice(0,10);
/* S-a (review of #50): what this device itself sent to the Sheet, kept on the device with its owner, so a Sheet
   sign-in after the page was closed still knows which answers are this device's own (the ref of lift()). Written
   when the Sheet took the save, at once, not when the shadow copy runs. */
function sent(h,s,e){if(!h||e!==epoch||!s||typeof s!=='object')return;const o=op();if(o.own!==h)return;const c=get(K.sent);
 o.put(K.sent,{own:h,s:core(c&&c.own===h?mx(c.s,s):s)})}
/* G2 (review of #55): a tab closed before the Sheet answered never sees the answer, so a save is marked as "sending"
   the moment it goes (with its owner); the answer promotes it to sent, a refusal drops it. Both count as this device's
   own in lift() (the Sheet usually has a save whose answer was lost with the page). */
let sendSeq=0;
function sending(d){const id=++sendSeq,mark=h=>{const o=op();if(!h||o.own!==h)return;const c=get(K.sending);
  o.put(K.sending,{own:h,id,s:core(c&&c.own===h?mx(c.s,d.s):d.s)})};
 const t=ownerKey(d);if(owners.has(t))mark(owners.get(t));else ownerOf(d).then(mark,()=>{});
 return{id,d}}
function sentDone(x,ok,e){const h=owners.get(ownerKey(x.d));if(!h)return;
 if(ok)sent(h,x.d.s,e);
 const c=get(K.sending);if(c&&c.id===x.id&&c.own===h)op().put(K.sending,null)}
const sentRef=owner=>{const a=get(K.sent),b=get(K.sending),x=a&&a.own===owner?a.s:null,y=b&&b.own===owner?b.s:null;return x&&y?mx(x,y):x||y}
/* only what events() and lift() read: the counters, never the rest of the record */
const core=x=>{x=obj(x);return{st:obj(x.st),g:{st:obj(obj(x.g).st)},m:{st:obj(obj(x.m).st)},read:obj(x.read),k:{reads:num(obj(x.k).reads)},x:{tries:arr(obj(x.x).tries).map(t=>({at:t&&t.at}))}}}
function shadow(a,d,r){
 if(!r||!r.ok||displaced)return;                       // the Sheet refused (or this tab gave the device up): nothing to copy
 if(a!=='login'&&a!=='register'&&a!=='save')return;     // the board, the teacher screen and reset stay on the Sheet
 if(busy){if(a!=='register')waiting[a]={d,r};return}
 const p=busy=run(a,d,r).catch(e=>{note('error',{e:String(e&&e.name||'x').slice(0,20)})}).finally(()=>{
  if(busy===p)busy=null;
  const w=waiting;waiting={};if(w.login)shadow('login',w.login.d,w.login.r);if(w.save)shadow('save',w.save.d,w.save.r)})}
async function run(a,d,r){
 if(leaving)await leaving;                              // a logout in progress finishes first (S2)
 const owner=await sameOwner(d);if(!owner||displaced)return;   // another pupil on this device: the old session is gone first
 if(typeof owner==='string')mine=owner;
 let o=op();                                            // the session this run works in; checked after every await (B2)
 if(a==='save'&&d.s&&typeof d.s==='object'){const c=get(K.sent);o.put(K.sent,{own:owner,s:core(c&&c.own===owner?mx(c.s,d.s):d.s)})}
 if((a==='login'||a==='register')&&r.s&&typeof r.s==='object'){const b=get(K.base);
  if(!b)o.put(K.base,a==='register'?{}:r.s);            // the first save after a sign-in is counted from what the Sheet had (review of #50)
  else{const p=get(K.pend),ref=sentRef(owner)||(p?p.next:b);   // S3: the record joined from the other devices
   o.put(K.base,lift(b,r.s,ref));if(p)o.put(K.pend,{...p,next:lift(p.next,r.s,ref)});o.put(K.sent,{own:owner,s:core(mx(ref,r.s))})}}
 else if(a==='register'&&!get(K.base))o.put(K.base,{});
 if(a==='save')o.queue(d.s,true);                       // the newest state waits here until it may go
 if(!(await o.token())){
  if(!o.live())return;
  const stop=get(K.stop);if(stop&&stop.owner===owner&&stop.day===today())return;
  const nf=get(K.netfail);if(nf&&nf.owner===owner&&Date.now()-nf.at<Math.max(600000,num(nf.ms)))return;
  const s0=get(K.ses)||{};o.put(K.ses,s0.device_token?{device_token:s0.device_token}:null);   // a session that cannot be used any more
  o=op();
  const j=await signIn(o,d);
  if(!o.live()&&!j.ok)return;
  note('signin',{e:j.ok?'ok':String(j.e||'net').slice(0,12)});
  // a network error, or the sign-in paused (locked, with the seconds to wait): try again later, not tomorrow (G4)
  if(!j.ok){if(!j.e||j.e==='net'||j.e==='server'||j.e==='locked')o.put(K.netfail,{owner,at:Date.now(),ms:1000*num(j.wait)});else o.put(K.stop,{owner,day:today()});return}
  o=op()}                                               // the new session
 if(a==='save'){if(!o.live())return;note('sheet',{pts:num(d.s&&d.s.pts)});await flush(false)}}

/* ---------- 'supabase': the new backend alone ----------
   The game signs in with the code once (register, login, recover); from then on only the session is used and the
   code is not kept anywhere (js/state.js keeps {c, n}). The pupil's record and the board are read from Supabase.
   The answers keep the server's error words (docs/BACKEND.md 4.4) and, for a lock, its wait, scope and help, so the
   sign-in screens can say what happened; js/state.js enter() is what the screens call (the seam in its PR).
   'signin': the session is gone (ended on the server, or it cannot be renewed); the pupil signs in again and what
   this device played waits for them. */
const BY=['name','device','address','class','everyone','system'];   // whom a lock is for (0008_lock_scope.sql); a wait of -1: until the teacher opens it
const ERRS=['input','weak','class','pin','taken','roster','full','picture','otc','locked','net','server'];
const err=j=>{const e=j&&typeof j.e==='string'&&ERRS.includes(j.e)?j.e:'net';
 return e==='locked'?{ok:false,e,wait:num(j.wait)<0?-1:Math.max(0,Math.floor(num(j.wait))),by:BY.includes(j.by)?j.by:'name',help:j.help==='teacher'?'teacher':'wait'}:{ok:false,e}};
/* who signed in: the pupil's id and class id, read with the new session (RLS: the pupil's own row only). The device
   keeps its record for this pupil of this class only (docs/PHASE4.md A); null when it could not be read */
async function whoIs(o){const r=await o.call('/rest/v1/pupils?select=id,class_id&limit=1');
 const x=!r.aborted&&r.status===200&&Array.isArray(r.j)&&r.j.length===1?r.j[0]:null;
 return x&&typeof x.id==='string'&&typeof x.class_id==='string'?{p:x.id,c:x.class_id}:null}
/* the end of a sign-in: the session is kept (or not, when the device was signed out meanwhile), then who it is */
async function opened(o,j){
 if(!(j&&j.ok))return err(j);
 if(!o.keep(j))return{ok:false,e:'net'};
 const at=j.updated_at||null,s=j.s&&typeof j.s==='object'&&!Array.isArray(j.s)?j.s:{};
 const who=await whoIs(op());
 return{ok:true,s,name:typeof j.name==='string'?j.name:null,who,at}}
const pics=x=>Array.isArray(x)?x.map(Number):x;
/* no token: 'signin' when there is no session to use (never signed in, signed out, or ended on the server: op.ended),
   'net' when another pupil's session took the device meanwhile */
const gone_=o=>({ok:false,e:o.ended||o.live()?'signin':'net'});
async function supa(a,d){
 try{
  /* G4 (review of #55) in this mode too: a tab whose pupil another tab replaced sends nothing more, or its save would
     take the device back (sameOwner) and end the other pupil's session; and the tab's pupil is remembered (mine), so
     the 'storage' listener can tell it was replaced and show the dialog (review of #111) */
  if(displaced&&a!=='board')return{ok:false,e:'net'};
  if(a==='login'||a==='register'||a==='recover'||a==='save'){if(leaving)await leaving;const ow=await sameOwner(d);if(!ow)return{ok:false,e:'net'};if(typeof ow==='string')mine=ow}
  if(a==='login'){const o=op();return await turn(async()=>{if(!o.live())return{ok:false,e:'net'};const dev=(get(K.ses)||{}).device_token;
   const r=await fn('pupil-login',{class_code:d.c,name:d.n,code:d.p,...(dev?{device_token:dev}:{})});return opened(o,r.j)})}
  if(a==='register'){const o=op();return await turn(async()=>{if(!o.live())return{ok:false,e:'net'};
   const r=await fn('pupil-register',{class_code:d.c,name:d.n,code:d.p,pictures:pics(d.pics)});return opened(o,r.j)})}
  if(a==='recover'){const o=op();return await turn(async()=>{if(!o.live())return{ok:false,e:'net'};
   const r=await fn('pupil-recover',{class_code:d.c,name:d.n,new_code:d.np,new_pictures:pics(d.npics),...(d.otc!==undefined?{otc:String(d.otc)}:{pictures:pics(d.pics)})});return opened(o,r.j)})}
  if(a==='save'){const o=op();if(!(await o.token()))return gone_(o);   // no session: sign in again; the progress stays
   const st=get(K.stale);if(st){o.put(K.stale,null);o.put(K.ses,{...get(K.ses),at:st.at});return{ok:false,e:'stale',s:st.state}}   // a kept save met another device's
   if(!o.queue(d.s,false))return{ok:false,e:'net'};
   const w=await flush(false);
   if(!w||w.ok||w.retry)return{ok:true};                 // written, or kept here and sent within SAVE_EVERY or when the page is hidden
   if(w.aborted)return{ok:false,e:'net'};
   if(w.conflict){o.put(K.stale,null);o.put(K.ses,{...get(K.ses),at:w.at});return{ok:false,e:'stale',s:w.state}}   // another device saved first: join and save again
   return{ok:false,e:w.status===401?'signin':'net'}}
  /* the pupil's own record, with the session (js/state.js pull()): the game joins it with its own; its time is the
     base of the next save, so that save is not taken for another device's */
  if(a==='record'){const o=op();if(!(await o.token()))return gone_(o);
   const r=await o.call('/rest/v1/progress?select=state,updated_at&limit=1');
   if(r.aborted)return{ok:false,e:'net'};if(r.status===401)return{ok:false,e:'signin'};
   if(r.status!==200||!Array.isArray(r.j))return{ok:false,e:'net'};
   const x=r.j[0]||null,s=x&&x.state&&typeof x.state==='object'&&!Array.isArray(x.state)?x.state:{};
   if(x&&x.updated_at)o.put(K.ses,{...get(K.ses),at:x.updated_at});
   return{ok:true,s}}
  if(a==='board'){const o=op();if(!(await o.token()))return gone_(o);
   const r=await o.call('/rest/v1/class_board?select=display_name,points,words,streak,me&order=points.desc');
   if(r.aborted)return{ok:false,e:'net'};if(r.status===401)return{ok:false,e:'signin'};
   if(r.status!==200||!Array.isArray(r.j))return{ok:false,e:'net'};return{ok:true,rows:r.j.map(x=>({n:String(x.display_name),pts:num(x.points),words:num(x.words),streak:num(x.streak),me:x.me===true}))}}
  return{ok:false,e:'teacher'}                           // the teacher signs in on teacher.html (Google); the game's teacher screen is the Sheet's
 }catch(e){return{ok:false,e:'net'}}}
/* ?dual=0 (or ?new=0) on a device of the trial: the backend is off for it from now on, so what it kept is let go too (review of #73): the
   session is revoked and the session, base, batch, sent record and owner marks leave the device. */
if(tryOff&&LS&&(sidNow()||get(K.owner)||get(K.base)))op().end(true).catch(()=>{});
