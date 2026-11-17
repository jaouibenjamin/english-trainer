/* Fraction Bay (מפרץ השברים): the math world. Map, islands, result, and two of its three levels
   (the pizza table and the exam sheet). The fraction slingshot is msling.js. Progress lives in S.m and travels with
   the pupil's account in the same saved record as the English game. */
import {M_ISLANDS,M_LEVEL,M_MAX,M_COUNT,MATH_EXAM,set,pizzaSet,F,top,same,formOK,fx,parts,PARTS_HE,mixedOf,shuf} from './mdata.js';
import {S,save,API,award,esc,reduced,hush} from './state.js';
import {T,starsFor} from './data.js';
import {SND} from './audio.js';
import {view,stage,BG,preload,CORE,setBg,bgMap,ico,spr,rb,btn,stars,num,toast,toastAt,confetti,clearFx,hud,hudReset,HINT_NOTE,SLIP_NOTE} from './ui.js';
import {fr,expr,eqn,mtext,pizza} from './mui.js';
import * as msling from './msling.js';

/* ---------- progress ---------- */
export const MS=()=>{if(!S.m||typeof S.m!=='object')S.m={};if(!S.m.st||typeof S.m.st!=='object')S.m.st={};S.m.plays=+S.m.plays||0;return S.m};
export const mStars=(i,t)=>MS().st[i+'-'+t]||0;
const islSt=i=>i.levels.reduce((a,t)=>a+mStars(i.id,t),0);
export const mTotal=()=>M_ISLANDS.reduce((a,i)=>a+islSt(i),0);
const isOpen=i=>mTotal()>=i.need;
function setM(id,t,n){const m=MS(),k=id+'-'+t,before=mTotal(),was=M_ISLANDS.filter(isOpen).map(i=>i.id);
 if(n>(m.st[k]||0))m.st[k]=n;m.plays++;award(n*T.ptsStar);
 return{gained:mTotal()-before,opened:M_ISLANDS.filter(i=>isOpen(i)&&!was.includes(i.id))}}

const star=()=>spr('star','st');
const nst=n=>`<span class="nb">${num(n)}${star()}</span>`;
const pts=n=>num((+n||0).toLocaleString('en-US'));
const isl=id=>M_ISLANDS.find(i=>i.id===+id);
const top_=(title,back)=>`<header class="top">${rb('nav',ico('back'),'חזרה',1,`data-to="${back}"`)}<h2 class="ribbon"><span>${title}</span></h2><span class="rbsp"></span></header>`;
const ICON={pizza:()=>`<span class="mic">${pizza(4,3,{size:'ic'})}</span>`,fork:()=>spr('fork'),sheet:()=>spr('scroll')};
export const daysToExam=()=>Math.ceil((MATH_EXAM-new Date())/864e5);

/* ---------- map ---------- */
export function map(){setBg('map','center');const tot=mTotal(),W=stage.clientWidth,H=stage.clientHeight,mt=H<700?130:132;   // the islands start below the bay's name
 const iw=Math.min(W*.4,160,H*.21),cell=iw*.76+48,rowH=(H-mt-cell-18)/3;
 const curI=M_ISLANDS.filter(i=>isOpen(i)&&islSt(i)<i.levels.length*3).sort((a,b)=>b.id-a.id)[0]||null;
 const place=M_ISLANDS.map(i=>{const r=4-i.id;return{i,x:r%2?70:30,y:mt+rowH*r}});
 const yp=p=>((p.y+iw*.36)/H*100).toFixed(2),seq=[...place].sort((a,b)=>a.i.id-b.i.id);
 const path=seq.map((p,k)=>{if(!k)return`M${p.x} ${yp(p)}`;const q=seq[k-1];return`C${q.x} ${((+yp(q)+ +yp(p))/2-2).toFixed(2)} ${p.x} ${((+yp(q)+ +yp(p))/2+2).toFixed(2)} ${p.x} ${yp(p)}`}).join('');
 const d=daysToExam();
 view.innerHTML=`<section class="scr map mmap" style="--iw:${iw.toFixed(1)}px">
  <header class="maphead"><button class="mb" data-a="nav" data-to=""><span class="rb t1">${ico('back')}</span><small>מקצועות</small></button>
   <div class="sign total"><b>${star()}<span>${num(tot+' / '+M_MAX)}</span></b></div>
   <span class="tr">${API&&S.u?`<button class="mb" data-a="nav" data-to="board"><span class="rb t3">${spr('trophy','rbi')}</span><small>טבלה</small></button>`:'<span class="mbsp"></span>'}</span></header>
  <p class="label mtitle"><b>מפרץ השברים</b><small>חשבון${d>0&&d<30?` · עוד ${num(d)} ימים למבחן`:''}</small></p>
  <svg class="route" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="${path}"/></svg>
  ${place.map(({i,x,y})=>{const o=isOpen(i),st=islSt(i),mx=i.levels.length*3,cur=i===curI;
   return `<button class="isl i${i.id}${o?'':' locked'}${st===mx?' full':''}${cur?' cur':''}${x<50?' lc':''}" style="left:${x}%;top:${y.toFixed(1)}px" data-a="${o?'nav':'locked'}" data-m="1" data-to="misland/${i.id}" data-need="${i.need}" aria-label="${esc(i.he)}${o?'':' (נעול)'}">
    <span class="pw">${spr('isl_'+i.art,'pic')}${o?'':spr('lock','lk')}${cur?`<span class="here">${spr('crab_wave','bc')}</span>`:''}</span>
    <span class="tag">${cur?`<em class="hb">${tot?'ממשיכים כאן':'מתחילים כאן'}</em>`:''}<b>${esc(i.he)}</b><small>${o?`${star()}${num(st+'/'+mx)}${st===mx?spr('ic_check','ck'):''}`:`נפתח ב־${num(i.need)}${star()}`}</small></span></button>`}).join('')}
 </section>`}

/* ---------- island ---------- */
export function island(id,go){const i=isl(id);if(!i||!isOpen(i))return go('math');setBg('paper','center');preload([BG(i.bg)]);
 const got=islSt(i);
 view.innerHTML=`<section class="scr island">${top_(esc(i.he),'math')}
  <p class="isub">${esc(i.sub)}</p>
  <div class="ihero">${spr('isl_'+i.art,'pic')}<p class="chips"><span class="chip">${star()}${num(got+' / '+i.levels.length*3)}</span></p></div>
  <div class="lvlist">${i.levels.map((t,k)=>{const L=M_LEVEL[t],s=mStars(i.id,t);
   return `<button class="lvrow p${k%4}" data-a="nav" data-to="mplay/${i.id}/${t}"><span class="lic">${ICON[L.icon]()}</span><span class="lt"><b>${L.name}</b>${stars(s)}<small>${t==='sheet'&&i.mode==='exam'?'שמונה תרגילים מכל הנושאים':L.sub}</small></span></button>`}).join('')}</div>
  <div class="guide">${spr('crab_wave','bob')}<p class="label">${got?'אפשר לחזור לכל שלב ולאסוף עוד כוכבים':i.mode==='exam'?'כמו במבחן: כל הנושאים ביחד':'מתחילים בפיצרייה: שם רואים את השברים'}</p></div>
 </section>`}

/* ---------- play + result ---------- */
const LEVELS={sling:msling,pizza:{start:pizzaLevel},sheet:{start:sheetLevel}};
export async function play(id,type,ctx){const i=isl(id);if(!i||!i.levels.includes(type)||!isOpen(i))return ctx.go('math');
 const bg=type==='sling'?i.bg:'paper';await preload([BG(bg),...CORE]);if(!ctx.live())return;
 setBg(bg,type==='sling'?'bottom':'center');hudReset();
 const n=type==='pizza'?M_COUNT.pizza:type==='sheet'&&i.mode==='exam'?M_COUNT.examSheet:M_COUNT[type];
 const items=type==='pizza'?pizzaSet(i.mode,n):set(i.mode,n);
 const l=await LEVELS[type].start(view,{island:i,type,items},{done:r=>result(i,type,r,ctx)});
 if(!ctx.live()){l.destroy();return}ctx.setLevel(l)}

function result(i,type,r,ctx){ctx.setLevel(null);clearFx();hush();
 const {gained,opened}=setM(i.id,type,r.stars),clean=r.first===r.total;
 const k=i.levels.indexOf(type),nx=i.levels[k+1],nextIsl=!nx&&M_ISLANDS.find(o=>o.id===i.id+1&&isOpen(o));
 const to=nx?`mplay/${i.id}/${nx}`:nextIsl?`misland/${nextIsl.id}`:'math',nextLabel=nx?'לשלב הבא':nextIsl?'לאי הבא':'למפה';
 const head=clean&&r.stars===3?'מושלם!':r.stars===3?'כל הכבוד!':r.stars===2?'יפה מאוד!':'סיימתם!';
 const capped=r.hint&&starsFor(r.first,r.total,0)===3;
 const note=capped?HINT_NOTE:clean?'בלי אף טעות!':r.stars===3?SLIP_NOTE:r.hint?HINT_NOTE+'. אפשר לשחק שוב':'אפשר לשחק שוב: כל פעם יש תרגילים חדשים';
 const tot=mTotal(),lockedI=M_ISLANDS.find(o=>!isOpen(o));
 const rv=(r.review||[]).slice(0,2);
 const extra=opened.length?`<p class="unlock">${spr('isl_'+opened[0].art,'ui')}<span><i>נפתח אי חדש!</i><b>${esc(opened[0].he)}</b></span></p>`
  :rv.length?`<div class="review mrev"><small>כדאי לחזור על</small>${rv.map(p=>`<span class="rv">${eqn(p)}</span>`).join('')}</div>`
  :lockedI?`<p class="unlock goal">${spr('isl_'+lockedI.art,'ui')}<span><i>עוד ${nst(lockedI.need-tot)} ונפתח</i><b>${esc(lockedI.he)}</b></span></p>`
  :`<p class="unlock goal">${spr('trophy','ui')}<span><i>כל האיים פתוחים!</i><b>${star()}${num(tot+' / '+M_MAX)}</b></span></p>`;
 stage.dataset.scr='result';setBg(i.bg,'bottom');
 view.innerHTML=`<section class="scr result"><div class="scrollp card">
   <h2 class="ribbon"><span>${head}</span></h2>
   <div class="bigstars" dir="ltr">${[0,1,2].map(n=>`<span class="bs ${n<r.stars?'on':''}" style="--i:${n}">${spr(n<r.stars?'star':'star_off','')}</span>`).join('')}</div>
   ${spr(r.stars===3?'crab_star':r.stars===2?'crab_happy':'crab_wave','rcrab bob')}
   <p class="line">${num(r.first)} מתוך ${num(r.total)} בניסיון הראשון</p>
   <p class="note">${note}</p>
   <div class="xtra">${extra}</div>
   <p class="gain">${gained?`${num('+'+gained)} כוכבים למפה`:'הכוכבים שלכם נשמרו'}</p>${API&&S.u?`<p class="gain cp">${spr('trophy','gt')}${pts(S.pts)} נקודות לטבלת הכיתה</p>`:''}
   <div class="rbtns">${btn('nav',`${nextLabel} ${ico('next')}`,'green xl',`data-to="${to}"`)}
    <div class="row">${btn('nav',ico('retry')+' שוב','cream sm',`data-to="mplay/${i.id}/${type}" data-force="1"`)}${btn('nav','לשלבים','cream sm',`data-to="misland/${i.id}"`)}</div></div>
  </div></section>`;
 if(r.stars>=2){confetti();SND.win()}
 [0,1,2].forEach(n=>{if(n<r.stars)setTimeout(()=>SND.star(n),350+n*330)});
 if(opened.length)setTimeout(()=>SND.unlock(),1500)}

/* ---------- shared level bits ---------- */
function frame(host,cls,inner){host.innerHTML=`<div class="lv mlv ${cls}"><div id="hd"></div>${inner}</div>`}
function scorer(host,n){const g={i:0,first:0,bad:0,hint:0,wrongNow:0,lock:0,review:[]};
 g.hud=()=>{host.querySelector('#hd').innerHTML=hud({i:g.i,n,st:starsFor(n-g.bad,n,g.hint),hint:g.hint})};
 g.miss=()=>{if(!g.wrongNow)g.bad++;g.wrongNow++;g.hud()};
 g.done=p=>{const ok1=!g.wrongNow;if(ok1)g.first++;else g.review.push(p);award(ok1?T.ptsFirst:T.ptsLater);g.wrongNow=0};
 g.result=()=>({stars:starsFor(g.first,n,g.hint),first:g.first,total:n,hint:g.hint,review:g.review});
 return g}
const choiceBtns=(opts,cls='')=>`<div class="mch ${cls}">${opts.map((o,k)=>`<button class="mc" data-a="mpick" data-k="${k}">${o.html}</button>`).join('')}</div>`;

/* ======================================================================
   The exam sheet: the exercise as it looks on the test, the answer written digit by digit with an on-screen keypad.
   Wrong once: why (when the slip is a known one). Wrong twice: the worked solution, then on to the next.
   ====================================================================== */
async function sheetLevel(host,cfg,api){
 const ws=cfg.items,n=ws.length,g=scorer(host,n);let alive=true,tries=0,cur='w',val={w:'',n:'',d:''},shown=false,nextT=0;
 window.__lv={kind:'sheet',g,answer:()=>ws[g.i]&&ws[g.i].ans,form:()=>ws[g.i]&&ws[g.i].form};
 frame(host,'sheet',`<div class="paper label"><p class="qn" id="qn"></p><p class="ask" id="ask"></p>
   <div class="eqrow" dir="ltr"><span id="ex"></span><em>=</em><span class="ansbox" id="ab"></span></div>
   <div class="mfb" id="fb" role="status" aria-live="polite"></div></div>
  <div class="pad" id="pad">${[1,2,3,4,5,6,7,8,9].map(k=>`<button class="key" data-a="mkey" data-k="${k}">${k}</button>`).join('')}<button class="key kdel" data-a="mkey" data-k="del" aria-label="מחיקה">⌫</button><button class="key" data-a="mkey" data-k="0">0</button><button class="key kok" data-a="mkey" data-k="ok">בדיקה</button></div>`);
 const $=s=>host.querySelector(s),fb=$('#fb'),ab=$('#ab');
 function slots(){const p=ws[g.i],s=k=>`<button class="aslot${cur===k?' aon':''}${val[k]?'':' aempty'}" data-a="mslot" data-k="${k}" aria-label="${k==='w'?'שלמים':k==='n'?'מונה':'מכנה'}">${esc(val[k])||'&nbsp;'}</button>`;
  ab.innerHTML=`${p.form==='imp'?'':`<span class="aw">${s('w')}</span>`}<span class="af">${s('n')}<i class="abar"></i>${s('d')}</span>`}
 function round(){const p=ws[g.i];tries=0;shown=false;val={w:'',n:'',d:''};cur=p.form==='imp'?'n':'w';
  $('#qn').textContent=`תרגיל ${g.i+1} מתוך ${n}`;$('#ask').textContent=p.ask||(p.op==='+'?'פתרו. אם יצא יותר משלם, כתבו כמספר מעורב':'פתרו. אם צריך, פורטים שלם');
  $('#ex').innerHTML=expr(p);fb.className='mfb';fb.innerHTML='';$('#pad').classList.remove('off');slots();g.hud()}
 const say=(html,cls)=>{fb.className='mfb '+(cls?'m'+cls:'');fb.innerHTML=html};
 function key(k){if(g.lock||!alive)return;
  if(shown){if(k==='ok')next();return}
  if(k==='del'){val[cur]=val[cur].slice(0,-1);SND.tap();return slots()}   // only the chosen box: a pupil picks the box by tapping it
  if(k==='ok')return check();
  if(val[cur].length>=2){SND.bad();return}
  val[cur]+=k;SND.tap();slots()}
 function check(){const p=ws[g.i],w=+val.w||0,nn=val.n,dd=val.d;
  if(!val.w&&!nn&&!dd)return say('כתבו תשובה במשבצות. לוחצים על משבצת ואז על המספרים');
  if(nn&&!dd)return say('חסר המכנה: המספר שמתחת לקו');
  if(dd&&!nn)return say('חסר המונה: המספר שמעל הקו');
  if(dd&&+dd===0)return say('המכנה לא יכול להיות 0');
  const f=F(w,+nn||0,+dd||p.ans.d);
  if(same(f,p.ans)&&formOK(f,p.form)){g.lock=1;SND.pop();g.done(p);say(`נכון! ${eqn(p)}`,'ok');confetti(undefined,undefined,24);
   return nextT=setTimeout(()=>{if(alive){g.lock=0;next()}},1300)}
  g.miss();SND.bad();
  if(same(f,p.ans))return say(p.form==='imp'?'הערך נכון, אבל ביקשו שבר גדול מהשלם: בלי שלמים. כמה חלקים יש בסך הכול?':'הערך נכון, אבל צריך להוציא את השלמים: המונה צריך להיות קטן מהמכנה','warn');
  tries++;const known=p.alts.find(a=>same(a.f,f)&&a.why);
  if(tries<2)return say(`לא נכון. ${known?esc(known.why):`רמז: ${mtext(p.steps[0])}`}`,'bad');
  shown=true;$('#pad').classList.add('off');
  say(`<b>כך פותרים:</b>${p.steps.map(s=>`<span class="mst">${mtext(s)}</span>`).join('')}<span class="mst mres">${eqn(p)}</span><button class="btn green sm" data-a="mkey" data-k="ok"><span>הבא ${ico('next')}</span></button>`,'sol')}
 function next(){clearTimeout(nextT);g.i++;if(g.i>=n){alive=false;return api.done(g.result())}round()}
 round();
 return{destroy(){alive=false;clearTimeout(nextT);delete window.__lv},
  hint(){if(shown||g.lock)return;const isNew=!g.hint;if(isNew){g.hint=1;g.hud()}const p=ws[g.i];say(`<b>רמז:</b> <span class="mst">${mtext(p.steps[0])}</span>`,'hint');return isNew},
  key,slot(k){if(!shown){cur=k;SND.tap();slots()}}}}

/* ======================================================================
   The pizza table. Fractions you can see and touch.
   conv: put the amount on the table slice by slice, then name it in the other form.
   add:  the two amounts side by side; count the loose slices, make a whole pizza from them, name the sum.
   sub:  the first amount on the table; cut a whole pizza when there are not enough slices (פריטה), eat the slices
         and the whole pizzas that are taken away, name what is left.
   ====================================================================== */
async function pizzaLevel(host,cfg,api){
 const ws=cfg.items,n=ws.length,g=scorer(host,n);let alive=true,t=null,stepT=0;
 window.__lv={kind:'pizza',g,state:()=>t};
 frame(host,'pizza',`<div class="ptask label" id="pt"></div><div class="table" id="tb"></div><div class="pfoot" id="pf"></div>`);
 const $=s=>host.querySelector(s),tb=$('#tb'),pt=$('#pt'),pf=$('#pf');
 const name=d=>PARTS_HE[d]||'חלקים';
 const place=()=>{const st=stage.getBoundingClientRect(),r=pt.getBoundingClientRect();toastAt(r.bottom-st.top+8)};   // messages appear under the task card, never over the answers
 window.addEventListener('resize',place);
 /* the table: pizzas {d, on (topped slices), gone (eaten), cut, tone} */
 function draw(){const many=t.pz.length>4;tb.className='table'+(many?' many':'')+(t.plus?' plus':'');
  tb.innerHTML=t.pz.map((p,j)=>`${t.plus&&j===t.plus?'<em class="pplus" dir="ltr">+</em>':''}<button class="pz${p.cut?'':' whole'}${p.on===p.d&&p.cut?' full':''}" data-a="mpz" data-j="${j}" aria-label="פיצה ${j+1}: ${p.on} מתוך ${p.d} פרוסות">${pizza(p.d,p.on,{cut:p.cut,tone:p.tone,gone:p.gone})}</button>`).join('')}
 const loose=()=>t.pz.filter(p=>p.cut&&p.on<p.d).reduce((a,p)=>a+p.on,0);
 const total=()=>t.pz.reduce((a,p)=>a+p.on,0);
 const task=(html,small='')=>{pt.innerHTML=`<b>${html}</b>${small?`<small>${small}</small>`:''}`};
 const foot=html=>{pf.innerHTML=html};
 const lay=(N,d,tone,cut=true)=>{const out=[];let k=N;while(k>0){const on=Math.min(d,k);out.push({d,on,gone:0,cut:cut||on<d,tone});k-=on}return out};

 function round(){const p=ws[g.i],d=p.ans.d;g.wrongNow=0;
  if(p.kind==='m2i'||p.kind==='i2m'){
   const need=top(p.ans),P=Math.min(4,Math.ceil(need/d)+(Math.ceil(need/d)<4?1:0));
   t={p,step:'build',pz:Array.from({length:P},()=>({d,on:0,gone:0,cut:true,tone:'a'}))};
   task(`שימו על השולחן ${p.kind==='m2i'?expr(p):`${expr(p)} פיצה`}`,`לחיצה על פרוסה ממלאת את הפיצה עד אליה. כל פיצה חתוכה ל־${parts(d,d)}`);
   counter()}
  else if(p.kind==='add'){
   t={p,step:'count',plus:Math.ceil(top(p.a)/d),pz:[...lay(top(p.a),d,'a'),...lay(top(p.b),d,'b')]};
   task(`${expr(p)}`,'קודם סופרים את הפרוסות הבודדות, בלי הפיצות השלמות');
   const s=p.a.n+p.b.n,opts=shuf([...new Set([s,s+1,Math.max(1,s-1),p.a.n*p.b.n>s?p.a.n*p.b.n:s+2])].slice(0,3));
   t.opts=opts;foot(`<p class="mq">כמה ${name(d)} בודדות יש ביחד?</p>${choiceBtns(opts.map(v=>({html:`<b class="big">${v}</b>`})),'nums')}`)}
  else{ // sub
   t={p,step:p.a.n<p.b.n?'cut':'eat',eaten:0,wholes:0,pz:[...Array.from({length:p.a.w},()=>({d,on:d,gone:0,cut:false,tone:'a'})),...(p.a.n?[{d,on:p.a.n,gone:0,cut:true,tone:'a'}]:[])]};
   task(`${expr(p)}`,`על השולחן ${fr(p.a)} פיצה. צריך להוריד ${fr(p.b)}`);
   subStep()}
  draw();g.hud()}

 function counter(){const p=t.p,d=p.ans.d,k=total();foot(`<p class="mq cnt">על השולחן: <b>${parts(k,d)}</b></p>${btn('mpzok','מוכן','green')}`)}

 function subStep(){const p=t.p,d=p.ans.d;
  if(t.step==='cut')foot(`<p class="mq">צריך להוריד ${parts(p.b.n,d)}, ${p.a.n?`ויש רק ${parts(p.a.n,d)}`:'ואין פרוסות בכלל'}.<br><b>לחצו על פיצה שלמה כדי לחתוך אותה</b> (זו הפריטה)</p>`);
  else if(t.step==='eat')foot(`<p class="mq">מורידים ${parts(p.b.n,d)}: <b>לחצו על הפרוסות</b><span class="pc">נאכלו ${t.eaten} מתוך ${p.b.n}</span></p>`);
  else if(t.step==='wholes')foot(`<p class="mq">ועכשיו מורידים ${p.b.w===1?'פיצה שלמה אחת':`${p.b.w} פיצות שלמות`}: <b>לחצו עליהן</b><span class="pc">הורדנו ${t.wholes} מתוך ${p.b.w}</span></p>`);
  else ask()}

 /* the last step of every exercise: name the amount on the table */
 function ask(){const p=t.p;t.step='ask';
  const opts=shuf([{f:p.ans,ok:1},...shuf(p.alts).slice(0,2)]);t.opts=opts;
  const q=p.kind==='m2i'?`כמה ${name(p.ans.d)} יש על השולחן? כתבו כשבר גדול מהשלם`:p.kind==='i2m'?'כמה פיצות שלמות, וכמה פרוסות נשארו? כמספר מעורב':p.kind==='add'?`אז כמה יש בסך הכול? ${expr(p)} =`:`כמה נשאר על השולחן? ${expr(p)} =`;
  foot(`<p class="mq">${q}</p>${choiceBtns(opts.map(o=>({html:fr(o.f)})))}`)}

 function pick(k){if(g.lock)return;const p=t.p;
  if(t.step==='count'){const v=t.opts[k],s=p.a.n+p.b.n,d=p.ans.d;
   if(v!==s){g.miss();SND.bad();return toast(`ספרו רק את הפרוסות בפיצות החתוכות שאינן מלאות: ${p.a.n} ועוד ${p.b.n}`,2600)}
   SND.pop();
   if(s>=d){t.step='merge';foot(`<p class="mq">${parts(s,d)}! זה יותר מפיצה שלמה.<br><b>מאחדים ${parts(d,d)} לפיצה שלמה אחת</b></p>${btn('mmerge','מרכיבים פיצה שלמה','green')}`)}
   else ask();return}
  if(t.step==='ask'){const o=t.opts[k],btns=pf.querySelectorAll('.mc');
   if(!o.ok){g.miss();SND.bad();btns[k].classList.add('mbad');btns[k].disabled=true;return toast(esc(o.why||'בדקו שוב: ספרו את מה שעל השולחן'),2800)}
   g.lock=1;btns[k].classList.add('mgood');SND.pop();g.done(p);confetti(undefined,undefined,30);
   foot(`<p class="mq okq">נכון! ${eqn(p)}</p>`);
   stepT=setTimeout(()=>{if(!alive)return;g.lock=0;g.i++;if(g.i>=n){alive=false;api.done(g.result())}else round()},1500)}}

 function merge(){const p=t.p,d=p.ans.d;SND.star(1);
  t.pz=[...lay(top(p.ans),d,'a',true)];t.plus=0;draw();
  tb.classList.add('merged');setTimeout(()=>tb.classList.remove('merged'),700);ask()}

 function ok(){const p=t.p,d=p.ans.d,k=total(),need=top(p.ans);
  if(k!==need){g.miss();SND.bad();return toast(k<need?`חסרות עוד ${need-k} ${name(d)}`:`יש ${k-need} ${name(d)} יותר מדי`,2400)}
  SND.pop();t.pz=lay(need,d,'a');draw();ask()}   // tidy the slices into whole pizzas before asking

 function tap(j,s){const p=t.p,pz=t.pz[j];if(!pz||g.lock)return;
  if(t.step==='build'){if(s<0)pz.on=pz.on===pz.d?0:pz.d;else{const k=s+1;pz.on=pz.on===k?s:k}SND.tap();draw();counter();return}   // the crust: the whole pizza on or off
  if(t.step==='cut'){if(pz.cut){SND.bad();return toast('לחצו על פיצה שלמה, לא על הפרוסות')}
   pz.cut=true;SND.pop();
   const d=p.ans.d;t.step='eat';draw();tb.querySelectorAll('.pz')[j].classList.add('justcut');
   task(`${expr(p)}`,`פרטנו שלם אחד: <span class="ex" dir="ltr">${fr(p.a)}<em>=</em>${fr(F(p.a.w-1,p.a.n+d,d))}</span>`);return subStep()}
  if(t.step==='eat'){if(!pz.cut){SND.bad();return toast('קודם אוכלים פרוסות מהפיצות החתוכות')}
   if(pz.on<1)return;pz.on--;pz.gone++;t.eaten++;SND.pop();draw();
   if(t.eaten>=p.b.n){t.step=p.b.w?'wholes':'ask';t.pz=t.pz.filter(q=>q.on>0)}
   if(t.step!=='eat')draw();return subStep()}
  if(t.step==='wholes'){if(pz.on!==pz.d){SND.bad();return toast('מורידים פיצות שלמות בלבד')}
   t.pz.splice(j,1);t.wholes++;SND.pop();if(t.wholes>=p.b.w)t.step='ask';draw();return subStep()}
  if(t.step==='count'||t.step==='merge'||t.step==='ask')return}

 round();place();
 return{destroy(){alive=false;clearTimeout(stepT);window.removeEventListener('resize',place);delete window.__lv},
  hint(){if(g.lock)return;const isNew=!g.hint;if(isNew){g.hint=1;g.hud()}
   if(t.step==='ask'){const k=t.opts.findIndex(o=>o.ok);pf.querySelectorAll('.mc')[k].classList.add('mglow')}
   else toast(mtext(t.p.steps[0]),3600);return isNew},
  tap,pick,ok,merge}}
