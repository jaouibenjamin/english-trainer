/* The slow-playback stretch (js/stretch.js), measured on real clips: node tests/stretch_check.mjs
   For every clip checked: the result is 1/0.75 as long (within 3%), is not louder than the original at its peak (no
   clipping), keeps the loudness (RMS within 1.5 dB), and keeps the pitch (the voice's period, measured by
   autocorrelation over the voiced frames, moves by less than 3%). Needs ffmpeg to decode the MP3s. */
import {stretch} from '../js/stretch.js';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const ROOT=path.dirname(path.dirname(fileURLToPath(import.meta.url))),SR=24000,RATE=.75;
const rows=readFileSync(path.join(ROOT,'assets/voice/sources.tsv'),'utf8').split('\n').slice(1,-1).map(l=>l.split('\t')).filter(r=>r[0]==='voice-en');
const head=readFileSync(path.join(ROOT,'assets/voice/sources.tsv'),'utf8').split('\n')[0].split('\t'),FI=head.indexOf('file'),TI=head.indexOf('text'),SI=head.indexOf('s'),EI=head.indexOf('e');
const all=process.argv.includes('--all'),pickN=all?rows.length:40;
const pick=rows.filter((_,i)=>i%Math.max(1,Math.floor(rows.length/pickN))===0).slice(0,pickN);
const dec=f=>{const b=execFileSync('ffmpeg',['-v','error','-i',path.join(ROOT,'assets/voice',f),'-f','f32le','-ac','1','-ar',String(SR),'-'],{maxBuffer:1<<28});return new Float32Array(b.buffer,b.byteOffset,b.length>>2)};
const peak=a=>{let p=0;for(const v of a)p=Math.max(p,Math.abs(v));return p},rms=a=>{let s=0;for(const v of a)s+=v*v;return Math.sqrt(s/a.length)};
/* the voice's period (in samples) in the 40 ms frame at o: the lag between 2.5 and 12.5 ms with the highest
   autocorrelation; 0 when the frame is quiet or not clearly voiced */
function periodAt(a,o,tot){const F=Math.round(SR*.04),lo=Math.round(SR*.0025),hi=Math.round(SR*.0125);if(o<0||o+F+hi>a.length)return 0;
 const f=a.subarray(o,o+F+hi);if(rms(f.subarray(0,F))<tot*.6)return 0;
 let e0=0;for(let i=0;i<F;i++)e0+=f[i]*f[i];let best=0,bl=0;
 for(let l=lo;l<=hi;l++){let c=0,e1=0;for(let i=0;i<F;i++){c+=f[i]*f[i+l];e1+=f[i+l]*f[i+l]}const v=c/Math.sqrt(e0*e1+1e-12);if(v>best){best=v;bl=l}}
 return best>.7?bl:0}
/* pitch of the slow clip against the original, moment by moment: the frame at time t of the slow clip is compared with
   the frame at t*rate of the original; the median of the period ratios (1 = same pitch; a plain slowed-down tape gives 1.33) */
function pitchRatio(x,y){const tx=rms(x),ty=rms(y),F=Math.round(SR*.02),rs=[];
 for(let o=0;o<y.length;o+=F){const py=periodAt(y,o,ty),px=periodAt(x,Math.round(o*RATE),tx);if(px&&py)rs.push(py/px)}
 rs.sort((a,b)=>a-b);return rs.length>=3?rs[rs.length>>1]:0}
let bad=0,worst={len:0,peak:0,rms:0,pitch:0},n=0,voiced=0;
for(const r of pick){const full=dec(r[FI]),s=Math.max(0,+r[SI]-30)*SR/1000|0,e=Math.min(full.length,(+r[EI]+80)*SR/1000|0),x=full.subarray(s,e),y=stretch(x,SR,RATE);
 const len=y.length/(x.length/RATE),pk=peak(y)/peak(x),lv=20*Math.log10(rms(y)/rms(x)),pr=pitchRatio(x,y),pitch=pr||1,p0=pr,p1=pr;
 n++;if(p0&&p1)voiced++;
 worst.len=Math.max(worst.len,Math.abs(len-1));worst.peak=Math.max(worst.peak,pk);worst.rms=Math.max(worst.rms,Math.abs(lv));worst.pitch=Math.max(worst.pitch,Math.abs(pitch-1));
 const ok=Math.abs(len-1)<.03&&pk<=1.02&&Math.abs(lv)<1.5&&Math.abs(pitch-1)<.03&&y.every(Number.isFinite);
 if(!ok){bad++;console.log('FAIL',r[TI],{len:+len.toFixed(3),peak:+pk.toFixed(3),rmsdB:+lv.toFixed(2),pitch:+pitch.toFixed(3)})}}
console.log(`${n} clips at ${RATE}x (${voiced} with a measurable pitch): length off by at most ${(worst.len*100).toFixed(1)}%, peak at most ${worst.peak.toFixed(3)} of the original, loudness off by at most ${worst.rms.toFixed(2)} dB, pitch off by at most ${(worst.pitch*100).toFixed(1)}%`);
{const r=pick[Math.min(5,pick.length-1)],full=dec(r[FI]),x=full.subarray(Math.max(0,+r[SI]-30)*SR/1000|0,Math.min(full.length,(+r[EI]+80)*SR/1000|0));
 const tape=new Float32Array(Math.floor(x.length/RATE));for(let i=0;i<tape.length;i++){const p=i*RATE,a=Math.floor(p);tape[i]=x[a]+(x[Math.min(x.length-1,a+1)]-x[a])*(p-a)}
 const t=pitchRatio(x,tape);console.log(`control: the same clip slowed like a tape (pitch drops) measures ${t.toFixed(3)}; the check must see it is not 1`);if(!(t>1.2)){bad++;console.log('FAIL the pitch measure does not see a slowed tape')}}
console.log(bad?`${bad} FAILED`:'ALL PASSED');process.exit(bad?1:0);
