/* Level 3: the story bottle. Read the passage (tap any word for its meaning), then answer by choosing a bottle.
   Reading is meant to feel safe: the story is always one tap away, wrong picks just say "try again". */
import {TEXTS,GL,TOKRE,glossKey,VOC,EVIDENCE,T,starsFor} from './data.js';
import {S,award,save,say,hush,shuffle,esc} from './state.js';
import {SND} from './audio.js';
import {SP,hud,confetti,ico,spr,btn,en} from './ui.js';

const tok=s=>s.replace(TOKRE,t=>{if(!/[A-Za-z]/.test(t))return esc(t);const k=glossKey(t);return k?`<span class="t${VOC.has(k)?' v':''}" data-k="${esc(k)}" data-t="${esc(t)}">${esc(t)}</span>`:esc(t)});
const sentences=t=>t.match(/[^.!?]+[.!?]+["”]?\s*/g)||[t];

export async function start(host,cfg,api){
 const t=TEXTS.find(x=>x.p===cfg.part),sents=sentences(t.text);
 const g={phase:'story',i:0,miss:0,hint:0,first:0,wrongNow:0,lock:0,order:t.qs.map(q=>shuffle(q[1].map((_,i)=>i))),mark:[],peek:0};let alive=true,glT=0;
 window.__lv={kind:'read',g,answer:()=>t.qs[g.i]?t.qs[g.i][2]:null};
 const story=()=>`<div class="scrollp story"><h3 class="en" dir="ltr">${esc(t.title)}</h3>
   <div class="text en" dir="ltr">${sents.map((s,i)=>`<span class="sn${g.mark.includes(i)?' hl':''}">${tok(s)}</span>`).join('')}</div></div>`;
 function render(){hush();
  if(g.phase==='story'||g.peek){
   host.innerHTML=`<div class="lv read">${hud({i:g.peek?g.i:-1,n:t.qs.length,st:starsFor(g.miss,g.hint,T.starRead),hint:false})}
    ${story()}
    <p class="tip label" id="gl">${g.mark.length?'התשובה מתחבאת במשפט המסומן':'לחצו על כל מילה כדי לראות מה הפירוש שלה'}</p>
    <div class="row">${btn('readall',ico('sound')+' הקריאו לי','cream sm')}${g.peek?btn('unpeek','חזרה לשאלה '+ico('next'),'green'):btn('toq','לשאלות '+ico('next'),'green')}</div></div>`}
  else{const q=t.qs[g.i];
   host.innerHTML=`<div class="lv read qs">${hud({i:g.i,n:t.qs.length,st:starsFor(g.miss,g.hint,T.starRead)})}
    <div class="sign prompt q"><small>בחרו את הבקבוק עם התשובה הנכונה</small><b class="en" dir="ltr">${tok(q[0])}</b></div>
    <div class="bottles">${g.order[g.i].map(oi=>`<button class="bottle" data-o="${oi}" dir="ltr">${spr('bottle','bt')}<span class="ans label en">${esc(q[1][oi])}</span></button>`).join('')}</div>
    <p class="tip label" id="gl">אפשר ללחוץ על מילה בשאלה, או להציץ שוב בסיפור</p>
    <div class="row">${btn('peek',ico('book')+' הצצה בסיפור','cream')}</div></div>`}}
 function gloss(el){host.querySelectorAll('.t.sel').forEach(x=>x.classList.remove('sel'));el.classList.add('sel');
  const gl=host.querySelector('#gl');gl.innerHTML=`${en(el.dataset.t)} <span class="eq">=</span> ${esc(GL[el.dataset.k])}`;gl.classList.add('on');say(el.dataset.t);
  clearTimeout(glT)}
 function answer(el){if(g.lock||el.classList.contains('bad'))return;const q=t.qs[g.i],o=+el.dataset.o;
  if(o===q[2]){g.lock=1;el.classList.add('ok');SND.pop();const first=!g.wrongNow;if(first)g.first++;award(first?T.ptsFirst:T.ptsLater);
   const r=el.getBoundingClientRect(),s=host.getBoundingClientRect();confetti(r.left-s.left+r.width/2,r.top-s.top+r.height/2,24);say(q[1][o]);
   setTimeout(()=>{if(!alive)return;g.i++;g.wrongNow=0;g.lock=0;g.mark=[];
    if(g.i>=t.qs.length){alive=false;const perfect=g.first===t.qs.length;if(perfect&&S.read[t.id]!==g.first)award(T.ptsReadPerfect);S.read[t.id]=Math.max(g.first,S.read[t.id]||0);save();
     api.done({stars:starsFor(g.miss,g.hint,T.starRead),first:g.first,total:t.qs.length,miss:g.miss,hint:g.hint,review:[]})}
    else render()},1300)}
  else{g.miss++;g.wrongNow++;el.classList.add('bad');SND.bad();const gl=host.querySelector('#gl');gl.textContent='לא נורא, נסו בקבוק אחר. אפשר גם להציץ בסיפור.';gl.classList.add('on');
   host.querySelector('.hud').outerHTML=hud({i:g.i,n:t.qs.length,st:starsFor(g.miss,g.hint,T.starRead)})}}
 const onClick=e=>{const w=e.target.closest('.t');if(w)return gloss(w);const b=e.target.closest('.bottle');if(b)return answer(b);
  const a=e.target.closest('[data-a]');if(!a)return;const k=a.dataset.a;
  if(k==='toq'){SND.tap();g.phase='q';render()}
  else if(k==='peek'){SND.tap();g.peek=1;render()}
  else if(k==='unpeek'){SND.tap();g.peek=0;render()}
  else if(k==='readall'){SND.tap();say(t.text,.78)}};
 host.addEventListener('click',onClick);
 render();
 return{destroy(){alive=false;hush();host.removeEventListener('click',onClick);delete window.__lv},
  hint(){if(g.phase!=='q'||g.lock)return;if(!g.hint)g.hint=1;g.mark=(EVIDENCE[t.id]||[])[g.i]||[];g.peek=1;render();const h=host.querySelector('.sn.hl');if(h&&h.scrollIntoView)h.scrollIntoView({block:'center'})}}}
