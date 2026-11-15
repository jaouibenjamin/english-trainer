/* Level 2: catching sounds. A word is spoken from the big conch; tap the drifting bubble that carries it.
   First rounds show the written English word, later rounds show the Hebrew meaning. */
import {wordsOf,T,starsFor} from './data.js';
import {S,mark,say,TTS,shuffle,weakest,esc,save} from './state.js';
import {SND} from './audio.js';
import {SP,hud,bgMap,confetti,en,ico,sleep} from './ui.js';

export async function start(host,cfg,api){
 const pool=wordsOf(cfg.part),ws=weakest(pool,Math.min(T.listenWords,pool.length));
 const g={i:0,miss:0,hint:0,first:0,lock:0,wrongNow:0,results:[],tts:TTS,mode:'en'};let alive=true;
 window.__lv={kind:'listen',g,answer:()=>ws[g.i]&&ws[g.i].en};
 host.innerHTML=`<div class="lv listen"><div id="hd"></div>
  <div class="sign prompt"><small id="lt"></small><b id="lw">&nbsp;</b></div>
  <div class="bubs" id="bubs"></div>
  <button class="conchbtn" data-a="again" aria-label="להשמיע שוב"><span class="waves" aria-hidden="true"><i></i><i></i><i></i></span><span class="again label">${ico('sound')} שוב</span></button>
  <p class="note label" id="note" hidden>בדפדפן הזה אין הקראה קולית, אז המילה מוצגת לרגע על השלט.</p></div>`;
 const bubs=host.querySelector('#bubs'),lw=host.querySelector('#lw'),lt=host.querySelector('#lt'),conch=host.querySelector('.conchbtn'),note=host.querySelector('#note');
 function place(){const m=bgMap('bottom');conch.style.left=(m.ox+430*m.s)+'px';conch.style.top=(m.oy+985*m.s)+'px';conch.style.width=conch.style.height=Math.max(120,250*m.s)+'px'}
 place();window.addEventListener('resize',place);
 const hudUp=()=>host.querySelector('#hd').innerHTML=hud({i:g.i,n:ws.length,st:starsFor(g.miss,g.hint,T.starListen)});
 async function speak(){const w=ws[g.i];if(!w)return;conch.classList.add('on');setTimeout(()=>conch.classList.remove('on'),900);
  let ok=false;if(g.tts)ok=await say(w.en);if(!alive||ws[g.i]!==w)return;
  if(!ok){g.tts=false;note.hidden=false;lw.textContent=w.en;lw.classList.add('en','flash');await sleep(1300);if(alive&&ws[g.i]===w&&!g.lock){lw.innerHTML='&nbsp;';lw.classList.remove('flash')}}}
 function round(){const w=ws[g.i];g.mode=g.i<Math.ceil(ws.length/2)?'en':'he';g.wrongNow=0;g.lock=0;
  const others=shuffle(pool.filter(o=>o.en!==w.en&&o.he!==w.he)).slice(0,3),opts=shuffle([w,...others]);
  lt.textContent=g.mode==='en'?'הקשיבו ותפסו את המילה':'הקשיבו ותפסו את הפירוש';lw.innerHTML='&nbsp;';lw.className='';
  bubs.innerHTML=opts.map((o,k)=>`<button class="bub b${k} ${g.mode==='en'?'en':''}" data-w="${esc(o.en)}" style="--d:${(k*0.09).toFixed(2)}s;background-image:url(${SP('bubble_'+((k+g.i)%4))})" ${g.mode==='en'?'dir="ltr"':''}><span>${esc(g.mode==='en'?o.en:o.he)}</span><em hidden></em></button>`).join('');
  hudUp();speak()}
 function pick(el){if(g.lock||el.classList.contains('bad'))return;const w=ws[g.i],o=pool.find(p=>p.en===el.dataset.w);
  if(o.en===w.en){g.lock=1;el.classList.add('ok');SND.pop();const first=!g.wrongNow;if(first)g.first++;mark(w,first);g.results.push({w,ok:first});
   lw.className='';lw.innerHTML=`${en(w.en)} <span class="eq">=</span> ${esc(w.he)}`;const r=el.getBoundingClientRect(),s=host.getBoundingClientRect();confetti(r.left-s.left+r.width/2,r.top-s.top+r.height/2,26);
   setTimeout(()=>{if(!alive)return;g.i++;if(g.i>=ws.length){alive=false;api.done({stars:starsFor(g.miss,g.hint,T.starListen),first:g.first,total:ws.length,miss:g.miss,hint:g.hint,review:g.results.filter(r=>!r.ok).map(r=>r.w)})}else round()},1250)}
  else{g.miss++;g.wrongNow++;el.classList.add('bad');SND.bad();const em=el.querySelector('em');em.textContent=g.mode==='en'?o.he.split(',')[0]:o.en;em.hidden=false;if(g.mode==='he')em.setAttribute('dir','ltr');hudUp()}}
 const onClick=e=>{const b=e.target.closest('.bub');if(b)return pick(b);if(e.target.closest('[data-a=again]')){SND.tap();speak()}};
 host.addEventListener('click',onClick);
 round();
 return{destroy(){alive=false;host.removeEventListener('click',onClick);window.removeEventListener('resize',place);delete window.__lv},
  hint(){if(g.lock)return;if(!g.hint){g.hint=1;hudUp()}const el=[...bubs.children].find(b=>b.dataset.w===ws[g.i].en);if(el)el.classList.add('glow')}}}
