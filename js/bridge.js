/* Level 4: the sentence bridge. Lay the word planks in order and the crab walks across.
   A wrong plank snaps and drops back; the planks already laid stay. am / is / are rounds fill one missing plank. */
import {SENT,TOBE_BY,T,starsFor} from './data.js';
import {award,say,warm,shuffle,esc} from './state.js';
import {SND} from './audio.js';
import {SP,hud,bgMap,confetti,stage,en} from './ui.js';

const toks=s=>s.replace(/([.!?])$/,' $1').split(/\s+/);
const GAP=[122,632],TOPY=1338;   // inner cliff edges and cliff-top height in the 752x1800 bridge art (taller than the others: sky to spare above)
const RULE='אות גדולה בהתחלה, נקודה בסוף';
const TOBE_RULE='I am · he / she / it is · we / you / they are';
/* a full stop sits on the baseline like a real one; a lone capital I gets drawn serifs so it cannot be read as l or | */
const CAP_I='<svg class="capi" viewBox="0 0 14 20" role="img" aria-label="I"><path d="M2.500 2.500h9M7 2.500v15M2.500 17.500h9"/></svg>';
const face=t=>t==='.'?'<span class="fstop" role="img" aria-label="נקודה"><i class="dot"></i></span>':t==='I'?CAP_I:esc(t);
/* why a wrong am / is / are plank broke */
const TOBE_WHY={am:`עם ${en('I')} אומרים ${en('am')}`,is:`על אחד או אחת (${en('he / she / it')}) אומרים ${en('is')}`,are:`על רבים, וגם עם ${en('you')}, אומרים ${en('are')}`};
const size=t=>t.length>8?' xl':t.length>6?' lg':'';

export async function start(host,cfg,api){
 const builds=shuffle(SENT[cfg.part]).slice(0,T.bridgeBuild),tobes=shuffle(TOBE_BY[cfg.part]).slice(0,T.bridgeTobe),rounds=[];
 for(let i=0;i<Math.max(builds.length,tobes.length);i++){if(builds[i])rounds.push({kind:'build',en:builds[i][0],he:builds[i][1]});if(tobes[i])rounds.push({kind:'tobe',en:tobes[i][0].replace('___',tobes[i][1]),gap:tobes[i][1],raw:tobes[i][0]})}
 warm(rounds.map(r=>r.en));
 const g={i:0,miss:0,hint:0,first:0,bad:0,wrongNow:0,lock:0,r:null,placed:0,lead:0},n=rounds.length;let alive=true,ruleT=0;
 window.__lv={kind:'bridge',g,next:()=>g.r&&(g.r.kind==='tobe'?g.r.gap:g.r.t[g.placed])};
 host.innerHTML=`<div class="lv bridge"><div id="hd"></div>
  <div class="sign prompt"><small id="bt"></small><b id="bh"></b></div>
  <div class="work" id="work">
   <div class="bank" id="bank" dir="ltr"></div>
   <p class="rule" id="rule"></p></div>
  <div class="span" id="span" dir="ltr"></div>
  <img class="walker" id="walker" src="${SP('crab_walk')}" alt="" draggable="false"></div>`;
 const q=s=>host.querySelector(s),span=q('#span'),bank=q('#bank'),work=q('#work'),walker=q('#walker'),bt=q('#bt'),bh=q('#bh'),rule=q('#rule'),sign=q('.prompt');
 let M=bgMap('bridge');
 function place(){M=bgMap('bridge');const st=stage.getBoundingClientRect(),top=M.oy+TOPY*M.s,gw=(GAP[1]-GAP[0])*M.s,sb=sign.getBoundingClientRect().bottom-st.top;
  span.style.left=(M.ox+GAP[0]*M.s)+'px';span.style.width=gw+'px';span.style.top=(top-10)+'px';
  work.style.top=(sb+6)+'px';work.style.height=Math.max(150,top-92-sb-6)+'px';   // the work area fills the sky between the sign and the crab
  if(g.r){const k=g.r.t.length,chars=g.r.t.reduce((a,t)=>a+t.length,0);span.style.setProperty('--fs',Math.max(12,Math.min(20,(gw-6*(k-1))/(chars*.62+k*1.3)))+'px')}
  walkTo(g.walk??-1,true)}
 function walkTo(k,instant){g.walk=k;const cnt=g.r?g.r.t.length:1,sl=span.children[k];let cx;
  if(k<0)cx=M.ox+(GAP[0]-40)*M.s;else if(k>=cnt)cx=M.ox+(GAP[1]+12)*M.s;else if(sl)cx=span.offsetLeft+sl.offsetLeft+sl.offsetWidth/2;else cx=M.ox+GAP[0]*M.s;
  cx=Math.max(36,Math.min(M.W-36,cx));walker.style.transition=instant?'none':'';walker.style.left=cx+'px';walker.style.top=(M.oy+TOPY*M.s-6)+'px'}
 const hudUp=()=>q('#hd').innerHTML=hud({i:g.i,n,st:starsFor(n-g.bad,n,g.hint),hint:g.hint});
 /* one status line: neutral ink by default, red only while a mistake is the latest thing that happened */
 const calm=()=>g.r.kind==='tobe'?(g.wrongNow?TOBE_RULE:''):RULE;
 function status(text,cls,ms,html){clearTimeout(ruleT);if(html)rule.innerHTML=text;else rule.textContent=text;rule.className='rule '+(cls||(text===TOBE_RULE?'en':''));g.err=cls==='bad';if(ms)ruleT=setTimeout(()=>{if(alive&&!g.lock)status(calm())},ms)}
 function round(){const r=g.r=rounds[g.i];r.t=toks(r.en);g.wrongNow=0;g.lock=0;g.lead=0;walker.src=SP('crab_walk');walker.classList.remove('hop');bank.classList.remove('gone');rule.style.transform='';
  const fx=t=>(t.length+2.1).toFixed(1);
  if(r.kind==='build'){g.placed=0;bt.textContent='בנו את המשפט באנגלית';bh.textContent=r.he;bh.className='';bh.removeAttribute('dir');
   span.innerHTML=r.t.map(t=>`<span class="slot" style="flex-grow:${fx(t)}"></span>`).join('');
   const order=shuffle(r.t.map((t,k)=>k));bank.className='bank n'+r.t.length;bank.innerHTML=order.map(k=>`<button class="pl p${k%5}${size(r.t[k])}" data-t="${esc(r.t[k])}">${face(r.t[k])}</button>`).join('')}
  else{g.placed=r.t.indexOf(r.gap);bt.textContent='משלימים את המשפט';bh.textContent='איזו מילה חסרה?';bh.className='';bh.removeAttribute('dir');
   /* the sentence is shown once: it is the bridge itself, with one missing plank */
   span.innerHTML=r.t.map((t,k)=>k===g.placed?`<span class="slot gap" style="flex-grow:${fx('are')}"><i>?</i></span>`:`<span class="slot f p${k%5}" style="flex-grow:${fx(t)}"><i>${face(t)}</i></span>`).join('');
   bank.className='bank tobe';bank.innerHTML=['am','is','are'].map((t,k)=>`<button class="pl big p${k+1}" data-t="${t}">${t}</button>`).join('')}
  status(calm());hudUp();place();walkTo(-1,true)}
 function fill(k,t){const sl=span.children[k];sl.className=`slot f p${k%5} laid`;sl.innerHTML=`<i>${face(t)}</i>`}
 function done(){const r=g.r;g.lock=1;const ok1=!g.wrongNow;if(ok1)g.first++;award(ok1?T.ptsFirst:T.ptsLater);
  bank.classList.add('gone');
  rule.style.transform=`translateY(${-(rule.offsetTop-bank.offsetTop-(bank.offsetHeight-rule.offsetHeight)/2).toFixed(1)}px)`;   // the tray is empty now, so the good news takes its place
  bh.className='en';bh.setAttribute('dir','ltr');bh.textContent=r.en;
  status('יופי! המשפט שלם','good');
  setTimeout(()=>{if(!alive)return;walkTo(r.t.length);SND.step()},300);
  setTimeout(()=>{if(!alive)return;walker.src=SP('crab_happy');walker.classList.add('hop');SND.pop();say(r.en);const b=walker.getBoundingClientRect(),s=host.getBoundingClientRect();confetti(b.left-s.left+b.width/2,b.top-s.top,26)},900);
  setTimeout(()=>{if(!alive)return;g.i++;if(g.i>=n){alive=false;api.done({stars:starsFor(g.first,n,g.hint),first:g.first,total:n,hint:g.hint,review:[]})}else round()},2500)}
 /* the wrong plank flies to its place on the bridge, snaps and falls into the sea; then it is back in the tray, outlined in red for a moment */
 function wrong(el){g.miss++;if(!g.wrongNow)g.bad++;g.wrongNow++;SND.snap();walker.src=SP('crab_oops');hudUp();
  const r=g.r,sl=span.children[g.placed],a=sl.getBoundingClientRect(),h=host.firstElementChild.getBoundingClientRect(),gh=document.createElement('div');
  gh.className=el.className.replace(/\b(big|lg|xl|hinted|lead|back)\b/g,'')+' ghost';gh.innerHTML=el.innerHTML;
  gh.style.cssText=`left:${(a.left-h.left).toFixed(1)}px;top:${(a.top-h.top).toFixed(1)}px;width:${a.width.toFixed(1)}px;height:${a.height.toFixed(1)}px;font-size:${getComputedStyle(span).getPropertyValue('--fs')||'16px'}`;
  host.firstElementChild.appendChild(gh);el.classList.remove('back');el.classList.add('snap');
  setTimeout(()=>{gh.remove();el.classList.remove('snap');el.classList.add('back');if(alive&&!g.lock)walker.src=SP('crab_walk')},850);
  setTimeout(()=>el.classList.remove('back'),2300);
  if(r.kind==='tobe')status('הקרש נשבר: '+TOBE_WHY[r.gap],'bad',4200,1);
  else{status(g.placed===0?'הקרש נשבר: משפט מתחיל באות גדולה':g.placed===r.t.length-1?'הקרש נשבר: בסוף המשפט שמים נקודה':'הקרש נשבר: זאת עוד לא המילה הבאה','bad',3200);
   /* stuck on the very first word twice: show which plank starts the sentence (no star cost, the mistakes already counted) */
   if(g.placed===0&&++g.lead>=2){const f=[...bank.children].find(b=>b.dataset.t===r.t[0]);if(f)f.classList.add('lead')}}}
 function pick(el){if(g.lock||el.classList.contains('used')||el.classList.contains('snap'))return;const r=g.r,t=el.dataset.t;
  if(g.err)status(calm());                                    // an old "plank broke" note never outlives the next tap
  if(r.kind==='tobe'){if(t!==r.gap)return wrong(el);el.classList.add('used');SND.plank();fill(g.placed,t);walkTo(0);return done()}
  if(t!==r.t[g.placed])return wrong(el);
  el.classList.remove('lead');el.classList.add('used');SND.plank();fill(g.placed,t);walkTo(g.placed);g.placed++;
  if(g.placed>=r.t.length)done()}
 const onClick=e=>{const p=e.target.closest('.pl');if(p)pick(p)};
 host.addEventListener('click',onClick);window.addEventListener('resize',place);
 round();
 return{destroy(){alive=false;clearTimeout(ruleT);host.removeEventListener('click',onClick);window.removeEventListener('resize',place);delete window.__lv},
  hint(){if(g.lock)return;const isNew=!g.hint;if(isNew){g.hint=1;hudUp()}const want=g.r.kind==='tobe'?g.r.gap:g.r.t[g.placed];const el=[...bank.children].find(b=>!b.classList.contains('used')&&b.dataset.t===want);if(el){el.classList.add('hinted');setTimeout(()=>el.classList.remove('hinted'),1800)}return isNew}}}
