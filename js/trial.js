/* A ?new=1 link opened on a device that is not in the trial yet: the device is not switched to the new backend silently
   (reviews of #117 and #121). js/api.js leaves it on the Sheet and notes the question (sessionStorage wi_new_ask); this
   asks it once, in the game (js/main.js) or in the Beach Run (js/run.js), as a screen of the game (docs/SIGNIN.md
   section 6, docs/mock/trial.html):
     "חזרה למשחק הרגיל" (the big gold button, with the focus: a child who came by mistake presses the obvious one):
         nothing changes, and the question goes;
     "להמשיך לניסיון" (the quiet button): the device joins the trial (localStorage wi_new) and the page opens again on
         the new backend; the Sheet's progress stays on the device as it was (docs/PHASE4.md A).
   While it is open the page behind it takes no tap, key or focus (inert), also what the page adds meanwhile; when it
   closes, only what it made inert is given back, and taps that land on the page in the next moments (a double tap)
   are dropped. The words are the designer's, for the teacher's review. */
const QUIET=700;   // ms after "חזרה" in which a tap on the page behind is dropped (reviews of #121 and #129: a child's taps come 200-500 ms apart, LESSONS 2)
const T={h:'רגע, זה מכשיר ניסיון',t:'כאן בודקים את המערכת החדשה של המשחק. הגעתם לכאן בטעות? אין בעיה: חוזרים למשחק הרגיל, וכל מה שעשיתם בו נשמר.',
 stay:'חזרה למשחק הרגיל',go:'להמשיך לניסיון'};
const PITZI='assets/al/pitzi/wave.hf_20261124_204450_c2effc24-9597-44ee-9eb7-204c981203c3.webp';

export function ask(){
 try{if(sessionStorage.getItem('wi_new_ask')!=='1')return}catch(e){return}
 if(document.getElementById('wi-trial-ask')||!document.body)return;
 /* its look: css/ds.css (wi- classes and tokens only, nothing outside them) and css/trial.css. The screen covers the page
    at once (navy, inline), so nothing behind it can be seen or tapped while they load */
 for(const h of['css/ds.css','css/trial.css'])if(!document.querySelector(`link[href="${h}"]`)){const l=document.createElement('link');l.rel='stylesheet';l.href=h;document.head.appendChild(l)}
 const d=document.createElement('section');
 d.id='wi-trial-ask';d.className='wt-ask wi-root';d.dir='rtl';d.lang='he';
 d.setAttribute('role','alertdialog');d.setAttribute('aria-modal','true');d.setAttribute('aria-labelledby','wi-trial-ask-t');d.setAttribute('aria-describedby','wi-trial-ask-d');
 d.style.cssText='position:fixed;inset:0;z-index:1000;background:#0B1E3F;color:#fff';
 d.innerHTML=`<div class="wt-mid"><img class="wt-crab" src="${PITZI}" alt="" width="120" height="120" draggable="false">
  <h2 class="wt-h" id="wi-trial-ask-t">${T.h}</h2><p class="wt-txt" id="wi-trial-ask-d">${T.t}</p></div>
  <div class="wt-bar"><button type="button" class="wi-btn wi-btn--block" data-ask="stay">${T.stay}</button>
  <button type="button" class="wi-btn wi-btn--quiet" data-ask="go">${T.go}</button></div>`;
 const stay=d.querySelector('[data-ask="stay"]'),go=d.querySelector('[data-ask="go"]');
 /* review of #121: only what this made inert is given back (the page may have made some of its own parts inert) */
 const made=[];
 const hush=c=>{if(c===d||c.inert||c.hasAttribute('inert'))return;try{c.inert=true;c.setAttribute('inert','');made.push(c)}catch(e){}};
 for(const c of Array.from(document.body.children))hush(c);
 let mo=null;try{mo=new MutationObserver(rs=>{for(const r of rs)for(const n of r.addedNodes)if(n.nodeType===1&&n.parentNode===document.body)hush(n)});mo.observe(document.body,{childList:true})}catch(e){}
 /* keys pressed on the screen do not reach the page's own key handlers (the Beach Run listens on window); the buttons
    still take them (nothing is prevented) */
 const KEYS=['keydown','keyup','keypress'],keys=e=>{if(d.contains(e.target))e.stopImmediatePropagation()};
 for(const t of KEYS)window.addEventListener(t,keys,true);
 const done=()=>{stay.disabled=go.disabled=true;try{sessionStorage.removeItem('wi_new_ask')}catch(e){}for(const t of KEYS)window.removeEventListener(t,keys,true)};
 go.addEventListener('click',()=>{done();try{localStorage.setItem('wi_new','1')}catch(e){}location.reload()});
 stay.addEventListener('click',()=>{done();if(mo)mo.disconnect();
  /* the second tap of a double tap would land on the page behind: dropped before anything on the page sees it */
  const until=Date.now()+QUIET,EV=['pointerdown','pointerup','mousedown','mouseup','touchstart','touchend','click','dblclick'];
  const off=()=>{for(const t of EV)window.removeEventListener(t,drop,true)};
  const drop=e=>{if(Date.now()>until)return off();e.stopImmediatePropagation();if(e.cancelable)e.preventDefault()};
  for(const t of EV)window.addEventListener(t,drop,{capture:true,passive:false});
  setTimeout(off,QUIET+50);
  d.remove();for(const c of made){try{c.inert=false;c.removeAttribute('inert')}catch(e){}}});
 document.body.appendChild(d);
 /* the focus starts on the safe button, inside the screen; again after the page's own start, which may move it */
 const f=()=>{try{if(d.isConnected&&!d.contains(document.activeElement))stay.focus()}catch(e){}};
 f();try{requestAnimationFrame(f)}catch(e){}setTimeout(f,0);setTimeout(f,300);
}
