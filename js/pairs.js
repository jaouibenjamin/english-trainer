/* Extra practice: pairs. Twelve cards face down, six English words and their six Hebrew meanings. The pupil turns two:
   a word and its own meaning stay open; two that do not belong together are shown for a moment, with the right
   meaning of each written under the board, and turn back.
   - The words and meanings are the teacher's list for the island (wordsOf), exactly as written there.
   - Nothing ends early: the round ends when all six pairs are found.
   - Practice only: it calls none of the functions that keep score (no mark, no award, no stars, no save). */
import {wordsOf} from './data.js';
import {say,warm,shuffle,esc,reduced} from './state.js';
import {SND} from './audio.js';
import {rb,ico,btn,en,num,spr} from './ui.js';

const PAIRS=6,SHOW=1500;
const first=he=>he.split(',')[0];

export async function start(host,cfg,api){
 /* six words whose meanings are all different, so a meaning card can only belong to one word card */
 const seen=new Set(),ws=[];for(const w of shuffle(cfg.parts.flatMap(p=>wordsOf(p)))){if(ws.length<PAIRS&&!seen.has(first(w.he))){seen.add(first(w.he));ws.push(w)}}
 warm(ws.map(w=>w.en));
 /* a card: which word it belongs to (k), and which side of it it shows */
 const cards=shuffle(ws.flatMap((w,k)=>[{k,side:'en',text:w.en},{k,side:'he',text:first(w.he)}]));
 const g={open:[],found:new Set(),turns:0,misses:0,lock:0,n:ws.length};let alive=true,timer=0;
 window.__lv={kind:'pairs',g,cards:()=>cards.map((c,i)=>({i,k:c.k,side:c.side,text:c.text}))};
 host.innerHTML=`<section class="scr pr"><header class="top">${rb('nav',ico('back'),'חזרה',1,`data-to="island/${cfg.island.id}"`)}<h2 class="ribbon"><span>זוגות</span></h2><span class="rbsp"></span></header>
  <p class="prc" id="prc" aria-live="polite"></p>
  <div class="prg" id="prg">${cards.map((c,i)=>`<button class="prk" data-i="${i}" aria-label="כרטיס סגור"><span class="prf" aria-hidden="true">?</span><span class="prt" ${c.side==='en'?'dir="ltr" lang="en"':'dir="rtl"'}></span></button>`).join('')}</div>
  <div class="prx" id="prx" role="status" aria-live="polite"></div>
  <p class="tfn">זה תרגול: בלי כוכבים ובלי נקודות</p></section>`;
 const grid=host.querySelector('#prg'),count=host.querySelector('#prc'),note=host.querySelector('#prx'),el=i=>grid.children[i];
 const head=()=>{count.innerHTML=`${num(g.found.size)} מתוך ${num(g.n)} זוגות`};
 /* a card's text is put on it only while it is open: a closed card holds nothing to read, on screen or for a screen reader */
 const face=(i,up)=>{const b=el(i),c=cards[i];b.classList.toggle('up',up);b.querySelector('.prt').textContent=up?c.text:'';b.setAttribute('aria-label',up?c.text:'כרטיס סגור')};
 function turn(i){if(!alive||g.lock||g.found.has(cards[i].k)||g.open.includes(i))return;
  const c=cards[i];face(i,true);g.open.push(i);if(c.side==='en')say(c.text);
  if(g.open.length<2){SND.tap();note.textContent='';return}
  g.turns++;const [a,b]=g.open,A=cards[a],B=cards[b];
  if(A.k===B.k){SND.pop();g.found.add(A.k);g.open=[];el(a).classList.add('ok');el(b).classList.add('ok');
   /* a found pair is disabled; a keyboard user's focus moves on to the next open card instead of dropping to the page */
   const kb=grid.contains(document.activeElement);el(a).disabled=el(b).disabled=true;head();
   if(kb)for(let d=1;d<cards.length;d++){const j=(b+d)%cards.length;if(!g.found.has(cards[j].k)){el(j).focus({preventScroll:true});break}}
   note.innerHTML=`<p class="tfr ok">${en(ws[A.k].en)} <span>=</span> ${esc(first(ws[A.k].he))}</p>`;
   if(g.found.size===g.n){alive=false;timer=setTimeout(end,900)}}
  else{SND.bad();g.misses++;g.lock=1;el(a).classList.add('no');el(b).classList.add('no');
   /* explain: each of the two cards that were turned, with its own pair */
   note.innerHTML=[A,B].map(x=>`<p class="tfr two">${en(ws[x.k].en)} <span>=</span> ${esc(first(ws[x.k].he))}</p>`).join('');
   timer=setTimeout(()=>{if(!host.isConnected)return;for(const j of [a,b]){face(j,false);el(j).classList.remove('no')}g.open=[];g.lock=0},reduced()?SHOW+500:SHOW)}}
 function end(){SND.win();count.innerHTML='';note.innerHTML='';const kb=grid.contains(document.activeElement)||document.activeElement===document.body;
  grid.outerHTML=`<div class="tfend">${spr('crab_happy','bob')}<h3>מצאתם את כל הזוגות!</h3>
    <p>${num(g.turns)} ניסיונות</p>
    <div class="tfrev">${ws.map(w=>`<span>${en(w.en)} · ${esc(first(w.he))}</span>`).join('')}</div>
    <div class="tfeb">${btn('nav','עוד סיבוב','green',`data-to="extra/${cfg.island.id}/pairs" data-force="1"`)}${btn('nav','לשלבים','cream',`data-to="island/${cfg.island.id}"`)}</div></div>`;
  if(kb){const nx=host.querySelector('.tfend [data-force]');if(nx)nx.focus({preventScroll:true})}   // the keyboard carries on from "another round"
  window.__lv.ended={turns:g.turns,misses:g.misses,n:g.n}}
 const onClick=e=>{const b=e.target.closest('.prk');if(b)turn(+b.dataset.i)};
 host.addEventListener('click',onClick);head();
 return{destroy(){alive=false;clearTimeout(timer);host.removeEventListener('click',onClick);delete window.__lv}}}
