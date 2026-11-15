/* Level 4: the sentence bridge. Lay the word planks in order and the crab walks across.
   A wrong plank snaps and drops back; the planks already laid stay. am / is / are rounds fill one missing plank. */
import {SENT,TOBE_BY,T,starsFor} from './data.js';
import {S,award,say,shuffle,esc,save} from './state.js';
import {SND} from './audio.js';
import {SP,hud,bgMap,confetti,toast,spr,en} from './ui.js';

const toks=s=>s.replace(/([.!?])$/,' $1').split(/\s+/);
const GAP=[152,662],TOPY=676;   // inner cliff edges and cliff-top height in the 752x1344 bridge art

export async function start(host,cfg,api){
 const builds=shuffle(SENT[cfg.part]).slice(0,T.bridgeBuild),tobes=shuffle(TOBE_BY[cfg.part]).slice(0,T.bridgeTobe),rounds=[];
 for(let i=0;i<Math.max(builds.length,tobes.length);i++){if(builds[i])rounds.push({kind:'build',en:builds[i][0],he:builds[i][1]});if(tobes[i])rounds.push({kind:'tobe',en:tobes[i][0].replace('___',tobes[i][1]),gap:tobes[i][1],raw:tobes[i][0]})}
 const g={i:0,miss:0,hint:0,first:0,wrongNow:0,lock:0,r:null,placed:0};let alive=true;
 window.__lv={kind:'bridge',g,next:()=>g.r&&(g.r.kind==='tobe'?g.r.gap:g.r.t[g.placed])};
 host.innerHTML=`<div class="lv bridge"><div id="hd"></div>
  <div class="sign prompt"><small id="bt"></small><b id="bh"></b></div>
  <div class="chips" id="chips"><span class="chip" id="c1">${spr('star_off','ci')}אות גדולה בהתחלה</span><span class="chip" id="c2">${spr('star_off','ci')}נקודה בסוף</span></div>
  <div class="echo label en" id="echo" dir="ltr"></div>
  <div class="span" id="span" dir="ltr"></div>
  <img class="walker" id="walker" src="${SP('crab_walk')}" alt="" draggable="false">
  <div class="bank" id="bank" dir="ltr"></div></div>`;
 const span=host.querySelector('#span'),bank=host.querySelector('#bank'),walker=host.querySelector('#walker'),bt=host.querySelector('#bt'),bh=host.querySelector('#bh'),c1=host.querySelector('#c1'),c2=host.querySelector('#c2'),echo=host.querySelector('#echo');
 let M=bgMap('width');
 function place(){M=bgMap('width');span.style.left=(M.ox+GAP[0]*M.s-4)+'px';span.style.width=((GAP[1]-GAP[0])*M.s+8)+'px';span.style.top=(M.oy+TOPY*M.s-8)+'px';
  echo.style.top=(M.oy+TOPY*M.s-(M.H<700?128:150))+'px';walkTo(g.walk??-1,true)}
 function walkTo(k,instant){g.walk=k;const n=g.r?g.r.t.length:1,sl=span.children[k];let cx;
  if(k<0)cx=M.ox+(GAP[0]-58)*M.s;else if(k>=n)cx=M.ox+(GAP[1]+52)*M.s;else if(sl)cx=span.offsetLeft+sl.offsetLeft+sl.offsetWidth/2;else cx=M.ox+GAP[0]*M.s;
  walker.style.transition=instant?'none':'';walker.style.left=cx+'px';walker.style.top=(M.oy+TOPY*M.s-4)+'px'}
 const hudUp=()=>host.querySelector('#hd').innerHTML=hud({i:g.i,n:rounds.length,st:starsFor(g.miss,g.hint,T.starBridge)});
 const chip=(el,on)=>{el.classList.toggle('on',on);el.querySelector('img').src=SP(on?'star':'star_off')};
 function round(){const r=g.r=rounds[g.i];r.t=toks(r.en);g.wrongNow=0;g.lock=0;walker.src=SP('crab_walk');walker.classList.remove('hop');
  const total=r.t.reduce((a,t)=>a+t.length+1.6,0);
  if(r.kind==='build'){g.placed=0;bt.textContent='בנו את המשפט באנגלית';bh.textContent=r.he;bh.className='';bh.removeAttribute('dir');
   span.innerHTML=r.t.map((t,k)=>`<span class="slot" style="flex:${((t.length+1.6)/total).toFixed(3)}"></span>`).join('');
   const order=shuffle(r.t.map((t,k)=>k));bank.innerHTML=order.map(k=>`<button class="pl p${k%5}" data-t="${esc(r.t[k])}" data-k="${k}">${esc(r.t[k])}</button>`).join('');chip(c1,false);chip(c2,false)}
  else{g.placed=r.t.indexOf(r.gap);bt.textContent='איזו מילה חסרה? am / is / are';bh.innerHTML=esc(r.raw).replace('___','<u>?</u>');bh.className='en';bh.setAttribute('dir','ltr');
   span.innerHTML=r.t.map((t,k)=>k===g.placed?`<span class="slot gap" style="flex:${((t.length+1.6)/total).toFixed(3)}"></span>`:`<span class="slot f p${k%5}" style="flex:${((t.length+1.6)/total).toFixed(3)}"><i>${esc(t)}</i></span>`).join('');
   bank.innerHTML=['am','is','are'].map((t,k)=>`<button class="pl big p${k+1}" data-t="${t}">${t}</button>`).join('');chip(c1,true);chip(c2,true)}
  hudUp();place();walkTo(-1,true);echoUp()}
 function echoUp(){const r=g.r;echo.innerHTML=r.t.map((t,k)=>{const shown=r.kind==='tobe'?k!==g.placed||g.lock:k<g.placed;return shown?(t==='.'?'<b class="dot">.</b>':`<b>${esc(t)}</b>`):(t==='.'?'<i class="dot">.</i>':`<i>${'_'.repeat(Math.max(2,Math.min(5,t.length)))}</i>`)}).join(' ').replace(/ (<[bi] class="dot">)/g,'$1')}
 function fill(k,t){const sl=span.children[k];sl.className=`slot f p${k%5} in`;sl.innerHTML=`<i>${esc(t)}</i>`}
 function done(){const r=g.r;g.lock=1;echoUp();const first=!g.wrongNow;if(first)g.first++;award(first?T.ptsFirst:T.ptsLater);
  setTimeout(()=>{if(!alive)return;walkTo(r.t.length);SND.step()},r.kind==='tobe'?350:250);
  setTimeout(()=>{if(!alive)return;walker.src=SP('crab_happy');walker.classList.add('hop');SND.pop();say(r.en);const b=walker.getBoundingClientRect(),s=host.getBoundingClientRect();confetti(b.left-s.left+b.width/2,b.top-s.top,26);
   bh.className='en';bh.setAttribute('dir','ltr');bh.textContent=r.en},900);
  setTimeout(()=>{if(!alive)return;g.i++;if(g.i>=rounds.length){alive=false;api.done({stars:starsFor(g.miss,g.hint,T.starBridge),first:g.first,total:rounds.length,miss:g.miss,hint:g.hint,review:[]})}else round()},2500)}
 function wrong(el){g.miss++;g.wrongNow++;SND.snap();el.classList.add('snap');walker.src=SP('crab_oops');hudUp();
  setTimeout(()=>{el.classList.remove('snap');if(alive&&!g.lock)walker.src=SP('crab_walk')},800);
  if(g.r.kind==='tobe')toast('<span class="en" dir="ltr">I am · he / she / it is · we / you / they are</span>',3200);
  else if(g.placed===0)toast('משפט מתחיל באות גדולה');else if(g.placed===g.r.t.length-1)toast('בסוף המשפט שמים נקודה')}
 function pick(el){if(g.lock||el.classList.contains('used')||el.classList.contains('snap'))return;const r=g.r,t=el.dataset.t;
  if(r.kind==='tobe'){if(t!==r.gap)return wrong(el);el.classList.add('used');SND.plank();fill(g.placed,t);walkTo(0);return done()}
  if(t!==r.t[g.placed])return wrong(el);
  el.classList.add('used');SND.plank();fill(g.placed,t);walkTo(g.placed);if(g.placed===0)chip(c1,true);g.placed++;echoUp();
  if(g.placed>=r.t.length){chip(c2,true);done()}}
 const onClick=e=>{const p=e.target.closest('.pl');if(p)pick(p)};
 host.addEventListener('click',onClick);window.addEventListener('resize',place);
 round();
 return{destroy(){alive=false;host.removeEventListener('click',onClick);window.removeEventListener('resize',place);delete window.__lv},
  hint(){if(g.lock)return;if(!g.hint){g.hint=1;hudUp()}const want=g.r.kind==='tobe'?g.r.gap:g.r.t[g.placed];const el=[...bank.children].find(b=>!b.classList.contains('used')&&b.dataset.t===want);if(el){el.classList.add('glow');setTimeout(()=>el.classList.remove('glow'),1600)}}}}
