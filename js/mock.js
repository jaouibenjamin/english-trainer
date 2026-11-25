/* The mock exam (מבחן דמו): a short paper in four stations, one try per question, like the real test.
   It ends in a check-in card (the teacher's "My Unit 1 check-in", filled in by the results), a practice for each skill
   that needs it, and then a new paper. Content: xdata.js. Progress: S.x, saved with the account. */
import {XSKILL,XORDER,XPASS,PIC,POOL,KIDS,TRIP,INVITE,WRITE_CHECK,RULES,paper,practice,shuf} from './xdata.js';
import {S,save,award,esc} from './state.js';
import {WORDS} from './data.js';
import {SND} from './audio.js';
import {helpOn,words,sentBtn} from './help.js';
import {view,stage,setBg,preload,SP,ico,spr,rb,btn,en,num,toast,confetti,clearFx,sleep} from './ui.js';

/* ---------- progress ---------- */
export const XS=()=>{if(!S.x||typeof S.x!=='object')S.x={};const x=S.x;if(!Array.isArray(x.tries))x.tries=[];if(!x.prac||typeof x.prac!=='object')x.prac={};if(!Array.isArray(x.seen))x.seen=[];return x};
const last=()=>XS().tries[XS().tries.length-1]||null;
const pct=sc=>sc&&sc[1]?sc[0]/sc[1]:0;
/* the skills of the last paper that need practice, and whether each was practised after it */
export function needs(){const t=last();if(!t)return[];return XORDER.filter(k=>pct(t.sc[k])<XPASS)}
const practised=k=>{const t=last();return!!t&&(XS().prac[k]||0)>t.at};
export const canRetake=()=>needs().every(practised);
const face=p=>p>=XPASS?['😀','אני מצליח/ה!','g']:p>=.5?['😐','צריך/ה קצת עזרה','n']:['☹️','צריך/ה עוד תרגול','r'];
const P100=p=>Math.round(p*100);

/* pictures from one sheet: 6 columns, 4 rows */
const pic=(w,cls='')=>{const i=PIC.indexOf(w);if(i<0)return'';const c=i%6,r=Math.floor(i/6);
 return`<span class="xpic ${cls}" role="img" aria-label="${esc(w)}" style="background-position:${c*20}% ${(r*100/3).toFixed(3)}%"></span>`};
const blank=s=>esc(s).replace('___','<i class="gap">&nbsp;</i>');
const top=(title,back)=>`<header class="top">${rb('nav',ico('back'),'חזרה',1,`data-to="${back}"`)}<h2 class="ribbon"><span>${title}</span></h2><span class="rbsp"></span></header>`;


/* ---------- the narrator: Pitzi the crab, in the gentle voice the pupils know from the English game ----------
   Short Hebrew lines at the start and the end, so a low first score reads as the start of practice, not as a failure.
   The words appear as she says them; the crab replays the line. Each line plays by itself once per visit. */
const VB='assets/voice/he/hf_20261121_';   // our own copies, served next to the game (sources: assets/voice/sources.tsv)
const NARR={
 intro:['173415_4c4e2d50-9e11-4134-bee4-95c2e6957987','היי! ברוכים הבאים למבחן הדמו. המטרה שלנו פשוטה: שתגיעו מוכנים למבחן ביום רביעי. כל השאלות כאן מבוססות רק על הדפים שקיבלתם מהמורה בכיתה. זה לא מבחן אמיתי, והוא לא נכנס לשום ציון. עונים, רואים במה אתם כבר חזקים ובמה כדאי עוד להתאמן, מתאמנים, ומנסים שוב. טעות זה בסדר גמור, כי כל טעות מראה לנו מה ללמוד. בהצלחה!'],
 again:['171203_3790986f-c9d9-421d-b2fa-f6bebc6bee6b','ברוכים השבים! התאמנתם, ועכשיו זה הזמן לראות כמה השתפרתם. לאט ובנחת, אני כאן איתכם.'],
 endPractice:['171203_b6a8b203-d883-4974-a015-b44ab3ba93c4','כל הכבוד שסיימתם! עכשיו אנחנו יודעים בדיוק במה להתאמן. אחרי אימון קצר, נסו שוב, ותראו כמה השתפרתם.'],
 endBetter:['171203_1cc9b5ff-12a9-450f-8005-03d0dd644eb8','השתפרתם מהפעם הקודמת! ככה זה עובד: מתאמנים, ומשתפרים. עוד קצת אימון, ואתם שם.'],
 endReady:['171204_7dd42f6e-ad55-4e0e-b77b-1c4d34e1dfaf','וואו! כל התחנות מעל שמונים אחוז. אתם מוכנים למבחן, ואני כל כך גאה בכם!'],
 pracStart:['171204_e83cd667-7795-46cb-ae24-30cbf5dab72e','בואו נתאמן ביחד. קודם כלל אחד קצר, ואחר כך תרגילים. אם טועים, מנסים שוב. ככה לומדים.'],
 pracDone:['171204_29e949fe-86ff-4277-b460-627f93df2f83','יופי של אימון! עכשיו אתם מוכנים לנסות שוב.']};
let na=null,naKey='',naT=0;const heard=new Set();
const narrBox=k=>`<div class="narr" data-k="${k}"><button class="ncrab" data-a="mocksay" data-k="${k}" aria-label="להשמיע שוב">${spr('crab_wave','nc')}<span class="nmouth"></span><span class="nsp">${spr('ic_speaker','')}</span></button>
 <p class="nbub">${NARR[k][1].split(' ').map(w=>`<span>${esc(w)} </span>`).join('')}</p></div>`;
export function stopNarr(){if(na){try{na.pause()}catch(e){}}clearInterval(naT);document.querySelectorAll('.narr.talk').forEach(e=>e.classList.remove('talk'))}
export function say(k,auto){const box=document.querySelector(`.narr[data-k="${k}"]`);if(!box||!NARR[k])return;
 if(auto&&heard.has(k)){box.classList.add('all');return}heard.add(k);stopNarr();
 if(!na){na=new Audio();na.preload='auto';na.setAttribute('playsinline','')}
 const words=[...box.querySelectorAll('.nbub span')];words.forEach(w=>w.classList.remove('on'));box.classList.remove('all');
 na.src=VB+NARR[k][0]+'.mp3';naKey=k;
 const show=()=>{const d=na.duration||0,t=na.currentTime||0;if(!d)return;const n=Math.ceil(words.length*Math.min(1,(t+.25)/(d*.94)));words.forEach((w,i)=>w.classList.toggle('on',i<n))};
 const end=()=>{clearInterval(naT);box.classList.remove('talk');box.classList.add('all')};
 na.onended=end;na.onerror=end;
 const p=na.play();box.classList.add('talk');naT=setInterval(show,120);
 if(p&&p.catch)p.catch(()=>{end();box.classList.add('tap')})}   // no sound allowed yet: the whole line shows, and the crab invites a tap
addEventListener('hashchange',stopNarr);

/* ======================================================================
   The hub: what the mock exam is, the last check-in, practice, retake
   ====================================================================== */
export function hub(){setBg('paper','center');const x=XS(),t=last(),nd=needs(),rt=canRetake();
 if(!t){view.innerHTML=`<section class="scr mockhub">${top('מבחן דמו','')}
  ${narrBox('intro')}
  <div class="xintro label">
   <h3>המטרה: להגיע מוכנים למבחן ביום רביעי</h3>
   <p class="xsrc">📄 כל השאלות כאן מבוססות <b>רק</b> על הדפים שקיבלתם מהמורה בכיתה</p>
   <div class="xloop" dir="rtl"><span>📝<small>מבחן</small></span><i>←</i><span>📋<small>תעודה</small></span><i>←</i><span>💪<small>אימון</small></span><i>←</i><span>📈<small>מבחן חדש</small></span></div>
   <p>${num(20)} שאלות ב־${num(4)} תחנות. לכל שאלה ניסיון אחד, כמו במבחן.</p>
   <p class="strong">טעות זה בסדר. היא מראה לנו במה להתאמן.</p></div>
  <div class="xstations">${XORDER.map((k,i)=>`<span class="xst s${i}"><b>${XSKILL[k].icon}</b><small>${XSKILL[k].he}</small></span>`).join('')}</div>
  <div class="xgo">${btn('nav','מתחילים את המבחן','green xl','data-to="mockrun"')}<p class="xnote">בערך ${num(12)} דקות</p></div></section>`;say('intro',true);return}
 const hist=x.tries.slice(-4);
 view.innerHTML=`<section class="scr mockhub">${top('מבחן דמו','')}
  ${rt?narrBox('again'):''}
  ${card(t,{small:true})}
  ${hist.length>1?`<div class="xhist label"><b>ההתקדמות שלי</b><div class="xh" dir="ltr">${hist.map((h,i)=>{const p=P100(h.total[0]/h.total[1]);return`<span class="hb" style="--h:${Math.max(8,p)}%"><i>${p}%</i><small>${i===hist.length-1?'עכשיו':'ניסיון '+(x.tries.length-hist.length+i+1)}</small></span>`}).join('')}</div></div>`:''}
  ${nd.length?`<div class="xplan label"><b>תוכנית האימון שלי</b>${nd.map(k=>`<button class="xpr ${practised(k)?'done':''}" data-a="nav" data-to="mockprac/${k}"><span class="xic">${XSKILL[k].icon}</span><span class="xt"><b>אימון ב${XSKILL[k].he}</b><small>${practised(k)?'עשיתם! אפשר להתאמן שוב':'כלל קצר ו־8 תרגילים עם הסברים'}</small></span>${practised(k)?spr('ic_check','xck'):ico('next')}</button>`).join('')}</div>`
   :`<p class="xready label">${spr('crab_star','')}<span><b>מוכנים למבחן!</b><span>כל התחנות מעל ${num('80%')}. אפשר לגשת שוב כדי להתאמן עוד.</span></span></p>`}
  <div class="xgo">${rt?btn('nav',`${ico('retry')} מבחן חדש`,'green xl','data-to="mockrun"')
   :`<button class="btn cream xl" disabled><span>${spr('lock','xlk')} מבחן חדש אחרי האימון</span></button><p class="xnote">קודם מתאמנים במה שסומן, ואז ניגשים שוב עם שאלות חדשות</p>`}</div>
 </section>`;if(rt)say('again',true)}

/* the check-in card: the teacher's self-check sheet, filled in by the results */
function card(t,{small=false}={}){const tot=t.total,p=P100(tot[0]/tot[1]);
 return`<div class="xcard label ${small?'small':''}"><h3><span>בדיקת סיום יחידה 1</span>${en('My Unit 1 Check-in')}</h3>
  <p class="xscore"><b dir="ltr">${num(tot[0]+' / '+tot[1])}</b><small>${p}%</small></p>
  <div class="xrows">${XORDER.map((k,i)=>{const sc=t.sc[k],q=pct(sc),f=face(q);return`<div class="xrow ${f[2]}" style="--i:${i}"><span class="xn">${XSKILL[k].icon} ${XSKILL[k].he}</span>
   <span class="xbar"><i style="--w:${P100(q)}%"></i></span><span class="xf" title="${f[1]}">${f[0]}</span><small class="xc" dir="ltr">${sc[0]}/${sc[1]}</small></div>`}).join('')}</div></div>`}

/* ======================================================================
   The exam: one try per question. No right answer is shown until the end.
   ====================================================================== */
export async function run(ctx){setBg('paper','center');await preload(['assets/x/pics.webp',SP('crab_walk'),SP('crab_happy'),SP('crab_oops')]);if(!ctx.live())return;
 const x=XS(),items=paper(new Set(x.seen),!x.tries.length),n=items.length,ans=[];let i=0,alive=true,armed=false;
 window.__lv={kind:'mock',items,i:()=>i,ans};
 view.innerHTML=`<section class="scr mockrun"><div class="xtop"><button class="rb t1 xquit" data-a="mockquit" aria-label="יציאה">${ico('x')}</button>
  <div class="xtrail" dir="rtl">${XORDER.map((k,j)=>`<span class="xs" data-k="${k}"><b>${XSKILL[k].icon}</b><small>${XSKILL[k].he}</small></span>`).join('<i class="xline"></i>')}${spr('crab_walk','xwalker')}</div>
  <p class="xcount" id="xc"></p></div><div class="xbody" id="xb"></div></section>`;
 const xb=document.getElementById('xb'),xc=document.getElementById('xc'),walker=view.querySelector('.xwalker');
 const moveCrab=k=>{const s=view.querySelector(`.xs[data-k="${k}"]`),tr=view.querySelector('.xtrail');if(!s||!tr)return;const a=s.getBoundingClientRect(),b=tr.getBoundingClientRect();
  walker.style.transform=`translateX(${(a.left+a.width/2-b.left-20).toFixed(1)}px)`;view.querySelectorAll('.xs').forEach(e=>e.classList.toggle('on',e.dataset.k===k))};
 async function station(k){const idx=XORDER.indexOf(k);moveCrab(k);
  xb.innerHTML=`<div class="xstation" data-k="${k}"><span class="xsn">${XSKILL[k].station}</span><b class="xbig">${XSKILL[k].icon}</b><h3>${XSKILL[k].he}</h3>${en(XSKILL[k].en)}
   <p>${{words:'מכירים את המילים?',grammar:'am, is, are ושאלות',reading:'קוראים ומוצאים את התשובה',writing:'כותבים באנגלית: אות גדולה ונקודה'}[k]}</p>${btn('mocknext','יאללה','green')}</div>`;
  SND.star(Math.min(2,idx));await waitNext()}
 async function step(){if(!alive)return;
  if(i>=n){alive=false;return finish()}
  const it=items[i];if(i===0||items[i-1].skill!==it.skill)await station(it.skill);if(!alive)return;
  xc.innerHTML=`שאלה ${num(i+1)} מתוך ${num(n)}`;xb.innerHTML=question(it,'exam');focusInput();
  const res=await answer(it,'exam',ctx);if(!alive)return;ans.push({k:it.k,skill:it.skill,ok:res.ok,v:res.v});
  await sleep(res.ok?650:900);i++;step()}
 async function finish(){const sc={};for(const k of XORDER){const a=ans.filter(r=>r.skill===k);sc[k]=[a.filter(r=>r.ok).length,a.length]}
  const right=ans.filter(r=>r.ok).length,t={at:Date.now(),sc,total:[right,n],miss:ans.filter(r=>!r.ok).map(r=>r.k),wrong:ans.filter(r=>!r.ok).map(r=>[r.k,r.v])};
  x.tries.push(t);x.seen=[...new Set([...x.seen,...items.map(it=>it.k)])].slice(-400);if(x.tries.length>20)x.tries=x.tries.slice(-20);
  award(right*5);save();delete window.__lv;report(t,items,ctx)}
 ctx.setLevel({destroy(){alive=false;waiter=null;pending=null;delete window.__lv},
  quit(el){if(!armed){armed=true;toast('לצאת? המבחן לא יישמר.<br>לחצו שוב על ✕ כדי לצאת',2600);setTimeout(()=>armed=false,2600);return false}return true}});
 step()}

/* the report: the check-in card, the plan, and the mistakes with the right answers */
function report(t,items,ctx){ctx.setLevel(null);clearFx();const nd=needs(),p=P100(t.total[0]/t.total[1]);
 const head=!nd.length?'מוכנים למבחן!':p>=60?'כל הכבוד על המבחן!':'סיימתם את המבחן!';
 const prev=XS().tries[XS().tries.length-2],better=prev&&t.total[0]/t.total[1]>prev.total[0]/prev.total[1],nk=!nd.length?'endReady':better?'endBetter':'endPractice';
 const weak=nd.map(k=>XSKILL[k].he);
 const wrong=t.wrong.map(([k,v])=>{const it=items.find(q=>q.k===k);return it?`<div class="xw"><span class="xwq">${XSKILL[it.skill].icon} ${it.sent?blank(it.sent):it.big?en(it.big):it.pic?pic(it.pic,'mini'):esc(it.q)}</span>
  <span class="xwa"><s dir="ltr">${esc(v||'—')}</s><b dir="ltr">${esc(it.type==='sentence'?it.a:it.a)}</b></span></div>`:''}).join('');
 view.innerHTML=`<section class="scr mockrep"><h2 class="ribbon"><span>${head}</span></h2>
  ${narrBox(nk)}
  ${card(t)}
  ${nd.length?`<div class="xmsg label"><b>שמנו לב שכדאי לחזק: ${weak.join(' ו')}</b><span>הכנו לכם אימון קצר ב${weak.length>1?'כל אחד מהם':weak[0]}. אחרי האימון אפשר לגשת שוב למבחן הדמו, עם שאלות חדשות.</span></div>`
   :`<div class="xmsg label ok"><b>כל התחנות מעל ${num('80%')}!</b><span>אפשר לגשת שוב למבחן חדש כדי להישאר בכושר.</span></div>`}
  <div class="xgo">${nd.length?btn('nav',`מתחילים לאמן: ${XSKILL[nd[0]].he} ${ico('next')}`,'green xl',`data-to="mockprac/${nd[0]}"`):btn('nav','לעמוד מבחן הדמו','green xl','data-to="mock"')}</div>
  ${wrong?`<details class="xrev label"><summary>הטעויות שלי (${num(t.wrong.length)}) והתשובות הנכונות</summary>${wrong}</details>`:''}
 </section>`;
 view.querySelectorAll('.xbar i').forEach((b,i)=>setTimeout(()=>b.classList.add('go'),300+i*250));
 if(!nd.length){confetti();SND.win()}else SND.star(1);setTimeout(()=>say(nk,true),900)}

/* ======================================================================
   Practice: a rule card, then 8 items. Wrong → why and one more try. Wrong twice → the answer and on.
   ====================================================================== */
export async function prac(k,ctx){if(!XSKILL[k])return ctx.go('mock');setBg('paper','center');await preload(['assets/x/pics.webp',SP('crab_listen')]);if(!ctx.live())return;
 const t=last(),items=practice(k,t?t.miss:[],new Set(XS().seen)),n=items.length,R=RULES[k];let i=0,alive=true,first=0;
 window.__lv={kind:'mockprac',items,i:()=>i};
 view.innerHTML=`<section class="scr mockprac">${top('אימון ב'+XSKILL[k].he,'mock')}<div class="xbody" id="xb"></div></section>`;
 const xb=document.getElementById('xb');
 xb.innerHTML=`${narrBox('pracStart')}<div class="xrule label"><h3>${esc(R.t)}</h3><ul>${R.lines.map((l,j)=>`<li style="--i:${j}"><span>${fmt(l[0])}</span>${l[1]?`<bdi class="xex" dir="ltr">${esc(l[1])}</bdi>`:''}</li>`).join('')}</ul>${btn('mocknext','הבנתי, מתאמנים','green')}</div>`;
 ctx.setLevel({destroy(){alive=false;waiter=null;pending=null;delete window.__lv}});
 say('pracStart',true);
 await waitNext();if(!alive)return;stopNarr();
 for(;i<n&&alive;i++){const it=items[i];xb.innerHTML=`<p class="xcount">תרגיל ${num(i+1)} מתוך ${num(n)}</p>${question(it,'prac')}`;focusInput();
  let tries=0,done=false;
  while(!done&&alive){const r=await answer(it,'prac',ctx,tries);if(!alive)return;
   if(r.ok){if(!tries)first++;award(tries?4:10);SND.pop();feedback(true,it,'');await sleep(900);done=true}
   else{tries++;SND.bad();
    if(tries<2){feedback(false,it,r.why||'');unlock(it)}
    else{feedback(false,it,'',true);await waitNext();done=true}}}}
 if(!alive)return;
 XS().prac[k]=Date.now();save();delete window.__lv;ctx.setLevel(null);
 const left=needs().filter(s=>!practised(s));
 view.innerHTML=`<section class="scr mockrep"><h2 class="ribbon"><span>סיימתם אימון ב${XSKILL[k].he}!</span></h2>${narrBox('pracDone')}
  <p class="line label">${num(first)} מתוך ${num(n)} בניסיון הראשון</p>
  <div class="xmsg label ${left.length?'':'ok'}"><b>${left.length?`עוד אימון אחד: ${XSKILL[left[0]].he}`:'אפשר לגשת שוב למבחן הדמו!'}</b><span>${left.length?'ואז נפתח מבחן חדש':'המבחן החדש עם שאלות אחרות. בהצלחה!'}</span></div>
  <div class="xgo">${left.length?btn('nav',`לאימון ב${XSKILL[left[0]].he} ${ico('next')}`,'green xl',`data-to="mockprac/${left[0]}"`):btn('nav',`${ico('retry')} למבחן חדש`,'green xl','data-to="mockrun"')}
   ${btn('nav','לעמוד מבחן הדמו','cream sm','data-to="mock"')}</div></section>`;
 confetti(undefined,undefined,40);SND.win();setTimeout(()=>say('pracDone'),700)}

const fmt=l=>esc(l).replace(/([A-Za-z][A-Za-z' .,?!\/…()·→]*[A-Za-z.?!)])/g,m=>`<bdi dir="ltr" class="en">${m}</bdi>`);

/* ---------- one question on the screen ---------- */
const NUMW=WORDS.filter(w=>w.p===7).map(w=>w.en.toLowerCase());
function question(it,mode){
 /* word help is for practice, not for the paper: the paper is the rehearsal of the real test. Off, or in the paper, the
    lines are drawn exactly as before. A word that is the answer of this question is never a help button. */
 const H=helpOn()&&mode==='prac',skip=[String(it.a||'').toLowerCase(),...(it.type==='who'?NUMW:[])],   // in "who is it?" a number word would give the age on the card away
 tx=l=>H?words(l,skip):esc(l),bl=s=>H?tx(s).replace('___','<i class="gap">&nbsp;</i>'):blank(s),
  sb=s=>H?sentBtn(it.a&&/^(am|is|are)$/.test(it.a)?s.replace('___',it.a):s):'';   // the Hebrew of a whole sentence: only when the data has it; with a gap only when the gap is am / is / are (the Hebrew does not give that away)
 let body='';
 if(it.type==='who')body=`<div class="xkids">${KIDS.map(c=>`<span class="xkid"><b>${c.em}</b><span class="xkn">${en(c.n)}</span><span class="xkf" dir="ltr">🎂 age <b>${c.age}</b></span>${c.month?`<span class="xkf" dir="ltr">📅 <b>${esc(c.month)}</b></span>`:''}</span>`).join('')}</div>
  <div class="xdesc" dir="ltr">${it.lines.map(l=>`<p>${tx(l)}</p>`).join('')}</div>`;
 else if(it.type==='read')body=`<details class="xtext" ${mode==='prac'||it.k==='trip:0'?'open':''} dir="ltr"><summary dir="rtl">📄 הקטע: ${en(TRIP.title)}</summary>${TRIP.lines.map((l,j)=>`<p class="${mode==='prac'&&j===it.line?'ev':''}" data-l="${j}">${tx(l)}</p>`).join('')}</details>
  <p class="xsent" dir="ltr">${bl(it.sent)}</p>`;
 else body=`${it.pic?pic(it.pic,'big'):''}${it.big?`<p class="xbigw" dir="ltr">${esc(it.big)}</p>`:''}${it.card==='invite'?invite():''}${it.sent?`<p class="xsent" dir="ltr">${bl(it.sent)}</p>${sb(it.sent)}`:''}${it.raw?`<p class="xraw" dir="ltr">${tx(it.raw)}</p>`:''}`;
 let ans='';
 if(it.type==='choice'||it.type==='who'||it.type==='read')ans=`<div class="xopts ${it.o.length>3?'four':''} ${it.o.some(o=>o.length>14)?'long':''}">${it.o.map((o,j)=>`<button class="xo" data-a="mockpick" data-j="${j}" dir="${/[א-ת]/.test(o)?'rtl':'ltr'}">${esc(o)}</button>`).join('')}</div>`;
 else if(it.type==='order')ans=`<div class="xans" dir="ltr" id="xl"><span class="xph">לחצו על המילים לפי הסדר</span></div><div class="xtiles" dir="ltr">${shuf(it.tiles).map(w=>`<button class="xtile" data-a="mocktile" data-w="${esc(w)}">${esc(w)}</button>`).join('')}<span class="xq">?</span></div>${btn('mockcheck','בדיקה','green')}`;
 else ans=`<div class="xtype"><input id="xi" class="in en" dir="ltr" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="done" placeholder="${it.type==='sentence'?'Write the sentence here':'Write here'}">${btn('mockcheck','בדיקה','green')}</div>`;
 return`<div class="xq label"${H?` data-hk="mock:${esc(it.k)}"`:''}><p class="xqt">${esc(it.q)}</p>${body}</div>${ans}<div class="xfb" id="xfb" role="status" aria-live="polite"></div>`}

export function invite(){const d=INVITE;
 return`<div class="xinv" dir="ltr"><span class="xi1">🎈 <b>${esc(d.name)}'s Birthday!</b></span><span class="xi2"><span style="font-size:34px">🎂</span> <b style="font-size:30px">${d.age}</b></span>
  <span class="xi3"><span class="xcal"><small>October</small><b>14</b></span><em>October 14</em></span><span class="xi4"><svg viewBox="-50 -50 100 100" role="img" aria-label="clock at four"><circle r="47" fill="#fffdf6" stroke="#5a4534" stroke-width="3.5"/>${[12,1,2,3,4,5,6,7,8,9,10,11].map((h,k)=>{const a=k*Math.PI/6;return`<text x="${(Math.sin(a)*36).toFixed(1)}" y="${(-Math.cos(a)*36+5.5).toFixed(1)}" text-anchor="middle" font-size="${h%3?12:15}" font-weight="800" fill="${h===4?'#c0392b':'#5a4534'}" font-family="Fredoka,Arial,sans-serif">${h}</text>`}).join('')}<line x1="0" y1="0" x2="0" y2="-23" stroke="#2f6fa8" stroke-width="3.5" stroke-linecap="round"/><line x1="0" y1="0" x2="${(Math.sin(4*Math.PI/6)*21).toFixed(1)}" y2="${(-Math.cos(4*Math.PI/6)*21).toFixed(1)}" stroke="#c0392b" stroke-width="6" stroke-linecap="round"/><circle r="4" fill="#5a4534"/></svg></span>
  <span class="xi5">🏠 <b>8 Rose Street</b></span></div>`}

function focusInput(){const i=document.getElementById('xi');if(i&&matchMedia('(pointer:fine)').matches)setTimeout(()=>i.focus(),50)}

/* wait for the pupil's answer to the question on screen; resolves {ok, v, why} */
let pending=null,lineWords=[],waiter=null;
/* the green 'next' buttons (station card, rule card, after a revealed answer) */
const waitNext=()=>new Promise(r=>{waiter=r});
export function next(){if(waiter){const f=waiter;waiter=null;f()}}
function answer(it,mode,ctx,tries=0){lineWords=tries?lineWords:[];
 curIt=it;return new Promise(res=>{pending=r=>{pending=null;res(r)}})}
export const MOCK_A={
 pick(d){const it=curItem();if(!pending||!it)return;const v=it.o[+d.j],ok=v===it.a,b=view.querySelectorAll('.xo')[+d.j];
  view.querySelectorAll('.xo').forEach(e=>e.disabled=true);b.classList.add(ok?'good':'bad');if(!ok){b.classList.add('shake')}
  SND[ok?'pop':'bad']();mark(ok);pending({ok,v,why:wrongWhy(it,v)})},
 tile(d,el){if(!pending)return;const xl=document.getElementById('xl');if(el.parentElement.id==='xl'){el.remove();view.querySelector('.xtiles').insertBefore(el,view.querySelector('.xtiles .xq'))}
  else{xl.querySelector('.xph')&&xl.querySelector('.xph').remove();xl.appendChild(el)}SND.tap()},
 check(){const it=curItem();if(!pending||!it)return;
  if(it.type==='order'){const w=[...document.querySelectorAll('#xl .xtile')].map(e=>e.dataset.w);if(w.length<it.tiles.length)return toast('השתמשו בכל המילים',1800);
   const v=w.join(' ')+'?',ok=v===it.a;lock();SND[ok?'pop':'bad']();mark(ok);return pending({ok,v,why:ok?'':/^(Is|Are) /.test(v)?'הסדר לא נכון. מה הנושא ומה התיאור?':'בשאלה מתחילים ב־Is או Are'})}
  const inp=document.getElementById('xi'),v=inp.value.trim();if(!v)return toast('כתבו תשובה באנגלית',1800);
  if(it.type==='sentence'){const r=WRITE_CHECK.sentence(v,it.a);lock();SND[r.ok?'pop':'bad']();mark(r.ok);
   return pending({ok:r.ok,v,why:{words:'בדקו שהמילים נכונות ושלא חסרה מילה',cap:'משפט מתחיל באות גדולה',name:`${r.w} כותבים באות גדולה`,stop:'חסרה נקודה בסוף המשפט'}[r.why]||''})}
  const ok=WRITE_CHECK.plain(v,it.acc);lock();SND[ok?'pop':'bad']();mark(ok);pending({ok,v,why:ok?'':it.hint?`רמז: ${it.hint}`:'בדקו את האיות'})},
 };
let curIt=null;const curItem=()=>curIt;
document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target&&e.target.id==='xi'){e.preventDefault();MOCK_A.check()}});
function lock(){view.querySelectorAll('.xtile,.xo,#xi,[data-a=mockcheck]').forEach(e=>{e.disabled=true});const i=document.getElementById('xi');if(i)i.readOnly=true}
function unlock(it){view.querySelectorAll('.xtile,.xo,#xi,[data-a=mockcheck]').forEach(e=>{if(!e.classList.contains('bad'))e.disabled=false});const i=document.getElementById('xi');if(i){i.readOnly=false;i.select()}
 if(it.type==='order'){const xl=document.getElementById('xl'),tl=view.querySelector('.xtiles');[...xl.querySelectorAll('.xtile')].forEach(e=>tl.insertBefore(e,tl.querySelector('.xq')));xl.innerHTML='<span class="xph">לחצו על המילים לפי הסדר</span>'}}
function mark(ok){const q=view.querySelector('.xq.label');if(q){q.classList.remove('okq','noq');void q.offsetWidth;q.classList.add(ok?'okq':'noq')}}
function wrongWhy(it,v){if(it.skill==='grammar'&&it.k.startsWith('be:'))return'בדקו מי הנושא: I, דבר אחד, או כמה?';if(it.type==='who')return'בדקו כל פרט: גיל, חודש ותחביב';if(it.type==='read')return'חפשו בקטע מילה מהשאלה';return''}
/* practice feedback under the question */
function feedback(ok,it,why,reveal){const fb=document.getElementById('xfb');if(!fb)return;
 if(ok){fb.className='xfb ok';fb.innerHTML=`<b>נכון!</b> ${fmt(it.tip||'')}`;return}
 if(!reveal){fb.className='xfb bad';fb.innerHTML=`<b>עוד ניסיון:</b> ${esc(why||'נסו שוב')}`;return}
 fb.className='xfb sol';fb.innerHTML=`<b>התשובה:</b> ${en(it.a)}<span>${fmt(it.tip||'')}</span>${btn('mocknext',`הבא ${ico('next')}`,'green sm')}`;
 if(it.type==='read'){const p=view.querySelector(`.xtext p[data-l="${it.line}"]`);if(p){p.classList.add('ev');view.querySelector('.xtext').open=true}}}
