/* A printable worksheet of one island: the same words, story and sentences as its levels, on light paper.
   Behind a switch that is off unless a device was given it (open the game once with ?sheet=1; ?sheet=0 takes it away).
   - Everything comes from js/data.js, the game's one source of content. The teacher's words and translations are
     printed exactly as they are there; nothing is written or translated here.
   - Nothing about a pupil is read or shown: the name line is empty, to be filled in by hand. Nothing is saved and
     nothing is sent anywhere. The only thing read from the device is the switch itself.
   - The mix of every exercise depends only on the island, so a sheet printed twice is the same sheet and the answer
     page always fits it. */
import {ISLANDS,RAW,TEXTS,SENT,TOBE_BY} from './data.js';

const SET_KEY='word-islands-settings-v1';   // the same device-only entry the game keeps its switches in (js/state.js)
export const sheetOn=()=>{try{return(JSON.parse(localStorage.getItem(SET_KEY))||{}).sheet===true}catch(e){return false}};
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const en=t=>`<bdi dir="ltr" lang="en" class="en">${esc(t)}</bdi>`;

/* a mix that depends only on its seed */
function rnd(seed){let a=seed>>>0;return()=>{a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
export function mix(list,seed){const a=[...list],r=rnd(seed);for(let i=a.length-1;i>0;i--){const j=r()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}
 if(a.length>1&&a.every((x,i)=>x===list[i]))a.push(a.shift());   // never the original order
 return a}

const pairs=p=>RAW[p].split(';').map(s=>{const[e,h]=s.split('|');return{en:e,he:h}});
const LETTERS='אבגדהוזחטיכלמנסעפצקרשת';
const letter=i=>i<LETTERS.length?LETTERS[i]:String(i+1);

/* ---------- the model of a sheet: pure data, so a test can check it against js/data.js ---------- */
export function build(id){const isl=ISLANDS.find(i=>i.id===id);if(!isl)return null;
 const parts=isl.bonus?[6,7]:[id],out={id,he:isl.he,en:isl.en,ex:[]};
 parts.forEach((p,k)=>{const w=pairs(p),right=mix(w.map((_,i)=>i),id*100+p);
  out.ex.push({kind:'match',title:isl.bonus?(p===6?'חודשים':'מספרים'):'מילים',task:'כתבו ליד כל מילה את האות של הפירוש שלה.',
   left:w.map(x=>x.en),right:right.map(i=>w[i].he),
   /* two words can share a translation (e.g. two that mean the same): any letter of that translation is right */
   key:w.map(x=>right.map((i,j)=>w[i].he===x.he?letter(j):'').filter(Boolean).join(' / '))})});
 if(!isl.bonus){
  const t=TEXTS.find(x=>x.p===id);
  if(t)out.ex.push({kind:'read',title:'סיפור',task:'קראו את הסיפור והקיפו את התשובה הנכונה.',name:t.title,text:t.text,
   qs:t.qs.map(([q,o,a],k)=>{const order=mix(o.map((_,i)=>i),id*1000+k);return{q,o:order.map(i=>o[i]),a:order.indexOf(a)}})});
  const tb=TOBE_BY[id];
  if(tb)out.ex.push({kind:'tobe',title:'am / is / are',task:'השלימו את המשפט במילה הנכונה.',bank:['am','is','are'],items:tb.map(([s,a])=>({s,a}))});
  const st=SENT[id];
  if(st)out.ex.push({kind:'order',title:'משפטים',task:'סדרו את המילים וכתבו את המשפט.',
   items:st.map(([s,he],k)=>{const end=/[.?!]$/.test(s)?s.slice(-1):'',words=(end?s.slice(0,-1):s).split(' ');return{words:mix(words,id*10000+k),end,he,a:s}})})}
 return out}

/* ---------- drawing ---------- */
const NUM=['א','ב','ג','ד','ה','ו'];
function exHtml(x,n){const head=`<h2><span class="n">${NUM[n]}</span>${x.kind==='tobe'?en(x.title):esc(x.title)}</h2><p class="task">${esc(x.task)}</p>`;
 if(x.kind==='match')return `<section class="ex match">${head}<div class="cols">
   <ol class="wl">${x.left.map(w=>`<li><span class="box"></span>${en(w)}</li>`).join('')}</ol>
   <ol class="hl">${x.right.map((h,i)=>`<li><b>${letter(i)}</b><span>${esc(h)}</span></li>`).join('')}</ol></div></section>`;
 if(x.kind==='read')return `<section class="ex read">${head}<div class="story" dir="ltr" lang="en"><h3>${esc(x.name)}</h3><p>${esc(x.text)}</p></div>
   <ol class="qs" dir="ltr" lang="en">${x.qs.map(q=>`<li><p>${esc(q.q)}</p><ul>${q.o.map((o,i)=>`<li><b>${'abc'[i]}</b> ${esc(o)}</li>`).join('')}</ul></li>`).join('')}</ol></section>`;
 if(x.kind==='tobe')return `<section class="ex tobe">${head}<p class="bank" dir="ltr" lang="en">${x.bank.map(b=>`<b>${esc(b)}</b>`).join('')}</p>
   <ol class="fill" dir="ltr" lang="en">${x.items.map(it=>`<li>${it.s.split('___').map(esc).join('<span class="gap"></span>')}</li>`).join('')}</ol></section>`;
 return `<section class="ex order">${head}<ol class="ord">${x.items.map(it=>`<li><p class="he">${esc(it.he)}</p>
   <p class="tiles" dir="ltr" lang="en">${it.words.map(w=>`<b>${esc(w)}</b>`).join('')}${it.end?`<b class="end">${esc(it.end)}</b>`:''}</p><p class="line"></p></li>`).join('')}</ol></section>`}
function keyHtml(m){return `<section class="page key" id="key"><header class="hd"><h1>תשובות · ${esc(m.he)}</h1></header>${m.ex.map((x,n)=>{
  const h=`<h2><span class="n">${NUM[n]}</span>${x.kind==='tobe'?en(x.title):esc(x.title)}</h2>`;
  if(x.kind==='match')return h+`<p class="kl">${x.left.map((w,i)=>`<span>${en(w)} ${esc(x.key[i])}</span>`).join('')}</p>`;
  if(x.kind==='read')return h+`<p class="kl">${x.qs.map((q,i)=>`<span>${i+1}. ${en('abc'[q.a]+' '+q.o[q.a])}</span>`).join('')}</p>`;
  if(x.kind==='tobe')return h+`<p class="kl">${x.items.map((it,i)=>`<span>${i+1}. ${en(it.a)}</span>`).join('')}</p>`;
  return h+`<p class="kl col">${x.items.map((it,i)=>`<span>${i+1}. ${en(it.a)}</span>`).join('')}</p>`}).join('')}</section>`}

export function render(root,id,withKey){const m=build(id);
 if(!m){root.innerHTML='';return null}
 root.innerHTML=`<section class="page"><header class="hd"><div><h1>${esc(m.he)}</h1><p class="sub">${en(m.en)} · דף עבודה</p></div>
   <p class="who"><span>שם: <i></i></span><span>תאריך: <i></i></span></p></header>
   ${m.ex.map(exHtml).join('')}<footer class="ft">איי המילים · ${en('Fantastic 5, Unit 1')}</footer></section>${withKey?keyHtml(m):''}`;
 return m}

/* ---------- the page ---------- */
function start(){const root=document.getElementById('sheet'),bar=document.getElementById('bar'),off=document.getElementById('off');
 if(!root)return;
 let id=1;try{const v=new URLSearchParams(location.search).get('i');if(/^[1-9]$/.test(v||'')&&ISLANDS.some(i=>i.id===+v))id=+v}catch(e){}
 const back=`index.html#island/${id}`;
 for(const a of document.querySelectorAll('[data-back]'))a.href=back;
 if(!sheetOn()){off.hidden=false;bar.hidden=true;return}
 const key=document.getElementById('key-on'),pick=document.getElementById('pick');
 pick.innerHTML=ISLANDS.map(i=>`<option value="${i.id}"${i.id===id?' selected':''}>${esc(i.he)}</option>`).join('');
 const draw=()=>{const m=render(root,id,key.checked);document.title='דף עבודה · '+m.he};
 pick.addEventListener('change',()=>{id=+pick.value;for(const a of document.querySelectorAll('[data-back]'))a.href=`index.html#island/${id}`;
  try{history.replaceState(null,'','?i='+id)}catch(e){}draw()});
 key.addEventListener('change',draw);
 document.getElementById('go').addEventListener('click',()=>window.print());
 draw()}
if(typeof document!=='undefined')start();
