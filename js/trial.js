/* A ?new=1 link opened on a device that holds the Sheet's game (a signed-in pupil, or progress): the device is not
   switched to the new backend silently (review of #117). js/api.js leaves it on the Sheet and notes the question
   (sessionStorage wi_new_ask); this asks it once:
     כן: the device joins the trial (localStorage wi_new) and the game opens again on the new backend; the Sheet's
         progress stays on the device as it was (docs/PHASE4.md A: the new backend has its own record);
     לא: nothing changes, and the question goes.
   Loaded by js/main.js only when the question is waiting. The words are the lead's, for the teacher's review. */
export function ask(){
 try{if(sessionStorage.getItem('wi_new_ask')!=='1')return}catch(e){return}
 if(document.getElementById('wi-trial-ask'))return;
 const d=document.createElement('div'),p=document.createElement('p'),row=document.createElement('div'),yes=document.createElement('button'),no=document.createElement('button');
 d.id='wi-trial-ask';d.dir='rtl';d.setAttribute('role','alertdialog');d.setAttribute('aria-modal','true');d.setAttribute('aria-labelledby','wi-trial-ask-t');
 d.style.cssText='position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px;padding:24px;background:var(--paper,#fff4de);color:var(--ink,#5a4534);text-align:center';
 p.id='wi-trial-ask-t';p.textContent='מכשיר ניסיון: להמשיך למערכת החדשה? ההתקדמות שלך במשחק הרגיל נשמרת ולא נמחקת';
 p.style.cssText='margin:0;max-width:22em;font-size:22px;font-weight:700;line-height:1.4';
 row.style.cssText='display:flex;gap:16px';
 for(const [b,t] of [[yes,'כן'],[no,'לא']]){b.type='button';b.textContent=t;
  b.style.cssText='min-width:120px;min-height:56px;padding:12px 28px;border:0;border-radius:16px;background:var(--ink,#5a4534);color:var(--paper,#fff4de);font:inherit;font-size:20px;font-weight:700'}
 no.style.background='transparent';no.style.color='var(--ink,#5a4534)';no.style.boxShadow='inset 0 0 0 2px var(--ink,#5a4534)';
 const done=()=>{try{sessionStorage.removeItem('wi_new_ask')}catch(e){}};
 yes.addEventListener('click',()=>{yes.disabled=no.disabled=true;try{localStorage.setItem('wi_new','1')}catch(e){}done();location.reload()});
 no.addEventListener('click',()=>{done();d.remove();for(const c of Array.from(document.body.children||[])){try{c.inert=false;c.removeAttribute('inert')}catch(e){}}});
 row.append(yes,no);d.append(p,row);
 for(const c of Array.from(document.body.children||[])){try{c.inert=true;c.setAttribute('inert','')}catch(e){}}   // the game behind it takes no tap, key or focus
 document.body.appendChild(d);try{yes.focus()}catch(e){}
}
