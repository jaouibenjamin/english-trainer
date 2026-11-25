/* world.html: the three new-world screens as a static preview. No saving, no backend, no network calls, no speech.
   Everything a pupil "chooses" here lives in memory and is gone on reload. The DEMO object below is the shape of the
   data each screen needs; docs/DESIGN.md describes it for the engineer who wires real state later.
   DOM is built with createElement and textContent only. */
import {ART} from './world_art.js';
import {AVATARS,NAME_A,NAME_B} from './world_data.js';   // the 20 characters and the two name lists
import {playAv} from './avanim.js';   // a character's 2 s animation, once, on tap, selection or hover

/* ---- flag: the page shows only with ?ds=1, or when the wi_ds flag is already set on this device (read only) ---- */
const flagOn=(()=>{
 if(new URLSearchParams(location.search).get('ds')==='1')return true;
 try{return localStorage.getItem('wi_ds')==='1'}catch(e){return false}
})();

/* ---- content ---- */
/* Where things sit on the pictures, in percent of the picture (x from the left, y from the top). */
const ISLES=[
 {id:'english',art:'map/island-english',he:'אנגלית',sub:'8 משימות',x:68,y:19,w:46,cls:''},
 {id:'math',art:'map/island-math',he:'חשבון',sub:'שברים',x:30,y:44,w:46,cls:' w-isle--gold'},
 {id:'soon1',art:'map/island-soon1',soon:1,x:76,y:60,w:30},
 {id:'soon2',art:'map/island-soon2',soon:1,x:24,y:84,w:30},
 {id:'soon3',art:'map/island-soon3',soon:1,x:70,y:88,w:30}];
const PATHS={
 english:[[41,89],[47,79.1],[53,69.2],[52,59.3],[49,49.4],[56,39.5],[63,29.6],[66,19.7]],
 math:[[44,89],[51,79.1],[53,69.2],[52,59.3],[48,49.4],[44,39.5],[50,29.6],[58,19.7]]};

/* ---- demo state: what the engineer's real state will provide ---- */
const DEMO={
 avatar:null,                    // avatar id, or null before the first choice
 name:[6,8],                     // indexes into NAME_A and NAME_B
 energy:{points:130,level:2,from:120,next:220,opens:'נפתחת דמות חדשה'},   // level only goes up; from/next are this level's thresholds
 stars:11,
 focus:{island:'english',mission:2,count:5},
 islands:{
  english:{he:'אנגלית',sub:['יחידה 1: ','All About Me'],bg:'bg/english',
   missions:[{en:'Meet Emma',stars:3},{en:'Cool Schools',stars:2},{en:'The New Flat',stars:1},{en:'A Birthday in Brazil',stars:0},
    {en:'A Special Present',stars:0},{en:'Months',stars:0},{en:'Numbers',stars:0},{he:'מבחן לדוגמה',stars:0}],current:3},
  math:{he:'חשבון',sub:['שברים',''],bg:'bg/math',
   missions:[{he:'חצי ורבע',stars:3},{he:'שברים שווים',stars:0},{he:'השוואת שברים',stars:0},{he:'חיבור שברים',stars:0},
    {he:'חיסור שברים',stars:0},{he:'מספרים מעורבים',stars:0},{he:'שברים על ישר',stars:0},{he:'מבחן לדוגמה',stars:0}],current:1}}};
const S={screen:'picker',pick:null,island:'english',muted:false};

/* ---- small DOM helpers ---- */
const $=id=>document.getElementById(id);
const SVG='http://www.w3.org/2000/svg';
function el(tag,cls,txt){const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}
function icon(id,cls){const s=document.createElementNS(SVG,'svg');s.setAttribute('class',cls||'wi-icon');s.setAttribute('aria-hidden','true');
 const u=document.createElementNS(SVG,'use');u.setAttribute('href','#'+id);s.appendChild(u);return s}
function img(art,cls){const i=el('img',cls);i.src=ART[art];i.alt='';i.decoding='async';i.draggable=false;return i}
function ltr(txt){const b=el('bdi',null,txt);b.dir='ltr';return b}
function stars(n){const w=el('span','wi-stars w-st__stars');for(let i=0;i<3;i++){const s=icon('i-star','wi-star'+(i<n?'':' wi-star--off'));w.appendChild(s)}return w}
const nameOf=()=>NAME_A[DEMO.name[0]].en+' '+NAME_B[DEMO.name[1]].en;
const STARS_HE=['בלי כוכבים עדיין','כוכב אחד','שני כוכבים','שלושה כוכבים'];

/* ---- screens ---- */
function show(name,focusId){
 S.screen=name;
 for(const n of ['picker','map','island'])$('s-'+n).hidden=n!==name;
 scrollTo(0,0);
 const h=$(focusId||{picker:'pk-h',map:'mp-h',island:'is-h'}[name]);if(h)h.focus({preventScroll:true});
}

/* 1. picker */
function drawGrid(){
 const g=$('avgrid');g.replaceChildren();
 for(const a of AVATARS){
  const locked=a.open>DEMO.energy.level,sel=S.pick===a.id;
  const b=el('button','wi-av'+(locked?' wi-av--locked':'')+(sel?' is-selected':''));b.type='button';
  if(locked)b.setAttribute('aria-label',a.he+', נפתחת ברמת אנרגיה '+a.open);
  else{b.setAttribute('aria-label',a.he);b.setAttribute('aria-pressed',sel?'true':'false')}
  b.appendChild(img('av/'+a.id,'wi-av__art'));
  if(sel){const bd=el('span','wi-av__badge');bd.appendChild(icon('i-check'));b.appendChild(bd)}
  if(locked){const lk=el('span','wi-av__lock');lk.appendChild(icon('i-lock'));b.appendChild(lk)}
  b.addEventListener('click',()=>{
   if(locked){$('pk-note-t').textContent=a.he+': נפתחת ברמת אנרגיה '+a.open+'. עכשיו אתם ברמה '+DEMO.energy.level+'.';return}
   S.pick=a.id;drawGrid();
   const again=g.querySelector('[aria-pressed=true]');if(again){again.focus({preventScroll:true});playAv(again.querySelector('.wi-av__art'),a.id)}
  });
  if(!locked)b.addEventListener('mouseenter',()=>{if(matchMedia('(hover: hover)').matches)playAv(b.querySelector('.wi-av__art'),a.id)});
  const w=el('div');w.appendChild(b);g.appendChild(w);
 }
 const nx=$('pk-next');nx.setAttribute('aria-disabled',S.pick?'false':'true');
 $('pk-why').textContent=S.pick?'':'קודם בוחרים דמות.';
}
function drawName(){
 const a=NAME_A[DEMO.name[0]],b=NAME_B[DEMO.name[1]];
 $('sp1-en').textContent=a.en;$('sp1-he').textContent=a.he;
 $('sp2-en').textContent=b.en;$('sp2-he').textContent=b.he;
 $('nm-name').textContent=nameOf();
 $('nm-pic').src=ART['av/'+S.pick];
}
function step(which,d){const L=which?NAME_B:NAME_A;DEMO.name[which]=(DEMO.name[which]+d+L.length)%L.length;drawName()}
function pickerStep(b){$('pk-a').hidden=b;$('pk-b').hidden=!b;scrollTo(0,0);$(b?'nm-h':'pk-h').focus({preventScroll:true})}

/* 2. map */
function drawMap(){
 $('s-map').style.backgroundImage='url("'+ART['bg/sea']+'")';
 $('mp-pic').src=ART['av/'+DEMO.avatar];
 $('mp-name').textContent=nameOf();
 $('mp-lv').textContent=DEMO.energy.level;
 $('mp-st').textContent=DEMO.stars;
 $('mp-focus-ico').src=ART['ui/focus'];
 /* The preview shows a neutral sample line, marked as a sample. The real line names the mission and comes with the state. */
 $('mp-focus-t').textContent='דוגמה: '+DEMO.focus.count+' מילים שכדאי לחזק. כמה דקות וזהו.';
 const sea=$('sea');sea.replaceChildren();
 for(const i of ISLES){
  const b=el('button','w-isle'+(i.soon?' w-isle--soon':i.cls));b.type='button';
  b.style.left=i.x+'%';b.style.top=i.y+'%';b.style.inlineSize=i.w+'%';
  b.appendChild(img(i.art));
  const tag=el('span','w-isle__tag');
  if(i.soon){tag.appendChild(icon('i-lock'));tag.appendChild(document.createTextNode('בקרוב'));b.setAttribute('aria-label','אי חדש, בקרוב')}
  else{tag.appendChild(document.createTextNode(i.he));tag.appendChild(el('small',null,i.sub))}
  b.appendChild(tag);
  b.addEventListener('click',()=>{
   const h=$('mp-hint');
   if(i.soon){h.textContent='האי הזה עוד בבנייה. הוא ייפתח בהמשך השנה.';h.hidden=false;return}
   h.hidden=true;openIsland(i.id);
  });
  sea.appendChild(b);
 }
}

/* 3. island */
function openIsland(id){S.island=id;drawIsland();show('island')}
function drawIsland(){
 const I=DEMO.islands[S.island],E=DEMO.energy,cur=I.current;
 $('is-h').textContent=I.he;
 const sub=$('is-sub');sub.replaceChildren(document.createTextNode(I.sub[0]));if(I.sub[1])sub.appendChild(ltr(I.sub[1]));
 $('is-bolt').src=ART['ui/bolt'];
 $('is-lv').textContent='רמה '+E.level;
 const pct=Math.max(0,Math.min(100,Math.round(100*(E.points-E.from)/(E.next-E.from))))||0;
 $('is-fill').style.setProperty('--p',pct);
 const bar=$('is-bar');bar.setAttribute('aria-label','רמת אנרגיה '+E.level);bar.setAttribute('aria-valuemax',E.next-E.from);bar.setAttribute('aria-valuenow',E.points-E.from);
 bar.setAttribute('aria-valuetext','רמה '+E.level+', עוד '+(E.next-E.points)+' לרמה '+(E.level+1));
 $('is-next').textContent='עוד '+(E.next-E.points)+' אנרגיה לרמה '+(E.level+1)+': '+E.opens+'.';
 $('stage').style.backgroundImage='url("'+ART[I.bg]+'")';
 const path=$('path');path.replaceChildren();
 $('is-hint').hidden=true;
 I.missions.forEach((m,k)=>{
  const state=k<cur?'done':k===cur?'current':'locked',n=k+1,[x,y]=PATHS[S.island][k];
  const li=el('li');li.style.left=x+'%';li.style.top=y+'%';
  const b=el('button','w-st w-st--'+state);b.type='button';
  b.setAttribute('aria-label','משימה '+n+(state==='done'?', '+STARS_HE[m.stars]:state==='current'?', כאן אתם עכשיו':', נעולה'));
  if(state==='current')b.setAttribute('aria-current','step');
  b.appendChild(img('ui/stone-'+state,'w-st__art'));
  const mark=el('span','w-st__mark');
  if(state==='locked')mark.appendChild(icon('i-lock'));else mark.textContent=n;
  b.appendChild(mark);
  if(state==='done')b.appendChild(stars(m.stars));
  if(state==='current')b.appendChild(img('av/'+DEMO.avatar,'w-st__who wi-bob'));
  b.addEventListener('click',()=>{
   const h=$('is-hint');
   if(state==='locked'){h.textContent='משימה '+n+' עוד נעולה. משחקים את משימה '+(cur+1)+' והדרך נפתחת.'}
   else if(state==='done'){h.textContent='משימה '+n+': '+STARS_HE[m.stars]+'. אפשר לשחק שוב ולאסוף עוד.'}
   else{h.textContent='כאן אתם עכשיו. לוחצים על הכפתור למטה ומתחילים.'}
   h.hidden=false;
  });
  li.appendChild(b);path.appendChild(li);
 });
 const p=$('is-play');
 p.replaceChildren(document.createTextNode('משחקים: משימה '+(cur+1)));
}

/* ---- dialogs: Esc and the button close; focus goes in and comes back ---- */
let lastFocus=null,openDlg=null;
function dlg(id,on){
 const d=$(id);
 if(on){lastFocus=document.activeElement;openDlg=id;d.hidden=false;d.querySelector('h2').focus()}
 else{d.hidden=true;openDlg=null;if(lastFocus)lastFocus.focus()}
}
function trap(e){
 if(!openDlg)return;
 if(e.key==='Escape'){dlg(openDlg,false);return}
 if(e.key!=='Tab')return;
 const f=[...$(openDlg).querySelectorAll('button')],a=document.activeElement;
 if(e.shiftKey&&(a===f[0]||!f.includes(a))){e.preventDefault();f[f.length-1].focus()}
 else if(!e.shiftKey&&a===f[f.length-1]){e.preventDefault();f[0].focus()}
}

/* ---- sound and calm: only the switches. There is no music file yet; calm mode also means no music. ---- */
function drawMute(){
 const calm=document.documentElement.classList.contains('calm'),off=S.muted||calm;
 for(const b of document.querySelectorAll('.js-mute')){
  b.setAttribute('aria-pressed',off?'false':'true');
  if(calm){b.setAttribute('aria-disabled','true');b.setAttribute('aria-label','מוזיקה כבויה במצב רגוע');b.title='מוזיקה כבויה במצב רגוע'}
  else{b.removeAttribute('aria-disabled');b.setAttribute('aria-label','מוזיקה');b.removeAttribute('title')}
  b.replaceChildren(icon(off?'i-mute':'i-sound'));
 }
}

function start(){
 document.title='ניצני אופק: העולם החדש (תצוגה)';   // the platform's new name (docs/PLAN.md); world.html shows only with the flag
 $('gate').hidden=true;$('app').hidden=false;
 drawGrid();
 $('pk-next').addEventListener('click',()=>{if(!S.pick){$('pk-why').textContent='קודם בוחרים דמות.';return}drawName();pickerStep(true)});
 $('sp1-prev').addEventListener('click',()=>step(0,-1));$('sp1-next').addEventListener('click',()=>step(0,1));
 $('sp2-prev').addEventListener('click',()=>step(1,-1));$('sp2-next').addEventListener('click',()=>step(1,1));
 $('nm-dice').addEventListener('click',()=>{
  let a,b;do{a=Math.floor(Math.random()*NAME_A.length);b=Math.floor(Math.random()*NAME_B.length)}while(a===DEMO.name[0]&&b===DEMO.name[1]);
  DEMO.name=[a,b];drawName()});
 $('nm-back').addEventListener('click',()=>pickerStep(false));
 $('nm-ok').addEventListener('click',()=>{DEMO.avatar=S.pick;drawMap();show('map')});
 $('mp-me').addEventListener('click',()=>{S.pick=DEMO.avatar;drawGrid();pickerStep(false);show('picker')});
 $('mp-go').addEventListener('click',()=>openIsland(DEMO.focus.island));
 $('is-back').addEventListener('click',()=>{drawMap();show('map')});
 $('is-play').addEventListener('click',()=>{const h=$('is-hint');h.textContent='זו תצוגה בלבד. המשחק עצמו יתחבר לכאן בהמשך.';h.hidden=false});
 for(const b of document.querySelectorAll('.js-energy'))b.addEventListener('click',()=>dlg('dlg-energy',true));
 for(const b of document.querySelectorAll('.js-gear'))b.addEventListener('click',()=>dlg('dlg-set',true));
 for(const b of document.querySelectorAll('.js-close'))b.addEventListener('click',()=>dlg(openDlg,false));
 for(const d of document.querySelectorAll('.wi-scrim'))d.addEventListener('click',e=>{if(e.target===d)dlg(d.id,false)});
 for(const b of document.querySelectorAll('.js-mute'))b.addEventListener('click',()=>{
  if(document.documentElement.classList.contains('calm'))return;S.muted=!S.muted;drawMute()});
 $('set-calm').addEventListener('click',e=>{
  const on=document.documentElement.classList.toggle('calm');e.currentTarget.setAttribute('aria-pressed',on?'true':'false');drawMute()});
 document.addEventListener('keydown',trap);
 drawMute();
 /* ?screen=map|island|name and ?island=math jump straight to a screen, for review and screenshots */
 const q=new URLSearchParams(location.search),sc=q.get('screen');
 if(sc==='name'||sc==='map'||sc==='island'){
  S.pick=DEMO.avatar='fox';drawGrid();
  if(sc==='name'){drawName();pickerStep(true);show('picker','nm-h')}
  else{drawMap();if(sc==='island')openIsland(q.get('island')==='math'?'math':'english');else show('map')}
 }else show('picker');
}
if(flagOn)start();
