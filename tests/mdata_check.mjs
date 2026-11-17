import * as M from '../js/mdata.js';   // node tests/mdata_check.mjs: 30,000 generated exercises, checked
const {top,same,formOK}=M;let bad=0,n=0;
const chk=(p,label)=>{n++;
 const va=top(p.a)/p.a.d, vb=p.b?top(p.b)/p.b.d:0, v=top(p.ans)/p.ans.d;
 const exp=p.kind==='add'?va+vb:p.kind==='sub'?va-vb:va;
 const err=[];
 if(Math.abs(exp-v)>1e-9)err.push('value');
 if(!formOK(p.ans,p.form))err.push('form');
 if(p.alts.length<3)err.push('alts'+p.alts.length);
 for(const x of p.alts){if(same(x.f,p.ans))err.push('altSame');if(!formOK(x.f,p.form))err.push('altForm')}
 if(p.kind==='sub'&&p.borrow&&!(p.a.n<p.b.n))err.push('noborrow');
 if(p.kind==='add'&&p.carry!==(p.a.n+p.b.n>=p.a.d))err.push('carry');
 if(p.a.n>=p.a.d&&p.kind!=='i2m')err.push('aform');
 if(err.length){bad++;if(bad<15)console.log(label,err.join(','),JSON.stringify([p.a,p.b,p.ans]))}};
for(let i=0;i<3000;i++){chk(M.m2i(),'m2i');chk(M.i2m(),'i2m');chk(M.add(),'add');chk(M.sub(),'sub');chk(M.sub('ff'),'subff');chk(M.add('ff',false),'addff')}
for(const m of['conv','add','sub'])for(let i=0;i<300;i++){const s=M.pizzaSet(m,4);if(s.length<4){bad++;console.log('pizzaSet short',m,s.length)}s.forEach(p=>{chk(p,'pz'+m);if(M.pizzasFor(p)>4)console.log('big')})}
for(const m of['conv','add','sub','exam'])for(let i=0;i<300;i++){const s=M.set(m,m==='exam'?10:6);if(s.length<(m==='exam'?10:6))console.log('short',m,s.length);s.forEach(p=>chk(p,'set'+m))}
console.log('checked',n,'bad',bad);
const ex=[M.m2i(4,2,3),M.i2m(5,2,1),M.add('mm',true,5),M.sub('mm',true,4),M.sub('wm',true,3)];
for(const p of ex)console.log(p.kind,M.fx(p.a),p.op||'',p.b?M.fx(p.b):'','=',M.fx(p.ans),'| alts',p.alts.slice(0,3).map(x=>M.fx(x.f)+' ('+x.why+')').join(' ; '),'| steps',p.steps.join(' / '));
