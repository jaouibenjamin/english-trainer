/* Word help (behind a switch that is off unless a device was given it: ?help=1 once, then a row in the settings).
   - A tap on an English word in a sentence or a question shows its Hebrew meaning in a small bubble.
   - "The sentence in Hebrew" appears only for a sentence that already has a Hebrew translation in the game's data.
   - The 🐢 button says a recorded clip again, slowly (js/state.js, js/stretch.js).
   Every meaning comes from data that is already in the game: the teacher's Unit 1 word list (WORDS) first, then the
   reading glossary the story level has always shown (GL). Nothing is translated by a machine and nothing is made up
   here: a word without an entry is simply not a button.
   Help never costs points and never ends anything. Each use is noted on this device only (HELP_KEY), next to but not
   inside the progress that is saved to the class: nothing new is sent anywhere. */
import {meaning,tokens,sentenceHe} from './helpdata.js';
import {SET,saveSet,esc} from './state.js';
export {meaning,tokens,sentenceHe};

export const helpOn=()=>SET.help===true;
export const helpKnown=()=>typeof SET.help==='boolean';      // this device has been given the switch
/* ?help=1 gives a device the switch (and turns it on), ?help=0 turns it off again */
export function initHelp(){let v=null;try{v=new URLSearchParams(location.search).get('help')}catch(e){}
 if(v==='1'||v==='0'){SET.help=v==='1';saveSet()}
 if(helpOn())install()}
export function setHelp(on){SET.help=!!on;saveSet();if(on)install();else close()}

/* the meanings themselves live in js/helpdata.js (data only, no browser), so tests/help_coverage.mjs can count them */
/* ---------- markup (plain escaped text when the switch is off: exactly what the screens drew before) ---------- */
/* skip: words that must not be given away here (lower case), e.g. the answer of the question on screen */
export function words(text,skip){if(!helpOn())return esc(text);
 return tokens(text).map(t=>/[A-Za-z]/.test(t)&&meaning(t)&&!(skip&&skip.includes(t.toLowerCase()))?`<button type="button" class="hw" data-hw="${esc(t)}" aria-expanded="false">${esc(t)}</button>`:esc(t)).join('')}
export const sentBtn=en=>helpOn()&&sentenceHe(en)?`<button type="button" class="hsb" data-hs="${esc(en)}" aria-expanded="false">המשפט בעברית</button>`:'';
export const slowBtn=(act,extra='')=>helpOn()?`<button type="button" class="btn cream hslow" data-a="${act}" aria-label="השמיעו לאט" title="השמיעו לאט" ${extra}><span><i aria-hidden="true">🐢</i> לאט</span></button>`:'';

/* ---------- what was looked up, on this device only ---------- */
export const HELP_KEY='wi-help-v1';
/* {items:{[item key]:{n: times, w:[words looked up], s: 1 if the whole sentence was shown, slow: times heard slowly, t: day}}} */
export function note(item,what,word){if(!helpOn()||!item)return;
 try{const d=JSON.parse(localStorage.getItem(HELP_KEY))||{},it=d.items||(d.items={}),r=it[item]||(it[item]={n:0,w:[]});
  r.n++;r.t=new Date().toISOString().slice(0,10);
  if(what==='word'&&word&&!r.w.includes(word)&&r.w.length<40)r.w.push(word);
  if(what==='sentence')r.s=1;if(what==='slow')r.slow=(r.slow||0)+1;
  const keys=Object.keys(it);if(keys.length>600)for(const k of keys.slice(0,keys.length-600))delete it[k];
  d.v=1;localStorage.setItem(HELP_KEY,JSON.stringify(d))}catch(e){}}
const itemOf=el=>{const h=el.closest('[data-hk]');return h?h.dataset.hk:'screen:'+((document.getElementById('stage')||{}).dataset||{}).scr};

/* ---------- the bubble ---------- */
/* what a pupil must always be able to see and press: the bubble never lies over one of these */
const KEEP='.xo,.xtile,.xans,#xi,[data-a=mockcheck],.pl,.bottle,.bub,.btn:not(.hslow)';
/* what it should also leave readable whenever there is room: the question and its sentence */
const READ='.xqt,.xsent,.xraw,.xdesc,.xbigw,.xtext,.xkids,.slot,.prompt';
let bub=null,from=null,installed=false;
function make(){const stage=document.getElementById('stage');bub=document.createElement('div');bub.id='hbub';bub.className='hbub';bub.setAttribute('role','status');bub.setAttribute('aria-live','polite');bub.hidden=true;stage.appendChild(bub)}
export function close(){if(from){from.setAttribute('aria-expanded','false');from.classList.remove('on')}from=null;if(bub){bub.hidden=true;bub.textContent=''}}
const hit=(a,b)=>a.left<b.right-1&&a.right>b.left+1&&a.top<b.bottom-1&&a.bottom>b.top+1;
function show(el,enText,heText){if(!bub||!bub.isConnected)make();
 if(from)close();from=el;el.setAttribute('aria-expanded','true');el.classList.add('on');
 /* text only, never markup: the words come from the page and are written as text */
 bub.textContent='';
 if(enText){const a=document.createElement('bdi');a.className='en';a.dir='ltr';a.textContent=enText;const q=document.createElement('span');q.className='eq';q.textContent=' = ';bub.append(a,q)}
 const h=document.createElement('span');h.className='he';h.dir='rtl';h.textContent=heText;bub.append(h);
 bub.hidden=false;bub.style.left='0px';bub.style.top='0px';
 const stage=bub.parentElement,S=stage.getBoundingClientRect(),r=el.getBoundingClientRect(),bw=bub.offsetWidth,bh=bub.offsetHeight,pad=8;
 const x=Math.max(pad,Math.min(S.width-bw-pad,r.left-S.left+r.width/2-bw/2));
 const rects=sel=>[...stage.querySelectorAll(sel)].filter(k=>k!==el&&k.offsetParent).map(k=>k.getBoundingClientRect());
 const keep=rects(KEEP),read=rects(READ);
 const free=(y,all)=>{const b={left:S.left+x,right:S.left+x+bw,top:S.top+y,bottom:S.top+y+bh};return y>=pad&&y+bh<=S.height-pad&&!hit(b,r)&&!keep.some(k=>hit(b,k))&&!(all&&read.some(k=>hit(b,k)))};
 /* the nearest free place above the word, else below it: first one that covers neither the answers nor the question's
    text; if there is none, one that at least covers nothing to press */
 let y=null;
 for(const all of [true,false]){
  for(let c=r.top-S.top-bh-8;c>=pad&&y===null;c-=10)if(free(c,all))y=c;
  for(let c=r.bottom-S.top+8;c+bh<=S.height-pad&&y===null;c+=10)if(free(c,all))y=c}
 if(y===null)y=Math.max(pad,r.top-S.top-bh-8);
 bub.style.left=x+'px';bub.style.top=y+'px'}
function onClick(e){if(!helpOn())return;
 const w=e.target.closest('.hw'),s=!w&&e.target.closest('.hsb');
 if(w){if(from===w)return close();const m=meaning(w.dataset.hw);if(!m)return;show(w,w.dataset.hw,m.he);note(itemOf(w),'word',w.dataset.hw.toLowerCase());return}
 if(s){if(from===s)return close();const h=sentenceHe(s.dataset.hs);if(!h)return;show(s,'',h);note(itemOf(s),'sentence');return}
 if(from&&!e.target.closest('#hbub'))close()}
function install(){if(installed)return;installed=true;
 document.addEventListener('click',onClick,true);
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&from){const f=from;close();f.focus&&f.focus()}});
 addEventListener('hashchange',close);addEventListener('resize',close);
 document.addEventListener('scroll',()=>{if(from)close()},true)}
