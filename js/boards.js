/* The class and grade boards for 'supabase' mode (docs/SIGNIN.md section 5, mock docs/mock/boards.html), loaded by
   js/main.js only when state.js NEW is true; otherwise the old board is shown, unchanged.
   One screen, two tabs "הכיתה" / "השכבה" (the grade tab only when the grade board has rows: the trial class has no
   grade). A row: rank, the name (first name and letter, only the first name is ever cut), on the grade board the
   class as its own tag, the points. Up to 10 rows; the pupil's own row has a gold outline and, when it is not among
   them, comes under a thin line with its rank. No surname, no code, nothing else about another child.
   Every outside value is escaped; the DOM is replaced on each draw, with one listener on the new section. */
const ESC={'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
const esc=s=>{let o='';for(const c of String(s??''))o+=ESC[c]||c;return o};
// NEW (on the teacher-review list): the headings and tabs are the designer's (docs/mock/boards.html)
const T={hCls:'הכיתה שלנו',hGrade:'כל השכבה',tCls:'הכיתה',tGrade:'השכבה',tabs:'לוחות',loading:'טוענים את הטבלה…',back:'חזרה',
 empty:'עוד אין כאן נקודות. כל שלב מוסיף נקודות!'};
const TOP=10;
/* "נועה כ." -> the first name (may be cut) and " כ." (never cut); a name with no letter is the first name alone */
export function nameParts(n){n=String(n??'');const k=n.lastIndexOf(' '),t=k>0?n.slice(k+1):'';
 return t.endsWith('.')&&[...t].length<=3?[n.slice(0,k),t]:[n,'']}
const nm=n=>{const[f,l]=nameParts(n);return`<bdi class="bd-nm"><span class="bd-fn">${esc(f)}</span>${l?`<span class="bd-ln">&nbsp;${esc(l)}</span>`:''}</bdi>`};
const pts=x=>{const v=Number(x);return String(Number.isFinite(v)&&v>0?Math.floor(v):0)};
/* the rows to show: the first ten, and the pupil's own with its rank when it is further down */
export function pick(rows){const R=Array.isArray(rows)?rows:[],i=R.findIndex(r=>r&&r.me===true);
 return{top:R.slice(0,TOP).map((r,k)=>[r,k+1]),mine:i>=TOP?[R[i],i+1]:null}}
const row=([r,k],grade)=>`<li${r.me===true?' class="me" aria-current="true"':''}><span class="bd-rk">${k}</span><span class="bd-nmc">${nm(r.n)}${grade&&r.cls?`<span class="bd-cl">${esc(r.cls)}</span>`:''}</span><span class="bd-pt" dir="ltr">${pts(r.pts)}</span></li>`;
/* host: the game's view. o: {rows, grade, tab ('class'|'grade'), err, onTab(tab)}. rows null: still loading */
export function show(host,o){
 if(!document.querySelector('link[href="css/boards.css"]'))for(const h of['css/ds.css','css/boards.css'])if(!document.querySelector(`link[href="${h}"]`)){const l=document.createElement('link');l.rel='stylesheet';l.href=h;document.head.appendChild(l)}
 const hasGrade=Array.isArray(o.grade)&&o.grade.length>0,tab=o.tab==='grade'&&hasGrade?'grade':'class',R=tab==='grade'?o.grade:o.rows;
 const sec=document.createElement('section');sec.className='scr bd wi-root';sec.dir='rtl';sec.lang='he';
 let body;
 if(!Array.isArray(R))body=`<p class="bd-msg" role="status">${esc(o.err||T.loading)}</p>`;
 else if(!R.length)body=`<p class="bd-msg">${T.empty}</p>`;
 else{const p=pick(R);body=`<ol class="bd-list">${p.top.map(x=>row(x,tab==='grade')).join('')}</ol>${p.mine?`<hr class="bd-sep"><ol class="bd-list" start="${p.mine[1]}">${row(p.mine,tab==='grade')}</ol>`:''}`}
 sec.innerHTML=`<div class="bd-top"><button type="button" class="wi-btn wi-btn--quiet bd-back" data-a="nav" data-to="map" aria-label="${T.back}">→</button></div>
  <h2 class="bd-h">${tab==='grade'?T.hGrade:T.hCls}</h2>
  ${hasGrade?`<div class="bd-tabs" role="tablist" aria-label="${T.tabs}">${[['class',T.tCls],['grade',T.tGrade]].map(([k,t])=>`<button type="button" role="tab" class="bd-tab${k===tab?' on':''}" data-bt="${k}" aria-selected="${k===tab}">${t}</button>`).join('')}</div>`:''}
  <div class="bd-mid">${body}</div>`;
 sec.addEventListener('click',e=>{const b=e.target.closest('[data-bt]');if(b&&b.dataset.bt!==tab&&typeof o.onTab==='function')o.onTab(b.dataset.bt)});
 host.replaceChildren(sec);
 return sec}
