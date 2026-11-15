/* Level 3: the story bottle. Read the passage (tap any word for its meaning), then answer by choosing a bottle.
   Reading is meant to feel safe: the story is always one tap away, wrong picks just say "try again". */
import {TEXTS,GL,TOKRE,glossKey,VOC,EVIDENCE,T,starsFor} from './data.js';
import {S,award,save,say,sayAll,warm,hush,shuffle,esc} from './state.js';
import {SND} from './audio.js';
import {hud,confetti,ico,spr,btn,en,toast} from './ui.js';

const tok=s=>s.replace(TOKRE,t=>{if(!/[A-Za-z]/.test(t))return esc(t);const k=glossKey(t);return k?`<span class="t${VOC.has(k)?' v':''}${t.length<4?' s':''}" data-k="${esc(k)}" data-t="${esc(t)}">${esc(t)}</span>`:esc(t)});
/* a lone "I" never ends a line: it stays with the word after it */
const bindI=h=>h.replace(/(>I<\/span>) (?=\S)/g,'$1&nbsp;');
const sentences=t=>t.match(/[^.!?]+[.!?]+["”]?\s*/g)||[t];

export async function start(host,cfg,api){
 const t=TEXTS.find(x=>x.p===cfg.part),sents=sentences(t.text),n=t.qs.length;
 const g={phase:'story',i:0,miss:0,hint:0,first:0,bad:0,wrongNow:0,lock:0,order:t.qs.map(q=>shuffle(q[1].map((_,i)=>i))),mark:[],peek:0,wrong:[]};let alive=true;
 window.__lv={kind:'read',g,answer:()=>t.qs[g.i]?t.qs[g.i][2]:null};
 const head=()=>hud({i:g.phase==='story'?-1:g.i,n,st:starsFor(n-g.bad,n,g.hint),hint:g.hint,book:g.phase==='story'?'c':'d'});
 const story=()=>`<div class="scrollp story${t.text.length>360?' long':''}"><h3 class="en" dir="ltr">${esc(t.title)}</h3>
   <div class="text en" dir="ltr">${sents.map((s,i)=>`<span class="sn${g.mark.includes(i)?' hl':''}">${bindI(tok(s))}</span>`).join('')}</div></div>`;
 function render(){hush();
  if(g.phase==='story'||g.peek){
   host.innerHTML=`<div class="lv read">${head()}
    <p class="tip" id="gl">${g.mark.length?'התשובה מתחבאת במשפט המסומן':'לחצו על מילה כדי לראות את הפירוש שלה'}</p>
    <div class="mid">${story()}</div>
    <div class="row">${btn('readall',spr('ic_speaker','bi')+' הקריאו לי','cream')}${g.peek?btn('unpeek','חזרה לשאלה '+ico('next'),'green'):btn('toq','לשאלות '+ico('next'),'green')}</div></div>`;
   const tx=host.querySelector('.text'),more=()=>tx.classList.toggle('more',tx.scrollHeight-tx.scrollTop-tx.clientHeight>6);tx.addEventListener('scroll',more,{passive:true});more();setTimeout(more,400)}
  else{const q=t.qs[g.i];
   host.innerHTML=`<div class="lv read qs">${head()}
    <div class="sign prompt q"><small>בחרו את הבקבוק עם התשובה הנכונה</small><b class="en" dir="ltr">${tok(q[0])}</b></div>
    <div class="bottles">${g.order[g.i].map(oi=>`<button class="bottle${g.wrong.includes(oi)?' bad':''}" data-o="${oi}" dir="ltr">${spr('bottle','bt')}<span class="ans label en">${esc(q[1][oi])}</span><i class="mk"></i></button>`).join('')}</div>
    <p class="fb" id="gl">${g.wrong.length?'לא נורא, נסו בקבוק אחר':'לחיצה על מילה בשאלה מראה את הפירוש שלה'}</p>
    <div class="row">${btn('peek',spr('ic_book','bi')+' הצצה בסיפור','cream')}</div></div>`}}
 function gloss(el){host.querySelectorAll('.t.sel').forEach(x=>x.classList.remove('sel'));el.classList.add('sel');
  const gl=host.querySelector('#gl');gl.innerHTML=`${en(el.dataset.t)} <span class="eq">=</span> ${esc(GL[el.dataset.k])}`;gl.classList.add('on');say(el.dataset.t)}
 function answer(el){if(g.lock||el.classList.contains('bad'))return;const q=t.qs[g.i],o=+el.dataset.o;
  if(o===q[2]){g.lock=1;el.classList.add('ok');SND.pop();const ok1=!g.wrongNow;if(ok1)g.first++;award(ok1?T.ptsFirst:T.ptsLater);
   const gl=host.querySelector('#gl');gl.textContent='נכון!';gl.classList.add('on','good');
   const r=el.getBoundingClientRect(),s=host.getBoundingClientRect();confetti(r.left-s.left+r.width/2,r.top-s.top+r.height/2,24);say(q[1][o]);
   setTimeout(()=>{if(!alive)return;g.i++;g.wrongNow=0;g.lock=0;g.mark=[];g.wrong=[];
    if(g.i>=n){alive=false;const perfect=g.first===n;if(perfect&&S.read[t.id]!==g.first)award(T.ptsReadPerfect);S.read[t.id]=Math.max(g.first,S.read[t.id]||0);save();
     api.done({stars:starsFor(g.first,n,g.hint),first:g.first,total:n,hint:g.hint,review:[]})}
    else render()},1300)}
  else{g.miss++;if(!g.wrongNow)g.bad++;g.wrongNow++;g.wrong.push(o);el.classList.add('bad');SND.bad();const gl=host.querySelector('#gl');gl.textContent='לא נורא, נסו בקבוק אחר';gl.classList.add('on');
   host.querySelector('.hud').outerHTML=head()}}
 const onClick=e=>{const w=e.target.closest('.t');if(w)return gloss(w);const b=e.target.closest('.bottle');if(b)return answer(b);
  const a=e.target.closest('[data-a]');if(!a)return;const k=a.dataset.a;
  if(k==='toq'){SND.tap();g.phase='q';render()}
  else if(k==='peek'){SND.tap();g.peek=1;render()}
  else if(k==='unpeek'){SND.tap();g.peek=0;render()}
  else if(k==='readall'){SND.tap();sayAll([t.title,...sents],.78)}};   // title, then sentence by sentence
 host.addEventListener('click',onClick);
 warm([t.title,...sents,...t.qs.map(q=>q[1][q[2]])]);   // the story and the right answers; tapped words load when tapped
 render();
 return{destroy(){alive=false;hush();host.removeEventListener('click',onClick);delete window.__lv},
  hint(){if(g.lock)return;
   if(g.phase==='story'||g.peek)return toast('לחצו על מילה בסיפור ותראו מה היא אומרת');   // nothing to reveal yet, so no star cap
   const isNew=!g.hint;g.hint=1;g.mark=(EVIDENCE[t.id]||[])[g.i]||[];g.peek=1;render();const h=host.querySelector('.sn.hl');if(h&&h.scrollIntoView)h.scrollIntoView({block:'center'});return isNew}}}
