/* Level 1: the word slingshot. Hebrew meaning on the sign, pull back and pop the balloon with the matching English word. */
import {wordsOf,T,starsFor} from './data.js';
import {S,mark,say,shuffle,weakest,esc,reduced,save} from './state.js';
import {SND} from './audio.js';
import {img,SP,hud,stage,confetti,en} from './ui.js';

const INK='#5a4534',FONT="'Playpen Sans Hebrew','Varela Round','Rubik','Arial Hebrew',sans-serif";

export async function start(host,cfg,api){
 const pool=wordsOf(cfg.part),ws=weakest(pool,Math.min(T.slingWords,pool.length));
 const [fork,crabI,crabH,crabO,ballI,...bal]=await Promise.all([SP('fork'),SP('crab_wave'),SP('crab_happy'),SP('crab_oops'),SP('ball_'+(S.g.ball||0)),SP('balloon_0'),SP('balloon_1'),SP('balloon_2'),SP('balloon_3')].map(img));
 try{await document.fonts.load("800 16px 'Playpen Sans Hebrew'","goal שער")}catch(e){}
 host.innerHTML=`<div class="lv sling"><div id="hd"></div>
  <div class="sign prompt"><small>פגעו במילה שהפירוש שלה</small><b id="tg"></b></div>
  <canvas id="cv" aria-label="קלע המילים: גוררים אחורה, מכוונים ומשחררים"></canvas>
  <div class="cap label" id="cap" hidden></div>
  <div class="coach" id="coach" hidden><div class="hand"></div><p class="label">גוררים אחורה, מכוונים ומשחררים</p></div></div>`;
 const cv=host.querySelector('#cv'),x=cv.getContext('2d'),tg=host.querySelector('#tg'),cap=host.querySelector('#cap'),coach=host.querySelector('#coach');
 let W=0,H=0,D=1,AX=0,AY=0,R=42,alive=true;
 const g={i:0,miss:0,hint:0,first:0,bx:0,by:0,vx:0,vy:0,fly:0,gone:0,drag:0,trail:[],last:[],bub:[],fx:[],t:0,ft:0,lock:0,pose:'i',poseT:0,glow:0,down:null,wrongNow:0,results:[]};
 window.__lv={kind:'sling',g,geom:()=>({W,H,AX,AY,R}),K:T.launchK,G:T.gravity};

 function layout(){W=stage.clientWidth;H=stage.clientHeight;D=Math.min(3,window.devicePixelRatio||1);cv.width=Math.round(W*D);cv.height=Math.round(H*D);
  AX=W/2;AY=H-Math.max(168,H*.215);R=Math.min(47,W*.116);
  const top=Math.max(240,H*.3),xs=[.16,.385,.615,.84],ys=[84,0,32,98];
  g.bub.forEach(b=>{b.x=W*xs[b.slot];b.y=top+ys[b.slot]*(H<700?.8:1)});
  if(!g.fly){g.bx=AX;g.by=AY}}
 function hudUp(){host.querySelector('#hd').innerHTML=hud({i:g.i,n:ws.length,st:starsFor(g.miss,g.hint,T.starSling)})}
 function round(){const w=ws[g.i],others=shuffle(pool.filter(o=>o.en!==w.en&&o.he!==w.he)).slice(0,3),slots=shuffle([0,1,2,3]);
  g.bub=[w,...others].map((o,j)=>({w:o,slot:slots[j],x:0,y:0,ph:Math.random()*6,ok:j===0,bad:0,pop:0,img:bal[(slots[j]+g.i)%4],cool:0}));
  g.glow=0;g.wrongNow=0;g.last=[];tg.textContent=w.he;layout();hudUp()}
 function reset(){g.fly=0;g.gone=0;g.bx=AX;g.by=AY;g.vx=g.vy=0;if(g.trail.length)g.last=g.trail;g.trail=[]}
 function pose(p,ms){g.pose=p;g.poseT=performance.now()+ms}

 /* ----- input: grab the ball, or drag anywhere in the lower part of the screen ----- */
 const pos=e=>{const r=cv.getBoundingClientRect();return[e.clientX-r.left,e.clientY-r.top]};
 function setPull(dx,dy){if(dy<4)dy=4;const d=Math.hypot(dx,dy);if(d>T.maxPull){dx*=T.maxPull/d;dy*=T.maxPull/d}g.bx=AX+dx;g.by=AY+dy}
 cv.addEventListener('pointerdown',e=>{if(g.fly||g.lock)return;const[px,py]=pos(e);if(py<AY-R*1.6)return;
  const near=Math.hypot(px-AX,py-AY)<70;g.drag=1;g.down=near?null:[px,py];try{cv.setPointerCapture(e.pointerId)}catch(_){}
  if(near)setPull(px-AX,py-AY);if(!coach.hidden){coach.hidden=true;S.g.ob.sling=1;save()}SND.pull();e.preventDefault()});
 cv.addEventListener('pointermove',e=>{if(!g.drag)return;const[px,py]=pos(e);if(g.down)setPull(px-g.down[0],py-g.down[1]);else setPull(px-AX,py-AY)});
 const up=()=>{if(!g.drag)return;g.drag=0;const dx=AX-g.bx,dy=AY-g.by;if(Math.hypot(dx,dy)<T.minPull){g.bx=AX;g.by=AY;return}
  g.vx=dx*T.launchK;g.vy=dy*T.launchK;g.fly=1;g.ft=0;g.trail=[];SND.shoot()};
 cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);

 function hitOK(b,by){b.pop=1;g.gone=1;g.lock=1;SND.pop();say(b.w.en);pose('h',1200);
  const first=!g.wrongNow;if(first)g.first++;mark(b.w,first);g.results.push({w:b.w,ok:first});
  cap.innerHTML=`${en(b.w.en)} <span>=</span> ${esc(b.w.he)}`;cap.hidden=false;
  if(!reduced())for(let i=0;i<18;i++)g.fx.push({x:b.x,y:by,vx:(Math.random()-.5)*7,vy:-Math.random()*5-1,l:46,r:3+Math.random()*4,c:['#F7D774','#A9C58F','#EF8F7A','#D7C2E6','#9CCBE0'][i%5]});
  setTimeout(()=>{if(!alive)return;cap.hidden=true;g.lock=0;g.i++;reset();g.last=[];
   if(g.i>=ws.length)finish();else round()},1050)}
 function hitBad(b){if(!b.bad){g.miss++;g.wrongNow++;hudUp()}b.bad=1;b.cool=g.t+45;b.shake=g.t+26;g.vx*=-.45;g.vy=Math.abs(g.vy)*.35+1.2;SND.bad();pose('o',900)}
 function finish(){alive=false;api.done({stars:starsFor(g.miss,g.hint,T.starSling),first:g.first,total:ws.length,miss:g.miss,hint:g.hint,review:g.results.filter(r=>!r.ok).map(r=>r.w)})}

 function step(k){g.t+=k;
  g.fx=g.fx.filter(p=>(p.l-=k)>0);g.fx.forEach(p=>{p.vy+=.2*k;p.x+=p.vx*k;p.y+=p.vy*k});
  if(!g.fly)return;g.ft+=k;g.vy+=T.gravity*k;g.bx+=g.vx*k;g.by+=g.vy*k;
  const r=T.ballR;if(g.bx<r){g.bx=r;g.vx=Math.abs(g.vx)*.8}if(g.bx>W-r){g.bx=W-r;g.vx=-Math.abs(g.vx)*.8}if(g.by<r+70){g.by=r+70;g.vy=Math.abs(g.vy)*.5}
  if(!g.trail.length||Math.hypot(g.bx-g.trail[g.trail.length-1][0],g.by-g.trail[g.trail.length-1][1])>15)g.trail.push([g.bx,g.by]);
  if(!g.gone)for(const b of g.bub){if(b.pop||g.t<b.cool)continue;const by=b.y+Math.sin(g.t/30+b.ph)*5;
   if(Math.hypot(g.bx-b.x,g.by-by)<R+r+T.hitPad){b.ok?hitOK(b,by):hitBad(b);break}}
  if(g.by>H+40||g.ft>520)reset()}

 function fit(text,maxW,size,min,weight){x.font=`${weight} ${size}px ${FONT}`;while(size>min&&x.measureText(text).width>maxW){size-=1;x.font=`${weight} ${size}px ${FONT}`}return size}
 function label(b,cy){const t=b.w.en,max=R*1.62;x.textAlign='center';x.textBaseline='middle';x.direction='ltr';x.fillStyle=INK;
  const parts=t.includes(' ')&&t.length>7?[t.slice(0,t.lastIndexOf(' ')),t.slice(t.lastIndexOf(' ')+1)]:[t];
  if(b.bad){const s=fit(t,max,15,10,800);x.fillText(t,b.x,cy-10);x.direction='rtl';const he=b.w.he.split(',')[0].split(' / ')[0];fit(he,max,14,10,700);x.fillText(he,b.x,cy+9);x.direction='ltr';return}
  if(parts.length===2){const s=Math.min(fit(parts[0],max,18,11,800),fit(parts[1],max,18,11,800));x.font=`800 ${s}px ${FONT}`;x.fillText(parts[0],b.x,cy-s*.56);x.fillText(parts[1],b.x,cy+s*.56)}
  else{fit(t,max,19,11,800);x.fillText(t,b.x,cy)}}
 function draw(){x.setTransform(D,0,0,D,0,0);x.clearRect(0,0,W,H);x.lineCap=x.lineJoin='round';
  // trail of the previous shot, then of this one
  x.fillStyle='rgba(90,69,52,.28)';g.last.forEach(p=>{x.beginPath();x.arc(p[0],p[1],2.6,0,6.3);x.fill()});
  x.fillStyle='rgba(239,143,122,.7)';g.trail.forEach(p=>{x.beginPath();x.arc(p[0],p[1],2.6,0,6.3);x.fill()});
  // balloons
  for(const b of g.bub){if(b.pop)continue;const by=b.y+Math.sin(g.t/30+b.ph)*5,sx=b.shake>g.t?Math.sin(g.t*1.3)*4:0,w=R*2.06,h=w*1.5;
   if(g.glow&&b.ok){x.save();x.strokeStyle='#F2B63C';x.lineWidth=5;x.setLineDash([3,9]);x.lineDashOffset=-g.t*.5;x.beginPath();x.arc(b.x,by,R+9,0,6.3);x.stroke();x.restore()}
   x.globalAlpha=b.bad?.62:1;if(b.img)x.drawImage(b.img,b.x-w/2+sx,by-R*1.03,w,h);x.globalAlpha=1;
   x.save();x.translate(sx,0);label(b,by-1);x.restore()}
  // crab mascot
  const now=performance.now(),ci=now<g.poseT?(g.pose==='h'?crabH:crabO):crabI,cw=Math.min(96,W*.24),chh=ci?cw*ci.height/ci.width:0,hop=now<g.poseT&&g.pose==='h'&&!reduced()?Math.abs(Math.sin(g.t/7))*9:0;
  if(ci)x.drawImage(ci,AX-cw-58,H-chh-34-hop,cw,chh);
  // slingshot: back band, ball, front band, fork
  const fw=64,fh=fw*362/251,fx0=AX-fw/2,fy0=AY-12,tl=[AX-fw*.34,AY-2],tr=[AX+fw*.34,AY-2],held=!g.fly;
  const band=(a)=>{x.strokeStyle='#b8674f';x.lineWidth=5;x.beginPath();x.moveTo(a[0],a[1]);x.lineTo(g.bx,g.by+2);x.stroke();x.strokeStyle='rgba(90,69,52,.55)';x.lineWidth=1.4;x.beginPath();x.moveTo(a[0],a[1]-2.6);x.lineTo(g.bx,g.by-.6);x.stroke()};
  if(held)band(tr);
  if(fork)x.drawImage(fork,fx0,fy0,fw,fh);
  // aim guide
  if(g.drag){const dx=AX-g.bx,dy=AY-g.by;if(Math.hypot(dx,dy)>=T.minPull){let px=g.bx,py=g.by,vx=dx*T.launchK,vy=dy*T.launchK;
    for(let i=1;i<=64;i++){vy+=T.gravity*1.5;px+=vx*1.5;py+=vy*1.5;if(px<T.ballR||px>W-T.ballR)vx=-vx*.8;if(py<86||py>H)break;
     if(i%2===0){x.globalAlpha=Math.max(.12,.8-i/90);x.fillStyle=INK;x.beginPath();x.arc(px,py,Math.max(1.6,4.2-i/22),0,6.3);x.fill()}}x.globalAlpha=1}}
  if(!g.gone&&ballI){const br=T.ballR*1.12;x.drawImage(ballI,g.bx-br,g.by-br,br*2,br*2*ballI.height/ballI.width)}
  if(held)band(tl);
  for(const p of g.fx){x.globalAlpha=Math.min(1,p.l/18);x.fillStyle=p.c;x.beginPath();x.arc(p.x,p.y,p.r,0,6.3);x.fill()}x.globalAlpha=1}

 round();
 if(!S.g.ob.sling){coach.hidden=false}
 const onResize=()=>{layout()};window.addEventListener('resize',onResize);
 let last=performance.now();
 (function loop(now){if(!alive&&!host.contains(cv))return;if(!host.contains(cv))return;const k=Math.min(2.4,(now-last)/16.67);last=now;step(k);draw();requestAnimationFrame(loop)})(last);
 return{destroy(){alive=false;window.removeEventListener('resize',onResize);delete window.__lv},
  hint(){if(g.lock)return;if(!g.hint){g.hint=1;hudUp()}g.glow=1}}}
