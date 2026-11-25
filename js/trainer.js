/* The classic trainer (moved out of trainer.html unchanged, so the page can run under a Content-Security-Policy without
   inline scripts). A classic script, loaded after js/trainer-data.js and config.js. */
const app=document.getElementById('app'),KEY='aam-unit1-v1';
const blank=()=>({w:{},read:{},parts:[1,2,3,4,5],dir:'en-he',cnt:10,me:[],ct:3,ccnt:15,ctypes:['en-he','he-en','tobe'],pts:0,st:{},day:'',streak:0,u:null,lastC:''});
let S=blank();
try{Object.assign(S,JSON.parse(localStorage.getItem(KEY))||{})}catch(e){}
const saveLocal=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}};
const save=()=>{saveLocal();touch()};
/* ---------- class backend (Google Sheet via Apps Script) ---------- */
const API=(window.API_URL||'').trim();
const ERR={class:'קוד הכיתה לא נכון.',pin:'הקוד הסודי לא נכון. נסו שוב.',nouser:'לא מצאנו את השם הזה. פעם ראשונה? לחצו על הכפתור השני.',taken:'השם הזה כבר תפוס. הוסיפו אות משם המשפחה, למשל: נועה כ.',locked:'יותר מדי ניסיונות. חכו 5 דקות ונסו שוב.',full:'הכיתה מלאה. פנו למורה.',input:'צריך קוד כיתה, שם (אותיות בלבד) וקוד סודי של 4 ספרות.',teacher:'קוד המורה לא נכון.',setup:'המערכת עוד לא הוגדרה.',net:'אין חיבור כרגע. בדקו את האינטרנט ונסו שוב.'};
async function api(a,d){const r=await fetch(API,{method:'POST',body:JSON.stringify({a,...d}),keepalive:a==='save'});return r.json()}
const cred=()=>({c:S.u.c,n:S.u.n,p:S.u.p});
const pack=()=>({w:S.w,read:S.read,st:S.st,pts:S.pts,day:S.day,streak:S.streak,me:S.me,g:S.g,k:{words:WORDS.filter(w=>w.p<6&&(S.w[w.en]||0)>=2).length,reads:TEXTS.filter(t=>S.read[t.id]===t.qs.length).length}});
let dirty=0,syncT=0;
function touch(){if(!API||!S.u)return;dirty=1;clearTimeout(syncT);syncT=setTimeout(push,2500)}
async function push(){clearTimeout(syncT);if(!dirty||!API||!S.u)return;dirty=0;try{const r=await api('save',{...cred(),s:pack()});if(!r.ok)dirty=1}catch(e){dirty=1}}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')push()});
const dstr=d=>d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate();
function award(n){const t=dstr(new Date());if(S.day!==t){const y=new Date();y.setDate(y.getDate()-1);S.streak=S.day===dstr(y)?(S.streak||0)+1:1;S.day=t;S.pts+=20}S.pts+=n;save()}
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const shuffle=a=>{a=[...a];for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a};
const pool=ps=>{const s=new Set;return WORDS.filter(w=>ps.includes(w.p)&&!s.has(w.en)&&s.add(w.en))};
const VOC=new Set(WORDS.filter(w=>w.p<6).map(w=>w.en.toLowerCase()));
const TTS='speechSynthesis' in window;
function say(t,r){if(!TTS)return;try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.lang='en-US';u.rate=r||.85;speechSynthesis.speak(u)}catch(e){}}
const mark=(w,ok,p=10)=>{S.w[w.en]=ok?Math.min(3,(S.w[w.en]||0)+1):0;const t=S.st[w.en]||[0,0];S.st[w.en]=[t[0]+1,t[1]+(ok?0:1)];ok?award(p):save()};
let V={name:'home'},timer=0;
const NAMES={cards:'כרטיסיות',quiz:'חידון תרגום',listen:'הבנת הנשמע',read:'הבנת הנקרא',write:'כתיבת משפטים',class:'משחק כיתתי',login:'כניסה',board:'טבלת הכיתה',teacher:'מסך המורה'};
function hd(t){return `<div class="top"><h2>${t}</h2><a class="back" href="#home">→ לתפריט</a></div>`}
function chips(){return `<div><p class="lbl">על אילו מילים מתרגלים?</p><div class="row">${PARTS.map(p=>`<button class="chip" data-a="part" data-p="${p.id}" aria-pressed="${S.parts.includes(p.id)}">${p.id<6?p.id+' · ':''}<span class="en">${p.en}</span></button>`).join('')}</div></div>`}
function seg(key,items){return `<div class="row">${items.map(([v,l])=>`<button class="chip" data-a="set" data-k="${key}" data-v="${v}" aria-pressed="${String(S[key])===String(v)}">${l}</button>`).join('')}</div>`}

/* ---------- home ---------- */
function home(){
 const d=Math.ceil((new Date(2026,10,25)-new Date())/864e5);
 const tiles=[['listen','♪','var(--violet)','הבנת הנשמע','שומעים מילה ובוחרים מה היא אומרת','חלק 1 במבחן'],['cards','Aa','var(--coral)','כרטיסיות','לומדים את המילים, הופכים ובודקים','חלק 2 במבחן'],['quiz','א?','var(--sky)','חידון תרגום','מאנגלית לעברית ולהפך, בוחרים כמה שאלות','חלק 2 במבחן'],['read','¶','var(--mint)','הבנת הנקרא','קטעים קצרים. לוחצים על מילה ורואים תרגום','חלק 3 במבחן'],['write','✎','var(--pink)','כתיבת משפטים','בונים משפט, am / is / are, כותבים על עצמי','חלק 4 במבחן'],['class','★','var(--ink)','משחק כיתתי','קבוצות, ניקוד, המורה בוחרת את השאלות','למסך בכיתה']];
 app.innerHTML=`${API&&S.u?`<div class="row"><span class="chip" aria-pressed="true">${esc(S.u.n)} · ${S.pts.toLocaleString()} נק׳${S.streak>1?` · ${S.streak} ימים ברצף`:''}</span><a class="chip" href="#board">טבלת הכיתה</a><button class="chip" data-a="logout">יציאה</button></div>`:''}<section class="hero"><div><h1><span>All About</span> Me</h1><p>מתאמנים למבחן באנגלית · <span class="en">Fantastic 5, Unit 1</span></p></div>
 <div class="count">${d>0?`<b>${d}</b>ימים למבחן`:'<b>!</b>בהצלחה במבחן'}</div></section>
 <section class="tiles">${tiles.map(t=>`<a class="tile" href="#${t[0]}"><span class="ic" style="background:${t[2]}">${t[1]}</span><b>${t[3]}</b><small>${t[4]}</small><span class="tag">${t[5]}</span></a>`).join('')}</section>
 <section class="box" style="margin-top:22px"><p class="lbl">כמה מילים כבר יודעים (שתי תשובות נכונות ברצף = מילה שנלמדה)</p><div class="prog">${PARTS.map(p=>{const ws=WORDS.filter(w=>w.p===p.id),k=ws.filter(w=>(S.w[w.en]||0)>=2).length;return `<div><span><span class="en">${p.en}</span><b>${k}/${ws.length}</b></span><div class="pbar"><i style="width:${k/ws.length*100}%;background:${p.c}"></i></div></div>`}).join('')}</div></section>
 <p style="text-align:center;margin-top:22px"><a class="btn alt" style="text-decoration:none;display:inline-block" href="./">→ חזרה למשחק איי המילים</a></p><footer>המילים והתרגומים לפי רשימת אוצר המילים של המורה ליחידה 1. ${API?'ההתקדמות נשמרת לפי השם והקוד הסודי. · <a href="#teacher">כניסת מורה</a>':'ההתקדמות נשמרת רק במכשיר הזה.'}</footer>`}

/* ---------- setup for cards / quiz / listen ---------- */
function setup(kind){
 const n=pool(S.parts).length;
 app.innerHTML=hd(NAMES[kind])+`<div class="box stack">${chips()}
 ${kind==='quiz'?`<div><p class="lbl">כיוון התרגום</p>${seg('dir',[['en-he','אנגלית ← עברית'],['he-en','עברית ← אנגלית'],['mix','מעורבב']])}</div>`:''}
 ${kind!=='cards'?`<div><p class="lbl">כמה שאלות?</p>${seg('cnt',[[5,'5'],[10,'10'],[20,'20'],[999,'כל המילים']])}</div>`:''}
 ${kind==='listen'&&!TTS?'<p class="note">בדפדפן הזה אין הקראה קולית. נסו בכרום או בספארי.</p>':''}
 <div class="row"><button class="btn go" data-a="start" data-kind="${kind}">מתחילים · ${kind==='cards'?n:Math.min(n,S.cnt)} מילים</button></div></div>`}

/* ---------- flashcards ---------- */
function cards(){
 if(!V.deck)return setup('cards');
 if(V.i>=V.deck.length){boom();app.innerHTML=hd('כרטיסיות')+`<div class="box stack" style="text-align:center"><div class="stars">★★★</div><h3>סיימתם את כל הכרטיסיות</h3><div class="row" style="justify-content:center"><button class="btn" data-a="start" data-kind="cards">סיבוב נוסף</button><a class="btn alt" href="#quiz" style="text-decoration:none">לחידון תרגום</a></div></div>`;return}
 const w=V.deck[V.i];
 app.innerHTML=hd('כרטיסיות')+`<div class="stack"><div class="meter"><i style="width:${V.i/V.deck.length*100}%"></i></div>
 <button class="flip${V.f?' on':''}" data-a="flip" aria-label="הפכו את הכרטיס"><div class="in"><div class="face"><span class="big en">${esc(w.en)}</span><small>לחצו כדי לראות את התרגום</small></div><div class="face b"><span class="big">${esc(w.he)}</span><small class="en">${esc(w.en)}</small></div></div></button>
 <div class="row" style="justify-content:center">${TTS?`<button class="say" data-a="say" data-t="${esc(w.en)}">♪ להקשיב</button>`:''}</div>
 <div class="row" style="justify-content:center"><button class="btn no" data-a="know" data-v="0">עוד לא יודע/ת</button><button class="btn go" data-a="know" data-v="1">ידעתי</button></div>
 <p style="text-align:center;color:var(--muted)">${V.i+1} מתוך ${V.deck.length}</p></div>`}

/* ---------- quiz engine (translate / listen / class) ---------- */
function mkQ(w,dir){
 if(dir==='tobe'){const t=TOBE[Math.random()*TOBE.length|0];return{label:'מה חסר? am / is / are',prompt:t[0],ltr:1,opts:['am','is','are'],oltr:1,ans:t[1]}}
 if(dir==='mix')dir=Math.random()<.6?'en-he':'he-en';
 let ds=shuffle(WORDS.filter(x=>x.p===w.p&&x.en!==w.en&&x.he!==w.he)).slice(0,3);
 const k=dir==='he-en'?'en':'he';
 return{w,dir,label:dir==='listen'?'הקשיבו ובחרו את הפירוש':dir==='he-en'?'איך אומרים באנגלית?':'מה הפירוש בעברית?',prompt:dir==='he-en'?w.he:w.en,ltr:dir!=='he-en',opts:shuffle([w,...ds]).map(x=>x[k]),oltr:k==='en',ans:w[k]}}
function startQuiz(kind,words){
 const dir=kind==='listen'?'listen':S.dir;
 const ws=words||shuffle(pool(S.parts)).sort((a,b)=>(S.w[a.en]||0)-(S.w[b.en]||0)).slice(0,S.cnt);
 V={name:kind,qs:shuffle(ws).map(w=>mkQ(w,dir)),i:0,ok:0,miss:[],pick:null};render();
 if(dir==='listen')say(V.qs[0].w.en)}
function qHTML(q,pick,big){
 const listen=q.dir==='listen';
 return `<div class="prompt box ${big?'classq':''}"><p class="lbl">${q.label}</p>
 ${listen&&pick===null?`<button class="say" style="font-size:26px;padding:16px 28px" data-a="say" data-t="${esc(q.w.en)}">♪ השמיעו שוב</button>`:`<div class="q ${q.ltr?'en':''}">${esc(q.prompt)}</div>${q.w&&q.ltr&&TTS&&!big?`<p><button class="say" data-a="say" data-t="${esc(q.w.en)}">♪</button></p>`:''}`}</div>`}
function optsHTML(q,pick,act){return `<div class="opts">${q.opts.map((o,i)=>`<button class="opt ${q.oltr?'en':''} ${pick!==null?(o===q.ans?'ok':i===pick?'bad':''):''}" data-a="${act}" data-i="${i}" ${pick!==null?'disabled':''}>${esc(o)}</button>`).join('')}</div>`}
function quiz(){
 if(!V.qs)return setup(V.name);
 const n=V.qs.length;
 if(V.i>=n){const pct=V.ok/n,st=pct>=.9?3:pct>=.7?2:pct>=.4?1:0;if(st>=2)boom();
  app.innerHTML=hd(NAMES[V.name])+`<div class="box stack"><div class="stars">${'★'.repeat(st)}${'☆'.repeat(3-st)}</div><h3 style="text-align:center;margin:0">${V.ok} תשובות נכונות מתוך ${n}</h3>
  ${V.miss.length?`<div><p class="lbl">המילים שכדאי לחזור עליהן</p><ul class="miss">${V.miss.map(w=>`<li><span class="en">${esc(w.en)}</span><span>${esc(w.he)}</span></li>`).join('')}</ul></div>`:'<p style="text-align:center">בלי אף טעות. כל הכבוד!</p>'}
  <div class="row" style="justify-content:center">${V.miss.length?'<button class="btn go" data-a="redo">תרגול חוזר של הטעויות</button>':''}<button class="btn" data-a="start" data-kind="${V.name}">סיבוב חדש</button></div></div>`;return}
 const q=V.qs[V.i],ok=V.pick!==null&&q.opts[V.pick]===q.ans;
 app.innerHTML=hd(NAMES[V.name])+`<div class="stack"><div class="meter"><i style="width:${V.i/n*100}%"></i></div>${qHTML(q,V.pick)}${optsHTML(q,V.pick,'opt')}
 <div class="fb ${ok?'g':'r'}">${V.pick===null?'':ok?'נכון!':`התשובה הנכונה: <span class="${q.oltr?'en':''}">${esc(q.ans)}</span>`}</div>
 ${V.pick!==null&&!ok?'<div class="row" style="justify-content:center"><button class="btn" data-a="next">הבא ←</button></div>':''}</div>`}
function nextQ(){V.i++;V.pick=null;render();const q=V.qs[V.i];if(q&&q.dir==='listen')say(q.w.en)}

/* ---------- reading ---------- */
function tok(s){return s.replace(TOKRE,t=>{if(!/[A-Za-z]/.test(t))return esc(t);const k=glossKey(t);return k?`<span class="t${VOC.has(k)?' v':''}" data-a="gl" data-k="${esc(k)}" data-t="${esc(t)}">${esc(t)}</span>`:esc(t)})}
function read(){
 if(!V.t){app.innerHTML=hd('הבנת הנקרא')+`<p>בחרו קטע. בזמן הקריאה אפשר ללחוץ על כל מילה ולראות מה הפירוש שלה. מילים מרשימת המבחן מסומנות בקו סגול.</p><div class="rlist">${TEXTS.map(t=>`<button class="tile" data-a="ropen" data-id="${t.id}"><span class="ic" style="background:${PARTS[t.p-1].c}">${t.id}</span><b class="en">${esc(t.title)}</b><small>${t.qs.length} שאלות · מילים מחלק ${t.p}</small>${S.read[t.id]!=null?`<span class="tag">הציון האחרון: ${S.read[t.id]}/${t.qs.length}</span>`:''}</button>`).join('')}</div>`;return}
 const t=V.t,done=Object.keys(V.a).length===t.qs.length;
 app.innerHTML=`<div class="top"><h2 class="en">${esc(t.title)}</h2><button class="back" data-a="rback">→ לכל הקטעים</button></div>
 <div class="stack"><div class="box"><div class="row" style="margin-bottom:10px">${TTS?'<button class="say" data-a="readall">♪ הקריאו לי את הקטע</button>':''}</div><div class="text">${tok(t.text)}</div></div>
 <div class="box stack">${t.qs.map((q,qi)=>{const p=V.a[qi];return `<div class="rq"><p>${qi+1}. ${tok(q[0])}</p><div class="opts">${V.o[qi].map(oi=>`<button class="opt en ${p!=null?(oi===q[2]?'ok':oi===p?'bad':''):''}" data-a="rans" data-q="${qi}" data-o="${oi}" ${p!=null?'disabled':''}>${esc(q[1][oi])}</button>`).join('')}</div></div>`}).join('')}
 ${done?`<div class="fb g">ענית נכון על ${t.qs.filter((q,i)=>V.a[i]===q[2]).length} מתוך ${t.qs.length}</div><div class="row" style="justify-content:center"><button class="btn" data-a="rback">לקטע הבא</button></div>`:''}</div></div>
 <div class="glbar" id="gl">לחצו על מילה בקטע כדי לראות תרגום</div>`}

/* ---------- writing ---------- */
function write(){
 const tab=V.tab||'build';
 let body='';
 if(tab==='build'){
  if(!V.b){const it=BUILD[V.bo[V.bi%BUILD.length]];V.b={en:it[0],he:it[1],bank:shuffle(it[0].replace(/\.$/,' .').split(' ')),pk:[],res:null}}
  const b=V.b;
  body=`<p class="lbl">בנו את המשפט באנגלית</p><div class="prompt" style="padding:6px"><div class="q" style="font-size:28px">${esc(b.he)}</div></div>
  <div class="slots">${b.pk.map((bi,i)=>`<button class="wt" data-a="untile" data-i="${i}">${esc(b.bank[bi])}</button>`).join('')}</div>
  <div class="bank">${b.bank.map((w,i)=>`<button class="wt${b.pk.includes(i)?' u':''}" data-a="tile" data-i="${i}">${esc(w)}</button>`).join('')}</div>
  <div class="fb ${b.res?'g':'r'}">${b.res===null?'':b.res?'מצוין! משפט נכון.':'עוד לא. בדקו את סדר המילים. משפט מתחיל באות גדולה ונגמר בנקודה.'}</div>
  <div class="row" style="justify-content:center">${b.res?'<button class="btn go" data-a="bnext">משפט הבא ←</button>':`<button class="btn" data-a="bcheck" ${b.pk.length<b.bank.length?'disabled':''}>בדיקה</button><button class="btn alt" data-a="bclear">ניקוי</button>`}</div>`}
 else if(tab==='tobe'){
  const t=TOBE[V.to[V.ti%TOBE.length]],p=V.tp;
  body=`<p class="lbl">בחרו את המילה החסרה</p><div class="gap">${esc(t[0]).replace('___',`<u>${p?esc(t[1]):'?'}</u>`)}</div>
  <div class="opts" style="grid-template-columns:repeat(3,1fr)">${['am','is','are'].map(o=>`<button class="opt en ${p?(o===t[1]?'ok':o===p?'bad':''):''}" data-a="tb" data-o="${o}" ${p?'disabled':''}>${o}</button>`).join('')}</div>
  <div class="fb ${p===t[1]?'g':'r'}">${!p?'':p===t[1]?'נכון!':'זכרו: I am · he / she / it is · we / you / they are'}</div>
  ${p?'<div class="row" style="justify-content:center"><button class="btn go" data-a="tbnext">הבא ←</button></div>':''}`}
 else{
  body=`<p class="note">זוכרים: משפט מתחיל באות גדולה ובסוף לא שוכחים נקודה!</p><div class="me">${ME.map((m,i)=>`<div><label for="me${i}">${m[0]}</label><input id="me${i}" data-me="${i}" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="${esc(m[1])}" value="${esc(S.me[i]||'')}"><div class="ticks" id="mk${i}">${ticks(S.me[i]||'')}</div></div>`).join('')}</div>`}
 app.innerHTML=hd('כתיבת משפטים')+`<div class="stack">${`<div class="row">${[['build','בונים משפט'],['tobe','am / is / are'],['me','כותבים על עצמי']].map(([v,l])=>`<button class="chip" data-a="wtab" data-v="${v}" aria-pressed="${tab===v}">${l}</button>`).join('')}</div>`}<div class="box stack">${body}</div></div>`}
function ticks(v){v=v.trim();const c=[[/^[A-Z]/.test(v),'אות גדולה בהתחלה'],[/[.!]$/.test(v),'נקודה בסוף'],[/\b(am|is|are)\b/i.test(v),'am / is / are'],[v.split(/\s+/).length>=3,'3 מילים לפחות']];return c.map(([y,l])=>`<span class="${y?'y':''}">${y?'✓':'○'} ${l}</span>`).join('')}

/* ---------- class game ---------- */
function klass(){
 if(!V.mode){
  app.innerHTML=hd('משחק כיתתי')+`<div class="box stack">${chips()}
  <div><p class="lbl">סוגי שאלות</p><div class="row">${[['en-he','תרגום לעברית'],['he-en','תרגום לאנגלית'],['tobe','am / is / are']].map(([v,l])=>`<button class="chip" data-a="ctype" data-v="${v}" aria-pressed="${S.ctypes.includes(v)}">${l}</button>`).join('')}</div></div>
  <div><p class="lbl">כמה שאלות?</p>${seg('ccnt',[[10,'10'],[15,'15'],[20,'20'],[30,'30']])}</div>
  <div><p class="lbl">כמה קבוצות?</p>${seg('ct',[[2,'2'],[3,'3'],[4,'4']])}</div>
  <div><p class="lbl">שמות הקבוצות</p><div class="row">${Array.from({length:S.ct},(_,i)=>`<input class="tin" id="tn${i}" aria-label="שם קבוצה ${i+1}" value="קבוצה ${i+1}">`).join('')}</div></div>
  <div class="row"><button class="btn go" data-a="cstart">מתחילים לשחק</button></div></div>`;return}
 const sc=`<div class="teams">${V.teams.map((t,i)=>`<div class="team${i===V.turn&&V.mode==='run'?' on':''}">${esc(t.n)}<b>${t.s}</b></div>`).join('')}</div>`;
 if(V.mode==='end'){boom();const mx=Math.max(...V.teams.map(t=>t.s)),w=V.teams.filter(t=>t.s===mx).map(t=>esc(t.n));
  app.innerHTML=hd('משחק כיתתי')+`<div class="stack">${sc}<div class="box stack" style="text-align:center"><div class="stars">★★★</div><h3 style="font-size:32px;margin:0">${w.length>1?'תיקו: '+w.join(' ו'):'המנצחת: '+w[0]}</h3><div class="row" style="justify-content:center"><button class="btn" data-a="cnew">משחק חדש</button></div></div></div>`;return}
 const q=V.qs[V.i];
 app.innerHTML=`<div class="top"><h2>שאלה ${V.i+1} מתוך ${V.qs.length} · התור של ${esc(V.teams[V.turn].n)}</h2><div class="row"><button class="back" data-a="fs">מסך מלא</button><button class="back" data-a="cend">סיום</button></div></div>
 <div class="stack">${sc}${qHTML(q,V.rev?-1:null,1)}<div class="classq">${optsHTML(q,V.rev?-1:null,'x')}</div>
 <div class="row" style="justify-content:center">${V.rev?`<button class="btn go" data-a="caward" data-v="1">נכון · נקודה ל${esc(V.teams[V.turn].n)}</button><button class="btn no" data-a="caward" data-v="0">לא נכון</button>`:`<button class="btn" data-a="creveal">הצגת התשובה</button>${q.w&&TTS?`<button class="say" data-a="say" data-t="${esc(q.w.en)}">♪ השמעה</button>`:''}`}</div></div>`}


/* ---------- login / leaderboard / teacher ---------- */
function login(){app.innerHTML=`<div class="box stack login"><h2>כניסה לכיתה</h2>
 <div><label class="lbl" for="lc">קוד הכיתה</label><input id="lc" class="tin big en" autocomplete="off" autocapitalize="characters" value="${esc(V.c??S.lastC)}"></div>
 <div><label class="lbl" for="ln">השם שלי</label><input id="ln" class="tin big" autocomplete="off" maxlength="20" value="${esc(V.n||'')}"></div>
 <div><label class="lbl" for="lp">הקוד הסודי שלי (4 ספרות)</label><input id="lp" class="tin big en" type="password" inputmode="numeric" maxlength="4" autocomplete="off" style="letter-spacing:10px"></div>
 <div class="fb r">${esc(V.err||'')}</div>
 <button class="btn go" data-a="auth" data-m="login" ${V.busy?'disabled':''}>${V.busy?'רגע…':'כניסה'}</button>
 <button class="btn alt" data-a="auth" data-m="register" ${V.busy?'disabled':''}>פעם ראשונה שלי כאן</button>
 <p class="lbl">פעם ראשונה? כותבים את קוד הכיתה ואת השם, ובוחרים 4 ספרות שרק אתם יודעים. בלי אימייל.</p></div>`}
function board(){
 if(!V.rows){app.innerHTML=hd('טבלת הכיתה')+`<p class="box">${esc(V.err||'טוען את הטבלה…')}</p>`;
  if(!V.req){V.req=1;const v=V;push().then(()=>api('board',cred())).then(r=>{if(V!==v)return;if(r.ok)V.rows=r.rows;else V.err=ERR[r.e]||ERR.net;render()}).catch(()=>{if(V!==v)return;V.err=ERR.net;render()})}return}
 const R=V.rows,c=['var(--grid)','var(--sun)','#F6C9A8'],o=[1,0,2],h=[92,128,70];
 app.innerHTML=hd('טבלת הכיתה')+`<div class="stack">${R.length>=3?`<div class="podium">${o.map((i,k)=>`<div style="background:${c[k]};min-height:${h[k]}px"><b>${i+1}</b>${esc(R[i].n)}<small>${R[i].pts.toLocaleString()} נק׳</small></div>`).join('')}</div>`:''}
 <ol class="lb">${R.map((d,i)=>`<li class="${d.n===S.u.n?'me':''}"><span class="rk">${i+1}</span><span>${esc(d.n)}${d.n===S.u.n?' (אני)':''}${d.streak>=3?` · ${d.streak} ימים ברצף`:''}</span><div class="pbar" title="מילים שנלמדו"><i style="width:${Math.min(100,d.words/59*100)}%;background:var(--mint)"></i></div><span class="pt">${d.pts.toLocaleString()}</span></li>`).join('')}</ol>
 <p class="lbl">נקודות: 10 על תשובה נכונה, 50 על קטע קריאה בלי טעויות, 20 בונוס על כל יום תרגול.</p></div>`}
function teacher(){
 if(!API){app.innerHTML=hd('מסך המורה')+'<p class="box">מסך המורה יהיה זמין אחרי חיבור הכיתה.</p>';return}
 if(!V.data){app.innerHTML=hd('מסך המורה')+`<div class="box stack login" style="margin-top:0"><div><label class="lbl" for="tc">קוד הכיתה</label><input id="tc" class="tin big en" autocomplete="off" value="${esc(V.c??(S.u?S.u.c:S.lastC))}"></div><div><label class="lbl" for="tt">קוד המורה</label><input id="tt" class="tin big en" type="password" autocomplete="off"></div><div class="fb r">${esc(V.err||'')}</div><button class="btn go" data-a="tlogin" ${V.busy?'disabled':''}>${V.busy?'רגע…':'כניסה'}</button></div>`;return}
 const D=V.data,he=Object.fromEntries(WORDS.map(w=>[w.en,w.he]));
 app.innerHTML=hd('מסך המורה')+`<div class="stack">
 <div class="box"><p class="lbl">המילים שהכיתה הכי טועה בהן</p>${D.hard.length?`<div class="hard">${D.hard.map(w=>`<div><span><span class="en">${esc(w[0])}</span><span>${esc(he[w[0]]||'')}</span><b>${w[1]}% טעויות</b></span><div class="pbar"><i style="width:${w[1]}%;background:var(--coral)"></i></div></div>`).join('')}</div>`:'<p>עדיין אין מספיק תרגול כדי לדעת.</p>'}</div>
 <div class="box tw">${D.kids.length?`<table><thead><tr><th>תלמיד/ה</th><th>מילים שנלמדו (מתוך 59)</th><th>קטעי קריאה</th><th>נקודות</th><th>תרגול אחרון</th><th>מצב</th></tr></thead><tbody>${D.kids.map(d=>{const s=d.words>=40?['g','מוכן/ה']:d.words>=25?['w','בדרך']:['r','צריך חיזוק'],dd=d.day.split('-');return `<tr><td><b>${esc(d.n)}</b></td><td><div class="row" style="flex-wrap:nowrap"><span style="min-width:26px">${d.words}</span><div class="pbar" style="flex:1"><i style="width:${Math.min(100,d.words/59*100)}%;background:var(--mint)"></i></div></div></td><td>${d.reads} מתוך 5</td><td>${d.pts.toLocaleString()}</td><td>${dd.length===3?dd[2]+'/'+dd[1]:'עוד לא'}</td><td><span class="pill ${s[0]}">${s[1]}</span></td></tr>`}).join('')}</tbody></table>`:'<p>עדיין אף תלמיד לא נרשם.</p>'}</div></div>`}
/* ---------- actions ---------- */
const A={
 async auth(d){const c=document.getElementById('lc').value.trim(),n=document.getElementById('ln').value.trim().replace(/\s+/g,' '),p=document.getElementById('lp').value;
  if(!c||n.length<2||!/^\d{4}$/.test(p)){V={name:'login',c,n,err:ERR.input};return render()}
  V={name:'login',c,n,busy:1};render();let r;try{r=await api(d.m,{c,n,p})}catch(e){r={e:'net'}}
  if(!r.ok){V={name:'login',c,n,err:ERR[r.e]||ERR.net};return render()}
  const o=S;S=Object.assign(blank(),{parts:o.parts,dir:o.dir,cnt:o.cnt,ct:o.ct,ccnt:o.ccnt,ctypes:o.ctypes},r.s||{},{u:{c,n,p},lastC:c});delete S.k;dirty=0;saveLocal();if(location.hash==='#home')route();else location.hash='home'},
 async logout(){await push();if(dirty&&navigator.onLine===false){alert('אין חיבור כרגע, וההתקדמות עוד לא נשמרה. נסו להתנתק שוב בעוד רגע.');return}const c=S.lastC;S=Object.assign(blank(),{lastC:c});dirty=0;saveLocal();route()},
 async tlogin(){const c=document.getElementById('tc').value.trim(),t=document.getElementById('tt').value.trim();V={name:'teacher',c,busy:1};render();let r;try{r=await api('teacher',{c,t})}catch(e){r={e:'net'}}
  if(V.name!=='teacher')return;V=r.ok?{name:'teacher',data:r}:{name:'teacher',c,err:ERR[r.e]||ERR.net};render()},
 part(d){const p=+d.p,i=S.parts.indexOf(p);if(i<0)S.parts.push(p);else if(S.parts.length>1)S.parts.splice(i,1);save();render()},
 set(d){S[d.k]=isNaN(+d.v)?d.v:+d.v;save();render()},
 start(d){if(d.kind==='cards'){const ws=shuffle(pool(S.parts)).sort((a,b)=>(S.w[a.en]||0)-(S.w[b.en]||0)).map(w=>({...w}));V={name:'cards',deck:ws,i:0,f:0};render()}else startQuiz(d.kind)},
 flip(){V.f=!V.f;document.querySelector('.flip').classList.toggle('on',V.f)},
 say(d){say(d.t)},
 know(d){const w=V.deck[V.i],ok=d.v==='1';mark(w,ok,2);if(!ok&&!w._r){w._r=1;V.deck.splice(Math.min(V.deck.length,V.i+4),0,{...w})}V.i++;V.f=0;render()},
 opt(d){if(V.pick!==null)return;const q=V.qs[V.i];V.pick=+d.i;const ok=q.opts[V.pick]===q.ans;if(q.w)mark(q.w,ok);if(ok){V.ok++;clearTimeout(timer);timer=setTimeout(nextQ,850)}else if(q.w&&!V.miss.includes(q.w))V.miss.push(q.w);render()},
 next(){nextQ()},
 redo(){startQuiz(V.name,V.miss)},
 ropen(d){const t=TEXTS.find(x=>x.id==d.id);V={name:'read',t,a:{},o:t.qs.map(q=>shuffle(q[1].map((_,i)=>i)))};render();scrollTo(0,0)},
 rback(){if(TTS)speechSynthesis.cancel();V={name:'read'};render()},
 rans(d){if(V.a[d.q]!=null)return;V.a[d.q]=+d.o;const t=V.t;if(+d.o===t.qs[d.q][2])award(10);if(Object.keys(V.a).length===t.qs.length){const sc=t.qs.filter((q,i)=>V.a[i]===q[2]).length,full=sc===t.qs.length;if(full&&S.read[t.id]!==sc)award(50);S.read[t.id]=Math.max(sc,S.read[t.id]||0);save();if(full)boom()}const y=scrollY;render();scrollTo(0,y)},
 gl(d,el){document.querySelectorAll('.t.sel').forEach(x=>x.classList.remove('sel'));el.classList.add('sel');document.getElementById('gl').innerHTML=`<span class="en">${esc(d.t)}</span><span>=</span><span>${esc(GL[d.k])}</span>`;say(d.t)},
 readall(){say(V.t.text,.75)},
 wtab(d){V.tab=d.v;render()},
 tile(d){V.b.pk.push(+d.i);V.b.res=null;render()},
 untile(d){if(V.b.res)return;V.b.pk.splice(+d.i,1);V.b.res=null;render()},
 bclear(){V.b.pk=[];V.b.res=null;render()},
 bcheck(){const b=V.b;b.res=b.pk.map(i=>b.bank[i]).join(' ').replace(' .','.')===b.en;if(b.res){award(10);say(b.en);V.bok=(V.bok||0)+1;if(V.bok%4===0)boom()}render()},
 bnext(){V.bi++;V.b=null;render()},
 tb(d){if(V.tp)return;V.tp=d.o;if(d.o===TOBE[V.to[V.ti%TOBE.length]][1])award(10);render()},
 tbnext(){V.ti++;V.tp=null;render()},
 ctype(d){const i=S.ctypes.indexOf(d.v);if(i<0)S.ctypes.push(d.v);else if(S.ctypes.length>1)S.ctypes.splice(i,1);save();render()},
 cstart(){const teams=Array.from({length:S.ct},(_,i)=>({n:(document.getElementById('tn'+i).value||'קבוצה '+(i+1)).slice(0,18),s:0}));let ws=shuffle(pool(S.parts));while(ws.length<S.ccnt)ws=ws.concat(shuffle(ws));V={name:'class',mode:'run',teams,turn:0,i:0,rev:0,qs:ws.slice(0,S.ccnt).map(w=>mkQ(w,S.ctypes[Math.random()*S.ctypes.length|0]))};render()},
 creveal(){V.rev=1;render()},
 caward(d){if(d.v==='1')V.teams[V.turn].s++;V.turn=(V.turn+1)%V.teams.length;V.i++;V.rev=0;if(V.i>=V.qs.length)V.mode='end';render()},
 cend(){V.mode='end';render()},
 cnew(){V={name:'class'};render()},
 fs(){try{document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}catch(e){}},
 x(){}
};
document.addEventListener('click',e=>{const el=e.target.closest('[data-a]');if(el&&A[el.dataset.a])A[el.dataset.a](el.dataset,el)});
document.addEventListener('input',e=>{const i=e.target.dataset.me;if(i==null)return;S.me[i]=e.target.value;save();document.getElementById('mk'+i).innerHTML=ticks(e.target.value)});
function render(){({home,cards,quiz,listen:quiz,read,write,class:klass,login,board,teacher}[V.name]||home)()}
function route(){clearTimeout(timer);if(TTS)try{speechSynthesis.cancel()}catch(e){}let n=location.hash.slice(1);if(API&&!S.u&&n!=='teacher')n='login';if(!API&&(n==='login'||n==='board'))n='home';V={name:NAMES[n]?n:'home'};if(V.name==='write'){V.bo=shuffle(BUILD.map((_,i)=>i));V.bi=0;V.to=shuffle(TOBE.map((_,i)=>i));V.ti=0;V.tp=null}render();scrollTo(0,0)}
addEventListener('hashchange',route);

/* ---------- confetti ---------- */
function boom(){if(matchMedia('(prefers-reduced-motion:reduce)').matches)return;const c=document.getElementById('fx'),x=c.getContext('2d');c.width=innerWidth;c.height=innerHeight;const cols=['#FFC933','#FF5A5F','#10B39E','#6C4DF5','#2F8CFF','#F25CB8'];const ps=Array.from({length:110},()=>({x:c.width/2,y:c.height*.35,vx:(Math.random()-.5)*16,vy:-Math.random()*13-3,s:6+Math.random()*7,c:cols[Math.random()*6|0],r:Math.random()*6}));let f=0;(function step(){x.clearRect(0,0,c.width,c.height);ps.forEach(p=>{p.vy+=.35;p.x+=p.vx;p.y+=p.vy;p.r+=.2;x.save();x.translate(p.x,p.y);x.rotate(p.r);x.fillStyle=p.c;x.fillRect(-p.s/2,-p.s/2,p.s,p.s*.6);x.restore()});if(++f<110)requestAnimationFrame(step);else x.clearRect(0,0,c.width,c.height)})()}
route();
