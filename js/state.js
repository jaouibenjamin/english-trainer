/* State, class backend client (same contract as the classic trainer) and speech. */
import {WORDS,TEXTS,ISLANDS,T,levelKey} from './data.js';
import {clipOf,HAS_CLIPS} from './voice.js';

export const KEY='aam-unit1-v1';          // shared with trainer.html so both keep one progress record
const SET_KEY='word-islands-settings-v1'; // device-only preferences
const blankG=()=>({st:{},ball:0,ob:{},plays:0});
export const blank=()=>({w:{},read:{},parts:[1,2,3,4,5],dir:'en-he',cnt:10,me:[],ct:3,ccnt:15,ctypes:['en-he','he-en','tobe'],pts:0,st:{},day:'',streak:0,u:null,lastC:'',g:blankG()});
export let S=blank();
function load(){try{Object.assign(S,JSON.parse(localStorage.getItem(KEY))||{})}catch(e){}fix()}
function fix(){if(!S.g||typeof S.g!=='object')S.g=blankG();const g=S.g;if(!g.st||typeof g.st!=='object')g.st={};if(!g.ob||typeof g.ob!=='object')g.ob={};g.ball=+g.ball||0;g.plays=+g.plays||0;
 for(const k of['w','read','st'])if(!S[k]||typeof S[k]!=='object')S[k]={};S.pts=+S.pts||0}
load();
export const saveLocal=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}};
export const save=()=>{saveLocal();touch()};

export const SET={music:true,sfx:true};
try{Object.assign(SET,JSON.parse(localStorage.getItem(SET_KEY))||{})}catch(e){}
export const saveSet=()=>{try{localStorage.setItem(SET_KEY,JSON.stringify(SET))}catch(e){}};

/* ---------- class backend (Google Sheet via Apps Script) ---------- */
export const API=(window.API_URL||'').trim();
export const ERR={class:'קוד הכיתה לא נכון.',pin:'הקוד הסודי לא נכון. נסו שוב.',nouser:'לא מצאנו את השם הזה בכיתה. עוד לא נרשמתם?',taken:'השם הזה כבר רשום. לא אתם? הוסיפו אות משם המשפחה. זה אתם?',locked:'יותר מדי ניסיונות.\nחכו 5 דקות ונסו שוב.',full:'הכיתה מלאה. פנו למורה.',input:'צריך קוד כיתה, שם באותיות\nוקוד סודי של 4 ספרות.',teacher:'קוד המורה לא נכון.',setup:'המערכת עוד לא הוגדרה.',net:'אין חיבור כרגע.\nבדקו את האינטרנט ונסו שוב.'};
export async function api(a,d){const r=await fetch(API,{method:'POST',body:JSON.stringify({a,...d}),keepalive:a==='save'});return r.json()}
export const cred=()=>({c:S.u.c,n:S.u.n,p:S.u.p});
export const wordsKnown=()=>WORDS.filter(w=>w.p<6&&(S.w[w.en]||0)>=2).length;
const pack=()=>({w:S.w,read:S.read,st:S.st,pts:S.pts,day:S.day,streak:S.streak,me:S.me,g:S.g,k:{words:wordsKnown(),reads:TEXTS.filter(t=>S.read[t.id]===t.qs.length).length}});
let dirty=0,syncT=0;
function touch(){if(!API||!S.u)return;dirty=1;clearTimeout(syncT);syncT=setTimeout(push,2500)}
export async function push(){clearTimeout(syncT);if(!dirty||!API||!S.u)return;dirty=0;try{const r=await api('save',{...cred(),s:pack()});if(!r.ok)dirty=1}catch(e){dirty=1}}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')push()});
export async function auth(mode,c,n,p){
 let r;try{r=await api(mode,{c,n,p})}catch(e){r={e:'net'}}
 if(!r.ok)return ERR[r.e]||ERR.net;
 const o=S;S=Object.assign(blank(),{parts:o.parts,dir:o.dir,cnt:o.cnt,ct:o.ct,ccnt:o.ccnt,ctypes:o.ctypes},r.s||{},{u:{c,n,p},lastC:c});delete S.k;fix();dirty=0;saveLocal();return null}
export async function logout(){await push();const c=S.lastC;S=Object.assign(blank(),{lastC:c});dirty=0;saveLocal()}

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

/* One <audio> element plays every clip: iOS only lets an element play freely once it has played inside a gesture. */
const SILENCE='data:audio/wav;base64,UklGRkQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YSAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==';
const START_MS=2500;   // a clip that has not started by then is given up and the browser voice speaks instead
let player=null,stopClip=null,seq=0,misses=0,retryAt=0,audioOpen=0;
function getPlayer(){if(!player){player=new Audio();player.preload='auto';player.playsInline=true;player.setAttribute('playsinline','')}return player}
/* 'end' = played to the end, 'stop' = hushed or replaced by newer speech, 'fail' = error or no start in time */
function playClip(url){return new Promise(res=>{
 if(stopClip)stopClip();
 let a;try{a=getPlayer()}catch(e){return res('fail')}
 let done=0,t=0;
 const fin=v=>{if(done)return;done=1;clearTimeout(t);a.removeEventListener('ended',onEnd);a.removeEventListener('error',onErr);a.removeEventListener('playing',onPlay);
   if(stopClip===stop)stopClip=null;if(v!=='end')try{a.pause()}catch(e){}res(v)},
  onEnd=()=>fin('end'),onErr=()=>fin('fail'),stop=()=>fin('stop'),
  /* once it plays, only a stalled stream can keep 'ended' away: do not let a level wait for ever */
  onPlay=()=>{audioOpen=1;clearTimeout(t);t=setTimeout(()=>fin('end'),((isFinite(a.duration)&&a.duration>0?a.duration:20)+4)*1000)};
 stopClip=stop;a.addEventListener('ended',onEnd);a.addEventListener('error',onErr);a.addEventListener('playing',onPlay);
 t=setTimeout(()=>fin('fail'),START_MS);
 try{a.src=url;const p=a.play();if(p&&p.catch)p.catch(()=>fin('fail'))}catch(e){fin('fail')}})}
/* after two clips in a row could not play (offline, storage gone) go straight to the browser voice for a while */
const clipFor=text=>misses>=2&&Date.now()<retryAt?null:clipOf(text);
const missed=()=>{misses++;retryAt=Date.now()+30000};
/* speak one text. Resolves true when it was spoken (a clip: when it ended or was interrupted; browser voice: when it started),
   false if this device could not say it (used by the listening level). */
export async function say(text,rate){seq++;
 const url=clipFor(text);
 if(url){synthStop();const r=await playClip(url);if(r==='end'){misses=0;return true}if(r==='stop')return true;missed()}
 else if(stopClip)stopClip();
 return synth(text,rate)}
/* speak several texts in order with a short breath between them ("read to me"); hush() or any newer speech stops it.
   A part without a clip (or whose clip fails) is read by the browser voice, then the clips carry on. */
export async function sayAll(parts,rate,gap=380){const my=++seq;if(stopClip)stopClip();synthStop();
 for(const part of parts){
  const url=clipFor(part);let r=url?await playClip(url):'none';
  if(my!==seq||r==='stop')return true;
  if(r==='fail')missed();else if(r==='end')misses=0;
  if(r!=='end'){await synth(part,rate,true);if(my!==seq)return true}
  await new Promise(d=>setTimeout(d,gap));if(my!==seq)return true}
 return true}
export function hush(){seq++;if(stopClip)stopClip();synthStop()}
/* fetch a level's clips ahead of time (separate elements, the shared player then finds them in the HTTP cache) */
const warmed=new Map();
export function warm(texts){for(const x of texts){const u=clipOf(x);if(!u||warmed.has(u))continue;
  try{const a=new Audio();a.preload='auto';a.src=u;warmed.set(u,a)}catch(e){}}
 for(const [u,a] of warmed){if(warmed.size<=48)break;try{a.removeAttribute('src');a.load()}catch(e){}warmed.delete(u)}}
/* first gesture: wake the speech engine and let the shared <audio> element play (iOS needs both inside a gesture) */
let synthOpen=0;
export function unlockTTS(){
 if(SYNTH&&!synthOpen){synthOpen=1;try{const u=new SpeechSynthesisUtterance(' ');u.volume=0;u.lang='en-US';speechSynthesis.speak(u)}catch(e){}}
 if(HAS_CLIPS&&!audioOpen&&!stopClip)try{const a=getPlayer();a.src=SILENCE;const p=a.play();if(p&&p.then)p.then(()=>{audioOpen=1},()=>{});else audioOpen=1}catch(e){}}

export const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const shuffle=a=>{a=[...a];for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a};
/* weakest words first, with a little shuffle inside equal knowledge */
export const weakest=(ws,n)=>shuffle(ws).sort((a,b)=>(S.w[a.en]||0)-(S.w[b.en]||0)).slice(0,n);
export const reduced=()=>matchMedia('(prefers-reduced-motion:reduce)').matches;
