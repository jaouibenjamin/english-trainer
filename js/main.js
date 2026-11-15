/* Word Islands: router and all non-level screens. */
import {ISLANDS,LEVEL_INFO,BALLS,MAX_STARS,WORDS,T} from './data.js';
import {S,SET,saveSet,save,API,ERR,api,cred,auth,logout,push,starsOf,islandStars,totalStars,isOpen,setStars,wordsKnown,unlockTTS,hush,esc,reduced} from './state.js';
import {SND,unlock,musicOn,measure} from './audio.js';
import {$,view,stage,SP,BG,preload,img,CORE,setBg,ico,spr,rb,btn,stars,en,toast,confetti,clearFx,sleep} from './ui.js';
import * as sling from './sling.js';
import * as listen from './listen.js';
import * as read from './read.js';
import * as bridge from './bridge.js';

const LEVELS={sling,listen,read,bridge};
const BGFIT={sling:'bottom',listen:'bottom',read:'center',bridge:'width'};
let level=null,V={name:''},navId=0;
const go=h=>{if(location.hash==='#'+h)route();else location.hash=h};
const isl=id=>ISLANDS.find(i=>i.id===+id);
const loader=()=>{view.innerHTML=`<div class="loader">${spr('crab_wave','bob')}<p>רגע, מפליגים…</p></div>`};
const top=(title,back='map')=>`<header class="top">${rb('nav',ico('back'),'חזרה',1,`data-to="${back}"`)}<h2 class="ribbon"><span>${title}</span></h2><span class="rbsp"></span></header>`;

/* ---------- title ---------- */
function title(){setBg('title','bottom');
 const d=Math.ceil((new Date(2026,10,24)-new Date())/864e5);
 view.innerHTML=`<section class="scr title">
  <div class="logo"><h1>איי המילים</h1><p class="en" dir="ltr">Word Islands · All About Me</p></div>
  ${d>0&&d<60?`<p class="label days">עוד <b>${d}</b> ימים למבחן</p>`:''}
  <div class="tfoot">${spr('crab_wave','tcrab bob')}
   ${btn('nav','יוצאים לדרך','green xl','data-to="map"')}
   ${API&&S.u?`<p class="who label">${ico('user')} ${esc(S.u.n)} · ${S.pts.toLocaleString()} נק׳</p>`:''}</div></section>`}

/* ---------- map ---------- */
function map(){setBg('map','center');const tot=totalStars();
 const open=ISLANDS.filter(isOpen),curI=open.filter(i=>!i.bonus&&islandStars(i)<i.levels.length*3).pop()||open[0];
 const pts=ISLANDS.map(i=>i.pos),path=pts.map((p,k)=>{if(!k)return`M${p[0]} ${p[1]}`;const q=pts[k-1];return`C${q[0]} ${(q[1]+p[1])/2-3} ${p[0]} ${(q[1]+p[1])/2+3} ${p[0]} ${p[1]}`}).join('');
 view.innerHTML=`<section class="scr map">
  <header class="top">${rb('nav',ico('gear'),'הגדרות',1,'data-to="settings"')}
   <div class="sign total"><b>${spr('star','st')} <span dir="ltr">${tot} / ${MAX_STARS}</span></b></div>
   <span class="tr">${API&&S.u?rb('nav',spr('trophy','rbi'),'טבלת הכיתה',3,'data-to="board"'):''}${rb('nav',spr('chest','rbi'),'האוסף שלי',2,'data-to="collection"')}</span></header>
  <svg class="route" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="${path}"/></svg>
  ${ISLANDS.map(i=>{const o=isOpen(i),st=islandStars(i),mx=i.levels.length*3;
   return `<button class="isl i${i.id}${o?'':' locked'}${st===mx?' full':''}" style="left:${i.pos[0]}%;top:${i.pos[1]}%" data-a="${o?'nav':'locked'}" data-to="island/${i.id}" data-need="${i.need}" aria-label="${esc(i.he)}${o?'':' (נעול)'}">
    ${spr('isl_'+i.id,'pic')}${o?'':spr('lock','lk')}
    <span class="tag label"><b>${esc(i.he)}</b><small>${o?`${spr('star','st')} <span dir="ltr">${st}/${mx}</span>`:`נפתח ב־${i.need} ${spr('star','st')}`}</small></span>
    ${i===curI?`<span class="here">${spr('boat','boat')}${spr('crab_wave','bc')}</span>`:''}</button>`}).join('')}
 </section>`}

/* ---------- island ---------- */
function island(id){const i=isl(id);if(!i||!isOpen(i))return go('map');setBg('paper','center');preload([BG(i.bg),BG('listen'),BG('read'),BG('bridge')]);
 view.innerHTML=`<section class="scr island">${top(esc(i.he))}
  <div class="ihero">${spr('isl_'+i.id,'pic')}<p class="label"><span class="en" dir="ltr">${esc(i.en)}</span> · ${spr('star','st')} <span dir="ltr">${islandStars(i)}/${i.levels.length*3}</span></p></div>
  <div class="lvlist">${i.levels.map(([t],k)=>{const L=LEVEL_INFO[t],s=starsOf(i.id,t);
   return `<button class="lvrow p${k%4}" data-a="nav" data-to="play/${i.id}/${t}">${spr(L.icon,'lic')}<span class="lt"><b>${L.name}</b><small>${L.sub}</small></span>${stars(s)}</button>`}).join('')}</div>
  <div class="guide">${spr('crab_wave','bob')}<p class="label">${i.bonus?'אי בונוס: חודשים ומספרים!':islandStars(i)?'אפשר לחזור לכל שלב ולאסוף עוד כוכבים':'בחרו שלב. ארבעה שלבים, כמו ארבעת חלקי המבחן'}</p></div></section>`}

/* ---------- play + result ---------- */
async function play(id,type){const i=isl(id),lv=i&&i.levels.find(l=>l[0]===type);if(!lv||!isOpen(i))return go('map');
 const my=navId;loader();const bg=LEVEL_INFO[type].bg||i.bg;await preload([BG(bg),...CORE]);if(my!==navId)return;
 setBg(bg,BGFIT[type]);
 const l=await LEVELS[type].start(view,{island:i,type,part:lv[1]},{done:r=>result(i,type,r)});
 if(my!==navId){l.destroy();return}level=l}
function result(i,type,r){if(level){level.destroy();level=null}clearFx();hush();
 const {gained,opened}=setStars(i.id,type,r.stars),pts=r.stars*T.ptsStar;
 const k=i.levels.findIndex(l=>l[0]===type),nx=i.levels[k+1],nextIsl=!nx&&ISLANDS.find(o=>o.id===i.id+1&&isOpen(o));
 const to=nx?`play/${i.id}/${nx[0]}`:nextIsl?`island/${nextIsl.id}`:'map',nextLabel=nx?'לשלב הבא':nextIsl?'לאי הבא':'למפה';
 const head=r.stars===3?'מושלם!':r.stars===2?'יפה מאוד!':'סיימתם, כל הכבוד!';
 V={name:'result'};stage.dataset.scr='result';
 view.innerHTML=`<section class="scr result"><div class="scrollp card">
   <h2 class="ribbon"><span>${head}</span></h2>
   <div class="bigstars" dir="ltr">${[0,1,2].map(n=>`<span class="bs ${n<r.stars?'on':''}" style="--i:${n}">${spr(n<r.stars?'star':'star_off','')}</span>`).join('')}</div>
   ${spr(r.stars===3?'crab_star':r.stars===2?'crab_happy':'crab_wave','rcrab bob')}
   <p class="line"><b>${r.first}</b> מתוך <b>${r.total}</b> בניסיון הראשון</p>
   ${r.hint?'<p class="sub">נעזרתם ברמז, ולכן הפעם עד 2 כוכבים</p>':''}
   ${r.review&&r.review.length?`<div class="review"><small>כדאי לחזור על:</small>${r.review.slice(0,4).map(w=>`<span class="rv">${en(w.en)} · ${esc(w.he.split(',')[0])}</span>`).join('')}</div>`:''}
   ${opened.length?`<p class="unlock label">${spr('isl_'+opened[0].id,'ui')}<span>נפתח אי חדש!<b>${esc(opened[0].he)}</b></span></p>`:gained?`<p class="sub">+${gained} כוכבים למפה</p>`:''}
   ${API&&S.u?`<p class="sub pts">${S.pts.toLocaleString()} נקודות בטבלת הכיתה</p>`:''}
   <div class="rbtns">${btn('nav',`${nextLabel} ${ico('next')}`,'green xl',`data-to="${to}"`)}
    <div class="row">${btn('nav',ico('retry')+' שוב','cream sm',`data-to="play/${i.id}/${type}" data-force="1"`)}${btn('nav','לשלבים','cream sm',`data-to="island/${i.id}"`)}</div></div>
  </div></section>`;
 if(r.stars>=2){confetti();SND.win()}
 [0,1,2].forEach(n=>{if(n<r.stars)setTimeout(()=>SND.star(n),350+n*330)});
 if(opened.length)setTimeout(()=>SND.unlock(),1500)}

/* ---------- collection ---------- */
function collection(){setBg('paper','center');const tot=totalStars();
 view.innerHTML=`<section class="scr coll">${top('האוסף של פיצי')}
  <div class="chero">${spr('crab_star','bob')}<p class="label">אוספים כוכבים ופותחים כדורים חדשים לקלע. יש לכם ${spr('star','st')} <b dir="ltr">${tot}</b></p></div>
  <div class="balls">${BALLS.map((b,k)=>{const ok=tot>=b.need,sel=(S.g.ball||0)===k;
   return `<button class="ball${ok?'':' locked'}${sel?' sel':''}" data-a="${ok?'ball':'locked'}" data-i="${k}" data-need="${b.need}" aria-pressed="${sel}">${spr('ball_'+k,'bi')}${ok?'':spr('lock','lk')}<b>${b.name}</b><small>${ok?(sel?'בקלע עכשיו':'לחצו כדי לבחור'):`${b.need} ${spr('star','st')}`}</small></button>`}).join('')}</div>
  ${(n=>n?`<p class="foot label">הכדור הבא נפתח בעוד <b dir="ltr">${n.need-tot}</b> ${spr('star','st')}</p>`:`<p class="foot label">כל הכדורים שלכם. אלופים!</p>`)(BALLS.find(b=>b.need>tot))}</section>`}

/* ---------- settings + help ---------- */
function settings(){setBg('paper','center');
 const tog=(k,label,icon)=>`<button class="setrow" data-a="toggle" data-k="${k}" role="switch" aria-checked="${SET[k]}">${ico(icon)}<span>${label}</span><i class="sw${SET[k]?' on':''}"><em></em></i></button>`;
 view.innerHTML=`<section class="scr settings">${top('הגדרות')}
  <div class="panel label">${tog('music','מוזיקה','note')}${tog('sfx','צלילים','sound')}</div>
  <div class="col">${btn('nav','איך משחקים?','yellow','data-to="help"')}
   <a class="btn cream" href="trainer.html"><span>${ico('book')} תרגול קלאסי</span></a>
   ${API?(S.u?`<p class="who label">${ico('user')} ${esc(S.u.n)} · ${S.pts.toLocaleString()} נק׳ · ${wordsKnown()} מילים</p>${btn('logout','יציאה מהחשבון','coral sm')}`:'')+btn('nav','כניסת מורה','cream sm','data-to="teacher"'):'<p class="who label">ההתקדמות נשמרת במכשיר הזה</p>'}</div>
  <p class="foot label">המילים והתרגומים לפי רשימת אוצר המילים של המורה ליחידה 1</p></section>`}
function help(){setBg('paper','center');
 const c=(icon,t,d)=>`<div class="hrow label">${spr(icon,'hi')}<span><b>${t}</b><small>${d}</small></span></div>`;
 view.innerHTML=`<section class="scr help">${top('איך משחקים?','settings')}
  ${c('fork','קלע המילים','גוררים את הכדור אחורה, מכוונים לפי הנקודות ומשחררים על המילה שמתאימה לפירוש.')}
  ${c('conch','תופסים צלילים','מקשיבים למילה מהקונכייה ולוחצים על הבועה הנכונה. אפשר לשמוע שוב ושוב.')}
  ${c('bottle','בקבוק הסיפור','קוראים סיפור קצר. לחיצה על מילה מראה מה הפירוש שלה. אחר כך בוחרים בקבוק עם התשובה.')}
  ${c('plank_1','גשר המשפטים','לוחצים על קרשי המילים לפי הסדר. אות גדולה בהתחלה, נקודה בסוף.')}
  ${c('star','כוכבים','בכל שלב אפשר לזכות בעד 3 כוכבים. כוכבים פותחים איים חדשים. רמז עוזר, אבל אז מקבלים עד 2.')}</section>`}

/* ---------- class mode: login, leaderboard, teacher (same backend calls as the classic trainer) ---------- */
function login(){setBg('title','bottom');
 view.innerHTML=`<section class="scr login"><div class="logo sm"><h1>איי המילים</h1></div>
  <form class="panel label" id="lf" autocomplete="off"><h3>כניסה לכיתה</h3>
   <label for="lc">קוד הכיתה</label><input id="lc" class="in en" dir="ltr" autocapitalize="characters" autocomplete="off" value="${esc(V.c??S.lastC)}">
   <label for="ln">השם שלי</label><input id="ln" class="in" maxlength="20" autocomplete="off" value="${esc(V.n||'')}">
   <label for="lp">הקוד הסודי שלי (4 ספרות)</label><input id="lp" class="in en pin" dir="ltr" type="password" inputmode="numeric" maxlength="4" autocomplete="off">
   <p class="err" role="alert">${esc(V.err||'')}</p>
   ${btn('auth',V.busy?'רגע…':'כניסה','green',`data-m="login" type="button" ${V.busy?'disabled':''}`)}
   ${btn('auth','פעם ראשונה שלי כאן','cream sm',`data-m="register" type="button" ${V.busy?'disabled':''}`)}
   <small class="hint">פעם ראשונה? כותבים את קוד הכיתה ואת השם, ובוחרים 4 ספרות שרק אתם יודעים. בלי אימייל.</small></form>
  <button class="tlink" data-a="nav" data-to="teacher">כניסת מורה</button></section>`}
function board(){if(!API||!S.u)return go('map');setBg('paper','center');
 if(!V.rows){view.innerHTML=`<section class="scr board">${top('טבלת הכיתה')}<p class="panel label msg">${esc(V.err||'טוענים את הטבלה…')}</p></section>`;
  if(!V.req){V.req=1;const v=V;push().then(()=>api('board',cred())).then(r=>{if(V!==v)return;if(r.ok)V.rows=r.rows;else V.err=ERR[r.e]||ERR.net;board()}).catch(()=>{if(V!==v)return;V.err=ERR.net;board()})}return}
 const R=V.rows,me=S.u.n,pod=[1,0,2].filter(i=>R[i]);
 view.innerHTML=`<section class="scr board">${top('טבלת הכיתה')}
  ${R.length>=3?`<div class="podium" dir="ltr">${pod.map(i=>`<div class="pd pd${i}${R[i].n===me?' me':''}">${i===0?spr('trophy','tro'):''}<b dir="rtl">${esc(R[i].n)}</b><small>${R[i].pts.toLocaleString()}</small><i class="step">${i+1}</i></div>`).join('')}</div>`:''}
  <ol class="lb">${R.map((d,i)=>`<li class="${d.n===me?'me':''}"><span class="rk">${i+1}</span><span class="nm">${esc(d.n)}${d.n===me?' (אני)':''}${d.streak>=3?`<small> · ${d.streak} ימים ברצף</small>`:''}</span><span class="pt" dir="ltr">${d.pts.toLocaleString()}</span></li>`).join('')}</ol>
  <p class="foot label">נקודות: ${T.ptsFirst} על תשובה נכונה בניסיון ראשון, ${T.ptsStar} על כל כוכב, ${T.ptsDay} בונוס על כל יום תרגול</p></section>`}
function teacher(){setBg('paper','center');const back=API&&!S.u?'login':'settings';
 if(!API){view.innerHTML=`<section class="scr teacher">${top('מסך המורה',back)}<p class="panel label msg">מסך המורה יהיה זמין אחרי חיבור הכיתה.</p></section>`;return}
 if(!V.data){view.innerHTML=`<section class="scr teacher">${top('מסך המורה',back)}<form class="panel label" id="tf" autocomplete="off">
   <label for="tc">קוד הכיתה</label><input id="tc" class="in en" dir="ltr" autocomplete="off" value="${esc(V.c??(S.u?S.u.c:S.lastC))}">
   <label for="tt">קוד המורה</label><input id="tt" class="in en" dir="ltr" type="password" autocomplete="off">
   <p class="err" role="alert">${esc(V.err||'')}</p>${btn('tlogin',V.busy?'רגע…':'כניסה','green',`type="button" ${V.busy?'disabled':''}`)}</form></section>`;return}
 const D=V.data,he=Object.fromEntries(WORDS.map(w=>[w.en,w.he]));
 view.innerHTML=`<section class="scr teacher wide">${top('מסך המורה',back)}
  <div class="panel label"><h3>המילים שהכיתה הכי טועה בהן</h3>${D.hard.length?`<div class="hard">${D.hard.map(w=>`<div><span>${en(w[0])}<i>${esc(he[w[0]]||'')}</i><b>${w[1]}%</b></span><div class="pbar"><i style="width:${w[1]}%"></i></div></div>`).join('')}</div>`:'<p>עדיין אין מספיק תרגול כדי לדעת.</p>'}</div>
  <div class="panel label tw">${D.kids.length?`<table><thead><tr><th>תלמיד/ה</th><th>מילים (מתוך 59)</th><th>קריאה</th><th>נקודות</th><th>תרגול אחרון</th><th>מצב</th></tr></thead><tbody>${D.kids.map(d=>{const s=d.words>=40?['g','מוכן/ה']:d.words>=25?['w','בדרך']:['r','צריך חיזוק'],dd=String(d.day||'').split('-');
   return `<tr><td><b>${esc(d.n)}</b></td><td><span class="num">${d.words}</span><div class="pbar"><i style="width:${Math.min(100,d.words/59*100)}%"></i></div></td><td>${d.reads} מתוך 5</td><td>${d.pts.toLocaleString()}</td><td>${dd.length===3?dd[2]+'/'+dd[1]:'עוד לא'}</td><td><span class="pill ${s[0]}">${s[1]}</span></td></tr>`}).join('')}</tbody></table>`:'<p>עדיין אף תלמיד לא נרשם.</p>'}</div></section>`}

/* ---------- actions ---------- */
const A={
 nav(d){SND.tap();if(d.force&&location.hash==='#'+d.to)route();else go(d.to)},
 quit(){SND.tap();const m=location.hash.match(/play\/(\d+)/);go(m?'island/'+m[1]:'map')},
 hint(){if(level&&level.hint){SND.tap();level.hint()}},
 locked(d,el){SND.bad();el.classList.remove('nope');void el.offsetWidth;el.classList.add('nope');const left=d.need-totalStars();toast(`עוד ${left} ${spr('star','st')} וזה נפתח. אפשר לשפר שלבים שכבר שיחקתם!`,2600)},
 ball(d){S.g.ball=+d.i;save();SND.pop();collection()},
 toggle(d){SET[d.k]=!SET[d.k];saveSet();if(d.k==='music')musicOn(SET.music);SND.tap();settings()},
 async auth(d){const c=$('#lc').value.trim(),n=$('#ln').value.trim().replace(/\s+/g,' '),p=$('#lp').value;
  if(!c||n.length<2||!/^\d{4}$/.test(p)){V={name:'login',c,n,err:ERR.input};return login()}
  V={name:'login',c,n,busy:1};login();const err=await auth(d.m,c,n,p);if(V.name!=='login')return;
  if(err){V={name:'login',c,n,err};return login()}go('map')},
 async logout(){await logout();go('login')},
 async tlogin(){const c=$('#tc').value.trim(),t=$('#tt').value.trim();V={name:'teacher',c,busy:1};teacher();let r;try{r=await api('teacher',{c,t})}catch(e){r={e:'net'}}
  if(V.name!=='teacher')return;V=r.ok?{name:'teacher',data:r}:{name:'teacher',c,err:ERR[r.e]||ERR.net};teacher()}};
document.addEventListener('click',e=>{const el=e.target.closest('[data-a]');if(el&&A[el.dataset.a]){A[el.dataset.a](el.dataset,el)}});
document.addEventListener('submit',e=>{e.preventDefault();const b=e.target.querySelector('[data-a=auth],[data-a=tlogin]');if(b)b.click()});
for(const ev of['pointerdown','touchend','click'])document.addEventListener(ev,()=>{unlock();unlockTTS()},{passive:true});
document.addEventListener('keydown',()=>unlock(),{passive:true});
/* no long-press callouts, selection or pull-to-refresh while playing */
document.addEventListener('contextmenu',e=>{if(!e.target.closest('input'))e.preventDefault()});
document.addEventListener('touchmove',e=>{if(e.target.closest('.lv canvas'))e.preventDefault()},{passive:false});

/* ---------- router ---------- */
function route(){navId++;document.getElementById('toast').classList.remove('on');if(level){level.destroy();level=null}clearFx();hush();
 let h=location.hash.slice(1),[n,a,b]=h.split('/');
 if(API&&!S.u&&n!=='teacher')n='login';
 if(!API&&(n==='login'||n==='board'))n='map';
 if(API&&S.u&&n==='login')n='map';
 V={name:n||'title'};stage.dataset.scr=V.name;
 switch(V.name){case'map':map();break;case'island':island(a);break;case'play':play(a,b);break;case'collection':collection();break;case'settings':settings();break;
  case'help':help();break;case'login':login();break;case'board':board();break;case'teacher':teacher();break;default:V.name='title';stage.dataset.scr='title';title()}}
addEventListener('hashchange',route);

/* ---------- boot ---------- */
(async function boot(){loader();
 const fonts=document.fonts?Promise.all([document.fonts.load("800 20px 'Playpen Sans Hebrew'",'איי'),document.fonts.load("800 20px 'Playpen Sans Hebrew'",'Word')]).catch(()=>{}):0;
 await Promise.race([Promise.all([preload([BG('title'),BG('map'),SP('crab_wave'),SP('pill_green'),SP('label'),SP('sign')]),fonts]),sleep(6000)]);
 route();preload([...CORE,BG('paper'),...ISLANDS.map(i=>SP('isl_'+i.id))])})();
window.__game={S:()=>S,SET,measure,totalStars,go};
