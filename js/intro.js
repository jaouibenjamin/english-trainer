/* The opening flow and the welcome film (36 s), behind the design flag (?ds=1). docs/INTRO.md "Opening flow".
   js/dsflag.js loads this file only when the flag is on and this device has not seen the film yet (localStorage
   wi_intro); with the flag off nothing of it is fetched or stored, and a device that has seen it gets no splash.
   - From the first paint the page is navy (dsflag's cover, html.wi-intro-pending); the game is laid out behind it.
   - "ניצני אופק" pops in, then "▶ צפייה בסרטון" with "עם קול": the one tap a browser needs before sound. The button and
     the logo both start the film; nothing plays by itself. "דלגו" is there from the first second; Escape = skip.
   - The film cross-fades in over the logo on its first frame. At the end "מתחילים" pops up.
   - Closing ("מתחילים", "דלגו", Escape) stores wi_intro=1 and fades the overlay out (0.45 s) onto the first screen,
     already laid out behind; focus goes to its first control. If the film never starts (10 s after the tap) or fails,
     "מתחילים" shows at once with a line, and wi_intro is not stored: it is offered again next time.
   - While the overlay is open (html.wi-intro-open, set by dsflag before any module runs) the game's own music, sound
     effects and voice stay silent and do not start (js/audio.js, js/state.js); they start only on 'wi-intro-closed'.
   - Captions of the narration are live text; a hidden tab pauses the film, and only a tap goes on.
   - Calm mode or prefers-reduced-motion: fades only (css/ds-intro.css).
   DOM is built with createElement and textContent only. The narration text is flagged for the teacher (docs/INTRO.md). */
const FILM='assets/al/intro/intro.hf_20261125_164702_e78eef89-88e1-4b0e-ab69-1469ee330bf6.mp4';
/* the same film, lighter (390 x 710, about 2.6 MB): the default. The full one only when the browser says the link is
   fast (4g) and data saving is off; Safari does not say, so iPhones get the light one */
const FILM_LIGHT='assets/al/intro/intro-light.hf_20261125_164702_e78eef89-88e1-4b0e-ab69-1469ee330bf6.mp4';
const full=()=>{try{const c=navigator.connection;return !!c&&!c.saveData&&c.effectiveType==='4g'}catch(e){return false}};
const LOGO='assets/al/intro/logo.webp';
const SOUND='assets/al/ui/sound-on.hf_20261124_204752_b82c7717-fa0a-4eef-b50e-de204f3e78e6.webp';
const START_MS=10000;   // the film has not started this long after the tap: say so and let the child in
/* [from, to, text] in seconds of the film, from the pauses in the narration */
const CUES=[
 [0.3,4.9,'הצלצול האחרון. נפרדים מהחברים, ויוצאים לדרך.'],
 [5.9,9.2,'הולכים יחד לאורך הים, כמו בכל יום.'],
 [11.2,14.6,'יושבים על הדשא, מדברים, צוחקים...'],
 [16.2,17.6,'ופתאום...'],
 [17.8,21.1,'מתוך הים עולה אי ענק!'],
 [23.0,26.6,'Hey kids! Are you ready for an adventure?\nהיי ילדים! מוכנים להרפתקה?'],
 [27.0,29.0,'Yeah, let\'s go!\nכן, יאללה!']];
/* the closing title, "ברוכים הבאים לניצני אופק!", is in the film itself from 32 s, so there is no caption for it */
const el=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!=null)e.textContent=txt;return e};
const H=document.documentElement;

export function showIntro(){
 if(document.getElementById('wi-intro'))return;
 const box=el('div','wi-intro');box.id='wi-intro';box.dataset.s='splash';box.setAttribute('role','dialog');box.setAttribute('aria-modal','true');box.setAttribute('aria-label','ניצני אופק, סרטון פתיחה');
 const v=el('video','wi-intro__film');v.setAttribute('playsinline','');v.preload='none';v.muted=false;v.setAttribute('aria-hidden','true');
 const splash=el('div','wi-intro__splash');
 const logo=el('img','wi-intro__logo');logo.src=LOGO;logo.alt='ניצני אופק';logo.width=640;logo.height=201;
 const play=el('button','wi-intro__play');play.type='button';
 play.append(el('span','wi-intro__tri','▶'),el('span','','צפייה בסרטון'));play.firstChild.setAttribute('aria-hidden','true');
 const snd=el('p','wi-intro__snd');const si=el('img');si.src=SOUND;si.alt='';si.width=22;si.height=22;snd.append(si,el('span','','עם קול'));
 const dots=el('div','wi-intro__dots');dots.setAttribute('aria-hidden','true');dots.append(el('b'),el('b'),el('b'));
 splash.append(logo,play,snd,dots);
 const cap=el('p','wi-intro__cap');cap.hidden=true;
 const skip=el('button','wi-intro__skip','דלגו');skip.type='button';
 const fail=el('p','wi-intro__fail','הסרטון לא נטען. ננסה שוב בפעם הבאה.');   // wi_intro is not stored: it is offered again on the next open (the spec's "in the settings" waits for a settings row: docs/INTRO.md)fail.hidden=true;
 const done=el('button','wi-intro__done','מתחילים');done.type='button';done.hidden=true;
 box.append(v,splash,cap,fail,done,skip);
 /* the rest of the page is inert while the film is open; it is laid out behind the overlay the whole time */
 const others=[...document.body.children].filter(n=>!n.inert);
 others.forEach(n=>{n.inert=true});document.body.appendChild(box);
 H.classList.add('wi-intro-open');H.classList.remove('wi-intro-pending');   // the overlay is the cover from now on
 let closed=false,failed=false,timer=0;
 const state=s=>{box.dataset.s=s};
 function close(){
  if(closed)return;closed=true;clearTimeout(timer);
  if(!failed)try{localStorage.setItem('wi_intro','1')}catch(e){}
  try{v.pause();v.removeAttribute('src');v.load()}catch(e){}
  document.removeEventListener('keydown',key);document.removeEventListener('visibilitychange',hide);
  others.forEach(n=>{n.inert=false});
  /* the overlay fades out onto the first screen, whose panel rises into place; the game's sound may start now */
  state('out');H.classList.add('wi-intro-rise');H.classList.remove('wi-intro-open');
  try{dispatchEvent(new Event('wi-intro-closed'))}catch(e){}
  const first=document.querySelector('#view button:not([disabled]),#view input,#view a[href],#view [tabindex="0"]');
  try{if(first)first.focus({preventScroll:true})}catch(e){}
  setTimeout(()=>{box.remove();H.classList.remove('wi-intro-rise')},500);
 }
 function key(e){if(e.key==='Escape')close()}
 function start(){
  if(closed||box.dataset.s==='load'||box.dataset.s==='film')return;
  state('load');if(!v.getAttribute('src'))v.src=full()?FILM:FILM_LIGHT;
  clearTimeout(timer);timer=setTimeout(broken,START_MS);
  const p=v.play();if(p&&p.catch)p.catch(()=>{if(!closed&&box.dataset.s==='load'&&v.paused)state(v.currentTime>0?'pause':'splash')});
 }
 function broken(){if(closed)return;failed=true;clearTimeout(timer);try{v.pause()}catch(e){}cap.hidden=true;fail.hidden=false;done.hidden=false;state('end');done.focus()}
 /* a hidden tab pauses the film (and its sound); it goes on only when the child taps "watch" again */
 function hide(){if(document.hidden&&!v.paused){v.pause();state('pause')}}
 document.addEventListener('keydown',key);document.addEventListener('visibilitychange',hide);
 skip.addEventListener('click',close);done.addEventListener('click',close);
 play.addEventListener('click',start);logo.addEventListener('click',start);
 v.addEventListener('playing',()=>{clearTimeout(timer);if(!closed)state('film')});
 v.addEventListener('error',()=>{if(v.getAttribute('src'))broken()});
 v.addEventListener('timeupdate',()=>{
  const t=v.currentTime,c=CUES.find(q=>t>=q[0]&&t<q[1]);
  /* one element per line, each with its own direction: an English first line must not turn the Hebrew line around */
  const k=c?c[2]:'';if(cap.dataset.k!==k){cap.dataset.k=k;cap.replaceChildren(...k.split('\n').filter(Boolean).map(t=>{const l=el('span','wi-intro__line',t);l.dir=/[֐-׿]/.test(t)?'rtl':'ltr';l.lang=l.dir==='rtl'?'he':'en';return l}))}
  cap.hidden=!c;
 });
 v.addEventListener('ended',()=>{cap.hidden=true;done.hidden=false;state('end');done.focus()});
 play.focus();
 return box;
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',showIntro);else showIntro();
