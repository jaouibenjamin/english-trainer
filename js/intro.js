/* The welcome film (36 s), behind the design flag (?ds=1). js/dsflag.js imports this file only when the flag is on and
   this device has not seen the film yet (localStorage wi_intro); with the flag off nothing of it is fetched or stored.
   - Nothing plays by itself: the poster shows with two buttons, "watch" and "skip". The film (with sound) starts on
     the child's tap. "Skip" is there from the first second, 48 px, and Escape closes too.
   - Captions of the narration are live text on screen, for a child without sound; the closing title is in the film itself.
   - Closing (skip, Escape, end) stores wi_intro=1 on this device and removes everything, the video's source included.
   - Calm mode or prefers-reduced-motion: the poster and the buttons show, the film still waits for a tap.
   DOM is built with createElement and textContent only. The narration text is flagged for the teacher (docs/INTRO.md). */
const FILM='assets/al/intro/intro.hf_20261125_164702_e78eef89-88e1-4b0e-ab69-1469ee330bf6.mp4';
/* the same film, lighter (390 x 710, about 2.6 MB): the default. The full one only when the browser says the link is
   fast (4g) and data saving is off; Safari does not say, so iPhones get the light one */
const FILM_LIGHT='assets/al/intro/intro-light.hf_20261125_164702_e78eef89-88e1-4b0e-ab69-1469ee330bf6.mp4';
const full=()=>{try{const c=navigator.connection;return !!c&&!c.saveData&&c.effectiveType==='4g'}catch(e){return false}};
const POSTER='assets/al/intro/poster.hf_20261125_160942_30220de2-7942-4db5-bb82-9f99b71a615f.webp';
/* [from, to, text] in seconds of the film, from the pauses in the narration */
const CUES=[
 [0.3,4.9,'הצלצול האחרון. נפרדים מהחברים, ויוצאים לדרך.'],
 [5.9,9.2,'הולכים יחד לאורך הים, כמו בכל יום.'],
 [11.2,14.6,'יושבים על הדשא, מדברים, צוחקים...'],
 [16.2,17.6,'ופתאום...'],
 [17.8,21.1,'מתוך הים עולה אי ענק!'],
 [23.0,26.6,'Hey kids! Are you ready for an adventure?\nהיי ילדים! מוכנים להרפתקה?'],
 [27.0,29.0,'Yeah, let\'s go!\nכן, יאללה!']];
/* the closing title, "ברוכים הבאים לניצני אופק!", is in the film itself from 32 s (it flies in from the front), so
   there is no live title and no caption for it */
const el=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!=null)e.textContent=txt;return e};

export function showIntro(){
 if(document.getElementById('wi-intro'))return;
 const box=el('div','wi-intro');box.id='wi-intro';box.setAttribute('role','dialog');box.setAttribute('aria-modal','true');box.setAttribute('aria-label','סרטון פתיחה');
 const v=el('video','wi-intro__film');v.setAttribute('playsinline','');v.preload='none';v.poster=POSTER;v.muted=false;v.setAttribute('aria-hidden','true');
 const cap=el('p','wi-intro__cap');
 const skip=el('button','wi-intro__skip','דלגו');skip.type='button';
 const play=el('button','wi-intro__play','צפייה בסרטון');play.type='button';
 const done=el('button','wi-intro__done','מתחילים');done.type='button';done.hidden=true;
 box.append(v,cap,play,done,skip);
 /* the rest of the page is inert while the film is open; focus goes back where it was on close */
 const back=document.activeElement,others=[...document.body.children].filter(n=>!n.inert);
 others.forEach(n=>{n.inert=true});document.body.appendChild(box);
 let closed=false;
 function close(){
  if(closed)return;closed=true;
  try{localStorage.setItem('wi_intro','1')}catch(e){}
  try{v.pause();v.removeAttribute('src');v.load()}catch(e){}
  document.removeEventListener('keydown',key);document.removeEventListener('visibilitychange',hide);box.remove();
  others.forEach(n=>{n.inert=false});try{if(back&&back.focus)back.focus()}catch(e){}
 }
 function key(e){if(e.key==='Escape')close()}
 /* a hidden tab pauses the film (and its sound); it goes on only when the child taps "watch" again */
 function hide(){if(document.hidden&&!v.paused){v.pause();play.hidden=false}}
 document.addEventListener('keydown',key);document.addEventListener('visibilitychange',hide);
 skip.addEventListener('click',close);done.addEventListener('click',close);
 play.addEventListener('click',()=>{
  play.hidden=true;if(!v.getAttribute('src'))v.src=full()?FILM:FILM_LIGHT;
  const p=v.play();if(p&&p.catch)p.catch(()=>{play.hidden=false});
 });
 v.addEventListener('timeupdate',()=>{
  const t=v.currentTime,c=CUES.find(q=>t>=q[0]&&t<q[1]);
  /* one element per line, each with its own direction: an English first line must not turn the Hebrew line around */
  const k=c?c[2]:'';if(cap.dataset.k!==k){cap.dataset.k=k;cap.replaceChildren(...k.split('\n').filter(Boolean).map(t=>{const l=el('span','wi-intro__line',t);l.dir=/[\u0590-\u05FF]/.test(t)?'rtl':'ltr';l.lang=l.dir==='rtl'?'he':'en';return l}))}
  cap.hidden=!c;
 });
 v.addEventListener('ended',()=>{cap.hidden=true;done.hidden=false;done.focus()});
 cap.hidden=true;play.focus();
 return box;
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',showIntro);else showIntro();
