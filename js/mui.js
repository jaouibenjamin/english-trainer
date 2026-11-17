/* How fractions are written on screen: stacked numerator over denominator, wholes beside them, always left to right
   (as in the pupils' math books, also inside Hebrew sentences). */
import {esc} from './state.js';

export const fr=f=>{
 if(!f.n)return`<span class="mx" dir="ltr"><b class="mw">${f.w}</b></span>`;
 return`<span class="mx" dir="ltr">${f.w?`<b class="mw">${f.w}</b>`:''}<span class="fr"><i>${f.n}</i><i>${f.d}</i></span></span>`};
export const expr=p=>`<span class="ex" dir="ltr">${fr(p.a)}${p.b?`<em>${p.op}</em>${fr(p.b)}`:''}</span>`;
export const eqn=p=>`<span class="ex" dir="ltr">${fr(p.a)}${p.b?`<em>${p.op}</em>${fr(p.b)}`:''}<em>=</em>${fr(p.ans)}</span>`;

/* a worked step is plain text such as "3 1/4 = 2 5/4": every run of numbers and signs is set left to right,
   and every "a/b" (with its wholes) becomes a stacked fraction */
const FR=/(?:(\d+) )?(\d+)\/(\d+)/g;
export function mtext(t){
 return esc(t).replace(/\d[\d\s\/=+−×÷]*\d|\d/g,run=>{
  const body=run.replace(FR,(m,w,n,d)=>fr({w:w?+w:0,n:+n,d:+d}));
  return`<bdi class="mrun" dir="ltr">${body}</bdi>`})}

/* a pizza, drawn as SVG: d slices, the first k of them with topping. cut=false draws a whole pizza with no cut lines.
   gone: slices already eaten (shown as crumbs on the plate). */
export function pizza(d,k,{cut=true,tone='a',gone=0,lit=-1,size=''}={}){
 const P=[],r=40,sl=(i,fill,cls)=>{const a0=-Math.PI/2+i*2*Math.PI/d,a1=a0+2*Math.PI/d,x0=Math.cos(a0)*r,y0=Math.sin(a0)*r,x1=Math.cos(a1)*r,y1=Math.sin(a1)*r;
  return d===1?`<circle class="${cls}" data-s="${i}" r="${r}" fill="${fill}"/>`:`<path class="${cls}" data-s="${i}" d="M0 0L${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)}Z" fill="${fill}"/>`};
 const top=tone==='b'?'#a9c58f':'#f4c46b',pep=tone==='b'?'#5f8a4a':'#d9604a';
 for(let i=0;i<d;i++){const on=i<k,eaten=i>=k&&i<k+gone;P.push(sl(i,on?top:eaten?'#efe2c6':'#fffaf0',`psl${on?' pon':''}${eaten?' pgone':''}${i===lit?' plit':''}`))}
 /* pepperoni: one or two per topped slice, at fixed spots so the pizza does not flicker when it is drawn again */
 const dots=[];for(let i=0;i<k;i++){const a=-Math.PI/2+(i+.5)*2*Math.PI/d;for(const [rr,da] of d<=4?[[22,-.22],[30,.18]]:[[25,0]])dots.push(`<circle cx="${(Math.cos(a+da/(d/4))*rr).toFixed(1)}" cy="${(Math.sin(a+da/(d/4))*rr).toFixed(1)}" r="${d>6?3.6:4.6}" fill="${pep}" pointer-events="none"/>`)}
 const cuts=cut&&d>1?Array.from({length:d},(_,i)=>{const a=-Math.PI/2+i*2*Math.PI/d;return`<line x1="0" y1="0" x2="${(Math.cos(a)*r).toFixed(2)}" y2="${(Math.sin(a)*r).toFixed(2)}"/>`}).join(''):'';
 return`<svg class="pzs ${size}" viewBox="-50 -50 100 100" aria-hidden="true"><circle r="47" class="crust"/>${P.join('')}${dots.join('')}<g class="cuts">${cuts}</g><circle r="40" class="rim"/></svg>`}
