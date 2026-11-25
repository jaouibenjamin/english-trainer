/* The new world in the live game, behind the design flag (?ds=1, js/dsflag.js): the pupil's character and its name,
   the energy level, and today's focus on the English map. main.js loads this file only when the flag is on, so with the
   flag off nothing of it is fetched, drawn or stored.

   Storage: local to this device, in its own key (wi_world), one record per pupil on the device. It is NOT part of the
   progress record that pack()/merge() send to the class's sheet, and this file makes no request of any kind.
   - avatar: one of the 20 ids in js/world_data.js. Locked characters open with the energy level.
   - name: two indexes into the two fixed word lists (no free text: nothing a pupil types is stored or shown).
   - energy: only goes up. It is worked out from what the pupil has learned (stars, words known, stories read) and kept
     as the highest value seen, so a word that is forgotten again never takes energy away.
   DOM is built with createElement and textContent only. */
import {S,API,totalStars,wordsKnown,isOpen} from './state.js';
import {ISLANDS,WORDS} from './data.js';
import {ART} from './world_art.js';
import {AVATARS,NAME_A,NAME_B} from './world_data.js';

const KEY='wi_world';
/* energy: what each thing learned is worth, and the level thresholds (a rule of ours, for the owner and designer to tune).
   Level n runs from LEVELS[n-1] to LEVELS[n]; past the list every level is 250 more. */
const WORTH={star:10,word:5,story:5};
const LEVELS=[0,120,220,340,480,640,820,1020];
const FOCUS_MAX=5;

/* ---------- storage ---------- */
const who=()=>API&&S.u?'c:'+S.u.c+'|'+S.u.n:'local';
function readAll(){try{const o=JSON.parse(localStorage.getItem(KEY)||'null');return o&&typeof o==='object'&&o.v===1&&o.p&&typeof o.p==='object'?o:{v:1,p:{}}}catch(e){return{v:1,p:{}}}}
function mine(){const r=readAll().p[who()];const m=r&&typeof r==='object'?r:{};
 return{av:AVATARS.some(a=>a.id===m.av)?m.av:null,
  nm:Array.isArray(m.nm)&&Number.isInteger(m.nm[0])&&Number.isInteger(m.nm[1])&&NAME_A[m.nm[0]]&&NAME_B[m.nm[1]]?m.nm:null,
  en:Number.isFinite(m.en)&&m.en>0?Math.floor(m.en):0}}
function keep(rec){try{const all=readAll();all.p[who()]=rec;localStorage.setItem(KEY,JSON.stringify(all))}catch(e){}}

/* ---------- energy: only goes up ---------- */
export const earned=()=>WORTH.star*totalStars()+WORTH.word*wordsKnown()+WORTH.story*Object.values(S.read||{}).filter(v=>v>0).length;
const step=n=>n<LEVELS.length?LEVELS[n]:LEVELS[LEVELS.length-1]+250*(n-LEVELS.length+1);
export function energy(){const r=mine(),pts=Math.max(r.en,earned());
 if(pts!==r.en)keep({...r,en:pts});
 let level=1;while(pts>=step(level))level++;
 const opens=AVATARS.some(a=>a.open===level+1)?'נפתחת דמות חדשה':'עוד רמה בדרך';
 return{points:pts,level,from:step(level-1),next:step(level),opens}}

/* ---------- today's focus: words the pupil got wrong and does not know yet, on the open island with the most ---------- */
export function focus(){
 const weak=WORDS.filter(w=>w.p<6&&((S.st||{})[w.en]||[0,0])[1]>0&&((S.w||{})[w.en]||0)<2);
 let best=null;
 for(const i of ISLANDS){if(!isOpen(i))continue;const parts=new Set(i.levels.map(l=>l[1]));const n=weak.filter(w=>parts.has(w.p)).length;
  if(n&&(!best||n>best.count))best={island:i.id,he:i.he,count:n}}
 return best&&{...best,count:Math.min(FOCUS_MAX,best.count)}}

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
export function decorateMap(view,go){
 const sec=view.querySelector('.scr.map');if(!sec||sec.querySelector('.wd'))return;
 style();
 const me=mine(),E=energy(),F=focus();
 const dock=el('div','wd');
 const meB=btn('wd__me',null,()=>go('avatar'));
 if(me.av)meB.appendChild(pic(me.av,'wd__pic'));else meB.appendChild(el('span','wd__pic wd__pic--none','?'));
 const txt=el('span','wd__txt');
 if(me.av&&me.nm){const hi=el('span','wd__hi');hi.appendChild(ltr(nameText(me.nm)));txt.appendChild(hi)}
 else txt.appendChild(el('span','wd__hi',me.av?'שלום!':'בוחרים דמות'));
 meB.setAttribute('aria-label',me.av?'הדמות שלי'+(me.nm?': '+nameText(me.nm):''):'בוחרים דמות');
 meB.appendChild(txt);
 const en=btn('wd__en',null,()=>{note.hidden=!note.hidden;en.setAttribute('aria-expanded',note.hidden?'false':'true')});
 en.append(el('b',null,'⚡'),el('span',null,'רמה '+E.level));
 en.setAttribute('aria-label','רמת אנרגיה '+E.level+'. מה זו אנרגיה?');en.setAttribute('aria-expanded','false');
 const note=el('p','wd__note','מרוויחים אנרגיה כשלומדים, והיא אף פעם לא נגמרת. עוד '+(E.next-E.points)+' אנרגיה לרמה '+(E.level+1)+': '+E.opens+'.');
 note.hidden=true;note.setAttribute('role','status');
 dock.append(meB,en);
 if(F){const f=btn('wd__focus',null,()=>go('island/'+F.island));
  f.append(el('b',null,'המיקוד להיום'),el('span',null,F.count+' מילים לחזק'));
  f.setAttribute('aria-label','המיקוד להיום: '+F.count+' מילים מ־'+F.he+' שכדאי לחזק. כמה דקות וזהו. מתחילים');
  dock.appendChild(f)}
 sec.classList.add('hasdock');sec.append(note,dock);
 window.__world={avatar:me.av,name:me.nm,energy:E,focus:F};   // for the tests
}

/* ---------- the character picker: choose, then name ---------- */
export function picker(view,go){
 style();
 const me=mine(),E=energy();let pick=me.av,nm=me.nm?[...me.nm]:[0,0];
 const sec=el('section','scr wpick');view.replaceChildren(sec);document.getElementById('stage').dataset.scr='avatar';
 const head=el('header','wpick__top');
 head.appendChild(btn('wpick__back','חזרה',()=>go('map')));
 const h=el('h1','wpick__h');h.tabIndex=-1;head.appendChild(h);sec.appendChild(head);
 const body=el('div','wpick__body');sec.appendChild(body);
 function choose(){h.textContent='בוחרים דמות';body.replaceChildren();
  body.appendChild(el('p','wpick__sub','אפשר להחליף אותה מתי שרוצים.'));
  const grid=el('div','wpick__grid');grid.setAttribute('role','group');grid.setAttribute('aria-label','הדמויות');
  const note=el('p','wpick__note','דמויות נוספות נפתחות כשמרוויחים אנרגיה.');note.setAttribute('role','status');
  for(const a of AVATARS){const locked=a.open>E.level,sel=pick===a.id;
   const b=btn('wpick__av'+(locked?' is-locked':'')+(sel?' is-selected':''),null,()=>{
    if(locked){note.textContent=a.he+': נפתחת ברמת אנרגיה '+a.open+'. עכשיו אתם ברמה '+E.level+'.';return}
    pick=a.id;choose();const s=body.querySelector('.is-selected');if(s)s.focus({preventScroll:true})});
   b.dataset.id=a.id;b.appendChild(pic(a.id,'wpick__art'));
   if(locked){b.setAttribute('aria-label',a.he+', נפתחת ברמת אנרגיה '+a.open);b.appendChild(el('span','wpick__lock','🔒'))}
   else{b.setAttribute('aria-label',a.he);b.setAttribute('aria-pressed',sel?'true':'false')}
   grid.appendChild(b)}
  body.append(grid,note);
  const why=el('p','wpick__why',pick?'':'קודם בוחרים דמות.');
  const nx=btn('wpick__ok','הלאה: בוחרים שם',()=>{if(!pick){why.textContent='קודם בוחרים דמות.';return}name()});
  nx.setAttribute('aria-disabled',pick?'false':'true');body.append(nx,why)}
 function name(){h.textContent='איך קוראים לדמות?';body.replaceChildren();
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
  body.appendChild(btn('wpick__ok','זה השם שלי',()=>{keep({...mine(),av:pick,nm:[...nm],en:energy().points});go('map')}));
  body.appendChild(btn('wpick__quiet','חזרה לדמויות',choose));
  draw();h.focus({preventScroll:true})}
 choose();h.focus({preventScroll:true});
 window.__world={picker:true,level:E.level};   // for the tests
}
