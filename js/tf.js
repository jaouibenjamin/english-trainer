/* Extra practice: true or not? A card shows an English word and a Hebrew meaning; the pupil says whether they belong
   together, by swiping the card (right: yes, left: no), by the two buttons, or by the arrow keys.
   - The words and meanings are the teacher's list for the island (wordsOf), exactly as written there. A "not true"
     card borrows the meaning of another word of the same list.
   - A wrong answer shows the right pair and the card comes back later in the round; the round ends when every word was
     answered right once. Nothing ends early and nothing is lost.
   - Practice only: it calls none of the functions that keep score (no mark, no award, no stars, no save). */
import {wordsOf} from './data.js';
import {say,warm,shuffle,esc,reduced} from './state.js';
import {SND} from './audio.js';
import {rb,ico,btn,en,num,spr} from './ui.js';

const ROUND=8,SWIPE=64;
const first=he=>he.split(',')[0];

export async function start(host,cfg,api){
 const pool=cfg.parts.flatMap(p=>wordsOf(p)),ws=shuffle(pool).slice(0,Math.min(ROUND,pool.length));
 warm(ws.map(w=>w.en));
 /* a card: the word, the meaning shown with it, and whether that meaning is the word's own */
 const deal=w=>{const others=pool.filter(o=>o.he!==w.he&&o.en!==w.en),truth=!others.length||Math.random()<.5,o=truth?w:others[Math.random()*others.length|0];return{w,he:o.he,from:o,truth}};
 const g={queue:ws.map(deal),done:0,first:0,missed:new Set(),lock:0,n:ws.length};let alive=true,drag=null;
 window.__lv={kind:'tf',g,card:()=>g.queue[0]&&{en:g.queue[0].w.en,he:g.queue[0].he,truth:g.queue[0].truth}};
 host.innerHTML=`<section class="scr tf"><header class="top">${rb('nav',ico('back'),'חזרה',1,`data-to="island/${cfg.island.id}"`)}<h2 class="ribbon"><span>נכון או לא?</span></h2><span class="rbsp"></span></header>
  <p class="tfc" id="tfc" aria-live="polite"></p><p class="xsr" id="tfl" aria-live="polite"></p>
  <div class="tfa" id="tfa"></div>
  <p class="tfn">זה תרגול: בלי כוכבים ובלי נקודות</p></section>`;
 const area=host.querySelector('#tfa'),count=host.querySelector('#tfc'),live=host.querySelector('#tfl');
 const speak=()=>{const c=g.queue[0];if(c)say(c.w.en)};
 function show(){const c=g.queue[0];g.lock=0;count.innerHTML=`${num(g.done)} מתוך ${num(g.n)} מילים`;
  area.innerHTML=`<div class="tfk" id="tfk"><button class="tfs" data-t="say" aria-label="השמיעו את המילה">${spr('ic_speaker','')}</button>
    <b class="tfw">${en(c.w.en)}</b><span class="tfq">הפירוש הוא</span><span class="tfhq"><b class="tfh">${esc(first(c.he))}</b><span class="tfq">?</span></span></div>
   <div class="tfb"><button class="tfy" data-t="yes"><i aria-hidden="true">→</i> נכון</button><button class="tfx" data-t="no">לא נכון <i aria-hidden="true">←</i></button></div>
   <p class="tft">אפשר גם להחליק את הכרטיס לצד של התשובה</p>`;
  live.textContent=`${c.w.en}. הפירוש הוא ${first(c.he)}?`;   // a screen reader hears each new card
  speak()}
 function answer(yes){const c=g.queue[0];if(!c||g.lock||!alive)return;g.lock=1;const ok=yes===c.truth,k=area.querySelector('#tfk');
  if(ok){SND.pop();if(!g.missed.has(c.w.en))g.first++;g.done++;g.queue.shift();
   if(k){k.classList.add('ok');if(!reduced())k.classList.add(yes?'fly-y':'fly-n')}
   area.querySelector('.tfb').innerHTML=`<p class="tfr ok">${en(c.w.en)} <span>=</span> ${esc(first(c.w.he))}</p>`;area.querySelector('.tft').textContent='';
   setTimeout(()=>{if(!alive)return;if(g.queue.length)show();else end()},1000)}
  else{SND.bad();g.missed.add(c.w.en);g.queue.shift();g.queue.push(deal(c.w));   // the word comes back, perhaps with another meaning
   if(k)k.classList.add('no');
   /* explain: the word's own meaning, and, when the card showed another word's meaning, whose it is */
   area.querySelector('.tfb').innerHTML=`<div class="tfe"><p class="tfm">${c.truth?'דווקא כן, זה הפירוש:':'לא, זה לא הפירוש. כך נכון:'}</p><p class="tfr">${en(c.w.en)} <span>=</span> ${esc(first(c.w.he))}</p>
     ${c.truth?'':`<p class="tfr two">${esc(first(c.he))} <span>=</span> ${en(c.from.en)}</p>`}
     <p class="tfm">המילה תחזור עוד מעט</p>${btn('tfnext','הבנתי','green')}</div>`;
   area.querySelector('.tft').textContent='';const b=area.querySelector('[data-a=tfnext]');if(b)b.focus({preventScroll:true})}}
 function end(){SND.win();count.innerHTML='';const miss=ws.filter(w=>g.missed.has(w.en));
  area.innerHTML=`<div class="tfend">${spr('crab_happy','bob')}<h3>סיימתם את הסיבוב!</h3>
    <p>${num(g.first)} מתוך ${num(g.n)} בניסיון הראשון</p>
    ${miss.length?`<div class="tfrev"><small>כדאי לחזור על</small>${miss.slice(0,4).map(w=>`<span>${en(w.en)} · ${esc(first(w.he))}</span>`).join('')}</div>`:'<p class="tfm">בלי אף טעות!</p>'}
    <div class="tfeb">${btn('nav','עוד סיבוב','green',`data-to="extra/${cfg.island.id}/tf" data-force="1"`)}${btn('nav','לשלבים','cream',`data-to="island/${cfg.island.id}"`)}</div></div>`;
  window.__lv.ended={first:g.first,n:g.n,missed:[...g.missed]}}
 const onClick=e=>{const t=e.target.closest('[data-t]');if(t){if(t.dataset.t==='say'){SND.tap();return speak()}return answer(t.dataset.t==='yes')}
  if(e.target.closest('[data-a=tfnext]')){SND.tap();if(alive&&g.queue.length)show()}};
 const onKey=e=>{if(!alive||e.altKey||e.ctrlKey||e.metaKey||e.target.closest('input,textarea'))return;   // Alt+Left is the browser's "back"
  if(g.lock){if((e.key==='Enter'||e.key===' ')&&area.querySelector('[data-a=tfnext]')){e.preventDefault();SND.tap();show()}return}
  if(e.key==='ArrowRight'){e.preventDefault();answer(true)}else if(e.key==='ArrowLeft'){e.preventDefault();answer(false)}};
 /* swipe: the card follows the finger; let go far enough to a side and that is the answer */
 const onDown=e=>{const k=e.target.closest('#tfk');if(!k||g.lock||e.target.closest('.tfs'))return;drag={k,x:e.clientX,dx:0,id:e.pointerId};try{k.setPointerCapture(e.pointerId)}catch(_){}};
 const onMove=e=>{if(!drag||e.pointerId!==drag.id)return;drag.dx=e.clientX-drag.x;drag.k.style.transform=`translateX(${drag.dx}px) rotate(${drag.dx/24}deg)`;
  drag.k.classList.toggle('to-y',drag.dx>SWIPE);drag.k.classList.toggle('to-n',drag.dx<-SWIPE)};
 const onUp=e=>{if(!drag||e.pointerId!==drag.id)return;const d=drag;drag=null;d.k.style.transform='';d.k.classList.remove('to-y','to-n');if(Math.abs(d.dx)>SWIPE)answer(d.dx>0)};
 host.addEventListener('click',onClick);document.addEventListener('keydown',onKey);
 host.addEventListener('pointerdown',onDown);host.addEventListener('pointermove',onMove);host.addEventListener('pointerup',onUp);host.addEventListener('pointercancel',onUp);
 show();
 return{destroy(){alive=false;host.removeEventListener('click',onClick);document.removeEventListener('keydown',onKey);
  host.removeEventListener('pointerdown',onDown);host.removeEventListener('pointermove',onMove);host.removeEventListener('pointerup',onUp);host.removeEventListener('pointercancel',onUp);delete window.__lv}}}
