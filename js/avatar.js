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
   - energy: only goes up. It is worked out from what the pupil has learned (stars, words known, stories read) and kept
     as the highest value seen, so a word that is forgotten again never takes energy away.
   DOM is built with createElement and textContent only. */
import {S,API,totalStars,wordsKnown,isOpen} from './state.js';
import {ISLANDS,WORDS,MAX_STARS,TEXTS} from './data.js';
import {ART} from './world_art.js';
import {AVATARS,NAME_A,NAME_B,NAME_V} from './world_data.js';
import {playAv} from './avanim.js';

const KEY='wi_world';
/* energy: what each thing learned is worth, and the level thresholds (a rule of ours, for the owner and designer to tune).
   Level n runs from LEVELS[n-1] to LEVELS[n]; past the list every level is 250 more.
   The most a pupil can earn today is 980 (66 stars, 59 words, 5 stories), so the 13 levels that open the 12 characters
   (js/world_data.js) all fit inside it: the last at 820. Every threshold is at or below the earlier ones
   (0,120,220,340,480,640,820,1020), so a level shown on a device never goes down. */
const WORTH={star:10,word:5,story:5};
export const LEVELS=[0,40,90,150,220,300,380,460,540,620,700,760,820];
/* The most energy a pupil can earn with today's content: every star, every word of the unit known, every story read
   (10 x 66 + 5 x 59 + 5 x 5 = 980). REVISIT THE LADDER when content adds energy (new islands, a new unit, Fraction Bay
   if it is ever counted): the last character must stay reachable, and should not come too early either.
   tests/world.py fails if the level that opens the last character is above this. */
export const MAX_ENERGY=WORTH.star*MAX_STARS+WORTH.word*WORDS.filter(w=>w.p<6).length+WORTH.story*TEXTS.length;
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
 return{av:AVATARS.some(a=>a.id===m.av)?m.av:null,
  nm:m.nv===NAME_V&&Array.isArray(m.nm)&&Number.isInteger(m.nm[0])&&Number.isInteger(m.nm[1])&&NAME_A[m.nm[0]]&&NAME_B[m.nm[1]]?[m.nm[0],m.nm[1]]:null,
  en:typeof m.en==='number'&&Number.isFinite(m.en)&&m.en>0?Math.min(EN_MAX,Math.floor(m.en)):0,
  sl:Number.isInteger(m.sl)&&m.sl>0&&m.sl<1000?m.sl:0}}
const KEY_OK=/^(local|h:[0-9a-f]{64})$/;   // the only keys a record may have; anything else is dropped on the next write
/* only the known fields, and a name always with the lists' version */
const clean=r=>{const o={av:r.av,nm:r.nm,en:r.en};if(r.nm)o.nv=NAME_V;if(r.sl)o.sl=r.sl;return o};
function keep(id,rec){if(!id.key||!same(id))return false;try{const all=readAll(),p={};for(const k of Object.keys(all.p))if(KEY_OK.test(k))p[k]=all.p[k];p[id.key]=clean(rec);localStorage.setItem(KEY,JSON.stringify({v:1,p}));return true}catch(e){return false}}

/* ---------- energy: only goes up ---------- */
export const earned=()=>WORTH.star*totalStars()+WORTH.word*wordsKnown()+WORTH.story*Object.values(S.read||{}).filter(v=>v>0).length;
const LAST=LEVELS[LEVELS.length-1];
const step=n=>n<LEVELS.length?LEVELS[n]:LAST+250*(n-LEVELS.length+1);
/* the level, worked out (not counted up one by one): inside the list by search, past it by division */
const levelOf=pts=>pts>=LAST?LEVELS.length+Math.floor((pts-LAST)/250):LEVELS.findIndex(t=>t>pts);
function energyOf(id){const r=mine(id),pts=Math.min(EN_MAX,Math.max(r.en,earned()));
 if(pts!==r.en)keep(id,{...r,en:pts});
 const level=levelOf(pts);
 const opens=AVATARS.some(a=>a.open===level+1)?'נפתחת דמות חדשה':'עוד רמה בדרך';
 return{points:pts,level,from:step(level-1),next:step(level),opens}}

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
let styled=false;
function style(){if(styled)return;styled=true;const l=document.createElement('link');l.rel='stylesheet';l.href='css/avatar.css';document.head.appendChild(l)}

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
 const note=el('p','wd__note','מרוויחים אנרגיה כשלומדים, והיא אף פעם לא נגמרת. עוד '+(E.next-E.points)+' אנרגיה לרמה '+(E.level+1)+': '+E.opens+'.');
 note.hidden=true;note.setAttribute('role','status');
 dock.append(meB,en);
 if(F){const f=btn('wd__focus',null,()=>go('island/'+F.island));
  f.append(el('b',null,'המיקוד להיום'),el('span',null,F.count+' מילים לחזק'));
  f.setAttribute('aria-label','המיקוד להיום: '+F.count+' מילים מ־'+F.he+' שכדאי לחזק. כמה דקות וזהו. מתחילים');
  dock.appendChild(f)}
 /* .wdock on #stage lifts main.js's sync bar above the dock; main.js route() takes it off on the next screen */
 sec.classList.add('hasdock');document.getElementById('stage').classList.add('wdock');sec.append(note,dock);
 /* a level that opened a character: said once, with its portrait and the way to the picker. The first visit only
    remembers the level (a device that already had this level is not told about old news). */
 let fresh=[];
 if(id.key){const r=mine(id);
  if(!r.sl)keep(id,{...r,sl:E.level});
  else if(E.level>r.sl){fresh=AVATARS.filter(a=>a.open>r.sl&&a.open<=E.level);keep(id,{...r,sl:E.level})}}
 if(fresh.length){const a=fresh[fresh.length-1],box=el('div','wnew');box.setAttribute('role','dialog');box.setAttribute('aria-labelledby','wnew-h');
  const h=el('h2','wnew__h',fresh.length>1?'דמויות חדשות נפתחו!':'דמות חדשה נפתחה!');h.id='wnew-h';
  const ok=btn('wnew__ok','לבחירת דמות',()=>go('avatar'));
  const pics=el('div','wnew__pics');for(const x of fresh.slice(-3).reverse())pics.appendChild(pic(x.id,'wnew__pic'));   // the newest first, up to three
  if(fresh.length>3)pics.appendChild(el('span','wnew__more','ועוד '+(fresh.length-3)));
  if(fresh.length>1){pics.classList.add('wnew__pics--many');box.classList.add('wnew--many')}
  box.append(pics,h,el('p','wnew__t',fresh.length>1?fresh.length+' דמויות חדשות מחכות לכם. רוצים להחליף?':a.he+' מחכה לכם. רוצים להחליף?'),ok,btn('wnew__later','אחר כך',()=>box.remove()));
  sec.appendChild(box);ok.focus({preventScroll:true})}
 window.__world={avatar:me.av,name:me.nm,energy:E,focus:F,key:id.key,fresh:fresh.map(a=>a.id)};   // for the tests
}

/* ---------- the character picker: choose, then name ---------- */
export async function picker(view,go,live=()=>true){
 const id=await ident();
 if(!live()||!same(id))return;
 if(!id.key)return go('map');   // nothing could be kept on this device: the dock says so
 style();
 const me=mine(id),E=energyOf(id);let pick=me.av,nm=me.nm?[...me.nm]:[0,0];
 const sec=el('section','scr wpick');view.replaceChildren(sec);document.getElementById('stage').dataset.scr='avatar';
 const head=el('header','wpick__top');
 head.appendChild(btn('wpick__back','חזרה',()=>go('map')));
 const h=el('h1','wpick__h');h.tabIndex=-1;head.appendChild(h);sec.appendChild(head);
 const body=el('div','wpick__body');sec.appendChild(body);
 function choose(){h.textContent='בוחרים דמות';body.replaceChildren();sec.scrollTop=0;
  body.appendChild(el('p','wpick__sub','אפשר להחליף אותה מתי שרוצים.'));
  const grid=el('div','wpick__grid');grid.setAttribute('role','group');grid.setAttribute('aria-label','הדמויות');
  const note=el('p','wpick__note','בכל רמה חדשה נפתחת דמות חדשה. עכשיו אתם ברמה '+E.level+'.');note.setAttribute('role','status');
  for(const a of AVATARS){const locked=a.open>E.level&&a.id!==me.av,sel=pick===a.id;   // the character a pupil already has stays theirs
   const b=btn('wpick__av'+(locked?' is-locked':'')+(sel?' is-selected':''),null,()=>{
    if(locked){note.textContent=lockedSay(a,E.level);return}
    pick=a.id;choose();const s=body.querySelector('.is-selected');if(s){s.focus({preventScroll:true});playAv(s.querySelector('img'),a.id)}});   // its short animation, once (js/avanim.js: nothing before a tap, nothing with reduced motion or calm)
   b.dataset.id=a.id;b.appendChild(pic(a.id,'wpick__art'));
   if(locked){b.setAttribute('aria-label',lockedSay(a,E.level));b.setAttribute('aria-disabled','true');
    const k=el('img','wpick__key');k.src=ART['ui/lock'];k.alt='';k.decoding='async';b.append(k,el('span','wpick__lock','רמה '+a.open))}   // a small lock in the top corner and "רמה N" in one short line at the bottom: the picture stays in view
   else{b.setAttribute('aria-label',a.he);b.setAttribute('aria-pressed',sel?'true':'false')}
   grid.appendChild(b)}
  body.append(grid,note);
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
