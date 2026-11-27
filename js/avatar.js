/* The new world in the live game, behind the design flag (?ds=1, js/dsflag.js): the pupil's character and its name,
   the energy level, and today's focus on the English map. main.js loads this file only when the flag is on, so with the
   flag off nothing of it is fetched, drawn or stored.

   Storage: local to this device, in its own key (wi_world), one record per pupil on the device. It is NOT part of the
   progress record that pack()/merge() send to the class's sheet, and this file makes no request of any kind.
   A signed-in pupil's record is filed under a SHA-256 digest of the class code (upper case) and the name (trimmed,
   spaces collapsed), never under the code or the name themselves; on a device that is not signed in, under 'local'.
   Every await is followed by a check that the same pupil is still signed in before anything is written (LESSONS.md 1).
   - avatar: one of the 20 ids in js/world_data.js. Locked characters open with the energy level.
   - name: two indexes into the two fixed word lists (no free text: nothing a pupil types is stored or shown), and the
     lists' version (nv). A name kept from earlier lists (no nv, or another one) reads as "no name yet", so nobody is
     given a different name silently.
   - sl: the highest level whose new character the map has already announced ("דמות חדשה נפתחה!" shows once).
   - a pupil keeps a character chosen earlier even if it would be locked at their level now: nothing is taken away.
   - energy: only goes up. It is worked out from what the pupil has learned (English stars, words known, stories read,
     Fraction Bay stars) and kept
     as the highest value seen, so a word that is forgotten again never takes energy away.
   DOM is built with createElement and textContent only. */
import {S,API,totalStars,wordsKnown,isOpen,starsOf} from './state.js';
import {ISLANDS,WORDS,MAX_STARS,TEXTS,LEVEL_INFO} from './data.js';
import {stars as starRow} from './ui.js';
import {pathPoints,stone} from './worldpath.js';
import {ART} from './world_art.js';
import {AVATARS,NAME_A,NAME_B,NAME_V} from './world_data.js';
import * as WD from './world_data.js';   // ENERGY and SOON are newer than the last ship: read through the namespace, so a phone
                                        // still holding the old world_data.js keeps the old ladder (tests/cache_mix.py)
const ENERGY=WD.ENERGY??{worth:{star:10,word:5,story:5,mstar:0},levels:[0,40,90,150,220,300,380,460,540,620,700,760,820],after:250};
const SOON=WD.SOON??[];
/* every character the picker can show: the first twenty, and the ten of levels 14 to 23 (MORE, newer than the last
   ship, so read through the namespace), each only where its picture is known (an older js/world_art.js has none for
   the ten: they stay "soon" there) */
const ALL=[...AVATARS,...(WD.MORE??[])].filter(a=>!!ART['av/'+a.id]);
/* the eagle was called a griffin while it was being drawn; a character stored under that name is the eagle */
const avId=v=>v==='griffin'?'eagle':v;
import {M_ISLANDS,M_MAX} from './mdata.js';
import {playAv,canMove} from './avanim.js';

const KEY='wi_world';
/* energy: what each thing learned is worth and the level thresholds, in one table (js/world_data.js ENERGY). Every
   threshold is at or below the earlier ones (0,120,220,340,480,640,820,1020), and levels 1 to 13 never moved, so a
   level shown on a device never goes down. */
const WORTH=ENERGY.worth;
export const LEVELS=ENERGY.levels;
/* The most energy a pupil can earn with today's content: every English star, every word of the unit known, every
   story read, every Fraction Bay star (10 x 66 + 5 x 59 + 5 x 5 + 20 x 33 = 1640). REVISIT THE LADDER when content adds
   energy: the last character must stay reachable, and should not come too early either. tests/world.py fails if the
   level that opens the last character (or the last "soon" level) is above this, or within reach of English alone. */
export const MAX_ENERGY=WORTH.star*MAX_STARS+WORTH.word*WORDS.filter(w=>w.p<6).length+WORTH.story*TEXTS.length+WORTH.mstar*M_MAX;
/* Fraction Bay's stars: the best stars per level, from the math record the game already keeps (S.m.st) */
const mathStars=()=>{const st=(S.m&&S.m.st)||{};let n=0;for(const i of M_ISLANDS)for(const t of i.levels)n+=Math.min(3,Math.max(0,Math.floor(+st[i.id+'-'+t]||0)));return Math.min(M_MAX,n)};
const FOCUS_MAX=5;
const EN_MAX=100000;   // a stored energy above this is read as this (a damaged or edited record must not freeze the map)

/* ---------- storage ---------- */
/* who is playing: the class code in upper case and the name as sameKid() in state.js reads it (trimmed, spaces collapsed) */
const pupil=()=>API&&S.u?{c:String(S.u.c||'').trim().toUpperCase(),n:String(S.u.n||'').trim().replace(/\s+/g,' ')}:null;
/* the record's key: 'local', or 'h:' and the SHA-256 of 'wi|'+code+'|'+name. Null when the browser has no digest
   (an insecure page): then nothing is read or written. */
async function ident(){const u=pupil();if(!u)return{key:'local',u:null};
 try{const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode('wi|'+u.c+'|'+u.n));
  return{key:'h:'+[...new Uint8Array(d)].map(b=>b.toString(16).padStart(2,'0')).join(''),u}}catch(e){return{key:null,u}}}
/* still the same pupil as when the key was made? (checked before every write: the pupil may have signed out or another
   signed in while a digest was being made) */
const same=id=>{const u=pupil();return id.u?!!u&&u.c===id.u.c&&u.n===id.u.n:!u};
function readAll(){try{const o=JSON.parse(localStorage.getItem(KEY)||'null');return o&&typeof o==='object'&&o.v===1&&o.p&&typeof o.p==='object'&&!Array.isArray(o.p)?o:{v:1,p:{}}}catch(e){return{v:1,p:{}}}}
function mine(id){const r=id.key&&Object.prototype.hasOwnProperty.call(readAll().p,id.key)?readAll().p[id.key]:null;const m=r&&typeof r==='object'?r:{};
 return{av:ALL.some(a=>a.id===avId(m.av))?avId(m.av):null,
  nm:m.nv===NAME_V&&Array.isArray(m.nm)&&Number.isInteger(m.nm[0])&&Number.isInteger(m.nm[1])&&NAME_A[m.nm[0]]&&NAME_B[m.nm[1]]?[m.nm[0],m.nm[1]]:null,
  en:typeof m.en==='number'&&Number.isFinite(m.en)&&m.en>0?Math.min(EN_MAX,Math.floor(m.en)):0,
  sl:Number.isInteger(m.sl)&&m.sl>0&&m.sl<1000?m.sl:0,
  at:Number.isInteger(m.at)&&ISLANDS.some(i=>i.id===m.at&&isOpen(i))?m.at:0}}   // the island the character last stood on (for the hop); an island not open (yet) is no position
const KEY_OK=/^(local|h:[0-9a-f]{64})$/;   // the only keys a record may have; anything else is dropped on the next write
/* only the known fields, and a name always with the lists' version */
const clean=r=>{const o={av:r.av,nm:r.nm,en:r.en};if(r.nm)o.nv=NAME_V;if(r.sl)o.sl=r.sl;if(r.at)o.at=r.at;return o};
function keep(id,rec){if(!id.key||!same(id))return false;try{const all=readAll(),p={};for(const k of Object.keys(all.p))if(KEY_OK.test(k))p[k]=all.p[k];p[id.key]=clean(rec);localStorage.setItem(KEY,JSON.stringify({v:1,p}));return true}catch(e){return false}}

/* ---------- energy: only goes up ---------- */
export const earned=()=>WORTH.star*totalStars()+WORTH.word*wordsKnown()+WORTH.story*Object.values(S.read||{}).filter(v=>v>0).length+WORTH.mstar*mathStars();
const LAST=LEVELS[LEVELS.length-1];
const step=n=>n<LEVELS.length?LEVELS[n]:LAST+ENERGY.after*(n-LEVELS.length+1);
/* the level, worked out (not counted up one by one): inside the list by search, past it by division */
const levelOf=pts=>pts>=LAST?LEVELS.length+Math.floor((pts-LAST)/ENERGY.after):LEVELS.findIndex(t=>t>pts);
function energyOf(id){const r=mine(id),pts=Math.min(EN_MAX,Math.max(r.en,earned()));
 if(pts!==r.en)keep(id,{...r,en:pts});
 const level=levelOf(pts);
 const opens=ALL.some(a=>a.open===level+1)?'נפתחת דמות חדשה':'עוד רמה בדרך';
 /* the most English can still bring is the English maximum plus the math already done: when that is below the next
    level, only Fraction Bay can take the pupil there, and the note says so */
 // only when math can still earn energy (a cached world_data.js older than the ladder gives it 0) and the pupil still has
 // math stars to win
 const mathOnly=WORTH.mstar>0&&mathStars()<M_MAX&&MAX_ENERGY-WORTH.mstar*M_MAX+WORTH.mstar*mathStars()<step(level);
 return{points:pts,level,from:step(level-1),next:step(level),opens,mathOnly}}

/* ---------- today's focus: words the pupil got wrong and does not know yet, on the open island with the most ---------- */
/* The bonus island (months and numbers) is left out on purpose: today's focus is about the unit's five word lists. */
export function focus(){
 const weak=WORDS.filter(w=>w.p<6&&((S.st||{})[w.en]||[0,0])[1]>0&&((S.w||{})[w.en]||0)<2);
 let best=null;
 for(const i of ISLANDS){if(i.bonus||!isOpen(i))continue;const parts=new Set(i.levels.map(l=>l[1]));const n=weak.filter(w=>parts.has(w.p)).length;
  if(n&&(!best||n>best.count))best={island:i.id,he:i.he,count:n}}
 return best&&{...best,count:Math.min(FOCUS_MAX,best.count)}}

/* what a tap on a locked character says (one neutral form, no gender slash), also its accessible name */
const lockedSay=(a,level)=>{const n=a.open-level;return a.he+': אפשר לפתוח ברמה '+a.open+' (עוד '+(n===1?'רמה אחת':n+' רמות')+'). מרוויחים אנרגיה כשלומדים, ואף פעם לא מפסידים אותה.'};

/* ---------- small DOM helpers ---------- */
function el(tag,cls,txt){const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}
function pic(id,cls){const i=el('img',cls);i.src=ART['av/'+id];i.alt='';i.decoding='async';i.draggable=false;return i}
function btn(cls,txt,fn){const b=el('button',cls,txt);b.type='button';b.addEventListener('click',fn);return b}
const ltr=t=>{const b=el('bdi',null,t);b.dir='ltr';return b};
const nameText=nm=>NAME_A[nm[0]].en+' '+NAME_B[nm[1]].en;
/* the two style sheets, added once; the promise settles when both have loaded (or failed), for what is measured after */
let styled=null;
function style(){if(styled)return styled;const w=[];for(const h of['css/worldpath.css','css/avatar.css']){const l=document.createElement('link');l.rel='stylesheet';l.href=h;
 w.push(new Promise(r=>{l.onload=l.onerror=r}));document.head.appendChild(l)}return styled=Promise.all(w)}

/* ---------- the map: a dock along the bottom (main.js keeps that room free): my character and name, my energy level,
   and today's focus ---------- */
export async function decorateMap(view,go,live=()=>true){
 const id=await ident();
 const sec=view.querySelector('.scr.map');if(!live()||!same(id)||!sec||sec.querySelector('.wd'))return;
 style();
 const me=mine(id),E=energyOf(id),F=focus();
 const dock=el('div','wd');
 /* without a digest (a browser with no crypto.subtle) a character could not be kept: say so instead of offering one */
 const meB=id.key?btn('wd__me',null,()=>go('avatar')):el('span','wd__me wd__me--off');
 if(me.av)meB.appendChild(pic(me.av,'wd__pic'));else if(id.key)meB.appendChild(el('span','wd__pic wd__pic--none','?'));   // no "?" ring where nothing can be chosen
 const txt=el('span','wd__txt');
 if(me.av&&me.nm){const hi=el('span','wd__hi');for(const w of nameText(me.nm).split(' '))hi.appendChild(ltr(w));txt.appendChild(hi)}   // one word per line
 else txt.appendChild(el('span','wd__hi',!id.key?'במכשיר הזה אין דמויות. משחקים כרגיל!':me.av?'שלום!':'בוחרים דמות'));
 if(id.key)meB.setAttribute('aria-label',me.av?'הדמות שלי'+(me.nm?': '+nameText(me.nm):''):'בוחרים דמות');
 meB.appendChild(txt);
 const en=btn('wd__en',null,()=>{note.hidden=!note.hidden;en.setAttribute('aria-expanded',note.hidden?'false':'true')});
 en.append(el('b',null,'⚡'),el('span','wd__lvw','רמה'),el('span',null,String(E.level)));   // the word goes on narrow phones (css/avatar.css); the label keeps it
 en.setAttribute('aria-label','רמת אנרגיה '+E.level+'. מה זו אנרגיה?');en.setAttribute('aria-expanded','false');
 const note=el('p','wd__note','מרוויחים אנרגיה כשלומדים, והיא אף פעם לא נגמרת. עוד '+(E.next-E.points)+' אנרגיה לרמה '+(E.level+1)+': '+E.opens+'.'+(E.mathOnly?' גם במפרץ השברים מרוויחים אנרגיה.':''));
 note.hidden=true;note.setAttribute('role','status');
 dock.append(meB,en);
 if(F){const f=btn('wd__focus',null,()=>go('island/'+F.island));
  f.append(el('b',null,'המיקוד להיום'),el('span',null,F.count+' מילים לחזק'));
  f.setAttribute('aria-label','המיקוד להיום: '+F.count+' מילים מ־'+F.he+' שכדאי לחזק. כמה דקות וזהו. מתחילים');
  dock.appendChild(f)}
 /* .wdock on #stage lifts main.js's sync bar above the dock; main.js route() takes it off on the next screen */
 sec.classList.add('hasdock');document.getElementById('stage').classList.add('wdock');sec.append(note,dock);
 const tok=token(sec,id,me,go);   // first, so the notice (if any) is drawn above it
 /* a level that opened a character: said once, with its portrait and the way to the picker. The first visit only
    remembers the level (a device that already had this level is not told about old news). */
 let fresh=[];
 if(id.key){const r=mine(id);
  if(!r.sl)keep(id,{...r,sl:E.level});
  else if(E.level>r.sl){fresh=ALL.filter(a=>a.open>r.sl&&a.open<=E.level);keep(id,{...r,sl:E.level})}}
 if(fresh.length){const a=fresh[fresh.length-1],box=el('div','wnew');box.setAttribute('role','dialog');box.setAttribute('aria-labelledby','wnew-h');
  const h=el('h2','wnew__h',fresh.length>1?'דמויות חדשות נפתחו!':'דמות חדשה נפתחה!');h.id='wnew-h';
  const ok=btn('wnew__ok','לבחירת דמות',()=>go('avatar'));
  const pics=el('div','wnew__pics');for(const x of fresh.slice(-3).reverse())pics.appendChild(pic(x.id,'wnew__pic'));   // the newest first, up to three
  if(fresh.length>3)pics.appendChild(el('span','wnew__more','ועוד '+(fresh.length-3)));
  if(fresh.length>1){pics.classList.add('wnew__pics--many');box.classList.add('wnew--many')}
  box.append(pics,h,el('p','wnew__t',fresh.length>1?fresh.length+' דמויות חדשות מחכות לכם. רוצים להחליף?':a.he+' מחכה לכם. רוצים להחליף?'),ok,btn('wnew__later','אחר כך',()=>{box.remove();const q=sec.querySelector('.wask');if(q)q.hidden=false}));
  sec.appendChild(box);ok.focus({preventScroll:true});style().then(()=>{if(box.isConnected)placeNew(sec,box)})}
 window.__world={avatar:me.av,name:me.nm,energy:E,focus:F,key:id.key,fresh:fresh.map(a=>a.id),token:tok};   // for the tests
 preload(sec);
}
/* The island path's pictures, fetched from the map so an island opens straight onto its path: they start once the
   page and the map's own pictures are in (so they never hold up the map or a first tap), at low priority, and are
   decoded before they count as ready. If the child goes anywhere but an island before they are in, they are dropped
   (and fetched again on the next map). window.__world.pathArt is the promise of it, for the tests. */
const PATH_ART=['bg/english','ui/stone-done','ui/stone-current'];
let pre=null;   // {imgs, ok, done}
function preload(sec){
 if(!pre){
  const P={imgs:{},ok:false,done:null};let stop=false,end;pre=P;
  /* settles once: true when all are in and decoded, false when one fails or the preload is dropped */
  P.done=new Promise(r=>end=r).then(ok=>{P.ok=ok;removeEventListener('hashchange',leave);if(!ok&&pre===P)pre=null;return ok});
  const leave=()=>{if(P.ok||/^#island\//.test(location.hash))return;stop=true;for(const im of Object.values(P.imgs))if(!im.complete)im.removeAttribute('src');end(false)};
  addEventListener('hashchange',leave);
  const after=document.readyState==='complete'?Promise.resolve():new Promise(r=>addEventListener('load',r,{once:true}));
  const own=()=>Promise.all([...sec.querySelectorAll('img')].map(i=>i.complete?0:i.decode().catch(()=>0)));
  after.then(own).then(()=>stop?false:Promise.all(PATH_ART.map(k=>{const im=new Image();im.decoding='async';im.fetchPriority='low';
    im.src=ART[k];P.imgs[k]=im;return im.decode().then(()=>true,()=>false)})).then(a=>a.every(Boolean)&&!stop)).catch(()=>false).then(end)}
 window.__world.pathArt=pre.done}

/* the new-character notice never covers the character on the map (or Pitzi's "?" badge): it sits above the dock, and
   when the character stands there it moves to the band under the map's header. Measured once the style sheets are in,
   from where the token ends up (its left/top), not where a hop shows it now. */
function placeNew(sec,box){const t=sec.querySelector('.wtok,.wask');if(!t)return;
 const x=parseFloat(t.style.left),y=parseFloat(t.style.top),r=t.offsetWidth/2;if(!Number.isFinite(x)||!Number.isFinite(y))return;
 const hit=()=>!(box.offsetLeft+box.offsetWidth<=x-r||box.offsetLeft>=x+r||box.offsetTop+box.offsetHeight<=y-r||box.offsetTop>=y+r);
 const s=sec.getBoundingClientRect();let top=0;for(const e of sec.querySelectorAll('.maphead,.subjpill'))top=Math.max(top,e.getBoundingClientRect().bottom-s.top);
 const at=up=>{box.classList.toggle('wnew--top',up);box.style.top=up?Math.round(top+4)+'px':''};
 /* above the dock; else under the header; on a short screen, the same two without the sentence (the heading says it) */
 for(const tight of [false,true]){box.classList.toggle('wnew--tight',tight);for(const up of [false,true]){at(up);if(!hit())return}}
 box.classList.remove('wnew--tight');at(false);   // no free place on this screen: above the dock, whole, as before
 /* that only happens with Pitzi's "?" badge on a short screen: the notice offers the same choice ("לבחירת דמות"), so the
    badge steps aside while the notice is up, and comes back with "אחר כך" */
 if(t.classList.contains('wask')&&hit())t.hidden=true}

/* ---------- the character on the map ----------
   The chosen character stands on the island the pupil plays now (the one marked "ממשיכים כאן"; when every island is
   full, the last open one), as a small framed portrait in place of the crab. When that island changes, it hops once
   from the island it stood on before, along the dotted line's direction: short, any tap ends it at once, and with
   reduced motion or calm mode it is simply there. With no character yet, Pitzi stands there as today, with a small
   "?" badge that opens the picker. A device that cannot keep a character shows Pitzi alone. */
/* no character yet: Pitzi stands on the island as today, with a small "?" badge by him that opens the picker. The
   island stays the island's button: the badge's 48 px tap area sits beside Pitzi on the sea side, off the island's
   picture or tag; where there is no room for that (a narrow screen), the tap area shrinks to the dot and a few px. */
const ASK=48,ASK_MIN=32;
function ask(sec,isl,go){const c=isl.querySelector('.here');if(!c)return null;const r=c.getBoundingClientRect(),s=sec.getBoundingClientRect();if(!r.width)return null;
 const p=(isl.querySelector('.pw')||isl).getBoundingClientRect(),out=(r.left+r.right)/2<(p.left+p.right)/2?-1:1;   // the sea side: away from the island's middle
 const pics=[...sec.querySelectorAll('.isl .pw,.isl .tag,.isl .hb')].map(e=>e.getBoundingClientRect());   // an island's picture, its tag and the "ממשיכים כאן" pill are all its button
 const free=(x,y,h)=>x-h/2>=s.left&&x+h/2<=s.right&&y-h/2>=s.top&&y+h/2<=s.bottom&&pics.every(q=>x+h/2<=q.left||x-h/2>=q.right||y+h/2<=q.top||y-h/2>=q.bottom);
 /* places by Pitzi, nearest first: on the sea side at his head, his middle, his feet, just above his head and a little
    higher; then under and over him */
 const cx=(r.left+r.right)/2,edge=out<0?p.left:p.right,spots=h=>[r.top+r.height*.1,r.top+r.height*.5,r.bottom,r.top-h/2,r.top-h].map(y=>[out<0?Math.min(cx,edge-h/2):Math.max(cx,edge+h/2),y])
  .concat([[cx,r.bottom+h/2],[cx,r.top-h/2]]);
 let hit=ASK,at=spots(ASK).find(([x,y])=>free(x,y,ASK));
 if(!at){hit=ASK_MIN;at=spots(ASK_MIN).find(([x,y])=>free(x,y,ASK_MIN))||[Math.max(s.left+ASK_MIN/2,Math.min(s.right-ASK_MIN/2,edge+out*ASK_MIN/2)),r.top+r.height*.1]}
 const [x,y]=at;
 const b=btn('wask',null,()=>go('avatar'));b.setAttribute('aria-label','בוחרים דמות שתצא לדרך');b.appendChild(el('span','wask__dot','?'));
 b.style.left=(x-s.left)+'px';b.style.top=(y-s.top)+'px';b.style.width=b.style.height=hit+'px';sec.appendChild(b);
 return{island:idOf(isl),hop:null,ask:true,hit}}
const HOP_MS=900;   // docs/DESIGN.md "the character on the map": an arc, 900 ms, a squash on landing
function islandEl(sec,i){return sec.querySelector('.isl.i'+i)}
function hereOf(sec){const c=sec.querySelector('.isl.cur');if(c)return c;const open=[...sec.querySelectorAll('.isl:not(.locked)')];return open[open.length-1]||null}
const idOf=el=>+([...el.classList].find(c=>/^i\d+$/.test(c))||'i0').slice(1);
/* the spot where the token stands, in the map section's own coordinates: Pitzi's place on the island played now (at the
   island's side, standing on its lower edge, never over the tag); on another island, the same place worked out */
function spot(sec,isl,tok=TOK){const s=sec.getBoundingClientRect(),c=isl.querySelector('.here');
 if(c){const r=c.getBoundingClientRect();if(r.width)return{x:r.left-s.left+r.width/2,y:r.bottom-s.top-tok/2}}
 const p=(isl.querySelector('.pw')||isl).getBoundingClientRect(),lc=isl.classList.contains('lc'),rtl=getComputedStyle(isl).direction==='rtl';
 const right=lc?!rtl:rtl;   // .here sits at the inline start (-15%), or the inline end on an island left of centre
 return{x:p.left-s.left+(right?p.width*.97:p.width*.03),y:p.top-s.top+p.height*.76-tok/2}}
const TOK=44;
/* 44 px, smaller on a small island (a short phone): never more than 60% of the island's picture */
const tokSize=isl=>Math.round(Math.min(TOK,(isl.querySelector('.pw')||isl).getBoundingClientRect().width*.6));
function token(sec,id,me,go){
 const isl=hereOf(sec);if(!isl||!id.key)return null;   // a device that cannot keep a character: Pitzi as today, nothing more
 if(!me.av)return ask(sec,isl,go);
 const sz=tokSize(isl),at=spot(sec,isl,sz),to=idOf(isl);
 /* never over the "ממשיכים כאן" pill: on a short phone the island's lower edge reaches it, so stand just above it */
 const pill=isl.querySelector('.tag .hb');if(pill){const pr=pill.getBoundingClientRect(),top=pr.top-sec.getBoundingClientRect().top;if(pr.height&&at.y+sz/2>top)at.y=top-sz/2}
 const t=el('span','wtok');t.setAttribute('aria-hidden','true');t.appendChild(pic(me.av,'wtok__pic'));   // a picture only: the island under it stays the button
 t.style.left=at.x+'px';t.style.top=at.y+'px';t.style.width=t.style.height=sz+'px';
 sec.classList.add('hastok');sec.appendChild(t);
 const info={island:to,hop:null,ask:false};
 const prev=me.at,from=prev&&prev!==to?islandEl(sec,prev):null;
 if(prev!==to)keep(id,{...mine(id),at:to});   // remembered at once: the hop is shown once, even if it is cut short
 if(from&&canMove()&&t.animate){
  const a=spot(sec,from,sz),dx=a.x-at.x,dy=a.y-at.y,lift=Math.min(60,Math.hypot(dx,dy)/3),T=(x,y,sx=1,sy=1)=>`translate(calc(-50% + ${x}px),calc(-50% + ${y}px)) scale(${sx},${sy})`;
  const anim=t.animate([{transform:T(dx,dy)},{transform:T(dx/2,dy/2-lift),offset:.45},{transform:T(0,0,1.14,.84),offset:.85},{transform:T(0,0)}],{duration:HOP_MS,easing:'ease-in-out'});
  /* any tap or key ends it at once and still does what it would have done (nothing is stopped or held) */
  const skip=()=>anim.finish(),off=()=>{document.removeEventListener('pointerdown',skip,true);document.removeEventListener('keydown',skip,true)};
  document.addEventListener('pointerdown',skip,true);document.addEventListener('keydown',skip,true);
  anim.onfinish=off;anim.oncancel=off;
  info.hop={from:prev,to,anim:true};window.__hop=anim;
 }else if(from)info.hop={from:prev,to,anim:false};
 return info}

/* ---------- an island as a path of stones ----------
   The island's levels, in their order, as stones along the painted path of the island backdrop (the same path and
   stones as the world.html preview: js/worldpath.js). Played levels are lit with their stars; the first level not
   played yet glows; the others are open as today (every level of an open island can be played) and are shown plain.
   Each stone carries the level's name and sub-line, as in the list; a dotted line joins the stones, gold up to the
   glowing one. The character stands on the glowing stone (on the last one when all are played) and glides to a tapped
   stone before the level opens (0.45 s; none with reduced motion or calm mode); a second tap ends the glide and goes at
   once, and the back button is never held up. Same routes, same order, same labels as the list it replaces
   (docs/DESIGN.md "the island as a path"). */
/* the dotted line that joins the stones: gold up to the glowing stone, dim after it (drawn in the stage's percent) */
const SVGNS='http://www.w3.org/2000/svg';
function line(pts,here){const s=document.createElementNS(SVGNS,'svg');s.setAttribute('class','w-line');s.setAttribute('viewBox','0 0 100 100');
 s.setAttribute('preserveAspectRatio','none');s.setAttribute('aria-hidden','true');s.setAttribute('focusable','false');
 const part=(a,b,c)=>{if(b<=a)return;const p=document.createElementNS(SVGNS,'polyline');p.setAttribute('class','w-line__'+c);
  p.setAttribute('points',pts.slice(a,b+1).map(q=>q[0]+','+q[1]).join(' '));s.appendChild(p)};
 part(0,here,'lit');part(here,pts.length-1,'dim');return s}
const STARS_HE=['עוד לא שיחקתם','כוכב אחד','שני כוכבים','שלושה כוכבים'];
const WALK_MS=450;
/* The path replaces today's list only when its pictures are here: already loaded (the map fetches them when idle), or
   arriving within ART_WAIT. Otherwise the list stays for this visit. The list is never hidden while we wait, so the
   island area is never empty, and the island never flips from list to path late. */
export const pathReady=()=>!!(pre&&pre.ok);   // the path's pictures are fetched and decoded (main.js holds the list back a moment)
const ART_WAIT=300;
const wait=ms=>new Promise(r=>setTimeout(()=>r(false),ms));
async function ready(){
 if(pre&&pre.ok)return true;                                                  // fetched and decoded from the map
 if(pre&&pre.done&&await Promise.race([pre.done,wait(ART_WAIT)])===true)return true;   // still coming: a short wait
 if(pre&&pre.done)return false;
 return Promise.race([Promise.all(PATH_ART.map(k=>{const im=new Image();im.src=ART[k];return im.decode().then(()=>true,()=>false)})).then(a=>a.every(Boolean)),wait(ART_WAIT)])}   // straight onto an island (a link): the same short wait
export async function islandPath(view,i,go,live=()=>true){
 const id=await ident();
 const sec=view.querySelector('.scr.island'),list=sec&&sec.querySelector('.lvlist');
 if(!live()||!list||!same(id))return;
 style();
 if(!await ready()||!live()||!list.isConnected||!same(id))return false;   // not here yet, or failed: today's list for this visit
 const me=id.key?mine(id):{av:null},lv=i.levels.map(([t])=>({t,s:starsOf(i.id,t),L:LEVEL_INFO[t]}));
 const next=lv.findIndex(x=>!x.s),here=next<0?lv.length-1:next,pts=pathPoints('english',lv.length);
 const wrap=el('div','w-stagewrap wisl'),stage=el('div','w-stage');stage.style.backgroundImage='url("'+ART['bg/english']+'")';
 const ol=el('ol','w-path');ol.setAttribute('aria-label','השלבים של האי, לפי הסדר');
 let walker=null,timer=0,walk=null;
 const at=k=>({x:pts[k][0],y:pts[k][1]});
 if(me.av){walker=el('span','w-walker');walker.setAttribute('aria-hidden','true');walker.appendChild(pic(me.av,'w-walker__pic'));
  walker.style.left=at(here).x+'%';walker.style.top=at(here).y+'%'}
 function open(k){const route='play/'+i.id+'/'+lv[k].t,busy=!!timer;clearTimeout(timer);timer=0;
  /* no glide, or a second tap during one: it ends there and the level opens at once */
  if(busy||!walker||!canMove()){if(walk)walk.cancel();if(walker){walker.style.left=at(k).x+'%';walker.style.top=at(k).y+'%'}return go(route)}
  /* a straight glide to the tapped stone; the level opens when it arrives */
  const r=stage.getBoundingClientRect(),w=walker.getBoundingClientRect(),fx=w.left+w.width/2-r.left,fy=w.top+w.height/2-r.top;
  walker.style.left=at(k).x+'%';walker.style.top=at(k).y+'%';
  const tx=at(k).x*r.width/100,ty=at(k).y*r.height/100;
  walk=walker.animate([{transform:`translate(calc(-50% + ${fx-tx}px),calc(-50% + ${fy-ty}px))`},{transform:'translate(-50%,-50%)'}],{duration:WALK_MS,easing:'ease-out'});
  timer=setTimeout(()=>{timer=0;if(live())go(route)},WALK_MS)}
 lv.forEach((x,k)=>{
  const state=x.s?'done':k===next?'current':'open',li=el('li');li.style.left=pts[k][0]+'%';li.style.top=pts[k][1]+'%';
  const b=stone(state,'שלב '+(k+1)+': '+x.L.name+', '+STARS_HE[x.s]+(k===next?', כאן אתם עכשיו':''),state==='open'?'current':state);
  b.dataset.to='play/'+i.id+'/'+x.t;
  b.appendChild(el('span','w-st__mark',String(k+1)));
  if(x.s){const st=el('span','w-st__stars');st.insertAdjacentHTML('beforeend',starRow(x.s));b.appendChild(st)}   // the game's own star row (ui.js), no outside text
  /* the label: the level's name and sub-line exactly as in the list, toward the middle, never off the picture; it is
     inside the button, so stone and label are one target */
  const lab=el('span','w-st__name '+(pts[k][0]<50?'w-st__name--r':'w-st__name--l'));
  lab.append(el('b',null,x.L.name),el('small',null,x.L.sub));b.appendChild(lab);
  b.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();open(k)});
  li.appendChild(b);ol.appendChild(li)});
 stage.appendChild(line(pts,here));stage.appendChild(ol);if(walker)stage.appendChild(walker);wrap.appendChild(stage);
 /* a stone picture that fails: back to today's list (the stones are buttons over a picture that is not there) */
 let back=false;const undo=()=>{if(back||!wrap.isConnected)return;back=true;wrap.replaceWith(list);list.style.visibility='';sec.classList.remove('wpath');if(hint)hint.remove()};   // a glide already under way still opens its level
 for(const im of ol.querySelectorAll('img'))im.addEventListener('error',undo,{once:true});
 /* Pitzi's hint from the list screen (the same words), one line under the path */
 const g=sec.querySelector('.guide .label'),hint=g&&g.textContent.trim()?el('p','w-hint',g.textContent.trim()):null;
 list.replaceWith(wrap);if(hint)wrap.after(hint);sec.classList.add('wpath');
 window.__world={...(window.__world||{}),path:{island:i.id,levels:lv.map(x=>x.t),here,next,walker:!!walker,key:id.key}};   // for the tests
 return true}

/* ---------- the character picker: choose, then name ---------- */
export async function picker(view,go,live=()=>true){
 const id=await ident();
 if(!live()||!same(id))return;
 if(!id.key)return go('map');   // nothing could be kept on this device: the dock says so
 style();
 const me=mine(id),E=energyOf(id);let pick=me.av,nm=me.nm?[...me.nm]:[0,0],seen=false,io=null;
 const sec=el('section','scr wpick');view.replaceChildren(sec);document.getElementById('stage').dataset.scr='avatar';
 const head=el('header','wpick__top');
 head.appendChild(btn('wpick__back','חזרה',()=>go('map')));
 const h=el('h1','wpick__h');h.tabIndex=-1;head.appendChild(h);sec.appendChild(head);
 const body=el('div','wpick__body');sec.appendChild(body);
 function choose(){h.textContent='בוחרים דמות';body.replaceChildren();sec.scrollTop=0;
  body.appendChild(el('p','wpick__sub','אפשר להחליף אותה מתי שרוצים.'));
  const grid=el('div','wpick__grid');grid.setAttribute('role','group');grid.setAttribute('aria-label','הדמויות');
  const note=el('p','wpick__note','בכל רמה חדשה נפתחת דמות חדשה. עכשיו אתם ברמה '+E.level+'.');note.setAttribute('role','status');
  const later=[];
  for(const a of ALL){const locked=a.open>E.level&&a.id!==me.av,sel=pick===a.id;   // the character a pupil already has stays theirs
   const b=btn('wpick__av'+(locked?' is-locked':'')+(sel?' is-selected':''),null,()=>{
    if(locked){note.textContent=lockedSay(a,E.level);const i=b.querySelector('.wpick__art--thumb');if(i){i.classList.remove('wpick__art--thumb');i.style.transform='';i.src=ART['av/'+a.id]}return}   // tapped: its full picture, once
    pick=a.id;choose();const s=body.querySelector('.is-selected');if(s){s.focus({preventScroll:true});playAv(s.querySelector('img'),a.id)}});   // its short animation, once (js/avanim.js: nothing before a tap, nothing with reduced motion or calm)
   /* review of #122 (the picker opened 3.7 s slower): a locked tile shows a small thumbnail of the character (tools/
      avthumb.py, a few KB), an open one its full still; and every tile gets its picture only when it comes near the
      screen (below the fold, when scrolled to) */
   b.dataset.id=a.id;const ip=el('img','wpick__art'+(locked?' wpick__art--thumb':''));ip.alt='';ip.decoding='async';ip.draggable=false;
   ip.dataset.src=locked?'assets/al/avthumb/'+a.id+'.webp':ART['av/'+a.id];later.push(ip);b.appendChild(ip);
   if(locked){ip.style.transform='none';   // the thumbnail is the crop box already (inline too, so an older css/avatar.css in the cache does not zoom it twice)
    ip.onerror=()=>{ip.onerror=null;ip.style.transform='';ip.classList.remove('wpick__art--thumb');ip.src=ART['av/'+a.id]}}   // no thumbnail (a character added later): its full still
   if(locked){b.setAttribute('aria-label',lockedSay(a,E.level));b.setAttribute('aria-disabled','true');
    const k=el('img','wpick__key');k.src=ART['ui/lock'];k.alt='';k.decoding='async';b.append(k,el('span','wpick__lock','רמה '+a.open))}   // a small lock in the top corner and "רמה N" in one short line at the bottom: the picture stays in view
   else{b.setAttribute('aria-label',a.he);b.setAttribute('aria-pressed',sel?'true':'false')}
   grid.appendChild(b)}
  /* the characters still being drawn: a plain tile, "בקרוב" and its level; no picture (nothing broken), opens nothing */
  for(const n of SOON){if(ALL.some(a=>a.open===n))continue;
   const t=el('div','wpick__soon-tile');t.setAttribute('role','img');t.setAttribute('aria-label','דמות חדשה בקרוב, ברמה '+n);
   t.append(el('span','wpick__soon','בקרוב'),el('span','wpick__lock','רמה '+n));grid.appendChild(t)}
  body.append(grid,note);
  /* the first time the grid is drawn, a picture is fetched when its tile comes within 200 px of the picker's view; when
     it is drawn again (each tap redraws it), every picture at once, so the tapped tile's animation is never written over */
  if(seen||typeof IntersectionObserver!=='function')for(const i of later){if(!i.getAttribute('src'))i.src=i.dataset.src}
  else{if(io)io.disconnect();
   io=new IntersectionObserver(es=>{for(const e of es)if(e.isIntersecting){const i=e.target;io.unobserve(i);if(!i.getAttribute('src'))i.src=i.dataset.src}},{root:sec,rootMargin:'200px 0px'});
   for(const i of later)io.observe(i)}
  seen=true;
  const why=el('p','wpick__why',pick?'':'קודם בוחרים דמות.');
  const nx=btn('wpick__ok','הלאה: בוחרים שם',()=>{if(!pick){why.textContent='קודם בוחרים דמות.';return}name()});
  nx.setAttribute('aria-disabled',pick?'false':'true');body.append(nx,why)}
 function name(){h.textContent='איך קוראים לדמות?';body.replaceChildren();sec.scrollTop=0;   // each step starts at its heading (the picker may have scrolled to its button)
  body.appendChild(el('p','wpick__sub','בוחרים מילה אחת מכל רשימה. השם באנגלית.'));
  const who=el('div','wpick__who');who.appendChild(pic(pick,'wpick__big'));const shown=el('p','wpick__name');shown.setAttribute('aria-live','polite');who.appendChild(shown);body.appendChild(who);
  const rows=[0,1].map(k=>{const L=k?NAME_B:NAME_A,row=el('div','wpick__spin');row.appendChild(el('span','wpick__l',k?'מילה שנייה':'מילה ראשונה'));
   const w=el('span','wpick__w');
   const prev=btn('wpick__arrow','→',()=>{nm[k]=(nm[k]-1+L.length)%L.length;draw()}),next=btn('wpick__arrow','←',()=>{nm[k]=(nm[k]+1)%L.length;draw()});
   prev.setAttribute('aria-label','המילה הקודמת');next.setAttribute('aria-label','המילה הבאה');
   row.append(prev,w,next);body.appendChild(row);return w});
  function draw(){shown.replaceChildren(ltr(nameText(nm)));
   rows.forEach((w,k)=>{const x=(k?NAME_B:NAME_A)[nm[k]];w.replaceChildren(ltr(x.en),el('small',null,x.he))})}
  body.appendChild(btn('wpick__dice','הפתעה',()=>{let a,b;do{a=Math.random()*NAME_A.length|0;b=Math.random()*NAME_B.length|0}while(a===nm[0]&&b===nm[1]);nm=[a,b];draw()}));
  body.appendChild(btn('wpick__ok','זה השם שלי',()=>{if(same(id))keep(id,{...mine(id),av:pick,nm:[...nm],en:energyOf(id).points});go('map')}));
  body.appendChild(btn('wpick__quiet','חזרה לדמויות',choose));
  draw();h.focus({preventScroll:true})}
 choose();h.focus({preventScroll:true});
 window.__world={picker:true,level:E.level};   // for the tests
}
