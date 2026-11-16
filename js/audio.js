/* Generated soundtrack and sound effects (Web Audio, no files).
   Music: C major pentatonic, two 8-bar sections (A: C Am F G, B: F C Am G), soft kalimba plucks over sine pads.
   Everything goes through one master gain and a gentle low-pass; levels are kept low on purpose. */
import {SET} from './state.js';

let AC=null,MASTER=null,MUS=null,SFX=null,timer=0,next=0,step=0,wanted=false;
const hz=m=>440*Math.pow(2,(m-69)/12);
export const BPM=76,STEP=60/BPM/2;

/* builds the graph on any (real or offline) context; returns the buses */
export function graph(ctx){
 const master=ctx.createGain();master.gain.value=.8;
 const lp=ctx.createBiquadFilter();lp.type='lowpass';lp.frequency.value=2400;lp.Q.value=.3;
 const dl=ctx.createDelay(1);dl.delayTime.value=STEP*1.5;const fb=ctx.createGain();fb.gain.value=.2;const wet=ctx.createGain();wet.gain.value=.35;
 const mus=ctx.createGain();mus.gain.value=.8;const sfx=ctx.createGain();sfx.gain.value=.9;
 mus.connect(lp);lp.connect(master);lp.connect(dl);dl.connect(fb);fb.connect(dl);dl.connect(wet);wet.connect(master);
 sfx.connect(master);master.connect(ctx.destination);
 return{master,mus,sfx}}
function ac(){if(!AC){try{AC=new(window.AudioContext||window.webkitAudioContext)();const g=graph(AC);MASTER=g.master;MUS=g.mus;SFX=g.sfx}catch(e){AC=null}}
 if(AC&&AC.state!=='running'&&AC.state!=='closed')AC.resume().catch(()=>{});return AC}   // iOS also has 'interrupted' (after a call, Siri, a locked screen)

/* the recorded voice (js/state.js) plays on this same context, so the output is already awake when a word is spoken.
   It gets its own bus straight to the output (no music filter); the music steps back a little while a word is spoken. */
let VOX=null;
export const voiceCtx=()=>ac();
export function voiceOut(){if(!ac())return null;if(!VOX){VOX=AC.createGain();VOX.gain.value=1;VOX.connect(AC.destination)}return VOX}
export function duck(on){if(!AC||!MUS)return;try{MUS.gain.setTargetAtTime(on?.3:.8,AC.currentTime,on?.03:.25)}catch(e){}}

/* kalimba / music-box pluck: sine body, a quiet octave partial that dies fast, tiny click of a third partial */
export function pluck(ctx,out,m,t,v){
 const f=hz(m),g=ctx.createGain();g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(v,t+.006);g.gain.exponentialRampToValueAtTime(v*.35,t+.18);g.gain.exponentialRampToValueAtTime(.0008,t+1.5);
 const o=ctx.createOscillator();o.type='sine';o.frequency.value=f;o.connect(g);
 const g2=ctx.createGain();g2.gain.setValueAtTime(v*.22,t);g2.gain.exponentialRampToValueAtTime(.0008,t+.3);
 const o2=ctx.createOscillator();o2.type='sine';o2.frequency.value=f*2;o2.connect(g2);
 const g3=ctx.createGain();g3.gain.setValueAtTime(v*.08,t);g3.gain.exponentialRampToValueAtTime(.0008,t+.07);
 const o3=ctx.createOscillator();o3.type='sine';o3.frequency.value=f*4.02;o3.connect(g3);
 g.connect(out);g2.connect(out);g3.connect(out);
 o.start(t);o2.start(t);o3.start(t);o.stop(t+1.6);o2.stop(t+.35);o3.stop(t+.1)}
export function pad(ctx,out,ms,t,d){ms.forEach(m=>{const o=ctx.createOscillator(),g=ctx.createGain();o.type='sine';o.frequency.value=hz(m);
 g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(.03,t+d*.3);g.gain.linearRampToValueAtTime(.022,t+d*.7);g.gain.linearRampToValueAtTime(0,t+d);
 o.connect(g);g.connect(out);o.start(t);o.stop(t+d+.05)})}

// melody in eighth notes (0 = rest), one row per bar; chord tones + pentatonic passing notes only
const A_MEL=[[64,0,67,0,69,0,67,64],[72,0,69,0,67,0,64,0],[69,0,72,0,74,0,72,69],[67,0,69,0,67,0,62,0],
             [64,67,0,69,0,72,0,69],[67,0,64,0,60,0,64,0],[65,0,69,0,72,69,0,65],[67,0,62,0,67,0,0,0]];
const B_MEL=[[72,0,0,69,0,72,0,0],[67,0,64,0,67,0,72,0],[69,0,0,64,0,69,0,72],[74,0,71,0,67,0,0,0],
             [72,0,69,0,65,0,69,0],[67,0,72,0,76,0,72,0],[69,0,72,0,69,0,64,0],[62,0,67,0,62,0,0,0]];
const A_CH=[[48,55,64],[45,52,60],[41,48,57],[43,50,59]],B_CH=[[41,48,57],[48,55,64],[45,52,60],[43,50,59]];
export const SONG_STEPS=8*8*3;   // form: A A B
/* schedule one eighth-note step of the song at time t */
export function songStep(ctx,out,n,t){
 const s=n%SONG_STEPS,sec=s<128?0:1,bar=(s/8|0)%8,i=s%8,mel=(sec?B_MEL:A_MEL)[bar][i],ch=(sec?B_CH:A_CH)[bar%4];
 if(i===0)pad(ctx,out,ch,t,STEP*8.1);
 if(i===0)pluck(ctx,out,ch[0],t,.085);
 if(i===4)pluck(ctx,out,ch[1],t,.06);
 if(sec&&(i===2||i===6))pluck(ctx,out,ch[2],t,.04);
 if(mel)pluck(ctx,out,mel,t,s>=64&&s<128?.12:.1)}
function tick(){if(!AC)return;while(next<AC.currentTime+.3){songStep(AC,MUS,step,next);next+=STEP;step++}}
function run(on){clearInterval(timer);timer=0;if(!on||!SET.music||!ac())return;next=AC.currentTime+.1;timer=setInterval(tick,100)}
/* ---------- iPhone and iPad: the ring/silent switch ----------
   iOS treats Web Audio as "ambient" sound and mutes it when the side switch is on silent, which is how most children's
   phones are set. Two ways out, both harmless elsewhere:
   - iOS 17 and later: tell the browser this page plays media (navigator.audioSession.type='playback').
   - older iOS: keep a silent <audio> element looping while the game is in front; that moves the whole page,
     Web Audio included, to the media channel. It is dropped when the page is hidden so no player shows on the lock screen. */
const IOS=/iP(hone|ad|od)/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
let keep=null,keepUrl='';
function playbackSession(){try{if(navigator.audioSession){if(navigator.audioSession.type!=='playback')navigator.audioSession.type='playback';return true}}catch(e){}return false}
function silentUrl(){if(keepUrl)return keepUrl;const sr=8000,n=sr/2,b=new Uint8Array(44+n),v=new DataView(b.buffer),w=(o,t)=>{for(let i=0;i<t.length;i++)b[o+i]=t.charCodeAt(i)};
 w(0,'RIFF');v.setUint32(4,36+n,true);w(8,'WAVEfmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,sr,true);v.setUint32(28,sr,true);v.setUint16(32,1,true);v.setUint16(34,8,true);w(36,'data');v.setUint32(40,n,true);b.fill(128,44);
 keepUrl=URL.createObjectURL(new Blob([b],{type:'audio/wav'}));return keepUrl}
function keepAwake(on){if(!IOS||playbackSession())return;
 try{if(!on){if(keep){keep.pause();keep.removeAttribute('src');keep.load();keep=null}return}
  if(!keep){keep=new Audio();keep.loop=true;keep.preload='auto';keep.setAttribute('playsinline','');keep.setAttribute('x-webkit-airplay','deny');keep.src=silentUrl()}
  if(keep.paused){const p=keep.play();if(p&&p.catch)p.catch(()=>{})}}catch(e){}}
playbackSession();
/* call from every user gesture (cheap after the first) */
export function unlock(){keepAwake(true);if(!ac())return;if(!wanted){wanted=true;run(true)}}
export function musicOn(v){SET.music=v;if(wanted)run(v&&document.visibilityState==='visible')}
document.addEventListener('visibilitychange',()=>{const vis=document.visibilityState==='visible';if(wanted)run(vis);
 if(!vis)keepAwake(false);
 if(AC){if(vis)AC.resume().catch(()=>{});else AC.suspend().catch(()=>{})}});

/* ---------- sound effects: short sine/triangle blips only ---------- */
export function blip(ctx,out,f,d,v,f2,type,at){const t=at||ctx.currentTime,o=ctx.createOscillator(),g=ctx.createGain();o.type=type||'sine';o.frequency.setValueAtTime(f,t);if(f2)o.frequency.exponentialRampToValueAtTime(f2,t+d);
 g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(v,t+.008);g.gain.exponentialRampToValueAtTime(.0008,t+d);o.connect(g);g.connect(out);o.start(t);o.stop(t+d+.02)}
const fx=(...a)=>{if(!SET.sfx||!ac())return;blip(AC,SFX,...a)};
export const SND={
 tap:()=>fx(660,.07,.05),
 pull:()=>fx(180,.09,.04,230),
 shoot:()=>fx(240,.22,.09,680),
 pop:()=>{fx(700,.16,.11,1400);if(SET.sfx&&AC)blip(AC,SFX,1050,.22,.06,1580,'sine',AC.currentTime+.07)},
 bad:()=>fx(220,.26,.07,150,'triangle'),
 plank:()=>fx(330,.1,.08,260,'triangle'),
 snap:()=>{fx(200,.2,.08,90,'triangle')},
 step:()=>fx(520,.05,.035),
 star:i=>{if(!SET.sfx||!ac())return;blip(AC,SFX,[784,988,1175][i]||784,.35,.09)},
 win:()=>{if(!SET.sfx||!ac())return;[523,659,784,1047].forEach((f,i)=>blip(AC,SFX,f,.4,.08,0,'sine',AC.currentTime+i*.11))},
 unlock:()=>{if(!SET.sfx||!ac())return;[659,784,988,1319].forEach((f,i)=>blip(AC,SFX,f,.5,.07,0,'sine',AC.currentTime+i*.14))}};

/* render the soundtrack offline and report levels (used by tests; nobody can listen in CI) */
export async function measure(seconds=30){
 const OAC=window.OfflineAudioContext||window.webkitOfflineAudioContext,sr=22050,ctx=new OAC(1,sr*seconds,sr),g=graph(ctx);
 for(let n=0,t=.1;t<seconds-2;n++,t+=STEP)songStep(ctx,g.mus,n,t);
 [5,12,20].forEach(t=>{blip(ctx,g.sfx,700,.16,.11,1400,'sine',t);blip(ctx,g.sfx,240,.22,.09,680,'sine',t+.5);[523,659,784,1047].forEach((f,i)=>blip(ctx,g.sfx,f,.4,.08,0,'sine',t+1+i*.11))});
 const buf=await ctx.startRendering(),d=buf.getChannelData(0);let peak=0,sq=0;for(let i=0;i<d.length;i++){const a=Math.abs(d[i]);if(a>peak)peak=a;sq+=d[i]*d[i]}
 return{peak,rms:Math.sqrt(sq/d.length),seconds}}
