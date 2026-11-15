/* Level 2: catching sounds. A word is spoken from the big conch; tap the drifting bubble that carries it.
   First rounds show the written English word, later rounds show the Hebrew meaning. */
import {wordsOf,T,starsFor} from './data.js';
import {mark,say,TTS,shuffle,weakest,esc} from './state.js';
import {SND} from './audio.js';
import {SP,hud,bgMap,confetti,en,spr,sleep,stage} from './ui.js';

const CONCH=[430,975],CONCH_TOP=915;   // mouth of the conch and its highest point in the 752x1344 lagoon art

export async function start(host,cfg,api){
 const pool=wordsOf(cfg.part),ws=weakest(pool,Math.min(T.listenWords,pool.length));
 const g={i:0,miss:0,hint:0,first:0,bad:0,lock:0,wrongNow:0,results:[],tts:TTS,mode:'en'};let alive=true;
 window.__lv={kind:'listen',g,answer:()=>ws[g.i]&&ws[g.i].en};
 host.innerHTML=`<div class="lv listen"><div id="hd"></div>
  <div class="sign prompt"><small id="lt"></small><b id="lw">&nbsp;</b></div>
  <div class="bubs" id="bubs"></div>
  <button class="conchbtn" data-a="again" aria-label="להשמיע שוב" tabindex="-1"><span class="waves" aria-hidden="true"><i></i><i></i></span></button>
  <button class="btn blue replay" data-a="again"><span>${spr('ic_speaker','bi')}<b id="rl">השמיעו שוב</b></span></button></div>`;
 const bubs=host.querySelector('#bubs'),lw=host.querySelector('#lw'),lt=host.querySelector('#lt'),conch=host.querySelector('.conchbtn'),rl=host.querySelector('#rl'),sign=host.querySelector('.prompt');
 function place(){const m=bgMap('bottom'),st=stage.getBoundingClientRect(),top=sign.getBoundingClientRect().bottom-st.top+8;
  conch.style.left=(m.ox+CONCH[0]*m.s)+'px';conch.style.top=(m.oy+CONCH[1]*m.s)+'px';conch.style.width=conch.style.height=Math.max(110,210*m.s)+'px';
  bubs.style.top=top+'px';bubs.style.height=Math.max(190,m.oy+CONCH_TOP*m.s-top-6)+'px'}
 place();window.addEventListener('resize',place);
 const hudUp=()=>host.querySelector('#hd').innerHTML=hud({i:g.i,n:ws.length,st:starsFor(ws.length-g.bad,ws.length,g.hint)});
 const prompt=()=>{lt.textContent=!g.tts?'המילה מופיעה כאן לרגע. תפסו אותה!':g.mode==='en'?'הקשיבו ותפסו את המילה':'הקשיבו ותפסו את הפירוש';rl.textContent=g.tts?'השמיעו שוב':'הראו שוב'};
 async function speak(){const w=ws[g.i];if(!w||g.lock)return;conch.classList.remove('on');void conch.offsetWidth;conch.classList.add('on');
  let ok=false;if(g.tts)ok=await say(w.en);if(!alive||ws[g.i]!==w||g.lock)return;
  if(!ok){g.tts=false;prompt();lw.textContent=w.en;lw.className='en flash';await sleep(1200);if(alive&&ws[g.i]===w&&!g.lock){lw.innerHTML='&nbsp;';lw.className=''}}}
 function round(){const w=ws[g.i];g.mode=g.i<Math.ceil(ws.length/2)?'en':'he';g.wrongNow=0;g.lock=0;
  const others=shuffle(pool.filter(o=>o.en!==w.en&&o.he!==w.he)).slice(0,3),opts=shuffle([w,...others]);
  prompt();lw.innerHTML='&nbsp;';lw.className='';
  bubs.innerHTML=opts.map((o,k)=>`<button class="bub b${k} ${g.mode==='en'?'en':''}" data-w="${esc(o.en)}" style="--d:${(k*0.09).toFixed(2)}s;background-image:url(${SP('bubble_'+((k+g.i)%4))})"><span ${g.mode==='en'?'dir="ltr"':''}>${esc(g.mode==='en'?o.en:o.he)}</span><em hidden></em></button>`).join('');
  hudUp();speak()}
 function pick(el){if(g.lock||el.classList.contains('bad'))return;const w=ws[g.i],o=pool.find(p=>p.en===el.dataset.w);
  if(o.en===w.en){g.lock=1;el.classList.add('ok');SND.pop();const ok1=!g.wrongNow;if(ok1)g.first++;mark(w,ok1);g.results.push({w,ok:ok1});
   lw.className='';lw.innerHTML=`${en(w.en)} <span class="eq">=</span> ${esc(w.he)}`;const r=el.getBoundingClientRect(),s=host.getBoundingClientRect();confetti(r.left-s.left+r.width/2,r.top-s.top+r.height/2,26);
   setTimeout(()=>{if(!alive)return;g.i++;if(g.i>=ws.length){alive=false;api.done({stars:starsFor(g.first,ws.length,g.hint),first:g.first,total:ws.length,hint:g.hint,review:g.results.filter(r=>!r.ok).map(r=>r.w)})}else round()},1250)}
  else{g.miss++;if(!g.wrongNow)g.bad++;g.wrongNow++;el.classList.add('bad');SND.bad();const em=el.querySelector('em');em.textContent=g.mode==='en'?o.he.split(',')[0]:o.en;em.hidden=false;if(g.mode==='he')em.setAttribute('dir','ltr');hudUp()}}
 const onClick=e=>{const b=e.target.closest('.bub');if(b)return pick(b);if(e.target.closest('[data-a=again]')){SND.tap();speak()}};
 host.addEventListener('click',onClick);
 round();
 return{destroy(){alive=false;host.removeEventListener('click',onClick);window.removeEventListener('resize',place);delete window.__lv},
  hint(){if(g.lock)return;if(!g.hint){g.hint=1;hudUp()}const el=[...bubs.children].find(b=>b.dataset.w===ws[g.i].en);if(el)el.classList.add('hinted')}}}
