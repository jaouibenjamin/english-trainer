/* State, class backend client (same contract as the classic trainer) and speech. */
import {WORDS,TEXTS,ISLANDS,T,levelKey} from './data.js';
import {clipOf,HAS_CLIPS} from './voice.js';
import {voiceCtx,voiceOut,duck} from './audio.js';

export const KEY='aam-unit1-v1';          // shared with trainer.html so both keep one progress record
const SET_KEY='word-islands-settings-v1'; // device-only preferences
const blankG=()=>({st:{},ball:0,ob:{},plays:0});
export const blank=()=>({m:{st:{},plays:0},w:{},read:{},parts:[1,2,3,4,5],dir:'en-he',cnt:10,me:[],ct:3,ccnt:15,ctypes:['en-he','he-en','tobe'],pts:0,st:{},day:'',streak:0,u:null,lastC:'',g:blankG()});
export let S=blank();
function load(){try{Object.assign(S,JSON.parse(localStorage.getItem(KEY))||{})}catch(e){}fix()}
function fix(){if(!S.g||typeof S.g!=='object')S.g=blankG();const g=S.g;if(!g.st||typeof g.st!=='object')g.st={};if(!g.ob||typeof g.ob!=='object')g.ob={};g.ball=+g.ball||0;g.plays=+g.plays||0;
 for(const k of['w','read','st'])if(!S[k]||typeof S[k]!=='object')S[k]={};S.pts=+S.pts||0;
 if(!S.m||typeof S.m!=='object')S.m={};if(!S.m.st||typeof S.m.st!=='object')S.m.st={};S.m.plays=+S.m.plays||0}   // m: the math world (Fraction Bay)
load();
export const saveLocal=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}};
export const save=()=>{saveLocal();touch()};

export const SET={music:true,sfx:true,calm:false};   // calm: the game's own "reduce motion" switch, for pupils who are sensitive to movement
try{Object.assign(SET,JSON.parse(localStorage.getItem(SET_KEY))||{})}catch(e){}
export const saveSet=()=>{try{localStorage.setItem(SET_KEY,JSON.stringify(SET))}catch(e){}};

/* ---------- class backend (Google Sheet via Apps Script) ---------- */
export const API=(window.API_URL||'').trim();
export const ERR={class:'קוד הכיתה לא נכון.',pin:'הקוד הסודי לא נכון. נסו שוב.',nouser:'לא מצאנו את השם הזה בכיתה. עוד לא נרשמתם?',taken:'השם הזה כבר רשום. לא אתם? הוסיפו אות אחת אחרי השם. זה אתם?',roster:'השם לא נמצא ברשימת הכיתה.\nכתבו את השם הפרטי, או בקשו מהמורה להוסיף אתכם.',locked:'יותר מדי ניסיונות.\nחכו 5 דקות ונסו שוב.',full:'הכיתה מלאה. פנו למורה.',input:'צריך קוד כיתה, שם באותיות\nוקוד סודי של 4 ספרות.',teacher:'קוד המורה לא נכון.',setup:'המערכת עוד לא הוגדרה.',net:'אין חיבור כרגע.\nבדקו את האינטרנט ונסו שוב.'};
import {api} from './api.js';export {api};   // the backend adapter; with today's config.js it makes the very same request this line used to make
export const cred=()=>({c:S.u.c,n:S.u.n,p:S.u.p});
export const wordsKnown=()=>WORDS.filter(w=>w.p<6&&(S.w[w.en]||0)>=2).length;
const pack=()=>({w:S.w,read:S.read,st:S.st,pts:S.pts,day:S.day,streak:S.streak,me:S.me,g:S.g,m:S.m,x:S.x,k:{words:wordsKnown(),reads:TEXTS.filter(t=>S.read[t.id]===t.qs.length).length}});
let dirty=0,syncT=0,retryT=0,retryN=0,inflight=null,fatal=false;
const FATAL=['pin','nouser','class','input','big','setup'];   // the server will never take this save: do not keep trying
/* ---------- is the class table up to date? ----------
   S.sync = {at: time of the last save the server took, err: why the last one was refused}. Kept on the device, never sent.
   A refusal for good (the class code changed, the pupil's name was edited in the sheet, the row was deleted) used to be
   silent: the device kept the points and the sheet never saw them. Now the pupil is asked to sign in again, and what this
   device earned is joined to the account they sign in to, when it is the same pupil (see auth). */
export const RELOGIN=['pin','nouser','class'];
export const syncState=()=>S.sync||{};
export const needsRelogin=()=>!!(API&&S.u&&S.sync&&RELOGIN.includes(S.sync.err));
const onSync=()=>{try{dispatchEvent(new Event('sync'))}catch(e){}};
const synced=()=>{S.sync={at:Date.now()};saveLocal();onSync()};
const refused=e=>{S.sync={...(S.sync||{}),err:e||'net',errAt:Date.now()};saveLocal();onSync()};
function touch(){if(!API||!S.u)return;dirty=1;clearTimeout(syncT);syncT=setTimeout(push,2500)}
/* resolves true when nothing is left to save. One save at a time; a save that failed is tried again by itself
   (5 s, 10 s, ... up to a minute) and as soon as the connection is back, not only at the pupil's next answer. */
export function push(){
 if(inflight)return inflight.then(()=>push());
 clearTimeout(syncT);clearTimeout(retryT);if(!dirty||!API||!S.u)return Promise.resolve(true);
 dirty=0;
 inflight=(async()=>{let r=null;try{r=await api('save',{...cred(),s:pack()})}catch(e){}
  inflight=null;
  if(r&&r.ok){retryN=0;fatal=false;synced();return true}
  dirty=1;fatal=!!(r&&FATAL.includes(r.e));refused(r&&r.e);
  if(!fatal)retryT=setTimeout(push,Math.min(60000,5000*2**retryN++));
  return false})();
 return inflight}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')push()});
addEventListener('online',()=>{push()});
/* ---------- two devices, one pupil ----------
   The record on the server and the one on this device are joined so that nothing earned is ever lost:
   the higher star count of every level, the higher knowledge of every word, the higher points. */
const dnum=d=>{const p=String(d||'').split('-').map(Number);return p.length===3&&!p.some(isNaN)?p[0]*10000+p[1]*100+p[2]:0};
const sum=o=>Object.values(o||{}).reduce((a,v)=>a+(+v||0),0);
const sig=o=>[+o.pts||0,sum(o.g&&o.g.st),sum(o.m&&o.m.st),(o.x&&o.x.tries||[]).length,sum(o.w),sum(o.read),Object.keys(o.st||{}).length,o.day||''].join('|');
function merge(r){
 const mx=(a,b)=>{for(const k in b||{})if((+b[k]||0)>(+a[k]||0))a[k]=+b[k]};
 mx(S.w,r.w);mx(S.read,r.read);
 if(r.g&&typeof r.g==='object'){mx(S.g.st,r.g.st);Object.assign(S.g.ob,r.g.ob||{});S.g.plays=Math.max(S.g.plays,+r.g.plays||0)}
 /* mock exam: every finished paper is kept, whichever device it was taken on */
 if(r.x&&typeof r.x==='object'){if(!S.x||typeof S.x!=='object')S.x={};const a=Array.isArray(S.x.tries)?S.x.tries:[],b=Array.isArray(r.x.tries)?r.x.tries:[],at=new Set(a.map(t=>t.at));
  S.x.tries=[...a,...b.filter(t=>t&&!at.has(t.at))].sort((p,q)=>p.at-q.at).slice(-20);S.x.prac=Object.assign({},r.x.prac||{},S.x.prac||{});for(const k in r.x.prac||{})S.x.prac[k]=Math.max(+S.x.prac[k]||0,+r.x.prac[k]||0);
  S.x.seen=[...new Set([...(S.x.seen||[]),...(r.x.seen||[])])].slice(-400)}
 if(r.m&&typeof r.m==='object'){if(!S.m||typeof S.m!=='object')S.m={st:{},plays:0};if(!S.m.st)S.m.st={};mx(S.m.st,r.m.st);S.m.plays=Math.max(+S.m.plays||0,+r.m.plays||0)}
 for(const k in r.st||{}){const a=S.st[k],b=r.st[k];if(Array.isArray(b)&&(!a||(+b[0]||0)>(+a[0]||0)))S.st[k]=b}
 S.pts=Math.max(S.pts,+r.pts||0);
 const dl=dnum(S.day),dr=dnum(r.day);if(dr>dl){S.day=r.day;S.streak=+r.streak||0}else if(dr===dl)S.streak=Math.max(+S.streak||0,+r.streak||0)}
/* fetch the pupil's record and join it with this device's; resolves true when this device learned something new */
let pullAt=0;
export async function pull(){
 if(!API||!S.u||Date.now()-pullAt<60000)return false;pullAt=Date.now();
 const u=S.u;let r;try{r=await api('login',cred())}catch(e){return false}
 if(r&&!r.ok&&S.u===u&&FATAL.includes(r.e)){fatal=true;refused(r.e);return true}   // the account no longer takes this device's progress: ask to sign in again
 if(!r||!r.ok||S.u!==u)return false;
 if(S.sync&&S.sync.err&&RELOGIN.includes(S.sync.err)){S.sync={at:Date.now()};onSync()}
 const rs=r.s||{},before=sig(S);merge(rs);fix();saveLocal();
 if(sig(S)!==sig(rs))touch();
 return sig(S)!==before}
export async function auth(mode,c,n,p){
 let r;try{r=await api(mode,{c,n,p})}catch(e){r={e:'net'}}
 if(!r.ok)return ERR[r.e]||ERR.net;
 newPin=r.newpin?p:'';   // the code was reset: these digits are the pupil's new code
 const o=S,mine=o.u?{n:o.u.n,s:pack()}:o.stash||null;
 S=Object.assign(blank(),{parts:o.parts,dir:o.dir,cnt:o.cnt,ct:o.ct,ccnt:o.ccnt,ctypes:o.ctypes},r.s||{},{u:{c,n,p},lastC:c});delete S.k;delete S.stash;delete S.sync;fix();dirty=0;fatal=false;pullAt=Date.now();
 /* the same pupil signing in again (same name, or the same first name after the sheet was tidied): nothing this device
    earned is lost. Someone else signing in on a shared device does not get it; it waits on the device for its owner. */
 if(mine&&sameKid(mine.n,n)){const before=sig(r.s||{});merge(mine.s);fix();if(sig(S)!==before)touch()}
 else if(mine&&hasProgress(mine.s))S.stash=mine;
 S.sync={at:Date.now()};saveLocal();onSync();return null}
let newPin='';
export const takeNewPin=()=>{const p=newPin;newPin='';return p};
const norm=x=>String(x||'').trim().replace(/\s+/g,' ');
export const sameKid=(a,b)=>{a=norm(a);b=norm(b);return!!a&&(a===b||a.split(' ')[0]===b.split(' ')[0])};
const hasProgress=s=>!!s&&((+s.pts||0)>0);
/* sign in again after a refusal: what this device earned is put aside and joined in when the same pupil signs in */
export function relogin(){const u=S.u;if(!u)return null;S.stash={n:u.n,s:pack()};clearTimeout(syncT);clearTimeout(retryT);const e=(S.sync&&S.sync.err)||'';S.u=null;dirty=0;fatal=false;delete S.sync;saveLocal();onSync();return{c:u.c,n:u.n,e}}
/* resolves false, and keeps the pupil signed in, while progress is still waiting to be saved (no connection):
   signing out would erase it. A record the server refuses for good (the teacher removed the pupil) does not hold anyone back. */
export async function logout(){const ok=await push();if(!ok&&!fatal)return false;
 clearTimeout(syncT);clearTimeout(retryT);const c=S.lastC,keep=fatal&&hasProgress(pack())?{n:S.u.n,s:pack()}:S.stash||null;   // a refused record is not thrown away: it waits for its owner to sign in
 S=Object.assign(blank(),{lastC:c},keep?{stash:keep}:{});dirty=0;fatal=false;saveLocal();onSync();return true}

/* ---------- points, streak, word knowledge ---------- */
const dstr=d=>d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate();
export function award(n){const t=dstr(new Date());if(S.day!==t){const y=new Date();y.setDate(y.getDate()-1);S.streak=S.day===dstr(y)?(S.streak||0)+1:1;S.day=t;S.pts+=T.ptsDay}S.pts+=Math.max(0,n|0);save()}
/* same bookkeeping as the trainer: S.w = knowledge 0..3, S.st = [tries, wrong] feeds the teacher's "hardest words" */
export function mark(w,ok){S.w[w.en]=ok?Math.min(3,(S.w[w.en]||0)+1):0;const t=S.st[w.en]||[0,0];S.st[w.en]=[t[0]+1,t[1]+(ok?0:1)];award(ok?T.ptsFirst:T.ptsLater)}

/* ---------- stars and unlocks ---------- */
export const starsOf=(isl,type)=>S.g.st[levelKey(isl,type)]||0;
export const islandStars=i=>i.levels.reduce((a,[t])=>a+starsOf(i.id,t),0);
export const totalStars=()=>ISLANDS.reduce((a,i)=>a+islandStars(i),0);
export const isOpen=i=>totalStars()>=i.need;
export function setStars(isl,type,n){const k=levelKey(isl,type),before=totalStars(),was=ISLANDS.filter(isOpen).map(i=>i.id);
 if(n>(S.g.st[k]||0))S.g.st[k]=n;S.g.plays++;award(n*T.ptsStar);
 return{gained:totalStars()-before,opened:ISLANDS.filter(i=>isOpen(i)&&!was.includes(i.id))}}

/* ---------- speech: the recorded voice first (js/voice.js), the browser's own voice as the fallback ---------- */
const SYNTH='speechSynthesis' in window&&'SpeechSynthesisUtterance' in window;
export const TTS=SYNTH||HAS_CLIPS;   // "this device can speak": true wherever clips exist, even with no speech engine
let voice=null;
function pickVoice(){try{const vs=speechSynthesis.getVoices();voice=vs.find(v=>/en[-_]US/i.test(v.lang)&&/samantha|google us|aria|jenny/i.test(v.name))||vs.find(v=>/en[-_]US/i.test(v.lang))||vs.find(v=>/^en/i.test(v.lang))||null}catch(e){}}
if(SYNTH){pickVoice();try{speechSynthesis.addEventListener('voiceschanged',pickVoice)}catch(e){}}
/* browser voice; resolves true if it really started speaking (with wait: when it finished), false if it could not */
function synth(text,rate,wait){return new Promise(res=>{
 if(!SYNTH)return res(false);
 try{speechSynthesis.cancel();if(!voice)pickVoice();
  const u=new SpeechSynthesisUtterance(text);u.lang='en-US';if(voice)u.voice=voice;u.rate=rate||T.ttsRate;
  let done=0;const fin=v=>{if(!done){done=1;res(v)}};
  let begun=0;u.onstart=()=>{begun=1;if(!wait)fin(true)};u.onend=()=>fin(true);u.onerror=()=>fin(false);
  /* slow engines (Android cold start) may need a moment: only give up if nothing is speaking or queued */
  setTimeout(()=>{let busy=false;try{busy=speechSynthesis.speaking||speechSynthesis.pending}catch(e){}if(wait&&(busy||begun))return;if(busy)setTimeout(()=>fin(true),1500);else fin(false)},1600);
  if(wait)setTimeout(()=>fin(true),8000+text.length*150);   // some engines never report the end
  speechSynthesis.speak(u)}catch(e){res(false)}})}
const synthStop=()=>{if(SYNTH)try{speechSynthesis.cancel()}catch(e){}};

/* ---------- recorded clips ----------
   A clip is {url,s,e}: the file and the stretch of it that holds the words (seconds, from js/voice.js).
   Main path: Web Audio. The file is fetched and decoded once, the stretch is cut out with a little air around it,
   levelled, cached, and scheduled a moment ahead on the game's own (already running) audio context with short fades,
   so a phone does not swallow the first sounds of a word. Fallback: one shared <audio> element, then the browser voice. */
const LEAD=.03,TAIL=.08,FADE_IN=.012,FADE_OUT=.04,AHEAD=.08,LOAD_MS=3000,CAP=60;
const BUF=new Map();   // url -> Promise<AudioBuffer|null>, least recently used first
const wait=ms=>new Promise(r=>setTimeout(r,ms));
/* cut [s-LEAD, e+TAIL] out of the decoded file and bring its peak to a common level */
function cut(ctx,full,c){const sr=full.sampleRate,D=full.duration,a=Math.max(0,(c.s||0)-LEAD),b=Math.min(D,(c.e>c.s?c.e:D)+TAIL),
  i0=Math.floor(a*sr),n=Math.max(1,Math.min(full.length-i0,Math.ceil((b-a)*sr))),out=ctx.createBuffer(1,n,sr),o=out.getChannelData(0),ch=full.numberOfChannels;
 for(let k=0;k<ch;k++){const d=full.getChannelData(k);for(let i=0;i<n;i++)o[i]+=d[i0+i]/ch}
 let pk=0;for(let i=0;i<n;i++){const v=o[i]<0?-o[i]:o[i];if(v>pk)pk=v}
 if(pk>.01){const g=Math.min(3,.7/pk);for(let i=0;i<n;i++)o[i]*=g}
 return out}
let active=0;const queue=[];
function pump(){while(active<3&&queue.length){const job=queue.shift();active++;job().then(()=>{active--;pump()})}}
/* fetch + decode + cut, at most three downloads at a time; a clip asked for again moves to the front of the cache */
function loadClip(c,urgent){let p=BUF.get(c.url);if(p){BUF.delete(c.url);BUF.set(c.url,p);if(urgent&&p.jump)p.jump();return p}
 const ctx=voiceCtx();if(!ctx||!window.fetch)return Promise.resolve(null);
 let go;p=new Promise(res=>{let begun=0;
  const run=()=>{if(begun)return Promise.resolve();begun=1;
   return fetch(c.url,{mode:'cors'}).then(r=>{if(!r.ok)throw 0;return r.arrayBuffer()})
    .then(ab=>new Promise((ok,no)=>{const q=ctx.decodeAudioData(ab,ok,no);if(q&&q.catch)q.catch(no)}))
    .then(full=>{const b=cut(ctx,full,c);b.clip=c;res(b)},()=>{if(BUF.get(c.url)===p)BUF.delete(c.url);res(null)})};
  go=run;queue.push(run)});
 p.jump=()=>{const i=queue.indexOf(go);if(i>=0){queue.splice(i,1);active++;go().then(()=>{active--;pump()})}};   // the word needed now does not wait in line
 BUF.set(c.url,p);for(const k of BUF.keys()){if(BUF.size<=CAP)break;BUF.delete(k)}
 if(urgent)p.jump();else pump();return p}
let stopClip=null,seq=0,misses=0,retryAt=0;
/* 'end' = played to the end, 'stop' = hushed or replaced by newer speech, 'fail' = could not play */
function playBuf(buf){return new Promise(res=>{
 const ctx=voiceCtx(),out=voiceOut();if(!ctx||!out||ctx.state!=='running')return res('fail');
 if(stopClip)stopClip();
 let src,g;const d=buf.duration,fi=Math.min(FADE_IN,d/4),fo=Math.min(FADE_OUT,d/4),t0=ctx.currentTime+AHEAD;
 try{src=ctx.createBufferSource();g=ctx.createGain();src.buffer=buf;
  g.gain.setValueAtTime(0,t0);g.gain.linearRampToValueAtTime(1,t0+fi);g.gain.setValueAtTime(1,t0+d-fo);g.gain.linearRampToValueAtTime(0,t0+d);
  src.connect(g);g.connect(out)}catch(e){return res('fail')}
 let done=0,t=0;
 const fin=v=>{if(done)return;done=1;clearTimeout(t);src.onended=null;if(stopClip===stop)stopClip=null;duck(false);
   if(v!=='end')try{const n=ctx.currentTime;g.gain.cancelScheduledValues(n);g.gain.setTargetAtTime(0,n,.008);src.stop(n+.06)}catch(e){}
   res(v)},stop=()=>fin('stop');
 stopClip=stop;src.onended=()=>fin('end');t=setTimeout(()=>fin('end'),(AHEAD+d)*1000+300);   // a frozen context must not hold a level
 try{duck(true);src.start(t0)}catch(e){fin('fail')}})}
/* the old way, kept as the fallback: one <audio> element (iOS only lets an element play freely once it has played inside a gesture) */
const SILENCE='data:audio/wav;base64,UklGRkQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YSAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==';
const START_MS=2500;   // a clip that has not started by then is given up and the browser voice speaks instead
let player=null,audioOpen=0;
function getPlayer(){if(!player){player=new Audio();player.preload='auto';player.playsInline=true;player.setAttribute('playsinline','')}return player}
function playEl(c){return new Promise(res=>{
 if(stopClip)stopClip();
 let a;try{a=getPlayer()}catch(e){return res('fail')}
 const from=Math.max(0,(c.s||0)-LEAD),to=c.e>c.s?c.e+TAIL:0;
 let done=0,t=0;
 const fin=v=>{if(done)return;done=1;clearTimeout(t);a.removeEventListener('ended',onEnd);a.removeEventListener('error',onErr);a.removeEventListener('playing',onPlay);a.removeEventListener('timeupdate',onTime);
   if(stopClip===stop)stopClip=null;if(v!=='end'||to)try{a.pause()}catch(e){}res(v)},
  onEnd=()=>fin('end'),onErr=()=>fin('fail'),stop=()=>fin('stop'),onTime=()=>{if(to&&a.currentTime>=to)fin('end')},
  /* once it plays, only a stalled stream can keep the end away: do not let a level wait for ever */
  onPlay=()=>{audioOpen=1;clearTimeout(t);t=setTimeout(()=>fin('end'),((to?to-from:isFinite(a.duration)&&a.duration>0?a.duration:20)+4)*1000)};
 stopClip=stop;a.addEventListener('ended',onEnd);a.addEventListener('error',onErr);a.addEventListener('playing',onPlay);a.addEventListener('timeupdate',onTime);
 t=setTimeout(()=>fin('fail'),START_MS);
 try{a.src=c.url+(to?'#t='+from.toFixed(2)+','+to.toFixed(2):'');const p=a.play();if(p&&p.catch)p.catch(()=>fin('fail'))}catch(e){fin('fail')}})}
/* Web Audio first; if the clip cannot be fetched or decoded within 3 s, or the context is not running, the <audio> element */
async function playClip(c,my){
 if(stopClip)stopClip();
 const ctx=voiceCtx();
 if(ctx){
  if(ctx.state!=='running')await Promise.race([ctx.resume().catch(()=>{}),wait(400)]);
  if(my===seq&&ctx.state==='running'){
   const buf=await Promise.race([loadClip(c,true),wait(LOAD_MS).then(()=>null)]);
   if(my!==seq)return 'stop';
   if(buf){const r=await playBuf(buf);if(r!=='fail')return r}}}
 if(my!==seq)return 'stop';
 return playEl(c)}
/* after two clips in a row could not play (offline, storage gone) go straight to the browser voice for a while */
const clipFor=text=>misses>=2&&Date.now()<retryAt?null:clipOf(text);
const missed=()=>{misses++;retryAt=Date.now()+30000};
/* speak one text. Resolves true when it was spoken (a clip: when it ended or was interrupted; browser voice: when it started),
   false if this device could not say it (used by the listening level). */
export async function say(text,rate){const my=++seq;
 const c=clipFor(text);
 if(c){synthStop();const r=await playClip(c,my);if(r==='end'){misses=0;return true}if(r==='stop')return true;missed()}
 else if(stopClip)stopClip();
 return synth(text,rate)}
/* speak several texts in order with a short breath between them ("read to me"); hush() or any newer speech stops it.
   A part without a clip (or whose clip fails) is read by the browser voice, then the clips carry on. */
export async function sayAll(parts,rate,gap=380){const my=++seq;if(stopClip)stopClip();synthStop();
 for(const part of parts){
  const c=clipFor(part);let r=c?await playClip(c,my):'none';
  if(my!==seq||r==='stop')return true;
  if(r==='fail')missed();else if(r==='end')misses=0;
  if(r!=='end'){await synth(part,rate,true);if(my!==seq)return true}
  await wait(gap);if(my!==seq)return true}
 return true}
export function hush(){seq++;if(stopClip)stopClip();synthStop()}
/* fetch and decode a level's clips ahead of time, in the order given */
export function warm(texts){for(const x of texts){const c=clipOf(x);if(c)loadClip(c)}}
/* resolves when the clip of this text is decoded and ready to play at once, or after ms (also when it has no clip) */
export function ready(text,ms=LOAD_MS){const c=clipFor(text);if(!c||!voiceCtx())return Promise.resolve(false);
 return Promise.race([loadClip(c,true).then(b=>!!b),wait(ms).then(()=>false)])}
/* first gesture: wake the speech engine and let the shared <audio> element play (iOS needs both inside a gesture);
   the audio context itself is resumed by unlock() in js/audio.js in the same gesture */
let synthOpen=0;
export function unlockTTS(){
 if(SYNTH&&!synthOpen){synthOpen=1;try{const u=new SpeechSynthesisUtterance(' ');u.volume=0;u.lang='en-US';speechSynthesis.speak(u)}catch(e){}}
 if(HAS_CLIPS&&!audioOpen&&!stopClip)try{const a=getPlayer();a.src=SILENCE;const p=a.play();if(p&&p.then)p.then(()=>{audioOpen=1},()=>{});else audioOpen=1}catch(e){}}

export const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const shuffle=a=>{a=[...a];for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a};
/* weakest words first, with a little shuffle inside equal knowledge */
export const weakest=(ws,n)=>shuffle(ws).sort((a,b)=>(S.w[a.en]||0)-(S.w[b.en]||0)).slice(0,n);
export const reduced=()=>SET.calm||matchMedia('(prefers-reduced-motion:reduce)').matches;
export const applyCalm=()=>document.documentElement.classList.toggle('calm',!!SET.calm);
applyCalm();
