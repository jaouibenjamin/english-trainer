/* Word help (behind a switch that is off unless a device was given it: ?help=1 once, then a row in the settings).
   - A tap on an English word in a sentence or a question shows its Hebrew meaning in a small bubble.
   - "The sentence in Hebrew" appears only for a sentence that already has a Hebrew translation in the game's data.
   - The 🐢 button says a recorded clip again, slowly (js/state.js, js/stretch.js).
   Every meaning comes from the teacher's Unit 1 word list (WORDS), which is already in the game. The reading glossary
   of the story level (GL) is not used until the teacher has gone over it (GLOSSARY in js/helpdata.js). Nothing is
   translated by a machine and nothing is made up here: a word without an entry is simply not a button.
   Help never costs points and never ends anything. Each use is noted on this device only (HELP_KEY), next to but not
   inside the progress that is saved to the class: nothing new is sent anywhere. */
import {meaning,tokens,sentenceHe,sentKey,sentByKey} from './helpdata.js';
import {SET,saveSet,esc} from './state.js';
export {meaning,tokens,sentenceHe};

export const helpOn=()=>SET.help===true;
export const helpKnown=()=>typeof SET.help==='boolean';      // this device has been given the switch
/* ?help=1 gives a device the switch (and turns it on), ?help=0 turns it off again. On a device that never had the
   switch ?help=0 changes nothing. The parameter is then taken out of the address, so a link copied from the address
   bar does not carry the switch to another device. */
export function initHelp(){let v=null,q=null;try{q=new URLSearchParams(location.search);v=q.get('help')}catch(e){}
 if(v==='1'||(v==='0'&&helpKnown())){SET.help=v==='1';saveSet()}
 if(v!==null)try{q.delete('help');const s=q.toString();history.replaceState(history.state,'',location.pathname+(s?'?'+s:'')+location.hash)}catch(e){}
 if(helpOn())install()}
export function setHelp(on){SET.help=!!on;saveSet();if(on)install();else close()}

/* the meanings themselves live in js/helpdata.js (data only, no browser), so tests/help_coverage.mjs can count them */
/* ---------- markup (plain escaped text when the switch is off: exactly what the screens drew before) ---------- */
/* skip: words that must not be given away here (lower case), e.g. the answer of the question on screen */
/* One call is one line of text. Its help words are one stop for the Tab key: the first is in the tab order, the
   arrow keys move along the line (a roving tabindex), so a long passage does not put sixty stops before the answers.
   A skipped word that has a meaning is drawn to look the same but is not a button: it must not stand out as the answer. */
let lineN=0;
export function words(text,skip){if(!helpOn())return esc(text);const g=++lineN;let first=true;
 return tokens(text).map(t=>{if(!/[A-Za-z]/.test(t)||!meaning(t))return esc(t);
  if(skip&&skip.includes(t.toLowerCase()))return `<span class="hw hx" lang="en">${esc(t)}</span>`;
  const b=`<button type="button" class="hw" lang="en" data-hw="${esc(t)}" data-hg="${g}" tabindex="${first?0:-1}" aria-expanded="false">${esc(t)}</button>`;first=false;return b}).join('')}
/* the button carries the sentence's place in the list, not the sentence (which may hold the answer) */
export const sentBtn=en=>helpOn()&&sentKey(en)>=0?`<button type="button" class="hsb" data-hs="${sentKey(en)}" aria-expanded="false">המשפט בעברית</button>`:'';
/* small: the turtle alone, for a row that has no room for the word (the name is still read out) */
export const slowBtn=(act,extra='',small=false)=>helpOn()?`<button type="button" class="btn cream hslow${small?' sm1':''}" data-a="${act}" aria-label="השמיעו לאט" title="השמיעו לאט" ${extra}><span><i aria-hidden="true">🐢</i>${small?'':' לאט'}</span></button>`:'';

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
/* a pupil signs out: the next pupil on this device starts with an empty note */
export const clearNotes=()=>{try{localStorage.removeItem(HELP_KEY)}catch(e){}};
const itemOf=el=>{const h=el.closest('[data-hk]');return h?h.dataset.hk:'screen:'+((document.getElementById('stage')||{}).dataset||{}).scr};

/* ---------- the bubble ---------- */
/* what a pupil must always be able to press or see to answer: the bubble never lies over one of these */
const KEEP='.xo,.xtile,.xans,#xi,[data-a=mockcheck],.pl,.bottle,.bub,.btn:not(.hslow),.xpic,.xinv,.xkids';   // answers, and what the question is about: its picture, its card
/* what it should leave readable when there is room: the question's text, its counter, the other help button */
const READ='.xqt,.xsent,.xraw,.xdesc,.xbigw,.xtext,.slot,.prompt,.hsb',COUNT='.xcount';
let bub=null,from=null,installed=false;
function make(){const stage=document.getElementById('stage');bub=document.createElement('div');bub.id='hbub';bub.className='hbub';bub.setAttribute('role','status');bub.setAttribute('aria-live','polite');bub.hidden=true;stage.appendChild(bub)}
export function close(){if(from){from.setAttribute('aria-expanded','false');from.classList.remove('on')}from=null;if(bub){bub.hidden=true;bub.textContent='';bub.classList.remove('hpd','hpu')}}
const hit=(a,b)=>a.left<b.right-1&&a.right>b.left+1&&a.top<b.bottom-1&&a.bottom>b.top+1;
function show(el,enText,heText){if(!bub||!bub.isConnected)make();
 if(from)close();from=el;el.setAttribute('aria-expanded','true');el.classList.add('on');
 /* text only, never markup: the words come from the page and are written as text */
 bub.textContent='';
 if(enText){const a=document.createElement('bdi');a.className='en';a.dir='ltr';a.lang='en';a.textContent=enText;const q=document.createElement('span');q.className='eq';q.textContent=' = ';bub.append(a,q)}
 const h=document.createElement('span');h.className='he';h.dir='rtl';h.textContent=heText;bub.append(h);
 bub.hidden=false;bub.style.left='0px';bub.style.top='0px';
 const stage=bub.parentElement,S=stage.getBoundingClientRect(),r=el.getBoundingClientRect(),bw=bub.offsetWidth,bh=bub.offsetHeight,pad=8,GAP=10;
 const x=Math.max(pad,Math.min(S.width-bw-pad,r.left-S.left+r.width/2-bw/2));
 const rects=sel=>[...stage.querySelectorAll(sel)].filter(k=>k!==el&&k.offsetParent).map(k=>k.getBoundingClientRect());
 /* a sentence's box is taller than its letters (its lines are set apart for the fingers): only its middle counts as text */
 const inset=q=>({left:q.left,right:q.right,top:q.top+8,bottom:q.bottom-8});
 const keep=rects(KEEP),read=rects(READ).map(inset),count=rects(COUNT),wt=r.top-S.top,wb=r.bottom-S.top;
 /* the sentence being explained: the line the word is in, or the sentence above its "in Hebrew" button */
 const ownEl=el.closest('.xsent,.xraw,.slot')||(el.classList.contains('hsb')?el.previousElementSibling:null),own=ownEl?[inset(ownEl.getBoundingClientRect())]:[];
 /* Every place the bubble could go, from the top of the screen to the bottom, gets a cost: covering an answer is out
    of the question unless nothing else exists, covering the counter or a line of the question costs a little, and so
    does every step away from the word. The cheapest place wins: next to the word whenever that is possible. */
 const cost=y=>{const b={left:S.left+x,right:S.left+x+bw,top:S.top+y,bottom:S.top+y+bh},n=l=>l.filter(k=>hit(b,k)).length;
  return n(keep)*1000+n(count)*8+n(own)*6+n(read)*3+(y>=wb?y-wb:wt-(y+bh))/25+(y>=wb?0:.02)};   // 75 px further from the word costs as much as covering one line of the question
 let y=null,best=Infinity;
 for(const c of [wb+GAP,wt-bh-GAP,...Array.from({length:Math.max(0,Math.ceil((S.height-bh-2*pad)/6))},(_,k)=>pad+k*6)]){
  if(c<pad||c+bh>S.height-pad||(c<wb+GAP-1&&c+bh>wt-GAP+1))continue;   // inside the screen, and never over the word itself
  const v=cost(c);if(v<best){best=v;y=c}}
 if(y===null)y=Math.max(pad,Math.min(S.height-bh-pad,wb+GAP));
 bub.style.left=x+'px';bub.style.top=y+'px';
 /* a small pointer on the side of the word, aimed at its middle, when the bubble sits right next to it */
 const below=y>=wb,gap=below?y-wb:wt-(y+bh);
 bub.classList.toggle('hpd',below&&gap<=14);bub.classList.toggle('hpu',!below&&gap<=14);
 bub.style.setProperty('--px',Math.max(14,Math.min(bw-14,r.left-S.left+r.width/2-x))+'px')}
function onClick(e){if(!helpOn())return;
 const w=e.target.closest('.hw'),s=!w&&e.target.closest('.hsb');
 if(w){if(from===w)return close();const m=meaning(w.dataset.hw);if(!m)return;show(w,w.dataset.hw,m.he);note(itemOf(w),'word',w.dataset.hw.toLowerCase());return}
 if(s){if(from===s)return close();const h=sentByKey(s.dataset.hs);if(!h)return;show(s,'',h);note(itemOf(s),'sentence');return}
 if(from&&!e.target.closest('#hbub'))close()}
function install(){if(installed)return;installed=true;
 document.addEventListener('click',onClick,true);
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&from){const f=from;close();f.focus&&f.focus();return}
  /* the arrow keys move along the help words of one line (English: right is the next word) */
  const w=helpOn()&&(e.key==='ArrowRight'||e.key==='ArrowLeft'||e.key==='Home'||e.key==='End')&&e.target.closest&&e.target.closest('button.hw');if(!w)return;
  const all=[...document.querySelectorAll(`button.hw[data-hg="${w.dataset.hg}"]`)],i=all.indexOf(w),to=e.key==='Home'?all[0]:e.key==='End'?all[all.length-1]:all[i+(e.key==='ArrowRight'?1:-1)];
  e.preventDefault();if(!to||to===w)return;for(const b of all)b.tabIndex=b===to?0:-1;to.focus()});
 addEventListener('hashchange',close);addEventListener('resize',close);
 document.addEventListener('scroll',()=>{if(from)close()},true)}
