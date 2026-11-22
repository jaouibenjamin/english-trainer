/* Beach Run: a 3D runner on its own page (run.html).
   Pitzi the crab runs along a boardwalk with three lanes. Obstacles are jumped or dodged; question gates hang one answer
   over each lane, and the pupil runs under the right one. A wrong answer never ends the run: the right answer is shown
   and the question comes back later in the same run. Questions are the mock exam's, built from the teacher's worksheets.
   It shares the pupil's record (points, login) with the main game and changes nothing else in it. */
import * as THREE from 'three';
import {GLTFLoader} from '../vendor/jsm/loaders/GLTFLoader.js';
import {S,award,saveLocal,API,esc,say as sayEn,SET,reduced,push} from './state.js';
import {POOL,PIC,shuf} from './xdata.js';
import {SND,unlock} from './audio.js';

const $=s=>document.querySelector(s);
const cv=$('#gl'),stageEl=$('#rstage'),hud=$('#hud'),pad=$('#pad'),menu=$('#menu'),banner=$('#banner'),flashEl=$('#flash');
if(SET.calm)document.documentElement.classList.add('calm');

/* ---------------- questions ---------------- */
const BANK=[...POOL.words.pic,...POOL.words.he,...POOL.words.num,...POOL.words.fill,...POOL.words.match,...POOL.words.act,...POOL.grammar.be,...POOL.grammar.short]
 .filter(it=>it.type==='choice');
const RUN_Q=12,PTS_FIRST=3,PTS_LATER=1,DAY_CAP=60;
const today=()=>{const d=new Date();return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate()};
function R(){if(!S.r||typeof S.r!=='object')S.r={};const r=S.r;r.best=+r.best||0;r.runs=+r.runs||0;if(!Array.isArray(r.miss))r.miss=[];if(r.day!==today()){r.day=today();r.dpts=0}r.dpts=+r.dpts||0;return r}
function deck(){const r=R(),miss=new Set(r.miss),w=BANK.filter(x=>x.skill==='words'),g=BANK.filter(x=>x.skill==='grammar');
 const rank=a=>shuf(a).sort((x,y)=>(miss.has(y.k)-miss.has(x.k))||((y.src==='ws')-(x.src==='ws')));
 return shuf([...rank(w).slice(0,7),...rank(g).slice(0,5)]).map(it=>({it,again:false}))}
function lanesFor(it){let o=[...new Set(it.opts())];if(!o.includes(it.a))o.unshift(it.a);
 if(it.fixed)o=o.slice(0,3);else o=shuf([it.a,...shuf(o.filter(x=>x!==it.a)).slice(0,2)]);
 return o.length===2?[o[0],null,o[1]]:o}

/* ---------------- renderer, scene, camera ---------------- */
let renderer;
try{renderer=new THREE.WebGLRenderer({canvas:cv,antialias:true,powerPreference:'high-performance'})}catch(e){$('#nogl').hidden=false;throw e}
renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));
renderer.outputColorSpace=THREE.SRGBColorSpace;
const scene=new THREE.Scene();
const SKY_TOP='#5d4fa3',SKY_LOW='#f6a77f';
scene.fog=new THREE.Fog(0xf3b08c,40,110);
scene.background=(()=>{const c=document.createElement('canvas');c.width=4;c.height=256;const g=c.getContext('2d'),gr=g.createLinearGradient(0,0,0,256);gr.addColorStop(0,SKY_TOP);gr.addColorStop(.62,SKY_LOW);gr.addColorStop(1,'#ffd7a6');g.fillStyle=gr;g.fillRect(0,0,4,256);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t})();
const cam=new THREE.PerspectiveCamera(62,1,.1,220);
scene.add(new THREE.HemisphereLight(0xffe6d0,0x6a5acd,1.35));
const sun=new THREE.DirectionalLight(0xffffff,1.6);sun.position.set(-4,10,6);scene.add(sun);

/* toon shading: three hard tones and a dark outline shell */
const GRAD=(()=>{const t=new THREE.DataTexture(new Uint8Array([90,90,90,255,170,170,170,255,255,255,255,255]),3,1);t.minFilter=t.magFilter=THREE.NearestFilter;t.needsUpdate=true;return t})();
const toon=(c,o={})=>new THREE.MeshLambertMaterial({color:c,flatShading:true,...o});
const toonC=(c,o={})=>new THREE.MeshToonMaterial({color:c,gradientMap:GRAD,...o});
const INK=new THREE.MeshBasicMaterial({color:0x3a281c,side:THREE.BackSide});
function mesh(geo,mat,outline=0.05){const m=new THREE.Mesh(geo,mat);if(outline&&mat.isMeshToonMaterial){const o=new THREE.Mesh(geo,INK);o.scale.setScalar(1+outline);m.add(o)}return m}

/* ---------------- Pitzi, built from shapes ---------------- */
function makeCrab(){
 const root=new THREE.Group(),body=new THREE.Group();root.add(body);
 const CORAL=toonC(0xf28466),CORAL2=toonC(0xe66e52),CREAM=toonC(0xfff2dc),WHITE=toonC(0xffffff),BLACK=new THREE.MeshBasicMaterial({color:0x2a1a12}),BLUE=toonC(0x6fa7d8),PINK=new THREE.MeshBasicMaterial({color:0xf7a1a1,transparent:true,opacity:.8});
 const shell=mesh(new THREE.SphereGeometry(.55,28,18),CORAL,.045);shell.scale.set(1.18,.8,.96);shell.position.y=.66;body.add(shell);
 const belly=mesh(new THREE.SphereGeometry(.42,20,14),CREAM,0);belly.scale.set(1.05,.62,.5);belly.position.set(0,.55,.3);body.add(belly);
 /* sailor scarf */
 const band=mesh(new THREE.TorusGeometry(.56,.075,8,32),BLUE,.08);band.rotation.x=Math.PI/2;band.scale.set(1.13,.95,1);band.position.y=.52;body.add(band);
 const knot=mesh(new THREE.ConeGeometry(.15,.28,4),BLUE,.08);knot.position.set(0,.4,.55);knot.rotation.set(.5,Math.PI/4,Math.PI);body.add(knot);
 /* face */
 const smile=new THREE.Mesh(new THREE.TorusGeometry(.12,.024,6,16,Math.PI),BLACK);smile.position.set(0,.72,.53);smile.rotation.z=Math.PI;body.add(smile);
 for(const s of[-1,1]){const ck=new THREE.Mesh(new THREE.CircleGeometry(.08,14),PINK);ck.position.set(s*.3,.74,.5);ck.rotation.y=s*.4;body.add(ck)}
 const eyes=[];
 for(const s of[-1,1]){const g=new THREE.Group();g.position.set(s*.22,.98,.18);body.add(g);
  const stalk=mesh(new THREE.CylinderGeometry(.05,.06,.34,10),CORAL2,.12);stalk.position.y=.12;g.add(stalk);
  const ball=mesh(new THREE.SphereGeometry(.17,18,14),WHITE,.07);ball.position.y=.34;g.add(ball);
  const pup=new THREE.Mesh(new THREE.SphereGeometry(.085,12,10),BLACK);pup.position.set(0,.35,.12);g.add(pup);
  const hl=new THREE.Mesh(new THREE.SphereGeometry(.03,8,6),new THREE.MeshBasicMaterial({color:0xffffff}));hl.position.set(.03,.39,.19);g.add(hl);eyes.push(g)}
 /* claws */
 const claws=[];
 for(const s of[-1,1]){const arm=new THREE.Group();arm.position.set(s*.58,.62,.12);body.add(arm);
  const a=mesh(new THREE.CylinderGeometry(.07,.08,.42,10),CORAL2,.1);a.position.set(s*.12,.15,0);a.rotation.z=-s*.7;arm.add(a);
  const hand=new THREE.Group();hand.position.set(s*.3,.36,0);arm.add(hand);
  const big=mesh(new THREE.SphereGeometry(.2,16,12),CORAL,.07);big.scale.set(1,.85,.75);hand.add(big);
  const top=new THREE.Group();top.position.set(0,.12,0);hand.add(top);
  const t1=mesh(new THREE.SphereGeometry(.12,12,10),CORAL,.09);t1.scale.set(.8,1.3,.6);t1.position.set(-s*.06,.1,0);top.add(t1);
  const t2=mesh(new THREE.SphereGeometry(.1,12,10),CORAL,.09);t2.scale.set(.8,1.2,.6);t2.position.set(s*.09,.06,0);t2.rotation.z=-s*.4;top.add(t2);
  claws.push({arm,top})}
 /* legs */
 const legs=[];
 for(const s of[-1,1])for(let i=0;i<3;i++){const p=new THREE.Group();p.position.set(s*.5,.45,.18-i*.24);body.add(p);
  const l=mesh(new THREE.CapsuleGeometry(.045,.36,4,8),CORAL2,.15);l.position.set(s*.16,-.15,0);l.rotation.z=s*.9;p.add(l);legs.push({p,s,ph:i*2.1+(s>0?Math.PI:0)})}
 const shadow=new THREE.Mesh(new THREE.CircleGeometry(.62,24),new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:.22,depthWrite:false}));shadow.rotation.x=-Math.PI/2;shadow.position.y=.02;
 return{root,body,eyes,claws,legs,shadow,smile}}
const crab=makeCrab();scene.add(crab.root);scene.add(crab.shadow);

/* the hero: a low-poly runner made in Higgsfield (image to rigged, animated 3D). If it cannot load, Pitzi runs instead. */
const HERO_URL='https://d8j0ntlcm91z4.cloudfront.net/user_3JLupmCBnVeyPDnR08kyxJxINCO/hf_20261122_091919_b439053f-4747-4a22-8aa0-0a67974a1928.glb';
let hero=null;
if(HERO_URL.startsWith('https://'))new GLTFLoader().load(HERO_URL,g=>{const m=g.scene;
  const b=new THREE.Box3().setFromObject(m),sz=b.getSize(new THREE.Vector3()),k=1.55/(sz.y||1);m.scale.setScalar(k);
  const b2=new THREE.Box3().setFromObject(m),c=b2.getCenter(new THREE.Vector3());m.position.set(-c.x,-b2.min.y,-c.z);
  m.traverse(o=>{if(o.isMesh){o.frustumCulled=false;const mt=o.material;if(mt&&mt.map)mt.map.colorSpace=THREE.SRGBColorSpace}});
  const root=new THREE.Group();root.add(m);scene.add(root);
  const mixer=new THREE.AnimationMixer(m),clip=g.animations[0],act=clip?mixer.clipAction(clip):null;if(act)act.play();
  hero={root,mixer,act};crab.root.visible=false;window.__heroLoaded=true},undefined,e=>{console.warn('hero did not load, Pitzi runs',e);window.__heroLoaded=false});

/* ---------------- the beach ---------------- */
const LANE=[-1.7,0,1.7],TRACK_W=5.6,TRACK_L=220;
function canvasTex(w,h,draw,rep){const c=document.createElement('canvas');c.width=w;c.height=h;draw(c.getContext('2d'),w,h);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=4;
 if(rep){t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(rep[0],rep[1])}return t}
const boardTex=canvasTex(256,256,(g,w,h)=>{g.fillStyle='#c99a66';g.fillRect(0,0,w,h);
 for(let y=0;y<h;y+=32){g.fillStyle=y%64?'#d4a874':'#c4925c';g.fillRect(0,y,w,30);g.fillStyle='rgba(90,55,30,.55)';g.fillRect(0,y+30,w,2);
  g.fillStyle='rgba(90,55,30,.25)';for(let k=0;k<6;k++)g.fillRect((k*53+y*7)%w,y+8+(k%3)*6,22,1.5)}
 g.fillStyle='rgba(255,255,255,.28)';for(const u of[.3534,.6466])g.fillRect(u*w-2,0,4,h);
 g.fillStyle='rgba(90,55,30,.6)';g.fillRect(0,0,6,h);g.fillRect(w-6,0,6,h)},[1,TRACK_L/4]);
const track=new THREE.Mesh(new THREE.PlaneGeometry(TRACK_W,TRACK_L),toon(0xffffff,{map:boardTex}));track.rotation.x=-Math.PI/2;track.position.set(0,.01,-TRACK_L/2+10);scene.add(track);
const sandTex=canvasTex(256,256,(g,w,h)=>{g.fillStyle='#f4c99a';g.fillRect(0,0,w,h);for(let i=0;i<500;i++){g.fillStyle=Math.random()<.5?'rgba(200,160,100,.35)':'rgba(255,255,255,.4)';g.fillRect(Math.random()*w,Math.random()*h,2,2)}},[8,TRACK_L/8]);
const sand=new THREE.Mesh(new THREE.PlaneGeometry(64,TRACK_L),toon(0xffffff,{map:sandTex}));sand.rotation.x=-Math.PI/2;sand.position.set(0,-.02,-TRACK_L/2+10);scene.add(sand);
const seaTex=canvasTex(256,256,(g,w,h)=>{g.fillStyle='#2bb3b1';g.fillRect(0,0,w,h);g.strokeStyle='rgba(255,255,255,.45)';g.lineWidth=3;for(let y=10;y<h;y+=32){g.beginPath();for(let x=0;x<=w;x+=8)g.lineTo(x,y+Math.sin(x/18+y)*4);g.stroke()}},[10,30]);
for(const s of[-1,1]){const sea=new THREE.Mesh(new THREE.PlaneGeometry(120,TRACK_L),new THREE.MeshBasicMaterial({map:seaTex}));sea.rotation.x=-Math.PI/2;sea.position.set(s*(32+60),.0,-TRACK_L/2+10);scene.add(sea);sea.userData.sea=1}
const SEAS=scene.children.filter(o=>o.userData.sea);
/* far islands */
for(const [x,z,r,c] of[[-30,-150,18,0x8fcf8a],[26,-160,22,0x7cc07a],[0,-185,30,0xa6d99a]]){const m=new THREE.Mesh(new THREE.SphereGeometry(r,8,4,0,Math.PI*2,0,Math.PI/2),toon(c));m.scale.y=.45;m.position.set(x,-1,z);scene.add(m)}

/* decorations that scroll past: palms, umbrellas, towels */
const GREEN=toon(0x3fae7a),TRUNK=toon(0xb07a4f),UMB=[toon(0xf2785c),toon(0xf6c64a),toon(0x8a6fd1),toon(0xffffff)];
function palm(){const g=new THREE.Group();let x=0,y=0;for(let i=0;i<6;i++){const c=mesh(new THREE.CylinderGeometry(.16-i*.012,.19-i*.012,.62,5),TRUNK,.08);x+=.05*i;c.position.set(x,y+.31,0);c.rotation.z=-.05*i;g.add(c);y+=.58}
 for(let i=0;i<7;i++){const l=mesh(new THREE.ConeGeometry(1,1,4),GREEN,.06);l.scale.set(.35,.08,1.3);const a=i/7*Math.PI*2;l.position.set(x+Math.sin(a)*.9,y+.05,Math.cos(a)*.9);l.rotation.set(Math.cos(a)*.45,a,0);l.rotation.order='YXZ';l.rotation.x=.35;g.add(l)}
 const co=toon(0x7a5230);for(let i=0;i<3;i++){const n=new THREE.Mesh(new THREE.SphereGeometry(.13,8,6),co);n.position.set(x+Math.sin(i*2)*.18,y-.12,Math.cos(i*2)*.18);g.add(n)}
 return g}
function umbrella(i){const g=new THREE.Group();const p=new THREE.Mesh(new THREE.CylinderGeometry(.04,.04,2.1,6),toon(0xf5f0e6));p.position.y=1.05;g.add(p);
 const c=mesh(new THREE.ConeGeometry(1.15,.55,6,1,true),UMB[i%3],.04);c.material=UMB[i%3].clone();c.material.side=THREE.DoubleSide;c.position.y=2.15;g.add(c);
 const t=new THREE.Mesh(new THREE.BoxGeometry(.9,.04,1.7),UMB[(i+1)%4]);t.position.set(.9,.03,.4);t.rotation.y=.3;g.add(t);return g}
const decor=[];
for(let i=0;i<18;i++){const side=i%2?1:-1,o=i%3===2?umbrella(i):palm();o.position.set(side*(4.4+Math.random()*3.5),0,-i*7-6);o.rotation.y=Math.random()*Math.PI;o.userData.side=side;scene.add(o);decor.push(o)}

/* ---------------- obstacles, shells, gates ---------------- */
const WOOD=toon(0xb07a45),WOOD2=toon(0x8e5c30),ROCK=toon(0x9aa3a8);
const ballTex=canvasTex(256,128,(g,w,h)=>{const c=['#f25c54','#ffffff','#f6c64a','#ffffff','#4aa3df','#ffffff'];c.forEach((k,i)=>{g.fillStyle=k;g.fillRect(i*w/6,0,w/6+1,h)})});
const OB={
 crate:()=>{const g=new THREE.Group();const b=mesh(new THREE.BoxGeometry(1.1,.85,.9),WOOD,.04);b.position.y=.43;g.add(b);for(const y of[.15,.7]){const s=new THREE.Mesh(new THREE.BoxGeometry(1.14,.1,.94),WOOD2);s.position.y=y;g.add(s)}g.userData.h=.85;return g},
 ball:()=>{const g=new THREE.Group();const b=mesh(new THREE.IcosahedronGeometry(.45,1),toon(0xffffff,{map:ballTex}),.04);b.position.y=.45;g.add(b);g.userData.h=.85;g.userData.spin=b;return g},
 rock:()=>{const g=new THREE.Group();const b=mesh(new THREE.DodecahedronGeometry(.55,0),ROCK,.05);b.scale.set(1.15,.75,.9);b.position.y=.38;g.add(b);g.userData.h=.75;return g},
 castle:()=>{const g=new THREE.Group(),m=toon(0xf0d08a);const b=mesh(new THREE.CylinderGeometry(.5,.58,.55,10),m,.05);b.position.y=.27;g.add(b);const t=mesh(new THREE.CylinderGeometry(.28,.32,.4,8),m,.06);t.position.y=.72;g.add(t);
  const f=new THREE.Mesh(new THREE.ConeGeometry(.12,.2,4),toon(0xf25c54));f.position.y=1.0;g.add(f);g.userData.h=.9;return g}};
const OB_KINDS=Object.keys(OB);
const SHELL_MAT=toon(0xffb8a8,{emissive:0x553322});
const shellGeo=new THREE.ConeGeometry(.24,.3,8);
function shell(){const m=mesh(shellGeo,SHELL_MAT,.1);m.rotation.x=Math.PI;m.position.y=.7;const g=new THREE.Group();g.add(m);return g}

function signTex(text,state){return canvasTex(512,288,(g,w,h)=>{
 const bg=state==='ok'?'#d8f5c8':state==='bad'?'#fbd3c9':'#fffaf0',bd=state==='ok'?'#3f8f2f':state==='bad'?'#c0392b':'#5a4534';
 g.fillStyle=bd;rr(g,6,6,w-12,h-12,46);g.fill();g.fillStyle=bg;rr(g,20,20,w-40,h-40,34);g.fill();
 g.fillStyle='#4a3628';g.textAlign='center';g.textBaseline='middle';
 if(text==null){g.font='800 150px "Playpen Sans Hebrew",sans-serif';g.fillStyle='rgba(90,69,52,.35)';g.fillText('?',w/2,h/2+8);return}
 const he=/[֐-׿]/.test(text);g.direction=he?'rtl':'ltr';
 let lines=[text],size=96;const fit=()=>{g.font=`800 ${size}px "Playpen Sans Hebrew",sans-serif`;return lines.every(l=>g.measureText(l).width<w-80)};
 while(!fit()&&size>58)size-=4;
 if(!fit()){const words=text.split(' ');let best=null;for(let i=1;i<words.length;i++){const a=words.slice(0,i).join(' '),b=words.slice(i).join(' ');const m=Math.max(a.length,b.length);if(!best||m<best[0])best=[m,a,b]}
  if(best){lines=[best[1],best[2]];size=88;while(!fit()&&size>34)size-=4}}
 while(!fit()&&size>26)size-=2;
 const lh=size*1.12,y0=h/2-(lines.length-1)*lh/2+6;lines.forEach((l,i)=>g.fillText(l,w/2,y0+i*lh))})}
function rr(g,x,y,w,h,r){g.beginPath();g.moveTo(x+r,y);g.arcTo(x+w,y,x+w,y+h,r);g.arcTo(x+w,y+h,x,y+h,r);g.arcTo(x,y+h,x,y,r);g.arcTo(x,y,x+w,y,r);g.closePath()}
const POST=toon(0x2bb3b1),BEAM=toon(0x8a6fd1),ROPE=new THREE.MeshBasicMaterial({color:0x7a5a40});
function makeGate(q){const g=new THREE.Group();g.userData.gate=q;
 for(const s of[-1,1]){const p=mesh(new THREE.CylinderGeometry(.16,.2,4.2,10),POST,.06);p.position.set(s*2.75,2.1,0);g.add(p);const k=mesh(new THREE.SphereGeometry(.26,12,10),BEAM,.06);k.position.set(s*2.75,4.3,0);g.add(k)}
 const beam=mesh(new THREE.BoxGeometry(5.9,.32,.32),BEAM,.04);beam.position.y=4.1;g.add(beam);
 q.boards=[];q.lanes.forEach((t,i)=>{const b=new THREE.Mesh(new THREE.PlaneGeometry(1.62,.92),new THREE.MeshBasicMaterial({map:signTex(t),transparent:true}));b.position.set(LANE[i],3.0,.18);g.add(b);q.boards.push(b);
  for(const s of[-1,1]){const r=new THREE.Mesh(new THREE.CylinderGeometry(.02,.02,.66,4),ROPE);r.position.set(LANE[i]+s*.6,3.62,.15);g.add(r)}
  const pad=new THREE.Mesh(new THREE.PlaneGeometry(1.5,1.4),new THREE.MeshBasicMaterial({color:t==null?0x000000:0xffffff,transparent:true,opacity:t==null?.06:.22,depthWrite:false}));pad.rotation.x=-Math.PI/2;pad.position.set(LANE[i],.03,.2);g.add(pad)});
 return g}
function markBoard(q,i,state){const b=q.boards[i];if(!b)return;b.material.map.dispose();b.material.map=signTex(q.lanes[i],state);b.material.needsUpdate=true}

/* confetti */
const bits=[];const BIT_COLS=[0xf25c54,0xf6c64a,0x7cc36b,0x4aa3df,0xffffff].map(c=>new THREE.MeshBasicMaterial({color:c,side:THREE.DoubleSide}));const bitGeo=new THREE.PlaneGeometry(.14,.09);
function burst(x,y,z,n=36){if(reduced())n=10;for(let i=0;i<n;i++){const m=new THREE.Mesh(bitGeo,BIT_COLS[i%5]);m.position.set(x,y,z);m.userData.v=new THREE.Vector3((Math.random()-.5)*6,3+Math.random()*5,(Math.random()-.2)*4);m.userData.t=0;scene.add(m);bits.push(m)}}

/* ---------------- the run ---------------- */
let G=null,paused=false,last=0,shakeT=0;
const things=[];   // obstacles and shells
function newRun(){for(const o of things)scene.remove(o);things.length=0;if(G&&G.gateObj)scene.remove(G.gateObj);
 G={on:true,queue:deck(),asked:0,right:0,firstRight:0,missed:[],hearts:3,shells:0,pts:0,speed:8.6,dist:0,since:0,rowAt:0,lane:1,x:0,y:0,vy:0,inv:0,stun:0,gate:null,gateObj:null,fb:0,ended:false,total:0,finish:null};
 G.total=G.queue.length;updHud();}
function updHud(){if(!G)return;$('#hearts').innerHTML=[0,1,2].map(i=>`<span class="${i<G.hearts?'':'off'}">❤️</span>`).join('');
 $('#qprog').innerHTML=`שאלה <b>${Math.min(G.asked+(G.gate?1:0),G.total)}</b> / ${G.total}`;$('#shells b').textContent=G.shells}
function flash(t,cls){flashEl.className='';void flashEl.offsetWidth;flashEl.textContent=t;flashEl.className='show '+cls}

function spawnRow(z){const free=[0,1,2];const n=Math.random()<.3?2:1;const block=shuf(free).slice(0,n);
 for(const l of block){const o=OB[OB_KINDS[Math.random()*OB_KINDS.length|0]]();o.position.set(LANE[l],0,z);o.userData.lane=l;o.userData.ob=1;scene.add(o);things.push(o)}
 if(Math.random()<.75){const l=free.filter(k=>!block.includes(k))[Math.random()*(3-n)|0];for(let i=0;i<5;i++){const s=shell();s.position.set(LANE[l],0,z-2-i*1.5);s.userData.lane=l;s.userData.sh=1;scene.add(s);things.push(s)}}}
function spawnGate(){const e=G.queue.shift();if(!e)return;const q={e,it:e.it,lanes:lanesFor(e.it)};G.gate=q;G.gateObj=makeGate(q);G.gateObj.position.z=-82;scene.add(G.gateObj);
 for(const o of things)if(o.position.z<-62){scene.remove(o);o.userData.dead=1}
 shownLane=-1;showQ(q.it,q);updHud();SND.pop()}
function laneChips(q){return`<div class="lanes" dir="ltr">${q.lanes.map((t,i)=>`<span class="ln${i===G.lane?' cur':''}${t==null?' none':''}" dir="${t&&/[\u0590-\u05FF]/.test(t)?'rtl':'ltr'}">${t==null?'—':esc(t)}</span>`).join('')}</div>`}
function showQ(it,q){let h=`<p class="q">${esc(it.q)}</p>`;
 if(it.pic){const i=PIC.indexOf(it.pic);if(i>=0)h+=`<span class="pic" role="img" aria-label="${esc(it.pic)}" style="background-position:${(i%6)*20}% ${(Math.floor(i/6)*100/3).toFixed(3)}%"></span>`}
 const spk=t=>`<button class="say" data-say="${esc(t)}" aria-label="להשמיע">🔊</button>`;
 if(it.big)h+=`<p class="big">${esc(it.big)}${/[a-z]/i.test(it.big)?spk(it.big):''}</p>`;
 if(it.sent)h+=`<p class="sent">${esc(it.sent).replace('___','<i class="gap"></i>')}</p>`;
 h+=laneChips(q);if(G.asked<2)h+=`<p class="hint">רוצו מתחת לשלט עם התשובה הנכונה</p>`;
 banner.className='banner';banner.innerHTML=h;banner.hidden=false}
let shownLane=-1;function syncChips(){if(!G||!G.gate||G.lane===shownLane)return;shownLane=G.lane;banner.querySelectorAll('.ln').forEach((e,i)=>e.classList.toggle('cur',i===G.lane))}
function judge(){const q=G.gate,lane=G.lane,pick=q.lanes[lane],ok=pick===q.it.a,ci=q.lanes.indexOf(q.it.a);G.asked++;
 if(ok){G.right++;const p=q.e.again?PTS_LATER:PTS_FIRST;if(!q.e.again)G.firstRight++;
  const r=R(),room=Math.max(0,DAY_CAP-r.dpts),got=Math.min(p,room);if(got){r.dpts+=got;G.pts+=got;award(got)}else saveLocal();
  markBoard(q,lane,'ok');burst(LANE[lane],1.6,0);flash(got?`נכון! +${got}`:'נכון!','ok');SND.star(Math.min(2,G.right%3));
  banner.className='banner ok';banner.innerHTML=`<p class="q">נכון! ${esc(q.it.tip||'')}</p>`;
  if(q.e.again)R().miss=R().miss.filter(k=>k!==q.it.k);G.speed=Math.min(13.2,G.speed+.32)}
 else{markBoard(q,lane,pick==null?'':'bad');markBoard(q,ci,'ok');flash(pick==null?'צריך לבחור שלט':'כמעט!','bad');SND.bad();G.stun=.9;
  if(!G.missed.some(m=>m.k===q.it.k))G.missed.push({k:q.it.k,q:q.it.q,sent:q.it.sent||q.it.big||'',pic:q.it.pic||'',a:q.it.a,tip:q.it.tip||''});
  const r=R();if(!r.miss.includes(q.it.k))r.miss=[...r.miss,q.it.k].slice(-40);
  if(!q.e.again){G.queue.splice(Math.min(3,G.queue.length),0,{it:q.it,again:true});G.total++}
  banner.className='banner bad';banner.innerHTML=`<p class="q">התשובה הנכונה:</p><p class="ans"><b>${esc(q.it.a)}</b></p><p class="ans">${esc(q.it.tip||'')}</p><p class="hint">השאלה הזאת תחזור עוד מעט</p>`}
 G.fb=ok?1.8:3.4;G.gate=null;updHud()}
function hit(o){if(G.inv>0||window.__runNoHit)return;G.hearts--;G.inv=1.6;shakeT=.35;SND.bad();const h=$('#hearts');h.classList.remove('hit');void h.offsetWidth;h.classList.add('hit');
 o.userData.fly=new THREE.Vector3((Math.random()-.5)*4,5,-6);updHud();if(G.hearts<=0)end(false)}

function step(dt){
 const sp=G.ended?0:G.speed*(G.gate?.74:1)*(G.stun>0?.55:1);const d=sp*dt;G.dist+=d;G.since+=d;
 /* the world flows toward the camera */
 boardTex.offset.y+=d*(TRACK_L/4)/TRACK_L;sandTex.offset.y+=d*(TRACK_L/8)/TRACK_L;seaTex.offset.x+=dt*.01;
 for(const o of decor){o.position.z+=d;if(o.position.z>10){o.position.z-=126;o.position.x=o.userData.side*(4.4+Math.random()*3.5)}}
 for(let i=things.length-1;i>=0;i--){const o=things[i];o.position.z+=d;
  if(o.userData.fly){o.userData.fly.y-=20*dt;o.position.addScaledVector(o.userData.fly,dt);o.rotation.x+=dt*6}
  if(o.userData.spin)o.userData.spin.rotation.x-=d*2;
  if(o.userData.sh){o.children[0].rotation.y+=dt*3;o.children[0].position.y=.7+Math.sin(G.dist*.8+o.position.z)*.08}
  if(o.position.z>9||o.userData.dead){scene.remove(o);things.splice(i,1);continue}
  if(G.ended||o.userData.fly||o.userData.got)continue;
  const dz=Math.abs(o.position.z),dx=Math.abs(o.position.x-G.x);
  if(o.userData.ob&&dz<.75&&dx<.95&&G.y<o.userData.h-.12)hit(o);
  else if(o.userData.sh&&dz<.8&&dx<.8&&G.y<1.4){o.userData.got=1;o.visible=false;G.shells++;$('#shells b').textContent=G.shells;SND.step()}}
 if(G.gateObj){G.gateObj.position.z+=d;if(G.gate&&G.gateObj.position.z>=0)judge();if(G.gateObj.position.z>2.4){scene.remove(G.gateObj);G.gateObj=null}}
 if(G.finish){G.finish.position.z+=d;if(G.finish.position.z>=0&&!G.ended)end(true)}
 /* what comes next: rows of obstacles, a gate every so often, a finish line at the end */
 if(!G.ended){
  const gateDue=G.since>(G.asked===0&&!G.gateObj?26:58),quiet=G.since>40;
  if(!G.gate&&!G.gateObj&&gateDue&&G.queue.length){spawnGate();G.since=0}
  else if(!G.gate&&!G.gateObj&&!G.queue.length&&!G.finish){G.finish=makeFinish();G.finish.position.z=-70;scene.add(G.finish)}
  if(G.dist-G.rowAt>10.5&&!quiet&&!G.finish&&!(G.gateObj&&G.gateObj.position.z<-64)){G.rowAt=G.dist;if(G.asked>0||G.gateObj||G.dist>8)spawnRow(-82)}
  if(G.fb>0){G.fb-=dt;if(G.fb<=0&&!G.gate)banner.hidden=true}}
 /* the crab */
 const tx=LANE[G.lane];G.x+=(tx-G.x)*Math.min(1,dt*12);
 if(G.y>0||G.vy>0){G.vy-=26*dt;G.y=Math.max(0,G.y+G.vy*dt);if(G.y===0)G.vy=0}
 G.inv=Math.max(0,G.inv-dt);G.stun=Math.max(0,G.stun-dt);
 syncChips();poseRun(dt,sp)}

let tAnim=0;
function poseRun(dt,sp){tAnim+=dt*(sp>0?sp*.9:3);const c=crab,air=G&&G.y>0;
 c.root.position.set(G?G.x:0,G?G.y:0,0);c.root.rotation.y=(G?(LANE[G.lane]-G.x)*.25:0);
 c.body.position.y=air?0:Math.abs(Math.sin(tAnim))*.08;c.body.rotation.z=G&&G.stun>0?Math.sin(G.stun*20)*.25:Math.sin(tAnim)*.05;
 c.body.rotation.x=air?-.25:0;
 for(const l of c.legs)l.p.rotation.x=air?(l.s>0?.5:.5):Math.sin(tAnim*2+l.ph)*.6;
 c.claws.forEach((k,i)=>{k.arm.rotation.x=Math.sin(tAnim+i*Math.PI)*.35-(air?.6:0);k.top.rotation.z=(i?-1:1)*(.2+Math.max(0,Math.sin(tAnim*1.5))*.3)});
 c.root.visible=!(G&&G.inv>0&&Math.floor(G.inv*12)%2);
 c.shadow.position.set(c.root.position.x,.02,0);const s=1-Math.min(.5,(G?G.y:0)*.25);c.shadow.scale.set(s,s,s);
 if(hero){c.root.visible=false;hero.root.position.copy(c.root.position);hero.root.rotation.y=Math.PI+(G?(LANE[G.lane]-G.x)*-.3:0);hero.root.rotation.z=G&&G.stun>0?Math.sin(G.stun*20)*.15:0;
  hero.root.visible=!(G&&G.inv>0&&Math.floor(G.inv*12)%2);hero.mixer.update(dt*(air?.25:Math.max(.6,sp/9)))}}
function poseIdle(dt){tAnim+=dt*2.5;const c=crab;c.root.position.set(0,0,0);c.root.rotation.y=Math.sin(tAnim*.3)*.25;c.body.position.y=Math.abs(Math.sin(tAnim))*.04;c.body.rotation.z=0;c.body.rotation.x=0;
 for(const l of c.legs)l.p.rotation.x=0;c.claws[0].arm.rotation.x=0;c.claws[1].arm.rotation.x=-1.1+Math.sin(tAnim*2)*.35;c.claws[1].top.rotation.z=-.2-Math.max(0,Math.sin(tAnim*3))*.4;c.claws[0].top.rotation.z=.2;
 c.root.visible=!hero;c.shadow.position.set(0,.02,0);c.shadow.scale.setScalar(1);
 if(hero){hero.root.position.set(0,0,0);hero.root.rotation.set(0,Math.sin(tAnim*.3)*.35,0);hero.root.visible=true;hero.mixer.update(dt*.55)}}

function makeFinish(){const g=new THREE.Group();for(const s of[-1,1]){const p=mesh(new THREE.CylinderGeometry(.16,.2,4.2,10),toon(0xf6c64a),.06);p.position.set(s*2.75,2.1,0);g.add(p)}
 const flagTex=canvasTex(512,128,(c,w,h)=>{for(let x=0;x<16;x++)for(let y=0;y<4;y++){c.fillStyle=(x+y)%2?'#3a2a20':'#ffffff';c.fillRect(x*32,y*32,32,32)}});
 const f=new THREE.Mesh(new THREE.PlaneGeometry(5.6,1.1),new THREE.MeshBasicMaterial({map:flagTex,side:THREE.DoubleSide}));f.position.y=3.8;g.add(f);return g}

/* ---------------- camera, loop, resize ---------------- */
function fit(){const w=stageEl.clientWidth,h=stageEl.clientHeight;renderer.setSize(w,h,false);cam.aspect=w/h;cam.fov=w/h<.62?64:56;cam.updateProjectionMatrix()}
addEventListener('resize',fit);fit();
const camRun=new THREE.Vector3(0,5.2,8.6),camMenu=new THREE.Vector3(0,2.1,4.6);let camMix=0;
function frame(t){requestAnimationFrame(frame);const dt=Math.min(.05,(t-(last||t))/1000)*(window.__runFast||1);last=t;
 if(paused){renderer.render(scene,cam);return}
 const run=G&&G.on&&!G.ended;
 if(run)step(dt);else{poseIdle(dt);boardTex.offset.y+=dt*.15;seaTex.offset.x+=dt*.01}
 for(let i=bits.length-1;i>=0;i--){const b=bits[i];b.userData.t+=dt;b.userData.v.y-=12*dt;b.position.addScaledVector(b.userData.v,dt);b.rotation.x+=dt*8;b.rotation.y+=dt*6;if(b.userData.t>1.4){scene.remove(b);bits.splice(i,1)}}
 camMix+=((run?1:0)-camMix)*Math.min(1,dt*2.2);
 const cx=(G&&run?G.x*.45:0);cam.position.lerpVectors(camMenu,camRun,camMix);cam.position.x+=cx;
 if(shakeT>0&&!reduced()){shakeT-=dt;cam.position.x+=(Math.random()-.5)*.25;cam.position.y+=(Math.random()-.5)*.2}
 cam.lookAt(cx*.6,camMix*1.2+.7,-6*camMix-1);
 renderer.render(scene,cam)}

/* ---------------- input ---------------- */
function act(k){if(!G||!G.on||G.ended||paused)return;
 if(k==='left'&&G.lane>0){G.lane--;SND.tap()}else if(k==='right'&&G.lane<2){G.lane++;SND.tap()}
 else if(k==='jump'&&G.y===0){G.vy=9.2;SND.pull()}}
addEventListener('keydown',e=>{const m={ArrowLeft:'left',KeyA:'left',ArrowRight:'right',KeyD:'right',ArrowUp:'jump',KeyW:'jump',Space:'jump'}[e.code];if(m){e.preventDefault();act(m)}
 if(e.code==='Escape')setPause(!paused)});
pad.addEventListener('pointerdown',e=>{const b=e.target.closest('.pb');if(b){e.preventDefault();act(b.dataset.k)}});
let t0=null;
stageEl.addEventListener('touchstart',e=>{if(e.target.closest('.pb,.sheet,button'))return;const t=e.touches[0];t0={x:t.clientX,y:t.clientY,done:false}},{passive:true});
stageEl.addEventListener('touchmove',e=>{if(!t0||t0.done)return;const t=e.touches[0],dx=t.clientX-t0.x,dy=t.clientY-t0.y;
 if(Math.abs(dx)>28&&Math.abs(dx)>Math.abs(dy)){act(dx<0?'left':'right');t0.done=true}else if(dy<-28&&Math.abs(dy)>Math.abs(dx)){act('jump');t0.done=true}},{passive:true});
stageEl.addEventListener('touchend',()=>{t0=null});
banner.addEventListener('click',e=>{const b=e.target.closest('[data-say]');if(b)sayEn(b.dataset.say)});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden'&&G&&G.on&&!G.ended)setPause(true)});
function setPause(v){if(!G||!G.on||G.ended)return;paused=v;if(v){menu.hidden=false;menu.innerHTML=`<div class="card"><h2>הפסקה</h2><p>הריצה מחכה לכם.</p></div><button class="big-btn" data-go="resume">ממשיכים</button>`}else{menu.hidden=true;last=0}}

/* ---------------- menus ---------------- */
const who=()=>API&&S.u?`<p class="who">${esc(S.u.n)} · <bdi>${S.pts}</bdi> נקודות</p>`:API?`<p class="who">לא מחוברים, אז הנקודות לא ייכנסו לטבלת הכיתה. <a href="index.html">להתחברות</a></p>`:'';
function start(){const r=R();hud.hidden=pad.hidden=true;menu.hidden=false;
 menu.innerHTML=`<div class="card"><img class="crabhead" src="assets/sp/crab_wave.webp" alt=""><h1>ריצת החוף</h1>
  <p class="goal">רצים, עונים, ומתאמנים עוד ועוד. כל השאלות מהדפים שקיבלתם מהמורה.</p>
  <div class="how"><span><b>◀ ▶</b>מחליפים מסלול</span><span><b>▲</b>קופצים מעל מכשול</span><span><b>🪧</b>רצים מתחת לתשובה הנכונה</span></div>
  <p>טעיתם? רואים את התשובה הנכונה, והשאלה חוזרת עוד מעט באותה ריצה.</p>${r.best?`<p class="who">השיא שלכם: <bdi>${r.best}</bdi> תשובות נכונות</p>`:''}${who()}</div>
  <button class="big-btn" data-go="run">רצים!</button><a class="sm-btn" href="index.html">חזרה למשחק</a>`}
function begin(){unlock();menu.hidden=true;hud.hidden=false;pad.hidden=false;banner.hidden=true;newRun();last=0}
function end(done){if(!G||G.ended)return;G.ended=true;G.gate=null;banner.hidden=true;const r=R();r.runs++;r.best=Math.max(r.best,G.firstRight);saveLocal();if(API&&S.u)push();
 if(done){burst(0,2,-1,60);SND.win()}
 setTimeout(()=>{hud.hidden=pad.hidden=true;menu.hidden=false;
  const mini=w=>{const i=PIC.indexOf(w);return i<0?'':`<span class="mpic" style="background-position:${(i%6)*20}% ${(Math.floor(i/6)*100/3).toFixed(3)}%"></span>`};
  const miss=G.missed.map(m=>`<li>${m.pic?mini(m.pic):''}${m.sent?`<bdi dir="ltr">${esc(m.sent)}</bdi>`:m.pic?'':esc(m.q)} ← <b>${esc(m.a)}</b></li>`).join('');
  menu.innerHTML=`<div class="card"><img class="crabhead" src="assets/sp/${done?'crab_star':'crab_oops'}.webp" alt=""><h2>${done?'הגעתם לסוף המסלול!':'נגמרו הלבבות'}</h2>
   <div class="score"><span><b>${G.firstRight}</b>נכון בפעם הראשונה</span><span><b>${G.shells}</b>צדפים</span><span><b dir="ltr">+${G.pts}</b>נקודות</span></div>
   ${G.missed.length?`<p>את אלה כדאי לחזור עליהם. הם יופיעו שוב בריצה הבאה:</p><ul class="miss">${miss}</ul>`:`<p class="goal">אף טעות! ככה מגיעים מוכנים למבחן.</p>`}
   ${R().dpts>=DAY_CAP?'<p class="who">היום כבר אספתם את כל הנקודות של ריצת החוף. אפשר להמשיך לרוץ ולהתאמן.</p>':''}${who()}</div>
   <button class="big-btn" data-go="run">רצים שוב</button><a class="sm-btn" href="index.html">חזרה למשחק</a>`},done?1400:900)}
menu.addEventListener('click',e=>{const b=e.target.closest('[data-go]');if(!b)return;SND.tap();if(b.dataset.go==='run')begin();else if(b.dataset.go==='resume')setPause(false)});

/* test hooks */
window.__run={G:()=>G,act,begin,lanes:()=>G&&G.gate?G.gate.lanes:null,answer:()=>G&&G.gate?G.gate.it.a:null,
 goLane:i=>{if(G)G.lane=i},noHit:v=>{window.__runNoHit=v}};
/* fonts first, so the signs are drawn in the game's own hand */
Promise.race([Promise.all([document.fonts.load('800 40px "Playpen Sans Hebrew"','אבג'),document.fonts.load('800 40px "Playpen Sans Hebrew"','Abc')]),new Promise(r=>setTimeout(r,2500))])
 .finally(()=>{start();requestAnimationFrame(frame)});
