/* Level 4: the sentence bridge. Lay the word planks in order and the crab walks across.
   A wrong plank snaps and drops back; the planks already laid stay. am / is / are rounds fill one missing plank. */
import {SENT,TOBE_BY,T,starsFor} from './data.js';
import {award,say,shuffle,esc} from './state.js';
import {SND} from './audio.js';
import {SP,hud,bgMap,confetti,en,stage} from './ui.js';

const toks=s=>s.replace(/([.!?])$/,' $1').split(/\s+/);
const GAP=[122,632],TOPY=882;   // inner cliff edges and cliff-top height in the 752x1344 bridge art
const RULE='אות גדולה בהתחלה, נקודה בסוף';

export async function start(host,cfg,api){
 const builds=shuffle(SENT[cfg.part]).slice(0,T.bridgeBuild),tobes=shuffle(TOBE_BY[cfg.part]).slice(0,T.bridgeTobe),rounds=[];
 for(let i=0;i<Math.max(builds.length,tobes.length);i++){if(builds[i])rounds.push({kind:'build',en:builds[i][0],he:builds[i][1]});if(tobes[i])rounds.push({kind:'tobe',en:tobes[i][0].replace('___',tobes[i][1]),gap:tobes[i][1],raw:tobes[i][0]})}
 const g={i:0,miss:0,hint:0,first:0,bad:0,wrongNow:0,lock:0,r:null,placed:0},n=rounds.length;let alive=true,ruleT=0;
 window.__lv={kind:'bridge',g,next:()=>g.r&&(g.r.kind==='tobe'?g.r.gap:g.r.t[g.placed])};
 host.innerHTML=`<div class="lv bridge"><div id="hd"></div>
  <div class="sign prompt"><small id="bt"></small><b id="bh"></b></div>
  <p class="rule" id="rule"></p>
  <div class="bank" id="bank" dir="ltr"></div>
  <div class="span" id="span" dir="ltr"></div>
  <img class="walker" id="walker" src="${SP('crab_walk')}" alt="" draggable="false"></div>`;
 const span=host.querySelector('#span'),bank=host.querySelector('#bank'),walker=host.querySelector('#walker'),bt=host.querySelector('#bt'),bh=host.querySelector('#bh'),rule=host.querySelector('#rule');
 let M=bgMap('bridge');
 function place(){M=bgMap('bridge');const st=stage.getBoundingClientRect(),top=M.oy+TOPY*M.s,gw=(GAP[1]-GAP[0])*M.s;
  span.style.left=(M.ox+GAP[0]*M.s)+'px';span.style.width=gw+'px';span.style.top=(top-10)+'px';
  const rb=rule.getBoundingClientRect().bottom-st.top;bank.style.top=(rb+6)+'px';bank.style.height=Math.max(120,top-96-rb-6)+'px';
  if(g.r){const chars=g.r.t.reduce((a,t)=>a+t.length,0);span.style.setProperty('--fs',Math.max(13,Math.min(20,gw/(chars*.6+g.r.t.length*1.25)))+'px')}
  walkTo(g.walk??-1,true)}
 function walkTo(k,instant){g.walk=k;const cnt=g.r?g.r.t.length:1,sl=span.children[k];let cx;
  if(k<0)cx=M.ox+(GAP[0]-58)*M.s;else if(k>=cnt)cx=M.ox+(GAP[1]+50)*M.s;else if(sl)cx=span.offsetLeft+sl.offsetLeft+sl.offsetWidth/2;else cx=M.ox+GAP[0]*M.s;
  cx=Math.max(36,Math.min(M.W-36,cx));walker.style.transition=instant?'none':'';walker.style.left=cx+'px';walker.style.top=(M.oy+TOPY*M.s-6)+'px'}
 const hudUp=()=>host.querySelector('#hd').innerHTML=hud({i:g.i,n,st:starsFor(n-g.bad,n,g.hint)});
 function say1(text,cls,ms){clearTimeout(ruleT);rule.textContent=text;rule.className='rule '+(cls||'');if(ms)ruleT=setTimeout(()=>{if(alive&&!g.lock)say1(g.r.kind==='tobe'?'':RULE)},ms)}
 function round(){const r=g.r=rounds[g.i];r.t=toks(r.en);g.wrongNow=0;g.lock=0;walker.src=SP('crab_walk');walker.classList.remove('hop');bank.classList.remove('gone');
  const total=r.t.reduce((a,t)=>a+t.length+1.25/.6,0),fx=t=>((t.length+1.25/.6)/total).toFixed(3);
  if(r.kind==='build'){g.placed=0;bt.textContent='בנו את המשפט באנגלית';bh.textContent=r.he;bh.className='';bh.removeAttribute('dir');
   span.innerHTML=r.t.map(t=>`<span class="slot" style="flex:${fx(t)}"></span>`).join('');
   const order=shuffle(r.t.map((t,k)=>k));bank.className='bank n'+r.t.length;bank.innerHTML=order.map(k=>`<button class="pl p${k%5}" data-t="${esc(r.t[k])}">${esc(r.t[k])}</button>`).join('');say1(RULE)}
  else{g.placed=r.t.indexOf(r.gap);bt.innerHTML=`איזו מילה חסרה? ${en('am / is / are')}`;bh.innerHTML=esc(r.raw).replace('___','<u>?</u>');bh.className='en';bh.setAttribute('dir','ltr');
   span.innerHTML=r.t.map((t,k)=>k===g.placed?`<span class="slot gap" style="flex:${fx(t)}"></span>`:`<span class="slot f p${k%5}" style="flex:${fx(t)}"><i>${esc(t)}</i></span>`).join('');
   bank.className='bank tobe';bank.innerHTML=['am','is','are'].map((t,k)=>`<button class="pl big p${k+1}" data-t="${t}">${t}</button>`).join('');say1('')}
  hudUp();place();walkTo(-1,true)}
 function fill(k,t){const sl=span.children[k];sl.className=`slot f p${k%5} in`;sl.innerHTML=`<i>${esc(t)}</i>`}
 function done(){const r=g.r;g.lock=1;const ok1=!g.wrongNow;if(ok1)g.first++;award(ok1?T.ptsFirst:T.ptsLater);clearTimeout(ruleT);
  bank.classList.add('gone');
  if(r.kind==='tobe')bh.innerHTML=esc(r.raw).replace('___',`<u class="ok">${esc(r.gap)}</u>`);else{bh.className='en';bh.setAttribute('dir','ltr');bh.textContent=r.en}
  say1('יופי! המשפט שלם','good');
  setTimeout(()=>{if(!alive)return;walkTo(r.t.length);SND.step()},300);
  setTimeout(()=>{if(!alive)return;walker.src=SP('crab_happy');walker.classList.add('hop');SND.pop();say(r.en);const b=walker.getBoundingClientRect(),s=host.getBoundingClientRect();confetti(b.left-s.left+b.width/2,b.top-s.top,26)},900);
  setTimeout(()=>{if(!alive)return;g.i++;if(g.i>=n){alive=false;api.done({stars:starsFor(g.first,n,g.hint),first:g.first,total:n,hint:g.hint,review:[]})}else round()},2500)}
 function wrong(el){g.miss++;if(!g.wrongNow)g.bad++;g.wrongNow++;SND.snap();el.classList.add('snap');walker.src=SP('crab_oops');hudUp();
  setTimeout(()=>{el.classList.remove('snap');if(alive&&!g.lock)walker.src=SP('crab_walk')},900);
  const r=g.r;say1(r.kind==='tobe'?'I am · he / she / it is · we / you / they are':g.placed===0?'הקרש נשבר: משפט מתחיל באות גדולה':g.placed===r.t.length-1?'הקרש נשבר: בסוף המשפט שמים נקודה':'הקרש נשבר: זאת עוד לא המילה הבאה',r.kind==='tobe'?'bad en':'bad',3200)}
 function pick(el){if(g.lock||el.classList.contains('used')||el.classList.contains('snap'))return;const r=g.r,t=el.dataset.t;
  if(r.kind==='tobe'){if(t!==r.gap)return wrong(el);el.classList.add('used');SND.plank();fill(g.placed,t);walkTo(0);return done()}
  if(t!==r.t[g.placed])return wrong(el);
  el.classList.add('used');SND.plank();fill(g.placed,t);walkTo(g.placed);g.placed++;
  if(g.placed>=r.t.length)done()}
 const onClick=e=>{const p=e.target.closest('.pl');if(p)pick(p)};
 host.addEventListener('click',onClick);window.addEventListener('resize',place);
 round();
 return{destroy(){alive=false;clearTimeout(ruleT);host.removeEventListener('click',onClick);window.removeEventListener('resize',place);delete window.__lv},
  hint(){if(g.lock)return;if(!g.hint){g.hint=1;hudUp()}const want=g.r.kind==='tobe'?g.r.gap:g.r.t[g.placed];const el=[...bank.children].find(b=>!b.classList.contains('used')&&b.dataset.t===want);if(el){el.classList.add('hinted');setTimeout(()=>el.classList.remove('hinted'),1800)}}}}
