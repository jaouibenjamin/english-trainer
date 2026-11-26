/* The teacher's sign-in (docs/PHASE3.md, step 1): Google through Supabase Auth, with PKCE, by plain fetch (no vendored
   library, as js/api.js). Only teacher.html uses it; no pupil page imports it.

   Where things live (a class computer is shared):
   - the session (access and refresh token, who she is) lives in this page's memory only. Nothing of it is written to
     sessionStorage or localStorage, so no other page of the site, in this tab or another, can ever read it;
   - it ends when the page is left (pagehide: a click to the game, the back button, closing the tab, a reload, the trip
     to Google), after 30 minutes without a tap or a key (counted by the clock, so a laptop that slept does not hand
     the next person her session), and with "sign out" (revoked on the server too);
   - the only thing kept across the trip to Google is the PKCE verifier, in sessionStorage, for 10 minutes, used once.

   The redirect target is always this page's own address (origin + path), never anything read from the URL, so the page
   cannot be made to send a sign-in elsewhere (open redirect). PKCE binds the code to the verifier this tab made: a code
   that was not started here (a link, another tab, an attacker's own sign-in) has no verifier and is refused without a
   request; a code started elsewhere but fed to this tab fails at the server (another challenge).

   One guard for every late answer (docs/LESSONS.md, entry 1): gen is raised whenever the session is let go (sign-out,
   leaving the page, idle, a new tap on "sign in"); every await checks it before it keeps or uses anything, and a
   session that arrives too late (a code exchange or a refresh) is revoked at once rather than dropped alive. */
const FLOW='wi-teacher-flow',FLOW_MS=10*60000,IDLE_MS=30*60000,PAGE=/\/teacher\.html$/;
const b64url=a=>btoa(String.fromCharCode(...new Uint8Array(a))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
/* the project in config.js, the same rule as js/api.js: without it the page does nothing */
export const projectOf=B=>B&&typeof B==='object'&&typeof B.url==='string'&&/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(B.url)&&typeof B.key==='string'&&B.key.length>20?{url:B.url,key:B.key}:null;

export function teacherAuth(env){
 const{url,key,fetch,crypto,store,location,history,now,setTimeout,clearTimeout}=env,onOut=env.onOut||(()=>{});
 let ses=null,gen=0,idle=null,last=0,refreshing=null;
 const self=()=>location.origin+location.pathname;
 const get=()=>{try{return JSON.parse(store.getItem(FLOW))}catch(e){return null}};
 const drop=()=>{try{store.removeItem(FLOW)}catch(e){}};
 async function call(path,body,token,method,keep){
  const r=await fetch(url+path,{method:method||'POST',keepalive:!!keep,headers:{apikey:key,...(body!==undefined?{'content-type':'application/json'}:{}),...(token?{authorization:'Bearer '+token}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
  let j=null;try{j=await r.json()}catch(e){}return{status:r.status,j}}
 /* a session's tokens: kept, never counted as activity (a refresh in the background is not her) */
 function keep(j){ses={access:j.access_token,refresh:j.refresh_token,exp:now()+1000*(+j.expires_in||3600),user:{id:j.user&&j.user.id||null,email:j.user&&j.user.email||''}}}
 /* a session that came back after it was let go: revoked, with keepalive (the page may be on its way out) */
 function revoke(j){if(j&&typeof j.access_token==='string')call('/auth/v1/logout?scope=local',{},j.access_token,'POST',true).catch(()=>{})}
 function arm(){last=now();clearTimeout(idle);const g=gen;idle=setTimeout(()=>{if(g===gen&&ses)signOut('idle')},IDLE_MS)}
 /* activity: a tap or a key; 30 minutes without one ends the session. The clock decides, not the timer: a laptop
    that slept 45 minutes has a timer that never ran, and the next person's first tap must not buy another 30 */
 function touch(){if(!ses)return;if(last&&now()-last>=IDLE_MS){signOut('idle');return}arm()}
 /* a page that comes back to the front after a long time (timers sleep in the background) checks the clock itself */
 function wake(){if(ses&&now()-last>=IDLE_MS)return signOut('idle');return null}
 /* let go of the session: here at once, on the server best effort */
 async function signOut(why){
  const s=ses;ses=null;gen++;refreshing=null;clearTimeout(idle);idle=null;last=0;
  if(s)try{onOut(why||'out')}catch(e){}                  // the screen forgets her at once, before the server is told
  // leaving the page: the revoke goes with keepalive, or the browser drops it with the page
  if(s&&s.access){try{await call('/auth/v1/logout?scope=local',{},s.access,'POST',why==='left')}catch(e){}}
  return why||'out'}
 /* "Sign in with Google": the session of whoever was here before goes first */
 async function begin(){
  if(!PAGE.test(location.pathname))return'path';          // only from teacher.html: the one address on the redirect list
  gen++;                                                  // a sign-in already on its way (an earlier tap) is let go
  if(ses)await signOut('switch');
  const raw=crypto.getRandomValues(new Uint8Array(32)),verifier=b64url(raw);
  const challenge=b64url(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));
  try{store.setItem(FLOW,JSON.stringify({verifier,at:now()}))}catch(e){return'storage'}
  // prompt=select_account: Google asks which account every time, so a shared computer never signs in as the last one
  location.assign(url+'/auth/v1/authorize?provider=google&redirect_to='+encodeURIComponent(self())+'&code_challenge='+challenge+'&code_challenge_method=s256&prompt=select_account');
  return'going'}
 /* back from Google: ?code=… (or ?error=…). The code leaves the address bar and the history at once. */
 async function finish(){
  if(location.hash)try{history.replaceState(null,'',self()+location.search)}catch(e){}   // nothing is ever read from a fragment
  const q=new URLSearchParams(location.search),code=q.get('code'),err=q.get('error');
  if(!code&&!err)return{state:ses?'in':'out'};
  try{history.replaceState(null,'',self())}catch(e){}
  const flow=get();drop();                               // used once, whatever happens next
  if(err)return{state:'out',e:'denied'};
  if(!flow||typeof flow.verifier!=='string'||!(now()-flow.at<FLOW_MS))return{state:'out',e:'flow'};   // not started in this tab, or too old: nothing is sent
  if(ses)await signOut('switch');
  const g=++gen;
  let r;try{r=await call('/auth/v1/token?grant_type=pkce',{auth_code:code,code_verifier:flow.verifier})}catch(e){return{state:'out',e:'net'}}
  if(g!==gen){if(r.status===200)revoke(r.j);return{state:'out',e:'stale'}}   // left, signed out or tapped again meanwhile
  if(r.status!==200||!r.j||!r.j.access_token)return{state:'out',e:'code'};
  keep(r.j);arm();return{state:'in',user:{...ses.user}}}
 /* the access token for a call, refreshed when it is about to end; null when there is no session any more */
 async function token(){
  if(!ses)return null;
  if(ses.exp-now()>60000)return ses.access;
  if(!refreshing){                                       // one refresh at a time: calls made together share it
   const s=ses,g=gen,p=(async()=>{
    let r;try{r=await call('/auth/v1/token?grant_type=refresh_token',{refresh_token:s.refresh})}catch(e){r=null}
    if(g!==gen||ses!==s){if(r&&r.status===200)revoke(r.j);return null}
    if(!r||r.status!==200||!r.j||!r.j.access_token){await signOut('expired');return null}
    keep({...r.j,user:r.j.user||{id:s.user.id,email:s.user.email}});return ses.access})();
   refreshing=p;p.then(()=>{if(refreshing===p)refreshing=null},()=>{if(refreshing===p)refreshing=null})}
  return refreshing}
 /* leaving the page ends the session, every time: also an exchange still on its way (its answer is revoked), also the
    trip to Google (which keeps only the verifier, in sessionStorage), also a page going into the back-forward cache */
 function left(){gen++;if(ses)signOut('left')}
 return{begin,finish,token,signOut,touch,wake,left,user:()=>ses?{...ses.user}:null,signedIn:()=>!!ses}}
