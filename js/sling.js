/* Level 1: the word slingshot. Hebrew meaning on the sign, pull back and pop the balloon with the matching English word. */
import {wordsOf,T,starsFor} from './data.js';
import {S,mark,say,warm,ready,shuffle,weakest,esc,reduced,save} from './state.js';
import {SND} from './audio.js';
import {img,SP,hud,stage,bgMap,en,toastAt} from './ui.js';

const INK='#5a4534',FONT="'Playpen Sans Hebrew','Varela Round','Rubik','Arial Hebrew',sans-serif";
const SKYLINE=1020;   // in the 752x1344 island art nothing is drawn above this row, so targets stay over clear sky

export async function start(host,cfg,api){
 const pool=wordsOf(cfg.part),ws=weakest(pool,Math.min(T.slingWords,pool.length));warm(ws.map(w=>w.en));
 const voiced=ready(ws[0].en);   // the level opens when its first word can be spoken (or after 3 s)
 const [fork,crabI,crabH,crabO,ballI,...bal]=await Promise.all([SP('fork'),SP('crab_wave'),SP('crab_happy'),SP('crab_oops'),SP('ball_'+(S.g.ball||0)),SP('balloon_0'),SP('balloon_1'),SP('balloon_2'),SP('balloon_3')].map(img));
 try{await document.fonts.load("700 16px 'Playpen Sans Hebrew'","goal שער")}catch(e){}
 await voiced;
 const first=!S.g.ob.sling;
 host.innerHTML=`<div class="lv sling"><div id="hd"></div>
  <div class="sign prompt"><small>קלעו לבלון עם המילה שפירושה</small><b id="tg"></b></div>
  <canvas id="cv" aria-label="קלע המילים: גוררים אחורה, מכוונים ומשחררים"></canvas>
  <div class="cap label" id="cap" hidden></div>
  <p class="tip ctip" id="ctip" hidden>גררו את הכדור אחורה ושחררו</p>
  <div class="coach" id="coach" hidden><img src="${SP('ic_arrow')}" alt=""></div></div>`;
 const cv=host.querySelector('#cv'),x=cv.getContext('2d'),tg=host.querySelector('#tg'),cap=host.querySelector('#cap'),coach=host.querySelector('#coach'),ctip=host.querySelector('#ctip'),sign=host.querySelector('.prompt');
 let W=0,H=0,D=1,AX=0,AY=0,R=42,zt=0,zb=0,alive=true,capT=0;
 const g={i:0,miss:0,hint:0,first:0,bad:0,bx:0,by:0,vx:0,vy:0,fly:0,gone:0,drag:0,trail:[],last:[],bub:[],fx:[],t:0,ft:0,lock:0,pose:'i',poseT:0,glow:0,down:null,wrongNow:0,results:[]};
 window.__lv={kind:'sling',g,geom:()=>({W,H,AX,AY,R}),K:T.launchK,G:T.gravity};
 const REST=12;   // the ball hangs a little below the prongs so the band is visible

 function layout(){W=stage.clientWidth;H=stage.clientHeight;D=Math.min(3,window.devicePixelRatio||1);cv.width=Math.round(W*D);cv.height=Math.round(H*D);
  const m=bgMap('bottom'),sr=sign.getBoundingClientRect(),st=stage.getBoundingClientRect();
  zt=sr.bottom-st.top+8;zb=m.oy+SKYLINE*m.s-8;             // clear sky between the sign and the island
  AX=W/2;AY=Math.min(H-150,zb+62);
  /* a balanced arc of four balloons: the same gap between every pair of neighbours, the inner pair a little higher.
     Every balloon is in open view of the slingshot and no two can touch. */
  const EDGE=10,GAPX=6;R=Math.max(30,Math.min(50,(W-2*EDGE-3*GAPX)/8,(zb-zt-70)/3.6));
  const stepX=2*R+GAPX,x0=W/2-1.5*stepX,lift=R*.62,yi=zt+R+6+Math.max(0,Math.min(40,(zb-zt-R*3.1-lift-120)*.3));
  const xs=[0,1,2,3].map(k=>x0+k*stepX),ys=[yi+lift,yi,yi,yi+lift];
  g.bub.forEach(b=>{b.x=xs[b.slot];b.y=ys[b.slot]});
  /* the open sky between the balloon strings and the slingshot holds the two passing notes: the word note, and under it the toast band */
  const skyT=ys[0]+R*1.95,skyB=AY-26,capT0=Math.min(zb-34,skyT+8+Math.max(0,skyB-skyT-118)*.3);
  cap.style.top=capT0.toFixed(1)+'px';toastAt(capT0+56);fitAll();ctip.style.top=Math.min(zb+6,AY-54)+'px';coach.style.left=AX+'px';coach.style.top=(AY+REST+20)+'px';   // the 'pull' arrow starts right under the ball
  if(!g.fly&&!g.drag){g.bx=AX;g.by=AY+REST}}
 function hudUp(){host.querySelector('#hd').innerHTML=hud({i:g.i,n:ws.length,st:starsFor(ws.length-g.bad,ws.length,g.hint),hint:g.hint})}
 function round(){const w=ws[g.i],others=shuffle(pool.filter(o=>o.en!==w.en&&o.he!==w.he)).slice(0,3),slots=shuffle([0,1,2,3]);
  g.bub=[w,...others].map((o,j)=>({w:o,slot:slots[j],x:0,y:0,ph:Math.random()*6,ok:j===0,bad:0,pop:0,img:bal[(slots[j]+g.i)%4],cool:0}));
  g.glow=0;g.wrongNow=0;g.last=[];tg.textContent=w.he;layout();hudUp()}
 function reset(){g.fly=0;g.gone=0;g.bx=AX;g.by=AY+REST;g.vx=g.vy=0;if(g.trail.length)g.last=g.trail;g.trail=[]}
 function pose(p,ms){g.pose=p;g.poseT=performance.now()+ms}
 function caption(html,bad,ms){clearTimeout(capT);cap.innerHTML=html;cap.classList.toggle('bad',!!bad);cap.hidden=false;capT=setTimeout(()=>{cap.hidden=true},ms)}

 /* ----- input: grab the ball, or drag anywhere in the lower part of the screen ----- */
 const pos=e=>{const r=cv.getBoundingClientRect();return[e.clientX-r.left,e.clientY-r.top]};
 function setPull(dx,dy){if(dy<REST)dy=REST;const d=Math.hypot(dx,dy);if(d>T.maxPull){dx*=T.maxPull/d;dy*=T.maxPull/d}g.bx=AX+dx;g.by=AY+dy}
 cv.addEventListener('pointerdown',e=>{if(g.fly||g.lock)return;const[px,py]=pos(e);if(py<zb-20)return;
  const near=Math.hypot(px-AX,py-AY-REST)<70;g.drag=1;g.down=near?null:[px,py-REST];try{cv.setPointerCapture(e.pointerId)}catch(_){}
  if(near)setPull(px-AX,py-AY);if(!coach.hidden){coach.hidden=ctip.hidden=true;S.g.ob.sling=1;save()}SND.pull();e.preventDefault()});
 cv.addEventListener('pointermove',e=>{if(!g.drag)return;const[px,py]=pos(e);if(g.down)setPull(px-g.down[0],py-g.down[1]);else setPull(px-AX,py-AY)});
 const up=()=>{if(!g.drag)return;g.drag=0;const dx=AX-g.bx,dy=AY-g.by;if(Math.hypot(dx,dy)<T.minPull){g.bx=AX;g.by=AY+REST;return}
  g.vx=dx*T.launchK;g.vy=dy*T.launchK;g.fly=1;g.ft=0;g.trail=[];SND.shoot()};
 cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);

 function hitOK(b,by){b.pop=1;g.gone=1;g.lock=1;SND.pop();say(b.w.en);pose('h',1100);
  const ok1=!g.wrongNow;if(ok1)g.first++;mark(b.w,ok1);g.results.push({w:b.w,ok:ok1});
  caption(`${en(b.w.en)} <span class="eq">=</span> ${esc(b.w.he)}`,false,1000);
  if(!reduced())for(let i=0;i<18;i++)g.fx.push({x:b.x,y:by,vx:(Math.random()-.5)*7,vy:-Math.random()*5-1,l:46,r:3+Math.random()*4,c:['#F7D774','#A9C58F','#EF8F7A','#D7C2E6','#9CCBE0'][i%5]});
  setTimeout(()=>{if(!alive)return;g.lock=0;g.i++;reset();g.last=[];
   if(g.i>=ws.length)finish();else round()},1050)}
 function hitBad(b){if(!b.bad){g.miss++;if(!g.wrongNow)g.bad++;g.wrongNow++;hudUp()}b.bad=1;b.cool=g.t+45;b.shake=g.t+26;g.vx*=-.45;g.vy=Math.abs(g.vy)*.35+1.2;SND.bad();pose('o',2000);
  caption(`כמעט! ${en(b.w.en)} <span class="eq">=</span> ${esc(b.w.he.split(',')[0])}`,true,2200)}
 function finish(){alive=false;api.done({stars:starsFor(g.first,ws.length,g.hint),first:g.first,total:ws.length,hint:g.hint,review:g.results.filter(r=>!r.ok).map(r=>r.w)})}

 function step(k){g.t+=k;
  g.fx=g.fx.filter(p=>(p.l-=k)>0);g.fx.forEach(p=>{p.vy+=.2*k;p.x+=p.vx*k;p.y+=p.vy*k});
  if(!g.fly)return;g.ft+=k;g.vy+=T.gravity*k;g.bx+=g.vx*k;g.by+=g.vy*k;
  const r=T.ballR;if(g.bx<r){g.bx=r;g.vx=Math.abs(g.vx)*.8}if(g.bx>W-r){g.bx=W-r;g.vx=-Math.abs(g.vx)*.8}if(g.by<zt-R*.4){g.by=zt-R*.4;g.vy=Math.abs(g.vy)*.5}
  if(!g.trail.length||Math.hypot(g.bx-g.trail[g.trail.length-1][0],g.by-g.trail[g.trail.length-1][1])>15)g.trail.push([g.bx,g.by]);
  if(!g.gone)for(const b of g.bub){if(b.pop||g.t<b.cool)continue;const by=b.y+Math.sin(g.t/30+b.ph)*4;
   if(Math.hypot(g.bx-b.x,g.by-by)<R+r+T.hitPad){b.ok?hitOK(b,by):hitBad(b);break}}
  if(g.by>H+40||g.ft>520)reset()}

 function fit(text,maxW,size,min,weight){x.font=`${weight} ${size}px ${FONT}`;while(size>min&&x.measureText(text).width>maxW){size-=1;x.font=`${weight} ${size}px ${FONT}`}return size}
 /* one lettering size for the four balloons of a round: the size the longest word needs. Long phrases and hyphenated numbers take two lines. */
 const split=t=>{if(t.length>7){const i=Math.max(t.lastIndexOf(' '),t.lastIndexOf('-'));if(i>0)return[t.slice(0,t[i]==='-'?i+1:i),t.slice(i+1)]}return[t]};
 function fitAll(){g.fs=Math.min(20,...g.bub.flatMap(b=>split(b.w.en).map(p=>fit(p,R*1.74,20,12,800))))}
 function label(b,cy){const t=b.w.en,max=R*1.74;x.textAlign='center';x.textBaseline='middle';x.direction='ltr';x.fillStyle=INK;
  const parts=split(t);
  if(b.bad){fit(t,max,16,10,800);x.fillText(t,b.x,cy-11);x.direction='rtl';const he=b.w.he.split(',')[0].split(' / ')[0];fit(he,max,16,10,700);x.fillText(he,b.x,cy+10);x.direction='ltr';return}
  const s=g.fs||18;x.font=`800 ${s}px ${FONT}`;
  if(parts.length===2){x.fillText(parts[0],b.x,cy-s*.56);x.fillText(parts[1],b.x,cy+s*.56)}
  else x.fillText(t,b.x,cy)}
 function strand(a){x.strokeStyle=INK;x.lineWidth=7.5;x.beginPath();x.moveTo(a[0],a[1]);x.lineTo(g.bx,g.by);x.stroke();x.strokeStyle='#e9917b';x.lineWidth=4;x.beginPath();x.moveTo(a[0],a[1]);x.lineTo(g.bx,g.by);x.stroke()}
 function draw(){x.setTransform(D,0,0,D,0,0);x.clearRect(0,0,W,H);x.lineCap=x.lineJoin='round';
  // trail of the previous shot, then of this one
  if(cap.hidden){   // the feedback note sits where the trails pass, so they wait until it is gone
   x.fillStyle='rgba(90,69,52,.25)';g.last.forEach(p=>{x.beginPath();x.arc(p[0],p[1],2.6,0,6.3);x.fill()});
   x.fillStyle='rgba(239,143,122,.7)';g.trail.forEach(p=>{x.beginPath();x.arc(p[0],p[1],2.6,0,6.3);x.fill()})}
  // balloons
  for(const b of g.bub){if(b.pop)continue;const by=b.y+Math.sin(g.t/30+b.ph)*4,sx=b.shake>g.t?Math.sin(g.t*1.3)*4:0,w=R*2.06,h=w*1.5;
   if(g.glow&&b.ok){const gr=x.createRadialGradient(b.x,by,R*.7,b.x,by,R+22);gr.addColorStop(0,'rgba(247,215,116,.95)');gr.addColorStop(1,'rgba(247,215,116,0)');x.fillStyle=gr;x.globalAlpha=.65+.35*Math.sin(g.t/9);x.beginPath();x.arc(b.x,by,R+22,0,6.3);x.fill();x.globalAlpha=1}
   x.globalAlpha=b.bad?.6:1;if(b.img)x.drawImage(b.img,b.x-w/2+sx,by-R*1.03,w,h);x.globalAlpha=1;
   x.save();x.translate(sx,0);label(b,by-1);x.restore()}
  // crab mascot
  const now=performance.now(),ci=now<g.poseT?(g.pose==='h'?crabH:crabO):crabI,cw=Math.min(74,W*.19),chh=ci?cw*ci.height/ci.width:0,hop=now<g.poseT&&g.pose==='h'&&!reduced()?Math.abs(Math.sin(g.t/7))*9:0;
  if(ci)x.drawImage(ci,AX+46,Math.min(H-chh-18,AY+112-chh)-hop,cw,chh);
  // slingshot: far strand, fork, pouch + ball, near strand
  const fw=82,fh=fw*362/251,tl=[AX-fw*.36,AY+2],tr=[AX+fw*.36,AY+2],held=!g.fly;
  if(held)strand(tr);
  if(fork)x.drawImage(fork,AX-fw/2,AY-12,fw,fh);
  // aim guide: a short arc of dots that stops at the first balloon
  if(g.drag){const dx=AX-g.bx,dy=AY-g.by;if(Math.hypot(dx,dy)>=T.minPull){let px=g.bx,py=g.by,vx=dx*T.launchK,vy=dy*T.launchK,stop=false;
    for(let i=1;i<=44&&!stop;i++){vy+=T.gravity*1.5;px+=vx*1.5;py+=vy*1.5;if(px<T.ballR+4||px>W-T.ballR-4||py<zt-R*.4||py>H)break;
     for(const b of g.bub)if(!b.pop&&Math.hypot(px-b.x,py-b.y)<R+6){stop=true;break}
     if(!stop&&i%2===0){x.globalAlpha=Math.max(.15,.85-i/52);x.fillStyle=INK;x.beginPath();x.arc(px,py,Math.max(1.8,4.4-i/14),0,6.3);x.fill()}}x.globalAlpha=1}}
  if(held){x.fillStyle='#c9795f';x.strokeStyle=INK;x.lineWidth=2.2;x.beginPath();x.ellipse(g.bx,g.by+3,T.ballR*1.02,T.ballR*.92,0,0,6.3);x.fill();x.stroke()}
  if(!g.gone&&ballI){const br=T.ballR*1.12;x.drawImage(ballI,g.bx-br,g.by-br-2,br*2,br*2*ballI.height/ballI.width)}
  if(held)strand(tl);
  for(const p of g.fx){x.globalAlpha=Math.min(1,p.l/18);x.fillStyle=p.c;x.beginPath();x.arc(p.x,p.y,p.r,0,6.3);x.fill()}x.globalAlpha=1}

 round();
 if(first)coach.hidden=ctip.hidden=false;
 const onResize=()=>{layout()};window.addEventListener('resize',onResize);
 let last=performance.now();
 (function loop(now){if(!host.contains(cv))return;const k=Math.min(2.4,(now-last)/16.67);last=now;step(k);draw();requestAnimationFrame(loop)})(last);
 return{destroy(){alive=false;clearTimeout(capT);window.removeEventListener('resize',onResize);delete window.__lv},
  hint(){if(g.lock)return;const isNew=!g.hint;if(isNew){g.hint=1;hudUp()}g.glow=1;return isNew}}}
