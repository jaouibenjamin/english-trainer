/* Slower speech at the same pitch (for the "slowly" button): the samples of a clip are laid out again at a slower pace.
   Method (WSOLA): the clip is cut into short overlapping windows; each next window is taken from where the slower pace
   says, moved a few milliseconds to the spot that best continues the wave already written, and cross-faded in. Whole
   periods of the voice are repeated, so it gets longer and not lower. Pure arithmetic on the samples: no network, no
   browser API, so tests/stretch_check.mjs can measure it with node. */
export function stretch(x,sr,rate){
 const n=x.length;if(!(rate>0)||rate>=1||n<sr*.06)return Float32Array.from(x);
 const W=Math.round(sr*.03)&~1,Hs=W>>1,Ha=Hs*rate,D=Math.round(sr*.01),step=2;   // 30 ms windows, half overlapped; search 10 ms each way
 const win=new Float32Array(W);for(let i=0;i<W;i++)win[i]=.5-.5*Math.cos(2*Math.PI*(i+.5)/W);
 const frames=Math.max(1,Math.ceil((n-W)/Ha)+1),out=new Float32Array((frames-1)*Hs+W),norm=new Float32Array(out.length);
 let prev=0;
 for(let k=0;k<frames;k++){
  let at=Math.min(Math.max(0,n-W),Math.round(k*Ha));
  if(k){const want=prev+Hs;   // where the wave would go on by itself
   if(want+Hs<=n){let best=-Infinity,bi=at;const lo=Math.max(0,at-D),hi=Math.min(n-W,at+D);
    for(let s=lo;s<=hi;s++){let c=0,e=1e-9;for(let i=0;i<Hs;i+=step){const a=x[s+i];c+=a*x[want+i];e+=a*a}
     const v=c/Math.sqrt(e);if(v>best){best=v;bi=s}}
    at=bi}}
  const o=k*Hs;for(let i=0;i<W&&at+i<n;i++){out[o+i]+=x[at+i]*win[i];norm[o+i]+=win[i]}
  prev=at}
 for(let i=0;i<out.length;i++)if(norm[i]>1e-3)out[i]/=norm[i];
 return out}
