/* Level 2: catching sounds. The word is only heard, never printed: tap the drifting bubble that carries it.
   First rounds show the written English words, later rounds show Hebrew meanings.
   If the device cannot speak (no recorded clip reachable and no browser voice), the level says so and flashes the word on the sign instead ("show again"). */
import {wordsOf,T,starsFor} from './data.js';
import {mark,say,warm,ready,TTS,shuffle,weakest,esc} from './state.js';
import {SND} from './audio.js';
import {SP,hud,bgMap,confetti,en,spr,ico,sleep,stage} from './ui.js';

const SHORE=1120;   // in the 752x1344 lagoon art the sand with the little shells starts below this row

export async function start(host,cfg,api){
 const pool=wordsOf(cfg.part),ws=weakest(pool,Math.min(T.listenWords,pool.length));
 /* the words are fetched and decoded before the level shows: it opens when the first word is ready to be spoken (or after 3 s) */
 warm(ws.map(w=>w.en));await ready(ws[0].en);
 const g={i:0,miss:0,hint:0,first:0,bad:0,lock:0,wrongNow:0,results:[],tts:TTS,mode:'en',said:0};let alive=true,onT=0;
 window.__lv={kind:'listen',g,answer:()=>ws[g.i]&&ws[g.i].en,t:performance.now()};
 host.innerHTML=`<div class="lv listen"><div id="hd"></div>
  <div class="sign prompt"><small id="lt"></small>
   <button class="btn blue spk" id="spk" data-a="again"><span>${spr('ic_speaker','bi')}${ico('eye','eye')}<em id="rl"></em><i class="eqz" aria-hidden="true"><i></i><i></i><i></i><i></i></i></span></button>
   <b id="lw" hidden></b></div>
  <div class="bubs" id="bubs"></div></div>`;
 const bubs=host.querySelector('#bubs'),lw=host.querySelector('#lw'),lt=host.querySelector('#lt'),spk=host.querySelector('#spk'),rl=host.querySelector('#rl'),sign=host.querySelector('.prompt');
 /* the four bubbles fill the sky between the sign and the shore, centred as one group */
 function place(){const m=bgMap('bottom'),st=stage.getBoundingClientRect(),top=sign.getBoundingClientRect().bottom-st.top+10,bot=Math.min(m.H-14,m.oy+SHORE*m.s),
   bh=bubs.clientWidth*.38*308/300,h=Math.max(bh*2+10,Math.min(bot-top,bh*2+64));
  bubs.style.height=h+'px';bubs.style.top=Math.max(top,top+(bot-top-h)/2)+'px'}
 window.addEventListener('resize',place);
 const hudUp=()=>host.querySelector('#hd').innerHTML=hud({i:g.i,n:ws.length,st:starsFor(ws.length-g.bad,ws.length,g.hint),hint:g.hint});
 /* sign, button and bubbles always tell the same story */
 const prompt=()=>{lt.textContent=g.tts?(g.mode==='en'?'הקשיבו ולחצו על המילה':'הקשיבו ולחצו על הפירוש'):('אין קול במכשיר הזה. המילה תופיע לרגע: זכרו אותה ולחצו '+(g.mode==='en'?'עליה':'על הפירוש שלה'));
  rl.textContent=g.tts?'השמיעו שוב':'הראו שוב';spk.classList.toggle('nov',!g.tts);sign.classList.toggle('nov',!g.tts);spk.setAttribute('aria-label',rl.textContent)};
 const showWord=html=>{lw.innerHTML=html;lw.hidden=false;spk.hidden=true};
 const showBtn=()=>{lw.hidden=true;spk.hidden=false};
 async function speak(){const w=ws[g.i];if(!w||g.lock)return;
  let ok=false;
  if(g.tts){clearTimeout(onT);spk.classList.remove('on');void spk.offsetWidth;spk.classList.add('on');onT=setTimeout(()=>spk.classList.remove('on'),1300);
   ok=await say(w.en);if(ok)g.said++;if(!alive||ws[g.i]!==w||g.lock)return}
  if(!ok){   // no voice on this device: be honest about it and show the word for a moment instead
   if(g.tts){g.tts=false;spk.classList.remove('on');prompt();place()}   // the sign itself now states the task
   showWord(en(w.en));lw.className='flash';await sleep(1300);if(alive&&ws[g.i]===w&&!g.lock)showBtn()}}
 function round(){const w=ws[g.i];g.mode=g.i<Math.ceil(ws.length/2)?'en':'he';g.wrongNow=0;g.lock=0;
  const others=shuffle(pool.filter(o=>o.en!==w.en&&o.he!==w.he)).slice(0,3),opts=shuffle([w,...others]);
  prompt();showBtn();
  bubs.innerHTML=opts.map((o,k)=>`<button class="bub b${k} ${g.mode==='en'?'en':''}" data-w="${esc(o.en)}" style="--d:${(k*0.09).toFixed(2)}s;background-image:url(${SP('bubble_'+((k+g.i)%4))})"><span ${g.mode==='en'?'dir="ltr"':''}>${esc(g.mode==='en'?o.en:o.he)}</span><em hidden></em></button>`).join('');
  hudUp();place();
  /* the very first word waits a quarter of a second, so the sound output is awake and the pupil is looking */
  if(g.i||g.said)speak();else sleep(250).then(()=>{if(alive&&!g.i&&!g.said)speak()})}
 function pick(el){if(g.lock||el.classList.contains('bad'))return;const w=ws[g.i],o=pool.find(p=>p.en===el.dataset.w);
  if(o.en===w.en){g.lock=1;el.classList.add('ok');SND.pop();const ok1=!g.wrongNow;if(ok1)g.first++;mark(w,ok1);g.results.push({w,ok:ok1});
   lw.className='';showWord(`${en(w.en)} <span class="eq">=</span> ${esc(w.he.split(',')[0])}`);const r=el.getBoundingClientRect(),s=host.getBoundingClientRect();confetti(r.left-s.left+r.width/2,r.top-s.top+r.height/2,26);
   setTimeout(()=>{if(!alive)return;g.i++;if(g.i>=ws.length){alive=false;api.done({stars:starsFor(g.first,ws.length,g.hint),first:g.first,total:ws.length,hint:g.hint,review:g.results.filter(r=>!r.ok).map(r=>r.w)})}else round()},1250)}
  else{g.miss++;if(!g.wrongNow)g.bad++;g.wrongNow++;el.classList.add('bad');SND.bad();const em=el.querySelector('em');em.textContent=g.mode==='en'?o.he.split(',')[0]:o.en;em.hidden=false;if(g.mode==='he')em.setAttribute('dir','ltr');hudUp()}}
 const onClick=e=>{const b=e.target.closest('.bub');if(b)return pick(b);if(e.target.closest('[data-a=again]')){SND.tap();speak()}};
 host.addEventListener('click',onClick);
 round();
 return{destroy(){alive=false;clearTimeout(onT);host.removeEventListener('click',onClick);window.removeEventListener('resize',place);delete window.__lv},
  hint(){if(g.lock)return;const isNew=!g.hint;if(isNew){g.hint=1;hudUp()}const el=[...bubs.children].find(b=>b.dataset.w===ws[g.i].en);if(el)el.classList.add('hinted');return isNew}}}
