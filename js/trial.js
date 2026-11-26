/* A ?new=1 link opened on a device that is not in the trial yet: the device is not switched to the new backend silently
   (reviews of #117 and #121). js/api.js leaves it on the Sheet and notes the question (sessionStorage wi_new_ask); this
   asks it once, in the game (js/main.js) or in the Beach Run (js/run.js):
     כן: the device joins the trial (localStorage wi_new) and the page opens again on the new backend; the Sheet's
         progress stays on the device as it was (docs/PHASE4.md A: the new backend has its own record);
     לא: nothing changes, and the question goes.
   While it is open the page behind it takes no tap, key or focus (inert), also what the page adds meanwhile; when it
   closes, only what it made inert is given back, and taps that land on the page in the next moments (a double tap on
   "לא") are dropped. The words are the lead's, for the teacher's review. */
const QUIET=350;   // ms after "לא" in which a tap on the page behind is dropped (review of #121: a double tap opened math)

export function ask(){
 try{if(sessionStorage.getItem('wi_new_ask')!=='1')return}catch(e){return}
 if(document.getElementById('wi-trial-ask')||!document.body)return;
 const d=document.createElement('div'),p=document.createElement('p'),row=document.createElement('div'),yes=document.createElement('button'),no=document.createElement('button');
 d.id='wi-trial-ask';d.dir='rtl';d.setAttribute('role','alertdialog');d.setAttribute('aria-modal','true');d.setAttribute('aria-labelledby','wi-trial-ask-t');
 d.style.cssText='position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px;padding:24px;background:var(--paper,#fff4de);color:var(--ink,#5a4534);text-align:center';
 p.id='wi-trial-ask-t';p.textContent='מכשיר ניסיון: להמשיך למערכת החדשה? ההתקדמות שלך במשחק הרגיל נשמרת ולא נמחקת';
 p.style.cssText='margin:0;max-width:22em;font-size:22px;font-weight:700;line-height:1.4';
 row.style.cssText='display:flex;gap:16px';
 for(const [b,t] of [[yes,'כן'],[no,'לא']]){b.type='button';b.textContent=t;
  b.style.cssText='min-width:120px;min-height:56px;padding:12px 28px;border:0;border-radius:16px;background:var(--ink,#5a4534);color:var(--paper,#fff4de);font:inherit;font-size:20px;font-weight:700'}
 no.style.background='transparent';no.style.color='var(--ink,#5a4534)';no.style.boxShadow='inset 0 0 0 2px var(--ink,#5a4534)';
 /* review of #121: only what this made inert is given back (the page may have made some of its own parts inert) */
 const made=[];
 const hush=c=>{if(c===d||c.inert||c.hasAttribute('inert'))return;try{c.inert=true;c.setAttribute('inert','');made.push(c)}catch(e){}};
 for(const c of Array.from(document.body.children))hush(c);
 let mo=null;try{mo=new MutationObserver(rs=>{for(const r of rs)for(const n of r.addedNodes)if(n.nodeType===1&&n.parentNode===document.body)hush(n)});mo.observe(document.body,{childList:true})}catch(e){}
 /* keys pressed on the dialog do not reach the page's own key handlers (the Beach Run listens on window); the button
    still takes them (nothing is prevented) */
 const keys=e=>{if(d.contains(e.target))e.stopImmediatePropagation()};
 for(const t of ['keydown','keyup','keypress'])window.addEventListener(t,keys,true);
 const done=()=>{try{sessionStorage.removeItem('wi_new_ask')}catch(e){}for(const t of ['keydown','keyup','keypress'])window.removeEventListener(t,keys,true)};
 yes.addEventListener('click',()=>{yes.disabled=no.disabled=true;try{localStorage.setItem('wi_new','1')}catch(e){}done();location.reload()});
 no.addEventListener('click',()=>{yes.disabled=no.disabled=true;done();if(mo)mo.disconnect();
  /* a second tap of a double tap would land on the page behind: dropped before anything on the page sees it */
  const until=Date.now()+QUIET,EV=['pointerdown','pointerup','mousedown','mouseup','touchstart','touchend','click','dblclick'];
  const off=()=>{for(const t of EV)window.removeEventListener(t,drop,true)};
  const drop=e=>{if(Date.now()>until)return off();e.stopImmediatePropagation();if(e.cancelable)e.preventDefault()};
  for(const t of EV)window.addEventListener(t,drop,{capture:true,passive:false});
  setTimeout(off,QUIET+50);
  d.remove();for(const c of made){try{c.inert=false;c.removeAttribute('inert')}catch(e){}}});
 row.append(yes,no);d.append(p,row);
 document.body.appendChild(d);
 /* review of #121: the focus starts on "לא" (the safe answer), inside the dialog; again after the page's own start,
    which may move it */
 const f=()=>{try{if(d.isConnected&&!d.contains(document.activeElement))no.focus()}catch(e){}};
 f();try{requestAnimationFrame(f)}catch(e){}setTimeout(f,0);setTimeout(f,300);
}
