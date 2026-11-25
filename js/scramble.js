/* Extra practice: letters. The Hebrew meaning is shown and the English word is heard; its letters lie mixed up as
   tiles. The pupil taps them in order (or types them on a keyboard) to build the word.
   - The words and meanings are the teacher's list for the island (wordsOf), exactly as written there. Only single
     words of 3 to 9 letters are used, so every tile is a letter.
   - A wrong letter is not placed: the tile shakes and the line under the word says which letter comes next is not
     that one. After two wrong letters in a row the right tile glows. A word with any wrong letter comes back once,
     later in the round. Nothing ends early.
   - Practice only: it calls none of the functions that keep score (no mark, no award, no stars, no save). */
import {wordsOf} from './data.js';
import {say,warm,shuffle,esc,reduced} from './state.js';
import {SND} from './audio.js';
import {rb,ico,btn,en,num,spr} from './ui.js';

const ROUND=6;
const first=he=>he.split(',')[0];
const OK=/^[A-Za-z]{3,9}$/;

/* the letters of a word, mixed so that they never already spell it */
/* tiles are lower case: in the game's font a capital I and a small l look the same. The word fills in with its own
   capitals as it is built. */
function mixOf(w){const a=[...w.toLowerCase()];if(new Set(a.map(c=>c.toLowerCase())).size<2)return a;let m;do{m=shuffle(a)}while(m.join('').toLowerCase()===w.toLowerCase());return m}

export async function start(host,cfg,api){
 const pool=cfg.parts.flatMap(p=>wordsOf(p)).filter(w=>OK.test(w.en)),ws=shuffle(pool).slice(0,Math.min(ROUND,pool.length));
 warm(ws.map(w=>w.en));
 const g={queue:ws.map(w=>({w,again:false})),done:0,first:0,missed:new Set(),pos:0,wrongRow:0,lock:0,n:ws.length,tiles:[]};let alive=true,timer=0;
 window.__lv={kind:'scramble',g,word:()=>g.queue[0]&&g.queue[0].w.en,tiles:()=>g.tiles.map((t,i)=>({i,ch:t.ch,used:t.used}))};
 host.innerHTML=`<section class="scr sc"><header class="top">${rb('nav',ico('back'),'חזרה',1,`data-to="island/${cfg.island.id}"`)}<h2 class="ribbon"><span>אותיות</span></h2><span class="rbsp"></span></header>
  <p class="tfc" id="scc" aria-live="polite"></p>
  <div class="tfa" id="sca"></div>
  <p class="tfn">זה תרגול: בלי כוכבים ובלי נקודות</p></section>`;
 const area=host.querySelector('#sca'),count=host.querySelector('#scc');
 const speak=()=>{const c=g.queue[0];if(c)say(c.w.en)};
 function show(){const c=g.queue[0],w=c.w.en;g.pos=0;g.wrongRow=0;g.lock=0;g.tiles=mixOf(w).map(ch=>({ch,used:false}));
  count.innerHTML=`${num(g.done)} מתוך ${num(g.n)} מילים`;
  area.innerHTML=`<div class="tfk sck"><button class="tfs" data-t="say" aria-label="השמיעו את המילה">${spr('ic_speaker','')}</button>
    <span class="tfq">איך כותבים באנגלית</span><span class="tfhq"><b class="tfh">${esc(first(c.w.he))}</b><span class="tfq">?</span></span>
    <p class="scw" dir="ltr" lang="en" aria-label="המילה עד עכשיו">${[...w].map(()=>'<i></i>').join('')}</p></div>
   <div class="sct" dir="ltr">${g.tiles.map((t,i)=>`<button class="scl" data-l="${i}" lang="en" aria-label="${esc(t.ch)}">${esc(t.ch)}</button>`).join('')}</div>
   <p class="scm" id="scm" role="status" aria-live="polite"></p>`;
  speak()}
 function pick(i){const c=g.queue[0];if(!c||g.lock||!alive)return;const t=g.tiles[i];if(!t||t.used)return;
  const w=c.w.en,want=w[g.pos],tile=area.querySelector(`[data-l="${i}"]`),msg=area.querySelector('#scm');
  if(t.ch.toLowerCase()===want.toLowerCase()){t.used=true;tile.disabled=true;tile.classList.add('used');
   const slot=area.querySelectorAll('.scw i')[g.pos];slot.textContent=want;slot.classList.add('on');g.pos++;g.wrongRow=0;msg.textContent='';SND.tap();
   for(const b of area.querySelectorAll('.scl.glow'))b.classList.remove('glow');
   if(g.pos===w.length)return solved(c)}
  else{SND.bad();g.wrongRow++;g.missed.add(w);c.wrong=true;
   if(!reduced()){tile.classList.remove('shake');void tile.offsetWidth;tile.classList.add('shake')}
   msg.innerHTML=`האות הבאה היא לא ${en(t.ch)}`;
   /* two wrong letters in a row: the right tile glows */
   if(g.wrongRow>=2){const j=g.tiles.findIndex(x=>!x.used&&x.ch.toLowerCase()===want.toLowerCase());const b=area.querySelector(`[data-l="${j}"]`);if(b)b.classList.add('glow')}}}
 function solved(c){g.lock=1;SND.pop();const w=c.w;
  if(!c.wrong&&!c.again)g.first++;
  g.queue.shift();
  if(c.wrong&&!c.again)g.queue.push({w,again:true});else g.done++;   // a word with a wrong letter comes back once
  area.querySelector('.sck').classList.add('ok');
  area.querySelector('.sct').innerHTML=`<p class="tfr ok">${en(w.en)} <span>=</span> ${esc(first(w.he))}</p>`;
  area.querySelector('#scm').textContent=c.wrong&&!c.again?'המילה תחזור עוד מעט':'';
  say(w.en);
  timer=setTimeout(()=>{if(!alive)return;if(g.queue.length)show();else end()},1400)}
 function end(){alive=false;SND.win();count.innerHTML='';const miss=ws.filter(w=>g.missed.has(w.en));
  area.innerHTML=`<div class="tfend">${spr('crab_happy','bob')}<h3>סיימתם את הסיבוב!</h3>
    <p>${num(g.first)} מתוך ${num(g.n)} בלי טעות</p>
    ${miss.length?`<div class="tfrev"><small>כדאי לחזור על</small>${miss.slice(0,4).map(w=>`<span>${en(w.en)} · ${esc(first(w.he))}</span>`).join('')}</div>`:'<p class="tfm">בלי אף טעות!</p>'}
    <div class="tfeb">${btn('nav','עוד סיבוב','green',`data-to="extra/${cfg.island.id}/scramble" data-force="1"`)}${btn('nav','לשלבים','cream',`data-to="island/${cfg.island.id}"`)}</div></div>`;
  window.__lv.ended={first:g.first,n:g.n,missed:[...g.missed]}}
 const onClick=e=>{const t=e.target.closest('[data-t=say]');if(t){SND.tap();return speak()}const l=e.target.closest('.scl');if(l)pick(+l.dataset.l)};
 /* a keyboard: typing a letter takes the first unused tile with that letter */
 const onKey=e=>{if(!alive||g.lock||e.ctrlKey||e.metaKey||e.altKey||e.target.closest('input,textarea')||!/^[a-z]$/i.test(e.key))return;
  let i=g.tiles.findIndex(x=>!x.used&&x.ch.toLowerCase()===e.key.toLowerCase());
  if(i<0)return;   // a letter that is not among the tiles: nothing to press
  e.preventDefault();pick(i)};
 host.addEventListener('click',onClick);document.addEventListener('keydown',onKey);
 show();
 return{destroy(){alive=false;clearTimeout(timer);host.removeEventListener('click',onClick);document.removeEventListener('keydown',onKey);delete window.__lv}}}
