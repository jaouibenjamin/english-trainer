/* Fraction Bay (מפרץ השברים): the math world. Exam topics from the teachers' notice (exam on Friday 20.11.26):
   - adding and subtracting fractions and mixed numbers with the same denominator, with regrouping (פריטה)
   - mixed number to improper fraction and back.
   Every exercise is generated, so a level never repeats itself exactly. A fraction is {w,n,d}: w wholes and n/d. */

export const MATH_EXAM=new Date(2026,10,20);

const R=(a,b)=>a+Math.floor(Math.random()*(b-a+1));
const pick=a=>a[Math.floor(Math.random()*a.length)];
export const shuf=a=>{a=[...a];for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a};
/* what the parts are called: 4 → רבעים. Used in the steps and in the pizza questions. */
export const PARTS_HE={2:'חצאים',3:'שלישים',4:'רבעים',5:'חמישיות',6:'שישיות',7:'שביעיות',8:'שמיניות',9:'תשיעיות',10:'עשיריות',12:'חלקים של 12'};
export const parts=(k,d)=>k===1?'חלק אחד':`${k} ${PARTS_HE[d]||'חלקים של '+d}`;

export const F=(w,n,d)=>({w,n,d});
export const top=f=>f.w*f.d+f.n;                                    // the numerator of the improper form
export const same=(a,b)=>top(a)*b.d===top(b)*a.d;                    // equal value
export const mixedOf=(N,d)=>F(Math.floor(N/d),N%d,d);
export const impOf=f=>F(0,top(f),f.d);
const id=f=>f.w+'|'+f.n+'|'+f.d;

/* how the answer must be written. 'imp': no whole part. 'mixed': the fraction part smaller than 1, wholes taken out. */
export function formOK(f,form){
 if(f.d<1||f.n<0||f.w<0)return false;
 if(form==='imp')return f.w===0&&f.n>0;
 return f.n<f.d&&!(f.n===0&&f.w===0&&top(f)!==0)}

/* ---------- the exercises ---------- */
const D_ALL=[2,3,4,5,6,7,8,9,10,12],D_PIZZA=[2,3,4,5,6,8];

/* a distractor is kept only if it is a real, different value written in the asked form, so no two balloons can both be right */
function alts(ans,form,cands,fill){
 const out=[],seen=new Set([id(ans)]);
 const add=(f,why)=>{if(!f||f.d<2||f.n<0||f.w<0||top(f)<=0)return;if(same(f,ans)||!formOK(f,form)||seen.has(id(f)))return;seen.add(id(f));out.push({f,why})};
 cands.forEach(([f,why])=>add(f,why));
 for(let k=0;out.length<6&&k<80;k++)add(fill(),'');
 return out}

export function m2i(d=pick(D_ALL),w=R(1,4),n=R(1,d-1)){
 const a=F(w,n,d),ans=impOf(a);
 return{kind:'m2i',a,ans,form:'imp',ask:'כתבו כשבר גדול מהשלם',
  alts:alts(ans,'imp',[[F(0,w+n,d),`כל שלם הוא ${d} חלקים: כופלים ${w} × ${d}`],[F(0,w*d-n,d),`מוסיפים את ${n} החלקים, לא מורידים`],[F(0,w*d+n,w*d),'המכנה לא משתנה'],[F(0,(w+1)*d+n,d),`יש כאן ${w} שלמים`],[F(0,w*n+d,d),`כופלים את השלמים במכנה: ${w} × ${d}`]],
   ()=>F(0,top(ans)+pick([-2,-1,1,2,d,-d]),d)),
  steps:[`כל שלם הוא ${parts(d,d)}, אז ${w} שלמים הם ${w} × ${d} = ${parts(w*d,d)}`,`ועוד ${parts(n,d)}: ${w*d} + ${n} = ${top(ans)}, כלומר ${fx(ans)}`]}}

export function i2m(d=pick(D_ALL),w=R(1,4),n=Math.random()<.15?0:R(1,d-1)){
 const ans=F(w,n,d),a=impOf(ans);
 return{kind:'i2m',a,ans,form:'mixed',ask:'כתבו כמספר מעורב',
  alts:alts(ans,'mixed',[[F(w+1,n,d),`${d} × ${w+1} = ${d*(w+1)}, וזה יותר מ־${top(ans)}`],[F(w-1,n,d),`נכנסים ${w} שלמים: ${d} × ${w} = ${d*w}`],[F(w,d-n,d),`נשארים ${top(ans)} − ${d*w} = ${n}`],[F(n,w,d),'השלמים הם כמה פעמים המכנה נכנס במונה'],[F(w,n+1,d),`נשארים ${n}`]],
   ()=>F(Math.max(0,w+pick([-1,0,1])),R(0,d-1),d)),
  steps:[`כמה פעמים ${d} נכנס ב־${top(ans)}? ${w} פעמים, כי ${w} × ${d} = ${w*d}`,n?`נשארו ${top(ans)} − ${w*d} = ${n}, אז התשובה ${fx(ans)}`:`לא נשאר כלום: ${w} שלמים בדיוק`]}}

/* addition. kind: 'ff' fraction + fraction, 'mf' mixed + fraction, 'mm' mixed + mixed. carry: the parts make one more whole */
export function add(kind=pick(['ff','mf','mm','mm']),carry=Math.random()<.65,d=pick(D_ALL)){
 let a1,b1;for(let k=0;k<50;k++){a1=R(1,d-1);b1=R(1,d-1);if((a1+b1>=d)===carry&&a1+b1!==d*2)break}
 const w1=kind==='ff'?0:R(1,4),w2=kind==='mm'?R(1,3):0,A=F(w1,a1,d),B=F(w2,b1,d),s=a1+b1,ans=F(w1+w2+Math.floor(s/d),s%d,d);
 const c=[[F(w1+w2,s%d,2*d),`את המכנה לא מחברים. נשאר ${d}`],[F(w1+w2,s-d,d),'מהחלקים יצא עוד שלם: מוסיפים אותו לשלמים'],[F(ans.w+1,ans.n,d),'ספרו שוב את השלמים'],[F(ans.w,(ans.n+1)%d,d),'חברו שוב את המונים']];
 c[0][0]=F(w1+w2,s,2*d);   // the classic slip: numerators and denominators both added
 return{kind:'add',op:'+',a:A,b:B,ans,form:'mixed',carry:s>=d,
  alts:alts(ans,'mixed',c,()=>F(Math.max(0,ans.w+pick([-1,0,1])),R(0,d-1),d)),
  steps:[`מחברים את החלקים: ${a1} + ${b1} = ${parts(s,d)}`,...(s>=d?[s===d?`${parts(s,d)} הם שלם אחד: ${fx(F(0,s,d))} = 1`:`${parts(s,d)} הם שלם אחד ועוד ${s-d}: ${fx(F(0,s,d))} = ${fx(F(1,s-d,d))}`]:[]),...(w1+w2?[`מחברים את השלמים: ${[w1,w2].filter(Boolean).join(' + ')}${s>=d?' + 1':''} = ${ans.w}`]:[])]}}

/* subtraction. kind: 'ff', 'mf' mixed − fraction, 'mm' mixed − mixed, 'wm' whole − mixed (or fraction). borrow: פריטה needed */
export function sub(kind=pick(['mf','mm','mm','wm']),borrow=Math.random()<.65,d=pick(D_ALL)){
 if(kind==='ff')borrow=false;if(kind==='wm')borrow=true;
 if(d<3&&kind!=='wm')d=pick([3,4,5,6,8]);   // halves leave no room to borrow, or to subtract two different parts
 let a1=0,b1=0;
 for(let k=0;k<60;k++){a1=kind==='wm'?0:R(1,d-1);b1=R(1,d-1);if(borrow?a1<b1:(kind==='ff'?a1>b1:a1>=b1))break}
 const w2=kind==='ff'||kind==='mf'?0:R(kind==='wm'?0:1,3);
 const w1=kind==='ff'?0:kind==='mf'?R(1,4):w2+R(borrow?1:0,3);
 const A=F(w1,a1,d),B=F(w2,b1,d),N=top(A)-top(B);
 if(N<=0||(kind==='mm'&&!borrow&&w1===w2&&a1===b1))return sub(kind,borrow,d);
 const ans=mixedOf(N,d);
 const c=[[F(Math.max(0,w1-w2),Math.abs(a1-b1),d),`אי אפשר להוריד ${b1} מ־${a1}: פורטים שלם אחד ל־${d} חלקים`],[F(Math.max(0,w1-w2),a1+d-b1,d),'פרטתם שלם, אז נשאר שלם אחד פחות'],[F(ans.w+1,ans.n,d),'ספרו שוב את השלמים'],[F(ans.w,(ans.n+1)%d,d),'חסרו שוב את המונים']];
 const steps=borrow?[a1?`אי אפשר להוריד ${b1} מ־${a1}: פורטים שלם אחד ל־${parts(d,d)}`:`אין חלקים להוריד מהם: פורטים שלם אחד ל־${parts(d,d)}`,`${fx(A)} = ${fx(F(w1-1,a1+d,d))}`,`חלקים: ${a1+d} − ${b1} = ${a1+d-b1}${w1-1||w2?`. שלמים: ${w1-1} − ${w2} = ${w1-1-w2}`:''}`]
  :[`מחסרים את החלקים: ${a1} − ${b1} = ${parts(a1-b1,d)}`,...(w1?[`מחסרים את השלמים: ${w1} − ${w2} = ${w1-w2}`]:[])];
 return{kind:'sub',op:'−',a:A,b:B,ans,form:'mixed',borrow,
  alts:alts(ans,'mixed',c,()=>F(Math.max(0,ans.w+R(-2,2)),R(0,d-1),d)),steps}}

/* plain-text fraction for the worked steps: "3 6/5". The screens turn these into stacked fractions. */
export const fx=f=>f.n===0?String(f.w):(f.w?f.w+' ':'')+f.n+'/'+f.d;

/* pizza levels keep the numbers small enough to tap: denominators up to 8, at most 4 pizzas on the table */
export const pizzaItem={
 conv:()=>{const d=pick(D_PIZZA);return Math.random()<.5?m2i(d,R(1,3)):i2m(d,R(1,3),R(1,d-1))},
 add:()=>add(pick(['ff','mf','mm']),true,pick(D_PIZZA)),
 sub:()=>sub(pick(['mf','mm','wm']),true,pick(D_PIZZA))};
export const pizzasFor=p=>Math.ceil((p.kind==='add'?top(p.ans):top(p.kind==='sub'?p.a:p.ans))/p.ans.d);
export function pizzaSet(mode,n){const out=[];for(let k=0;k<n*8&&out.length<n;k++){const p=pizzaItem[mode]();
  if(pizzasFor(p)<=4&&!out.some(o=>same(o.a,p.a)&&(!o.b||same(o.b,p.b))))out.push(p)}return out}

/* a set of n exercises for a level, with no exercise twice */
const MAKERS={
 conv:()=>Math.random()<.5?m2i():i2m(),
 add:()=>add(),
 sub:()=>sub(),
 exam:null};
export function set(mode,n){
 if(mode==='exam'){const plan=shuf([()=>m2i(),()=>m2i(),()=>i2m(),()=>i2m(),()=>add('mm',true),()=>add('mf',true),()=>sub('mm',true),()=>sub('wm'),()=>sub('mf',true)]).slice(0,n);return plan.map(f=>f())}
 const out=[],seen=new Set();for(let k=0;k<n*6&&out.length<n;k++){const p=MAKERS[mode]();const s=id(p.a)+(p.b?id(p.b):'');if(!seen.has(s)){seen.add(s);out.push(p)}}return out}

/* ---------- islands and levels ---------- */
export const M_LEVEL={
 pizza:{name:'הפיצרייה של פיצי',sub:'בונים שברים מפרוסות',icon:'pizza'},
 sling:{name:'קלע השברים',sub:'פוגעים בתשובה הנכונה',icon:'fork'},
 sheet:{name:'דף המבחן',sub:'כותבים תשובה, כמו במבחן',icon:'sheet'}};
export const M_ISLANDS=[
 {id:1,he:'אי השלמים',sub:'מספר מעורב ושבר גדול מהשלם',need:0,bg:'sling1',art:2,mode:'conv',levels:['pizza','sling','sheet']},
 {id:2,he:'אי החיבור',sub:'חיבור שברים ומספרים מעורבים',need:3,bg:'sling3',art:3,mode:'add',levels:['pizza','sling','sheet']},
 {id:3,he:'אי החיסור',sub:'חיסור עם פריטה',need:7,bg:'sling4',art:4,mode:'sub',levels:['pizza','sling','sheet']},
 {id:4,he:'אי המבחן',sub:'הכול ביחד, כמו במבחן',need:12,bg:'sling5',art:6,mode:'exam',levels:['sheet','sling']}];
export const M_MAX=M_ISLANDS.reduce((a,i)=>a+i.levels.length*3,0);
export const M_COUNT={pizza:4,sling:6,sheet:6,examSheet:8};
