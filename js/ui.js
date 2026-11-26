/* Shared UI helpers: asset loading, backgrounds, painted buttons, icons, confetti, toast. */
import {esc,reduced} from './state.js';

export const $=(s,r=document)=>r.querySelector(s);
export const view=document.getElementById('view');
export const stage=document.getElementById('stage');
export const SP=n=>`assets/sp/${n}.webp`;
export const BG=n=>`assets/bg/${n}.jpg`;
export const BGW=752,BGH=1344,BRIDGE_H=1800;   // the bridge art is taller: its sky continues above the sign on every phone

/* the old pictures the new look draws over, with their own size: a stand-in of that size (an empty SVG), used only with the
   design flag (spr() below), so a box sized from the picture stays as it was. tests/weight.py checks the
   sizes against the files. A picture not listed has no stand-in and is downloaded as before. */
const NAT={isl_1:[560,388],isl_2:[560,461],isl_3:[560,448],isl_4:[560,394],isl_5:[560,407],isl_6:[560,422],star:[200,183],star_off:[200,183],
 lock:[288,379],ic_gear:[200,199],crab_wave:[326,296],crab_star:[322,342],crab_happy:[340,351]};
const SVGNS='http://www.w3.org/2000/svg';   // an XML namespace name, never fetched
export const standIn=n=>NAT[n]?'data:image/svg+xml,'+encodeURIComponent(`<svg xmlns="${SVGNS}" width="${NAT[n][0]}" height="${NAT[n][1]}"/>`)+' 1x':'';

/* ---------- image cache / preload ---------- */
const cache=new Map();
export function img(src){let p=cache.get(src);if(!p){p=new Promise(res=>{const i=new Image();i.decoding='async';i.onload=()=>res(i);i.onerror=()=>res(null);i.src=src});cache.set(src,p)}return p}
export const preload=list=>Promise.all(list.map(img));
export const CORE=['pill','pill_green','pill_coral','pill_blue','pill_cream','sign','label','ribbon','scroll','star','star_off','lock','crab_wave','crab_happy','crab_oops','crab_walk','crab_listen','crab_star','bubble_0','bubble_1','bubble_2','bubble_3','plank_0','plank_1','plank_2','plank_3','plank_4','lamp','trophy','chest','fork','conch','bottle','ic_gear','ic_note','ic_speaker','ic_book','ic_bridge','ic_check','ic_x','ic_arrow','ic_door','ic_signpost','compass'].map(SP);

/* ---------- background layers (cross-fade) ---------- */
const layers=[...document.querySelectorAll('#bg .bgl')],backdrop=document.getElementById('backdrop');let cur=0,curBg='';
export function setBg(name,pos){
 const key=name+'|'+(pos||'');if(key===curBg)return;curBg=key;
 const nxt=layers[1-cur];nxt.style.backgroundImage=`url(${BG(name)})`;nxt.dataset.pos=pos||'bottom';nxt.classList.add('on');layers[cur].classList.remove('on');cur=1-cur;
 if(backdrop)backdrop.style.backgroundImage=`url(${BG(name)})`}   // wide screens: the same scene, soft, fills the window around the board
/* maps a point of the 752x1344 background art to stage pixels for the two fits we use */
export function bgMap(fit){const W=stage.clientWidth,H=stage.clientHeight;
 if(fit==='bridge'){const s=W/BGW;return{s,ox:0,oy:H-BRIDGE_H*s,W,H}}
 const s=Math.max(W/BGW,H/BGH);return{s,ox:(W-BGW*s)/2,oy:fit==='center'?(H-BGH*s)/2:H-BGH*s,W,H}}

/* ---------- small hand-drawn icons (ink strokes) ---------- */
const P={
 back:'<path d="M5 12h14M13 6l6 6-6 6"/>',
 close:'<path d="M6.500 6.500l11 11M17.500 6.500l-11 11"/>',
 gear:'<circle cx="12" cy="12" r="3.200"/><path d="M12 3.500v2.600M12 17.900v2.600M3.500 12h2.600M17.900 12h2.600M6 6l1.900 1.900M16.100 16.100L18 18M18 6l-1.900 1.900M7.900 16.100L6 18"/>',
 sound:'<path d="M4 10v4h3.500l4.500 3.500v-11L7.500 10z"/><path d="M15.500 9.200c1.600 1.500 1.600 4.100 0 5.600M18 6.800c3 2.900 3 7.500 0 10.400"/>',
 mute:'<path d="M4 10v4h3.500l4.500 3.500v-11L7.500 10z"/><path d="M16 9.500l5 5M21 9.500l-5 5"/>',
 note:'<path d="M9 18V6.500l10-2V16"/><ellipse cx="6.700" cy="18" rx="2.400" ry="1.900"/><ellipse cx="16.700" cy="16" rx="2.400" ry="1.900"/>',
 play:'<path d="M8 5.500v13l11-6.500z"/>',
 home:'<path d="M4 11.500L12 5l8 6.500M6.500 10v9h11v-9"/>',
 retry:'<path d="M19 12a7 7 0 1 1-2.300-5.200M19 4.500v4h-4"/>',
 book:'<path d="M4 6.500c3-1.300 5.500-1.300 8 0v12c-2.500-1.300-5-1.300-8 0zM12 6.500c2.500-1.300 5-1.300 8 0v12c-3-1.300-5.500-1.300-8 0"/>',
 check:'<path d="M5 12.500l4.500 4.500L19 7.500"/>',
 user:'<circle cx="12" cy="8.500" r="3.500"/><path d="M5 19.500c1.200-3.600 4-5 7-5s5.800 1.400 7 5"/>',
 eye:'<path d="M2.500 12c2.600-4.300 5.800-6.400 9.500-6.400s6.900 2.100 9.500 6.400c-2.600 4.300-5.800 6.400-9.500 6.400S5.100 16.300 2.500 12z"/><circle cx="12" cy="12" r="2.900"/>',
 next:'<path d="M19 12H5M11 6l-6 6 6 6"/>'};
export const ico=(n,cls='')=>`<svg class="ico ${cls}" viewBox="0 0 24 24" aria-hidden="true">${P[n]}</svg>`;
/* with the design flag, an old picture in the size list gets its stand-in written into the tag (and a marker that js/main.js
   dsSettle uses to give the picture back where the new look does not draw over it): the browser never starts on src.
   Without the flag the tag is exactly as before. */
const standInAttrs=n=>{const b=document.documentElement.classList.contains('ds')&&standIn(n);return b?` srcset="${b}" data-wi-sp=""`:''};
export const spr=(n,cls='',alt='')=>`<img class="${cls}" src="${SP(n)}"${standInAttrs(n)} alt="${esc(alt)}" draggable="false">`;
/* round painted button (a watercolour bubble with an ink icon or a small sprite) */
export const rb=(act,inner,label,tone=0,extra='')=>`<button class="rb t${tone}" data-a="${act}" aria-label="${esc(label)}" ${extra}>${inner}</button>`;
export const btn=(act,html,kind='',extra='')=>`<button class="btn ${kind}" data-a="${act}" ${extra}><span>${html}</span></button>`;
export const stars=(n,cls='')=>`<span class="stars ${cls}" dir="ltr" aria-label="${n} כוכבים מתוך 3">${[0,1,2].map(i=>spr(i<n?'star':'star_off','st')).join('')}</span>`;
export const en=t=>`<bdi class="en" dir="ltr">${esc(t)}</bdi>`;
/* numbers, signs and fractions inside Hebrew text keep their own left-to-right order */
export const num=t=>`<bdi dir="ltr">${esc(t)}</bdi>`;

/* ---------- toast ---------- */
/* inside a level the toast has its own band: right under the hanging sign (or over the reading tip, which says the same kind of thing),
   never over the header. A level whose band is elsewhere (the slingshot: balloons hang under the sign) sets it with toastAt. */
let toastT=0,toastY=null;
export const toastAt=y=>{toastY=y};
export function toast(html,ms=2200){const t=document.getElementById('toast');
 if(stage.dataset.scr==='play'){const a=view.querySelector('.lv .prompt'),b=view.querySelector('.lv>.tip:not([hidden])'),s=stage.getBoundingClientRect();
  const y=toastY!=null?toastY:a?a.getBoundingClientRect().bottom-s.top+5:b?b.getBoundingClientRect().top-s.top-3:null;t.style.top=y!=null?y.toFixed(1)+'px':''}
 else t.style.top='';t.innerHTML=`<div class="toastin">${html}</div>`;t.classList.add('on');clearTimeout(toastT);toastT=setTimeout(()=>t.classList.remove('on'),ms)}

/* ---------- confetti (paper scraps), skipped when the user prefers reduced motion ---------- */
const COLS=['#F7D774','#EF8F7A','#A9C58F','#D7C2E6','#9CCBE0','#F6B78A'];
let fxRun=0;
export function confetti(x,y,n=70){
 if(reduced())return;const c=document.getElementById('fx'),d=Math.min(2,devicePixelRatio||1),W=stage.clientWidth,H=stage.clientHeight;
 c.width=W*d;c.height=H*d;const g=c.getContext('2d');g.setTransform(d,0,0,d,0,0);
 const ps=Array.from({length:n},(_,i)=>({x:x??W/2,y:y??H*.35,vx:(Math.random()-.5)*11,vy:-Math.random()*10-3,s:5+Math.random()*6,c:COLS[i%COLS.length],r:Math.random()*6,vr:(Math.random()-.5)*.4}));
 const id=++fxRun;let f=0;(function stepf(){if(id!==fxRun)return;g.clearRect(0,0,W,H);
  for(const p of ps){p.vy+=.32;p.vx*=.99;p.x+=p.vx;p.y+=p.vy;p.r+=p.vr;g.save();g.translate(p.x,p.y);g.rotate(p.r);g.globalAlpha=Math.max(0,1-f/100);g.fillStyle=p.c;g.fillRect(-p.s/2,-p.s/3,p.s,p.s*.66);g.restore()}
  if(++f<100)requestAnimationFrame(stepf);else g.clearRect(0,0,W,H)})()}
export function clearFx(){fxRun++;const c=document.getElementById('fx');c.getContext('2d').clearRect(0,0,c.width,c.height)}

/* level HUD used by all four level types */
/* book: 'c' while the story is being read, 'd' once the questions started (reading level only).
   The stars are the ones this level is worth right now. One rule in every game (see starsFor): when one is lost it
   visibly drops, and the first time in a level a line says why. */
let hudSt=3,hudHint=0;
export function hudReset(){hudSt=3;hudHint=0;toastY=null}
export function hud({i,n,st,book,hint}){
 const lost=st<hudSt?st:-1,byHint=lost>=0&&hint&&!hudHint;hudSt=st;hudHint=hint?1:0;
 if(lost>=0&&!byHint)toast(st===2?LOSS_NOTE:LOSS_NOTE2,3000);
 return `<div class="hud">
 <button class="mb" data-a="quit" aria-label="יציאה מהשלב"><span class="rb t1">${ico('close')}</span><small>יציאה</small></button>
 <div class="pips" aria-label="שאלה ${Math.max(1,Math.min(i+1,n))} מתוך ${n}">${book?`<img class="pb ${book}" src="${SP('ic_book')}" alt="">`:''}${Array.from({length:n},(_,k)=>`<i class="${k<i?'d':k===i?'c':''}"></i>`).join('')}</div>
 <div class="hst"><span class="stars live" dir="ltr" aria-label="${st} כוכבים מתוך 3">${[0,1,2].map(k=>`<span class="hs${k===lost?' lost':''}">${spr(k<st?'star':'star_off','st')}${k===lost?spr('star','st fall'):''}</span>`).join('')}</span><small>כוכבי השלב</small></div>
 <button class="mb" data-a="hint" aria-label="רמז"><span class="rb t3">${spr('lamp','rbi')}</span><small>רמז</small></button>
</div>`}
/* the star rule, worded the same in the help screen, in the level and on the result card */
export const HINT_NOTE='עם רמז מקבלים עד 2 כוכבים';
export const SLIP_NOTE='טעות אחת לא מורידה כוכב';
export const LOSS_NOTE='טעות שנייה בשלב: ירד כוכב';
export const LOSS_NOTE2='עוד טעות: ירד עוד כוכב';
export const sleep=ms=>new Promise(r=>setTimeout(r,ms));
