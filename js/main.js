/* Word Islands: router and all non-level screens. */
import {ISLANDS,LEVEL_INFO,BALLS,MAX_STARS,WORDS,starsFor} from './data.js';
import {S,SET,saveSet,save,API,ERR,api,cred,auth,takeNewPin,award,logout,relogin,needsRelogin,syncState,push,pull,starsOf,islandStars,totalStars,isOpen,setStars,wordsKnown,unlockTTS,hush,esc,applyCalm} from './state.js';
import {initHelp,helpKnown,setHelp,clearNotes} from './help.js';
import {SND,unlock,musicOn,measure} from './audio.js';
import {$,view,stage,SP,BG,preload,CORE,setBg,bgMap,ico,spr,rb,btn,stars,en,num,toast,confetti,clearFx,sleep,HINT_NOTE,SLIP_NOTE,hudReset} from './ui.js';
import * as sling from './sling.js';
import * as listen from './listen.js';
import * as read from './read.js';
import * as bridge from './bridge.js';
import * as M from './math.js';
import * as X from './mock.js';
import {XSKILL,XORDER} from './xdata.js';
import {cardOn,initCard,cardScreen,cardSave,cardShare} from './card.js';
import {extraGame,extraOn,initExtra,extraRow,partsOf} from './extra.js';

const LEVELS={sling,listen,read,bridge};
const BGFIT={sling:'bottom',listen:'bottom',read:'bottom',bridge:'bridge'};
let level=null,V={name:''},navId=0;
const go=h=>{if(location.hash==='#'+h)route();else location.hash=h};
const isl=id=>ISLANDS.find(i=>i.id===+id);
const loader=()=>{view.innerHTML=`<div class="loader">${spr('crab_wave','bob')}<p>רגע, מפליגים…</p></div>`};
const top=(title,back='map')=>`<header class="top">${rb('nav',ico('back'),'חזרה',1,`data-to="${back}"`)}<h2 class="ribbon"><span>${title}</span></h2><span class="rbsp"></span></header>`;
const star=()=>spr('star','st');
const pts=n=>num((+n||0).toLocaleString('en-US'));
const nst=n=>`<span class="nb">${num(n)}${star()}</span>`;   // a number and its star never part at a line break

/* ---------- title ---------- */
/* The platform's name (owner's decision 25.11.2026, docs/PLAN.md). Shown only with the design flag (?ds=1) for now:
   the live class keeps "איי המילים" until the new look goes live. "איי המילים" stays the name of the English world
   (the English button, the card, the worksheet, Beach Run). */
const BRAND='ניצני אופק';
function title(){setBg('title','bottom');
 const d=Math.ceil((new Date(2026,10,25)-new Date())/864e5),md=M.daysToExam(),m=bgMap('bottom');
 view.innerHTML=`<section class="scr title">
  <div class="logo">${dsOn()?`<h1>${BRAND}</h1><p>אנגלית, חשבון ועוד: כל יום קצת</p>`:`<h1>איי המילים</h1><p class="en" dir="ltr">Word Islands · All About Me</p>`}</div>
  <div class="tgo subj"><p class="label pick">במה מתאמנים היום?</p>
   <button class="btn green xl sb" data-a="nav" data-to="map"><span><b>אנגלית</b><small>איי המילים${d>0&&d<60?` · מבחן בעוד ${num(d)} ימים`:''}</small></span></button>
   <button class="btn coral sb xm" data-a="nav" data-to="mock"><span><b>מבחן דמו באנגלית</b><small>${XS_last()}</small></span></button>
   <button class="btn blue xl sb" data-a="nav" data-to="math"><span><b>חשבון: שברים</b><small>מפרץ השברים${md>0&&md<30?` · מבחן בעוד ${num(md)} ימים`:''}</small></span></button>
   ${API&&S.u?`<p class="who">${esc(S.u.n)} · ${pts(S.pts)} נקודות</p>`:''}</div>
  ${spr('crab_wave','tcrab bob')}</section>`;
 const c=view.querySelector('.tcrab');c.style.left=(m.ox+466*m.s)+'px';c.style.top=(m.oy+1240*m.s)+'px'}

/* ---------- map ---------- */
function map(){setBg('map','center');const tot=totalStars(),W=stage.clientWidth,H=stage.clientHeight,mt=H<700?88:100;
 /* islands zigzag in two columns, so neighbours in a column are two rows apart; the lowest island and its label end 14px above the bottom */
 /* every level of every island has been played: a banner along the beach. "Finished" is said only at full stars;
    until then it says how many stars are missing, and every island that still has stars to collect is ringed */
 const played=ISLANDS.every(i=>i.levels.every(([t])=>starsOf(i.id,t)>0)),all=tot===MAX_STARS,m=bgMap('center'),iw0=Math.min(W*.37,150,(H-(dsOn()?WORLD_DOCK:0))*.19);   // with the design flag, sized from the height left after the dock
 /* the banner shows when every level was played; with the design flag only if the islands still fit with it and the dock (worldFits) */
 const fin=played&&(!dsOn()||worldFits(iw0,H,mt,84+WORLD_DOCK)),finH=(fin?84:0)+(dsOn()?WORLD_DOCK:0);   // with the design flag, room for the new world's dock (js/avatar.js)
 const iw=worldIw(iw0,H,mt,finH),
  cell=iw*.76+48,rowH=(H-mt-cell-14-finH)/5;
 /* the crab waits on the newest island that is open and still has stars to collect */
 const curI=ISLANDS.filter(i=>isOpen(i)&&islandStars(i)<i.levels.length*3).sort((a,b)=>b.id-a.id)[0]||null;

 const place=ISLANDS.map(i=>{const r=6-i.id;return{i,x:r%2?71:29,y:mt+rowH*r}});
 /* the sailboat and the whale swim in the two free gaps of the zigzag, so they can never sit under an island */
 const band=2*rowH-cell,deco=(n,x,r,h)=>band<34?'':`<img class="deco" src="${SP(n)}" alt="" style="left:${x}%;top:${(mt+rowH*r+cell+band/2).toFixed(1)}px;height:${Math.min(h,band-8).toFixed(1)}px">`;
 const yp=p=>((p.y+iw*.36)/H*100).toFixed(2),seq=[...place].sort((a,b)=>a.i.id-b.i.id);
 const path=seq.map((p,k)=>{if(!k)return`M${p.x} ${yp(p)}`;const q=seq[k-1];return`C${q.x} ${((+yp(q)+ +yp(p))/2-2).toFixed(2)} ${p.x} ${((+yp(q)+ +yp(p))/2+2).toFixed(2)} ${p.x} ${yp(p)}`}).join('');
 view.innerHTML=`<section class="scr map" style="--iw:${iw.toFixed(1)}px">
  <header class="maphead${API&&S.u?' cls':''}"><button class="mb" data-a="nav" data-to="settings"><span class="rb t1">${spr('ic_gear','rbi')}</span><small>הגדרות</small></button>
   <div class="sign total"><b>${star()}<span>${num(tot+' / '+MAX_STARS)}</span></b></div>
   <span class="tr">${API&&S.u?`<button class="mb" data-a="nav" data-to="board"><span class="rb t3">${spr('trophy','rbi')}</span><small>טבלה</small></button>`:''}<button class="mb" data-a="nav" data-to="collection"><span class="rb t2">${spr('chest','rbi')}</span><small>האוסף</small></button></span></header>
  ${fin?`<div class="fin label${all?' all':''}" role="status">${spr(all?'crab_star':'crab_wave','fc bob')}<p>${all?`<b>כל הכבוד! סיימתם את כל האיים</b><small>כל ${num(MAX_STARS)} הכוכבים שלכם. אפשר לשחק שוב בכל שלב${API&&S.u?' ולצבור נקודות':''}</small>`
   :`<b>עברתם בכל האיים!</b><small><span class="nb">${MAX_STARS-tot===1?'חסר לכם עוד כוכב אחד':`חסרים לכם עוד ${num(MAX_STARS-tot)} כוכבים`}</span> <span class="nb">באיים שבמסגרת הצהובה</span></small>`}</p>${all?spr('trophy','ft'):`<span class="fs">${star()}<i>${num(tot+'/'+MAX_STARS)}</i></span>`}</div>`:''}
  <button class="subjpill" data-a="nav" data-to="">${ico('back')}<span>מקצועות</span></button>
  ${deco('boat',24,0,58)}${deco('whale',76,1,46)}
  ${played?'':`<img class="compass" src="${SP('compass')}" alt="" style="top:${Math.min(H-80,m.oy+1215*m.s-36).toFixed(1)}px">`}
  <svg class="route" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="${path}"/></svg>
  ${place.map(({i,x,y})=>{const o=isOpen(i),st=islandStars(i),mx=i.levels.length*3,cur=i===curI,todo=played&&o&&st<mx;
   return `<button class="isl i${i.id}${o?'':' locked'}${st===mx?' full':''}${cur?' cur':''}${todo?' todo':''}${x<50?' lc':''}" style="left:${x}%;top:${y.toFixed(1)}px" data-a="${o?'nav':'locked'}" data-to="island/${i.id}" data-need="${i.need}" aria-label="${esc(i.he)}${o?'':' (נעול)'}${cur&&dsOn()?(tot?', ממשיכים כאן':', מתחילים כאן'):''}">
    <span class="pw">${spr('isl_'+i.id,'pic')}${o?'':spr('lock','lk')}${cur?`<span class="here">${spr('crab_wave','bc')}</span>`:''}</span>
    <span class="tag">${cur?`<em class="hb">${tot?'ממשיכים כאן':'מתחילים כאן'}</em>`:''}<b>${esc(i.he)}</b>${i.bonus?`<small class="bn">אי בונוס · שני שלבים</small>`:''}<small>${o?`${star()}${num(st+'/'+mx)}${st===mx?spr('ic_check','ck'):''}`:`נפתח ב־${num(i.need)}${star()}`}</small></span></button>`}).join('')}
 </section>`;worldMap();
 /* with the design flag, a very short screen leaves the all-played banner out (worldFits): say its line once per visit */
 if(played&&!fin&&!finSaid){finSaid=true;toast(all?'כל הכבוד! סיימתם את כל האיים':`עברתם בכל האיים! ${MAX_STARS-tot===1?'חסר לכם עוד כוכב אחד':`חסרים לכם עוד ${num(MAX_STARS-tot)} כוכבים`} באיים שבמסגרת הצהובה`,3200)}}
let finSaid=false;   // the all-played line was said as a toast in this visit (a logout resets it, for the next pupil on this tab)
/* the new world behind the design flag (?ds=1): js/avatar.js is fetched only on such a device; without the flag this does nothing */
const dsOn=()=>document.documentElement.classList.contains('ds');
const WORLD_DOCK=76;   // px kept free at the bottom of the map for the dock of js/avatar.js (css/avatar.css .wd)
/* The islands' size with the design flag. Its island pictures are 7:6 (4:3 when the viewport is at most 700px high)
   and its labels a little taller, so an island and its label need more height than the game's own layout gives them.
   Islands in one column are two rows apart: worldIw shrinks them until a picture and its label fit in that space.
   - THESE NUMBERS COPY css/ds-game.css (img.pic[src*="/isl_"] aspect-ratio 7/6, and 4/3 under @media (max-height:700px)):
     change them together. The media test below is the same viewport test as the CSS.
   - WORLD_TAG is the tallest label (the bonus island's three lines, 74px); 56px is the smallest island (320x568).
   - Without the flag the size is returned unchanged. */
const WORLD_TAG=74,worldPr=()=>matchMedia('(max-height:700px)').matches?.75:6/7,worldRoom=(w,H,mt,finH)=>2*(H-mt-(w*.76+48)-14-finH)/5;
function worldIw(iw,H,mt,finH){if(!dsOn())return iw;const pr=worldPr();
 while(iw>56&&iw*pr+WORLD_TAG>worldRoom(iw,H,mt,finH))iw-=2;
 return iw}
/* do the islands fit at all (even at the smallest size) with this much kept free at the bottom? On a very short phone
   (320x568) the all-played banner and the dock together leave too little: then the banner is left out */
function worldFits(iw0,H,mt,finH){const iw=worldIw(iw0,H,mt,finH);return iw*worldPr()+WORLD_TAG<=worldRoom(iw,H,mt,finH)}
function worldMap(){if(!dsOn())return;const my=navId;import('./avatar.js').then(m=>{if(my===navId&&V.name==='map')return m.decorateMap(view,go,()=>my===navId&&V.name==='map')}).catch(()=>{})}

/* ---------- island ---------- */
function island(id){const i=isl(id);if(!i||!isOpen(i))return go('map');setBg('paper','center');const next=[BG(i.bg),BG('listen'),BG('read'),BG('bridge')];if(!dsOn())preload(next);
 const got=islandStars(i);
 view.innerHTML=`<section class="scr island${extraOn()?' hasx':''}">${top(esc(i.he))}
  <p class="isub">${i.bonus?'אי בונוס: חודשים ומספרים, שני שלבים':`מילים מתוך: ${en(i.en)}`}</p>
  <div class="ihero">${spr('isl_'+i.id,'pic')}<p class="chips"><span class="chip">${star()}${num(got+' / '+i.levels.length*3)}</span>${SET.sheet===true?`<a class="chip wsl" href="worksheet.html?i=${i.id}">דף עבודה להדפסה</a>`:''}</p></div>
  ${extraRow(i)}<div class="lvlist">${i.levels.map(([t],k)=>{const L=LEVEL_INFO[t],s=starsOf(i.id,t);
   return `<button class="lvrow p${k%4}" data-a="nav" data-to="play/${i.id}/${t}"><span class="lic">${spr(L.icon)}</span><span class="lt"><b>${L.name}</b>${stars(s)}<small>${L.sub}</small></span></button>`}).join('')}</div>
  <div class="guide">${spr('crab_wave','bob')}<p class="label">${i.bonus&&!got?'כאן יש שני שלבים: חודשים בקלע, מספרים בהאזנה':got?'אפשר לחזור לכל שלב ולאסוף עוד כוכבים':'בחרו שלב. יש ארבעה, כמו חלקי המבחן'}</p></div></section>`;worldIsland(i,next)}
/* with the design flag, the island's levels become a path of stones (js/avatar.js islandPath): the list waits, hidden,
   only while that loads, and comes back if it cannot; the levels' backgrounds are fetched ahead only after that. Without
   the flag this does nothing (island() fetches them ahead at once, as before) */
function worldIsland(i,next){if(!dsOn())return;const list=view.querySelector('.scr.island .lvlist');if(!list)return;list.style.visibility='hidden';const my=navId;
 import('./avatar.js').then(m=>my===navId&&V.name==='island'?m.islandPath(view,i,go,()=>my===navId&&V.name==='island'):null).catch(()=>{}).then(()=>{if(list.isConnected)list.style.visibility='';preload(next)})}   // the levels' backgrounds, after the path: not before the screen's own art

/* ---------- play + result ---------- */
async function play(id,type){const i=isl(id),lv=i&&i.levels.find(l=>l[0]===type);if(!lv||!isOpen(i))return go('map');
 const my=navId;loader();const bg=LEVEL_INFO[type].bg||i.bg;await preload([BG(bg),...CORE]);if(my!==navId)return;
 setBg(bg,BGFIT[type]);hudReset();
 const l=await LEVELS[type].start(view,{island:i,type,part:lv[1]},{done:r=>result(i,type,r)});
 if(my!==navId){l.destroy();return}level=l}
function result(i,type,r){if(level){level.destroy();level=null}clearFx();hush();
 const {gained,opened}=setStars(i.id,type,r.stars),clean=r.first===r.total;
 const k=i.levels.findIndex(l=>l[0]===type),nx=i.levels[k+1],nextIsl=!nx&&ISLANDS.find(o=>o.id===i.id+1&&isOpen(o));
 const to=nx?`play/${i.id}/${nx[0]}`:nextIsl?`island/${nextIsl.id}`:'map',nextLabel=nx?'לשלב הבא':nextIsl?'לאי הבא':'למפה';
 const head=clean&&r.stars===3?'מושלם!':r.stars===3?'כל הכבוד!':r.stars===2?'יפה מאוד!':'סיימתם!';
 /* one line that explains the stars: the same score always gives the same stars unless the hint capped them, and then it says so */
 const capped=r.hint&&starsFor(r.first,r.total,0)===3;
 const note=capped?HINT_NOTE:clean?'בלי אף טעות!':r.stars===3?SLIP_NOTE:r.hint?HINT_NOTE+'. אפשר לשחק שוב':'אפשר לשחק שוב ולאסוף עוד כוכבים';
 const tot=totalStars(),lockedI=ISLANDS.find(o=>!isOpen(o));
 const extra=opened.length?`<p class="unlock">${spr('isl_'+opened[0].id,'ui')}<span><i>נפתח אי חדש!</i><b>${esc(opened[0].he)}</b></span></p>`
  :r.review&&r.review.length?`<div class="review"><small>כדאי לחזור על</small>${r.review.slice(0,2).map(w=>`<span class="rv">${en(w.en)} · ${esc(w.he.split(',')[0])}</span>`).join('')}</div>`
  :lockedI?`<p class="unlock goal">${spr('isl_'+lockedI.id,'ui')}<span><i>עוד ${nst(lockedI.need-tot)} ונפתח</i><b>${esc(lockedI.he)}</b></span></p>`
  :`<p class="unlock goal">${spr('trophy','ui')}<span><i>כל האיים פתוחים!</i><b>${star()}${num(tot+' / '+MAX_STARS)}</b></span></p>`;
 V={name:'result'};stage.dataset.scr='result';setBg(i.bg,'bottom');   // every result sits over the island's own beach
 view.innerHTML=`<section class="scr result"><div class="scrollp card">
   <h2 class="ribbon"><span>${head}</span></h2>
   <div class="bigstars" dir="ltr">${[0,1,2].map(n=>`<span class="bs ${n<r.stars?'on':''}" style="--i:${n}">${spr(n<r.stars?'star':'star_off','')}</span>`).join('')}</div>
   ${spr(r.stars===3?'crab_star':r.stars===2?'crab_happy':'crab_wave','rcrab bob')}
   <p class="line">${num(r.first)} מתוך ${num(r.total)} בניסיון הראשון</p>
   <p class="note">${note}</p>
   <div class="xtra">${extra}</div>
   <p class="gain">${gained?`${num('+'+gained)} כוכבים למפה`:'הכוכבים שלכם נשמרו'}</p>${API&&S.u?`<p class="gain cp">${spr('trophy','gt')}${pts(S.pts)} נקודות לטבלת הכיתה</p>`:''}
   <div class="rbtns">${btn('nav',`${nextLabel} ${ico('next')}`,'green xl',`data-to="${to}"`)}
    <div class="row">${btn('nav',ico('retry')+' שוב','cream sm',`data-to="play/${i.id}/${type}" data-force="1"`)}${btn('nav','לשלבים','cream sm',`data-to="island/${i.id}"`)}</div></div>
  </div></section>`;
 if(r.stars>=2){confetti();SND.win()}
 [0,1,2].forEach(n=>{if(n<r.stars)setTimeout(()=>SND.star(n),350+n*330)});
 if(opened.length)setTimeout(()=>SND.unlock(),1500)}

/* ---------- collection ---------- */
function collection(){setBg('paper','center');const tot=totalStars(),nxt=BALLS.find(b=>b.need>tot);
 view.innerHTML=`<section class="scr coll">${top('האוסף של פיצי')}
  <div class="chero">${spr('crab_star','bob')}<p class="label"><b>${nxt?`חסרים לכם עוד ${nst(nxt.need-tot)} לכדור הבא`:'כל הכדורים שלכם. אלופים!'}</b><small>הכדור שבוחרים כאן יעוף בקלע המילים</small></p></div>
  <div class="balls">${BALLS.map((b,k)=>{const ok=tot>=b.need,sel=(S.g.ball||0)===k;
   return `<button class="ball${ok?'':' locked'}${sel?' sel':''}" data-a="${ok?'ball':'locked'}" data-i="${k}" data-need="${b.need}" aria-pressed="${sel}"><span class="bw">${spr('ball_'+k,'bi')}${ok?'':spr('lock','lk')}${sel?spr('ic_check','sl'):''}</span><b>${b.name}</b><small>${ok?(sel?'בקלע עכשיו':'לחצו כדי לבחור'):`${num(b.need)}${star()}`}</small></button>`}).join('')}</div></section>`}

/* ---------- settings + help ---------- */
/* what the pages' security policy blocked on this device in the last 14 days (js/csplog.js keeps the last 10: directive, origin, day).
   Nothing shows while the list is empty, which is the usual case. Read here, never sent anywhere. */
function cspLine(){let l=[];try{l=JSON.parse(localStorage.getItem('wi_csp')||'[]')}catch(e){}
 const since=Math.floor(Date.now()/864e5)-14;   // only the last 14 days: after a fix the line goes away by itself
 l=Array.isArray(l)?l.filter(x=>x&&typeof x==='object'&&typeof x.d==='string'&&typeof x.o==='string'&&typeof x.t==='number'&&x.t>=since):[];
 if(!l.length)return'';const n={};for(const x of l){const k=x.d.slice(0,40)+' '+x.o.slice(0,120);n[k]=(n[k]||0)+1}
 return`<p class="credit csp">חסימות אבטחה אחרונות: <bdi dir="ltr">${Object.entries(n).map(([k,c])=>esc(k)+(c>1?' ×'+c:'')).join(' · ')}</bdi></p>`}
function settings(){setBg('paper','center');
 const tog=(k,label,icon)=>`<button class="setrow" data-a="toggle" data-k="${k}" role="switch" aria-checked="${SET[k]}">${spr(icon,'si')}<span class="sl">${label}</span><i class="sw${SET[k]?' on':''}"><em>${SET[k]?ico('check'):''}</em><b>${SET[k]?'פועל':'כבוי'}</b></i></button>`;
 const lnk=(inner,icon,t,d)=>`<${inner} class="setrow link">${spr(icon,'si')}<span class="sl">${t}<small>${d}</small></span>${ico('next','go')}</${inner.split(' ')[0]}>`;
 /* "more": a switch added a row (word help, the card); "signed": the account panel is there. game.css fits the screen to both */
 view.innerHTML=`<section class="scr settings${helpKnown()||cardOn()?' more':''}${API&&S.u?' signed':''}">${top('הגדרות')}
  <div class="fill">
  <div class="panel label">${tog('music','מוזיקה','ic_note')}${tog('sfx','צלילים','ic_speaker')}${tog('calm','תצוגה רגועה<small>בלי תנועה וקונפטי</small>','ic_check')}${helpKnown()?tog('help','עזרה במילים<small>לחיצה על מילה מראה פירוש, ו־🐢 משמיע לאט</small>','ic_book'):''}</div>
  <div class="panel label">${lnk('button data-a="nav" data-to="help"','ic_buoy','איך משחקים?','הסבר קצר על ארבעת השלבים')}
   ${lnk('a href="trainer.html"','ic_book','תרגול קלאסי','כרטיסיות וחידונים, בלי משחק')}${cardOn()?lnk('button data-a="nav" data-to="card"','trophy','הכרטיס שלי','להראות או לשמור כתמונה'):''}</div>
  <div class="panel label"><div class="prog"><p>${star()}<b>${num(totalStars()+' / '+MAX_STARS)}</b><small>כוכבים</small></p><p>${spr('ic_book','pi')}<b>${num(wordsKnown()+' / 59')}</b><small>מילים שנלמדו</small></p><p>${spr('bottle','pi')}<b>${num(Object.values(S.read).filter(v=>v>0).length+' / 5')}</b><small>סיפורים שנקראו</small></p></div>
   <p class="credit">המילים והפירושים לפי רשימת המורה ליחידה ${num(1)}</p>${cspLine()}</div>
  ${API&&S.u?`<div class="panel label acct"><p>${esc(S.u.n)}<small>${pts(S.pts)} נקודות<br><span class="aw">${num(wordsKnown())} מילים שנלמדו<br></span>${syncLine()}</small></p>${btn('logout',spr('ic_door','bi')+' התנתקות','coral sm')}</div>`:''}
  </div>
  ${API&&S.u?'':`<div class="guide">${spr('crab_listen','bob')}<p class="label">ההתקדמות נשמרת במכשיר הזה</p></div>`}</section>`}   // signed in, the account panel takes the note's place
function help(){setBg('paper','center');
 const c=(icon,t,d)=>`<div class="hrow label"><span class="hi">${spr(icon)}</span><span class="ht"><b>${t}</b><small>${d}</small></span></div>`;
 view.innerHTML=`<section class="scr help">${top('איך משחקים?','settings')}
  ${c('fork','קלע המילים','גוררים את הכדור אחורה, מכוונים לפי הנקודות ומשחררים. קולעים לבלון עם המילה שמתאימה לפירוש.')}
  ${c('conch','תופסים צלילים','שומעים מילה ולוחצים על הבועה שלה. בהמשך לוחצים על הפירוש. אפשר להשמיע שוב ושוב.')}
  ${c('bottle','בקבוק הסיפור','קוראים סיפור קצר. לחיצה על מילה מראה את הפירוש שלה. אחר כך בוחרים את הבקבוק עם התשובה.')}
  ${c('ic_bridge','גשר המשפטים','לוחצים על קרשי המילים לפי הסדר. אות גדולה בהתחלה, נקודה בסוף.')}
  ${c('star','כוכבים','בכל שלב יש עד 3 כוכבים, והם פותחים איים חדשים. הכוכבים למעלה מראים כמה השלב שווה עכשיו. '+SLIP_NOTE+'. '+HINT_NOTE+'.')}</section>`}

/* ---------- class mode: login, leaderboard, teacher (same backend calls as the classic trainer) ---------- */
function login(){setBg('paper','center');
 /* a device that has never signed in starts on "first time"; afterwards the usual case is coming back */
 const reg=(V.m||(S.lastC?'login':'register'))==='register';
 const tab=(m,t)=>`<button type="button" role="tab" aria-selected="${(m==='register')===reg}" data-a="lmode" data-m="${m}">${t}</button>`;
 const sw=V.sw?`<button type="button" class="swl" data-a="lmode" data-m="${V.sw}">${V.sw==='register'?'זאת הפעם הראשונה שלי':'כבר נרשמתי'} ${ico('next')}</button>`:'';
 const fg=`<button type="button" class="swl" data-a="forgot">שכחתי את הקוד ${ico('next')}</button>`,pinErr=V.err===ERR.pin||V.err===ERR.locked;
 view.innerHTML=`<section class="scr login"><div class="logo sm"><h1>${dsOn()?BRAND:'איי המילים'}</h1></div>
  <div class="lwrap">${spr('crab_wave','lcrab')}
  <form class="scrollp lcard" id="lf" autocomplete="off"><h3>כניסה לכיתה</h3>
   <div class="seg" role="tablist" aria-label="כניסה או הרשמה">${tab('login','כבר נרשמתי')}${tab('register','פעם ראשונה שלי')}</div>
   <label for="lc">קוד הכיתה (מהמורה)</label><input id="lc" class="in en" dir="ltr" autocapitalize="characters" autocomplete="off" value="${esc(V.c??S.lastC)}">
   <label for="ln">השם שלי</label><input id="ln" class="in" maxlength="20" autocomplete="off" value="${esc(V.n||'')}">
   <label for="lp">${reg?'קוד סודי חדש (4 ספרות)':'הקוד הסודי שלי (4 ספרות)'}</label><input id="lp" class="in en pin" dir="ltr" type="password" inputmode="numeric" maxlength="4" autocomplete="off" value="${esc(V.p||'')}">
   ${V.err?`<p class="err" role="alert"><span>${esc(V.err)}</span>${sw||(pinErr&&!reg?fg:'')}</p>`:`<p class="lnote">${reg?'בוחרים 4 ספרות שרק אתם יודעים. לא הקוד של הטלפון!':`נכנסים עם השם והקוד הסודי שבחרתם <button type="button" class="fgl" data-a="forgot">שכחתי את הקוד</button>`}</p>`}
   ${btn('auth',V.busy?'רגע…':reg?'נרשמים':'כניסה','green wide',`data-m="${reg?'register':'login'}" type="button" ${V.busy?'disabled':''}`)}</form></div>
  ${btn('nav','כניסת מורה','cream sm tlink','data-to="teacher"')}</section>`}
/* ---------- the class table did not take this device's progress ----------
   Shown on the main screens until the pupil signs in again. Before this, a refused save was silent. */
const RELOG_MSG={class:'קוד הכיתה השתנה. התחברו עם הקוד החדש.',nouser:'השם שלכם לא נמצא בטבלת הכיתה. אולי הוא שונה: התחברו עם השם החדש.',pin:'הקוד הסודי לא מתאים. התחברו שוב.'};
/* the mock exam line on the title: what to do next */
function XS_last(){const x=X.XS(),t=x.tries[x.tries.length-1];if(!t)return'20 שאלות, כמו במבחן';const p=Math.round(t.total[0]/t.total[1]*100);return X.needs().length&&!X.canRetake()?`${p}% · יש אימון שמחכה לכם`:`${p}% בניסיון האחרון`}
function syncBar(){const el=document.getElementById('syncbar');if(!el)return;
 const show=needsRelogin()&&['title','map','math','misland','island','settings','board','collection'].includes(V.name);
 el.classList.toggle('on',show);
 el.innerHTML=show?`<button class="syncb" data-a="relogin"><b>ההתקדמות לא נשמרת בטבלת הכיתה</b><small>${esc((RELOG_MSG[syncState().err]||'').split('.')[0])}. לחצו כאן כדי להתחבר שוב</small></button>`:''}
addEventListener('sync',syncBar);
function syncLine(){const s=syncState();if(needsRelogin())return'<b class="sbad">לא נשמר בטבלת הכיתה</b>';
 if(!s.at)return'עוד לא נשמר בטבלת הכיתה';const t=new Date(s.at),today=new Date().toDateString()===t.toDateString();
 return`נשמר בטבלת הכיתה ${today?'היום':num(t.getDate()+'/'+(t.getMonth()+1))} ב־${num(String(t.getHours()).padStart(2,'0')+':'+String(t.getMinutes()).padStart(2,'0'))}`}
function board(){if(!API||!S.u)return go('map');setBg('paper','center');
 if(!V.rows){view.innerHTML=`<section class="scr board">${top('טבלת הכיתה')}<p class="panel label msg">${esc(V.err||'טוענים את הטבלה…')}</p></section>`;
  if(!V.req){V.req=1;const v=V;push().then(()=>api('board',cred())).then(r=>{if(V!==v)return;if(r.ok)V.rows=r.rows;else V.err=ERR[r.e]||ERR.net;board()}).catch(()=>{if(V!==v)return;V.err=ERR.net;board()})}return}
 /* encouraging by design: the podium, the top five and the pupil's own place. Nobody is shown as last. */
 const R=V.rows,me=S.u.n,rank=R.findIndex(d=>d.n===me);
 /* the pupil's own row says where they stand in the class, and the line under it gives the next small step (never the gap to the leader) */
 const gap=rank>0?Math.max(1,(+R[rank-1].pts||0)-(+R[rank].pts||0)+1):0;
 const row=(d,i)=>d.n===me?`<li class="me"><span class="rk">${i+1}</span><span class="nm">${esc(d.n)} (אני)<small class="pl2">מקום ${num(i+1)} מתוך ${num(R.length)}</small></span><span class="pt">${pts(d.pts)}</span></li>${i>0?`<li class="nxt">כל שלב מוסיף נקודות. <span class="nb">עוד ${pts(gap)} נקודות למקום הבא</span></li>`:''}`
  :`<li><span class="rk">${i+1}</span><span class="nm">${esc(d.n)}${d.streak>=3?`<small> · ${num(d.streak)} ימים ברצף</small>`:''}</span><span class="pt">${pts(d.pts)}</span></li>`;
 view.innerHTML=`<section class="scr board">${top('טבלת הכיתה')}
  <div class="fill">
  <div class="podium" dir="ltr">${[1,0,2].map(i=>{const d=R[i];return `<div class="pd pd${i}${d&&d.n===me?' me':''}${d?'':' empty'}">${i===0?spr('trophy','tro'):''}<b dir="auto">${d?esc(d.n):'מקום פנוי'}</b><i class="step"><em>${i+1}</em></i></div>`}).join('')}</div>
  <ol class="lb">${R.slice(0,5).map(row).join('')}${rank>4?`<li class="sep" aria-hidden="true"><i></i><i></i><i></i></li>${row(R[rank],rank)}`:''}</ol>
  </div>
  <div class="guide">${spr('crab_happy','bob')}<p class="label">${R.length<3?'עוד מעט כל הכיתה כאן. כל שלב מוסיף נקודות!':rank===0?'אתם במקום הראשון. כל הכבוד!':'תשובה נכונה, כוכב חדש ויום תרגול: הכול מוסיף נקודות'}</p></div></section>`}
function teacher(){setBg('paper','center');const back=API&&!S.u?'login':'map';
 if(!API){view.innerHTML=`<section class="scr teacher">${top('מסך המורה',back)}<p class="panel label msg">מסך המורה יהיה זמין אחרי חיבור הכיתה.</p></section>`;return}
 if(!V.data){view.innerHTML=`<section class="scr teacher">${top('מסך המורה',back)}<form class="panel label" id="tf" autocomplete="off">
   <label for="tc">קוד הכיתה</label><input id="tc" class="in en" dir="ltr" autocomplete="off" value="${esc(V.c??(S.u?S.u.c:S.lastC))}">
   <label for="tt">קוד המורה</label><input id="tt" class="in en" dir="ltr" type="password" autocomplete="off">
   <p class="err" role="alert">${esc(V.err||'')}</p>${btn('tlogin',V.busy?'רגע…':'כניסה','green',`type="button" ${V.busy?'disabled':''}`)}</form>
   <div class="guide">${spr('crab_listen','bob')}<p class="label">קוד המורה נמצא בגיליון, בלשונית ${en('config')}</p></div></section>`;return}
 const D=V.data,he=Object.fromEntries(WORDS.map(w=>[w.en,w.he]));
 /* the class's hard words: only words of the unit (a pupil's browser could send anything), and a percentage that is a
    number from 0 to 100 (it becomes a width in the page) */
 const hardList=(Array.isArray(D.hard)?D.hard:[]).filter(w=>Array.isArray(w)&&typeof w[0]==='string'&&Object.prototype.hasOwnProperty.call(he,w[0])).map(w=>[w[0],Math.max(0,Math.min(100,Math.round(+w[1]||0)))]);
 /* days since the pupil last practised (null = never) */
 const idle=d=>{const p=String(d.day||'').split('-').map(Number);return p.length===3&&!p.some(isNaN)?Math.floor((Date.now()-new Date(p[0],p[1]-1,p[2]))/864e5):null};
 /* the coloured tag is kept for pupils who really need a nudge: many wrong answers, or no practice for 3 days.
    A backend that does not send stars yet (older deployment) falls back to the words-learned rule. */
 const NL=ISLANDS.reduce((a,i)=>a+i.levels.length,0),hasStars=d=>typeof d.stars==='number';
 const tag=d=>{const n=idle(d);if(n===null)return['r','עוד לא התחיל/ה'];
  if(!hasStars(d))return d.words<10?['r','צריך חיזוק']:n>=3?['r',`לא תרגל/ה ${n} ימים`]:d.words>=40?['g','מוכן/ה']:['n','בדרך'];
  return d.tries>=15&&d.miss/d.tries>=.3?['r','צריך חיזוק']:n>=3?['r',`לא תרגל/ה ${n} ימים`]:d.stars>=MAX_STARS*.8?['g','מוכן/ה']:['n','בדרך']};
 /* The mock exam on a pupil's card: behind a switch (?tmock=1 on the teacher's device), and only when the backend
    sends it. An older deployment sends no "mock" field at all: then the card is drawn exactly as before.
    Every number is checked before it is shown; nothing from the backend is drawn as text. */
 const pr=p=>Array.isArray(p)&&p.length===2&&p.every(v=>Number.isInteger(v)&&v>=0&&v<1000)&&p[1]>0&&p[0]<=p[1]?p:null,frac=p=>num(p[0]+' / '+p[1]);
 const mockRow=d=>{if(SET.tmock!==true||!d||typeof d!=='object'||!('mock' in d))return'';const m=d.mock,last=m&&pr(m.last);
  if(!last)return`<p class="ks km"><span>מבחן דמו: עוד לא ניסה/תה</span></p>`;
  const n=Number.isInteger(m.n)&&m.n>0&&m.n<100?m.n:1,first=pr(m.first),sc=XORDER.map(k=>[k,pr(m.sc&&m.sc[k])]).filter(x=>x[1]);
  return`<p class="ks km"><span><b>מבחן דמו</b> ${n===1?'ניסיון אחד':num(n)+' ניסיונות'}</span><span>אחרון ${frac(last)}</span>${n>1&&first?`<span>${n>=20?'הוותיק מ־20 האחרונים':'ראשון'} ${frac(first)}</span>`:''}</p>
   ${sc.length?`<p class="ks km sk">${sc.map(([k,p])=>`<span>${XSKILL[k].he} ${frac(p)}</span>`).join('')}</p>`:''}`};
 view.innerHTML=`<section class="scr teacher wide">${top('מסך המורה',back)}
  <div class="panel label"><h3>המילים הקשות לכיתה</h3>${hardList.length?`<div class="hard">${hardList.map(w=>`<div><span>${en(w[0])}<i>${esc(he[w[0]])}</i><b>${num(w[1]+'%')} טעויות</b></span><div class="pbar"><i style="width:${w[1]}%"></i></div></div>`).join('')}</div>`:'<p class="msg">עדיין אין מספיק תרגול כדי לדעת.</p>'}</div>
  ${D.kids.length?`<div class="kids">${D.kids.map(d=>{const s=tag(d),dd=String(d.day||'').split('-');
   return `<div class="kid label"><p class="kn"><b><bdi>${esc(d.n)}</bdi></b><span class="pill ${s[0]}">${s[1]}</span><button class="treset" data-a="treset" data-n="${esc(d.n)}">איפוס קוד</button></p>
    ${hasStars(d)?`<p class="kw"><span>כוכבים</span>${num(d.stars+' / '+MAX_STARS)}</p><div class="pbar"><i style="width:${Math.min(100,d.stars/MAX_STARS*100)}%"></i></div>
    <p class="ks"><span>שלבים ${num(d.levels+' / '+NL)}</span><span>${pts(d.pts)} נקודות</span><span>${dd.length===3?'תרגול אחרון '+num(dd[2]+'/'+dd[1]):'עוד לא תרגל/ה'}</span></p>
    <p class="ks"><span>מילים שנלמדו ${num(d.words+' / 59')}</span><span>קטעי קריאה בלי טעות ${num(d.reads+' / 5')}</span>${d.tries?`<span>${num(Math.round(d.miss/d.tries*100)+'%')} טעויות</span>`:''}`
    :`<p class="kw"><span>מילים שנלמדו</span>${num(d.words+' / 59')}</p><div class="pbar"><i style="width:${Math.min(100,d.words/59*100)}%"></i></div>
    <p class="ks"><span>קטעי קריאה ${num(d.reads+' / 5')}</span><span>${pts(d.pts)} נקודות</span><span>${dd.length===3?'תרגול אחרון '+num(dd[2]+'/'+dd[1]):'עוד לא תרגל/ה'}</span>`}</p>${mockRow(d)}</div>`}).join('')}</div>`:'<p class="panel label msg">עדיין אף תלמיד לא נרשם.</p>'}
  <p class="credit">כוכבים: עד ${num(3)} בכל שלב, ${num(MAX_STARS)} בסך הכול · מילה נחשבת "נלמדה" אחרי שתי תשובות נכונות ברצף, לכן המספר נמוך גם אצל מי שסיים · "צריך חיזוק": ${num('30%')} טעויות ומעלה · תגית אדומה גם אחרי ${num(3)} ימים בלי תרגול</p></section>`}

/* ---------- actions ---------- */
const A={
 cardsave(){SND.tap();cardSave()},cardshare(){SND.tap();cardShare()},
 nav(d){SND.tap();if(d.force&&location.hash==='#'+d.to)route();else go(d.to)},
 quit(){SND.tap();const m=location.hash.match(/(m?)play\/(\d+)/);go(m?(m[1]?'misland/':'island/')+m[2]:'map')},
 hint(){if(level&&level.hint){SND.tap();if(level.hint()===true)toast(HINT_NOTE,2800)}},   // the first hint in a level says what it costs
 locked(d,el){SND.bad();el.classList.remove('nope');void el.offsetWidth;el.classList.add('nope');const left=d.need-(d.m?M.mTotal():totalStars());toast(`עוד ${nst(left)} ${el.classList.contains('ball')?'והכדור שלכם':'והאי נפתח'}!<br>אוספים כוכבים בכל שלב שפתוח`,2600)},
 /* math levels: keypad, answer slots, choices, pizzas */
 /* mock exam */
 mockpick(d){X.MOCK_A.pick(d)},mocktile(d,el){X.MOCK_A.tile(d,el)},mockcheck(){X.MOCK_A.check()},mocknext(){SND.tap();X.next()},mocksay(d){X.say(d.k)},
 mockquit(){SND.tap();if(level&&level.quit&&!level.quit())return;go('mock')},
 mkey(d){if(level&&level.key)level.key(d.k)},
 mslot(d){if(level&&level.slot)level.slot(d.k)},
 mpick(d){if(level&&level.pick)level.pick(+d.k)},
 mpz(d,el,e){if(!level||!level.tap)return;const s=e&&e.target.closest&&e.target.closest('[data-s]');level.tap(+d.j,s?+s.dataset.s:-1)},
 mpzok(){if(level&&level.ok)level.ok()},
 mmerge(){if(level&&level.merge)level.merge()},
 ball(d){S.g.ball=+d.i;save();SND.pop();collection()},
 toggle(d){if(d.k==='help'){setHelp(!SET.help);SND.tap();return settings()}SET[d.k]=!SET[d.k];saveSet();if(d.k==='music')musicOn(SET.music);if(d.k==='calm')applyCalm();SND.tap();settings()},
 lmode(d){SND.tap();V={name:'login',m:d.m,c:$('#lc').value.trim(),n:$('#ln').value,p:$('#lp').value};login()},
 async auth(d){const m=d.m,c=$('#lc').value.trim(),n=$('#ln').value.trim().replace(/\s+/g,' '),p=$('#lp').value;
  if(!c||n.length<2||!/^\d{4}$/.test(p)){V={name:'login',m,c,n,p,err:ERR.input};return login()}
  V={name:'login',m,c,n,p,busy:1};login();const err=await auth(m,c,n,p);if(V.name!=='login')return;
  if(err){V={name:'login',m,c,n,p:err===ERR.pin||err===ERR.locked?'':p,err,sw:err===ERR.nouser?'register':err===ERR.taken?'login':''};return login()}
  const np=takeNewPin();go('title');if(np)setTimeout(()=>toast(`זה הקוד הסודי החדש שלכם: <b dir="ltr">${esc(np)}</b><br>כתבו אותו במקום שלא יאבד`,8000),400)},
 forgot(){SND.tap();V={name:'login',m:'login',c:$('#lc').value.trim(),n:$('#ln').value,p:'',err:'שכחתם את הקוד? בקשו מהמורה או מההורה שמנהל את הכיתה לאפס אותו.\nאחרי האיפוס נכנסים עם השם וכל 4 ספרות שבוחרים: הן הקוד החדש.'};login()},
 async treset(d,el){if(!V.data||el.disabled)return;SND.tap();
  if(!el.dataset.arm){el.dataset.arm=1;el.textContent='לאפס? לחצו שוב';clearTimeout(el._disarm);el._disarm=setTimeout(()=>{if(el.isConnected&&!el.disabled){delete el.dataset.arm;el.textContent='איפוס קוד'}},4000);return}
  clearTimeout(el._disarm);el.disabled=true;   // confirmed: the 4 s disarm must not write "איפוס קוד" over the result
  el.textContent='רגע…';let r;try{r=await api('reset',{c:V.c,t:V.t,n:d.n})}catch(e){r={e:'net'}}
  if(r.ok){el.textContent='הקוד אופס';toast(`הקוד של ${esc(d.n)} אופס.<br>עכשיו נכנסים עם השם וכל 4 ספרות, והן הקוד החדש`,6000)}
  else{el.disabled=false;delete el.dataset.arm;el.textContent='איפוס קוד';toast(esc(ERR[r.e]||ERR.net),3500)}},
 relogin(){SND.tap();const o=relogin();if(!o)return go('login');
  V={name:'login',m:'login',c:o.c,n:o.n,p:'',err:(RELOG_MSG[o.e]||RELOG_MSG.nouser)+'\nההתקדמות מהמכשיר הזה שמורה, והיא תעבור לחשבון כשתתחברו.'};login();syncBar()},
 async logout(){if(await logout()){clearNotes();finSaid=false;go('login')}else toast('אין חיבור כרגע, וההתקדמות עוד לא נשמרה.<br>נסו להתנתק שוב בעוד רגע',3600)},
 async tlogin(){const c=$('#tc').value.trim(),t=$('#tt').value.trim();V={name:'teacher',c,busy:1};teacher();let r;try{r=await api('teacher',{c,t})}catch(e){r={e:'net'}}
  if(V.name!=='teacher')return;V=r.ok?{name:'teacher',data:r,c,t}:{name:'teacher',c,err:ERR[r.e]||ERR.net};teacher()}};   // the teacher code is kept on this screen only, for resetting a pupil's code
document.addEventListener('click',e=>{const el=e.target.closest('[data-a]');if(el&&A[el.dataset.a]){A[el.dataset.a](el.dataset,el,e)}});
document.addEventListener('submit',e=>{e.preventDefault();const b=e.target.querySelector('[data-a=auth],[data-a=tlogin]');if(b)b.click()});
for(const ev of['pointerdown','touchend','click'])document.addEventListener(ev,()=>{unlock();unlockTTS()},{passive:true});
document.addEventListener('keydown',()=>unlock(),{passive:true});
/* no long-press callouts, selection or pull-to-refresh while playing */
document.addEventListener('contextmenu',e=>{if(!e.target.closest('input'))e.preventDefault()});
document.addEventListener('touchmove',e=>{if(e.target.closest('.lv canvas'))e.preventDefault()},{passive:false});

/* ---------- router ---------- */
function route(){navId++;if(stage.classList.contains('wdock'))stage.classList.remove('wdock');   // the new world's dock class (js/avatar.js), only when it is there: without the flag #stage is not touched
 document.getElementById('toast').classList.remove('on');if(level){level.destroy();level=null}clearFx();hush();
 let h=location.hash.slice(1),[n,a,b]=h.split('/');
 if(API&&!S.u&&n!=='teacher')n='login';
 if(!API&&(n==='login'||n==='board'))n='map';
 if(API&&S.u&&n==='login')n='map';
 V={name:n||'title'};stage.dataset.scr=V.name;
 switch(V.name){case'map':map();break;case'island':island(a);break;case'play':play(a,b);break;case'collection':collection();break;case'settings':settings();break;
  case'math':M.map();break;case'misland':M.island(a,go);break;case'mplay':{const my=navId;loader();M.play(a,b,{go,live:()=>my===navId,setLevel:l=>{level=l}});break}
  case'mock':X.hub();break;case'mockrun':{const my=navId;X.run({go,live:()=>my===navId,setLevel:l=>{level=l}});break}case'mockprac':{const my=navId;X.prac(a,{go,live:()=>my===navId,setLevel:l=>{level=l}});break}
  case'help':help();break;case'card':if(!cardOn())return go('settings');setBg('paper','center');cardScreen(top);break;
  /* extra practice games (js/extra.js): only on a device that was given the switch, only for an open island */
  case'extra':{const i=isl(a),G=extraGame(b);if(!extraOn()||!i||!isOpen(i)||!G)return go('map');const my=navId;setBg('paper','center');loader();
   G.load().then(m=>my===navId?m.start(view,{island:i,parts:partsOf(i)},{}):null).then(l=>{if(!l)return;if(my!==navId)l.destroy();else level=l}).catch(()=>{if(my===navId)go('island/'+i.id)});break}case'login':login();break;case'board':board();break;case'teacher':teacher();break;
  /* the character picker of the new world (js/avatar.js), behind the design flag; without the flag it is an unknown address like any other */
  case'avatar':if(dsOn()){const my=navId;setBg('paper','center');loader();import('./avatar.js').then(m=>{if(my===navId)return m.picker(view,go,()=>my===navId)}).catch(()=>{if(my===navId)go('map')});break}   // falls through
  default:V.name='title';stage.dataset.scr='title';title()}syncBar()}
initCard();   // the progress card (js/card.js) is behind a switch a device gets with ?card=1
initHelp();   // word help and the slowly button: only on a device that was given them (?help=1), see js/help.js
try{const v=new URLSearchParams(location.search).get('tmock');if(v==='1'||v==='0'){SET.tmock=v==='1';saveSet()}}catch(e){}
initExtra();   // extra practice games are behind a switch a device gets with ?games=1
addEventListener('hashchange',route);
/* a pupil who also plays on another device: bring that progress in when the game opens or comes back to the front.
   Only the calm screens are drawn again; a level in play just keeps the better record underneath. */
const redraw=changed=>{if(changed&&['title','map','island','collection','settings','math','misland','mock'].includes(V.name))route()};
const refresh=()=>pull().then(redraw);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')refresh()});
let rsT=0;addEventListener('resize',()=>{clearTimeout(rsT);rsT=setTimeout(()=>{if(V.name==='map')map();else if(V.name==='math')M.map();else if(V.name==='title')title()},150)});

/* With the design flag, an old-look picture that the new look draws over (the new art is the img's background, the old
   one is pushed out of its box or the box has no height: css/ds*.css) is not downloaded at all: it gets an empty stand-in
   of the same size in srcset, which the browser takes instead of src. The CSS selectors that match on src keep working.
   If the new look's style sheets are not in yet, nothing changes and the old picture loads as before. Never without the flag. */
/* the old pictures the new look draws over, with their own size: the stand-in keeps that size (an empty SVG of the
   same width and height), so a box sized from the picture stays as it was. A picture not listed is downloaded as before.
   tests/weight.py checks the sizes against the files. */
const NAT={isl_1:[560,388],isl_2:[560,461],isl_3:[560,448],isl_4:[560,394],isl_5:[560,407],isl_6:[560,422],star:[200,183],star_off:[200,183],
 lock:[288,379],ic_gear:[200,199],crab_wave:[326,296],crab_star:[322,342],crab_happy:[340,351]};
const blank=n=>NAT[n]?`data:image/svg+xml,%3Csvg%20xmlns=%22http://www.w3.org/2000/svg%22%20width=%22${NAT[n][0]}%22%20height=%22${NAT[n][1]}%22/%3E 1x`:'';
function dsSkip(root){if(!root||!root.querySelectorAll)return;const L=root.tagName==='IMG'?[root]:root.querySelectorAll('img[src]:not([srcset])');
 for(const im of L){if(im.hasAttribute('srcset'))continue;const m=/(^|\/)assets\/sp\/([a-z_0-9]+)\.webp$/.exec(im.getAttribute('src')||''),b=m&&blank(m[2]);if(!b)continue;
  const cs=getComputedStyle(im);if(cs.backgroundImage.includes('url(')&&(cs.objectPosition.startsWith('-9999')||cs.height==='0px'))im.srcset=b}}
function dsSkipOld(){dsSkip(stage);
 /* the screens are drawn by setting #view's innerHTML: checked right there, before the browser asks for the pictures
    (it does so a moment later); anything added elsewhere is checked when it arrives */
 const d=Object.getOwnPropertyDescriptor(Element.prototype,'innerHTML');
 Object.defineProperty(view,'innerHTML',{configurable:true,get(){return d.get.call(this)},set(v){d.set.call(this,v);dsSkip(this)}});
 new MutationObserver(ms=>{for(const m of ms)for(const n of m.addedNodes)if(n.nodeType===1)dsSkip(n)}).observe(stage,{childList:true,subtree:true})}

/* ---------- boot ---------- */
/* the printable worksheet (worksheet.html) is behind a switch a device gets with ?sheet=1 and loses with ?sheet=0 */
try{const v=new URLSearchParams(location.search).get('sheet');if(v==='1'||v==='0'){SET.sheet=v==='1';saveSet()}}catch(e){}
(async function boot(){loader();
 const pulled=pull();let late=true;   // asked for while the pictures load, so the first screen is usually drawn once, already up to date
 /* with the design flag the screens are drawn with the new look's own art (css/ds*.css): the old look's pictures are
    neither waited for nor fetched ahead, so a slow network spends itself on what the screen shows (each old picture
    still loads when a screen uses it). Without the flag, exactly as before. */
 const ds=dsOn(),F=ds?'WI Hebrew':'Playpen Sans Hebrew';
 const fonts=document.fonts?Promise.all([document.fonts.load(`700 20px '${F}'`,'איי'),document.fonts.load(`800 20px '${ds?'WI Latin':F}'`,'Word')]).catch(()=>{}):0;
 await Promise.race([Promise.all([preload(ds?[]:[BG('title'),BG('map'),BG('paper'),SP('crab_wave'),SP('pill_green'),SP('label'),SP('sign'),SP('scroll')]),fonts]),sleep(6000)]);
 await Promise.race([pulled.then(()=>{late=false}),sleep(1200)]);
 if(ds)dsSkipOld();
 route();if(late)pulled.then(redraw);if(!ds)preload([...CORE,...ISLANDS.map(i=>SP('isl_'+i.id))])})();
window.__game={S:()=>S,SET,measure,totalStars,go,award,push};
