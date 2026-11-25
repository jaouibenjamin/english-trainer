/* The welcome film (38 s), behind the design flag (?ds=1). js/dsflag.js imports this file only when the flag is on and
   this device has not seen the film yet (localStorage wi_intro); with the flag off nothing of it is fetched or stored.
   - Nothing plays by itself: the poster shows with two buttons, "watch" and "skip". The film (with sound) starts on
     the child's tap. "Skip" is there from the first second, 48 px, and Escape closes too.
   - Captions of the narration are live text on screen, for a child without sound; the closing title is in the film itself.
   - Closing (skip, Escape, end) stores wi_intro=1 on this device and removes everything, the video's source included.
   - Calm mode or prefers-reduced-motion: the poster and the buttons show, the film still waits for a tap.
   DOM is built with createElement and textContent only. The narration text is flagged for the teacher (docs/INTRO.md). */
const FILM='assets/al/intro/intro.hf_20261125_162146_00980a2b-0f5a-4695-b31f-982280cb406b.mp4';
/* the same film, lighter (390 x 710, about 3 MB), for a phone on a slow or saved-data connection */
const FILM_LIGHT='assets/al/intro/intro-light.hf_20261125_162146_00980a2b-0f5a-4695-b31f-982280cb406b.mp4';
const light=()=>{try{const c=navigator.connection;return !!c&&(c.saveData||/(^|-)2g|3g/.test(c.effectiveType||''))}catch(e){return false}};
const POSTER='assets/al/intro/poster.hf_20261125_160942_30220de2-7942-4db5-bb82-9f99b71a615f.webp';
/* [from, to, text] in seconds of the film, from the pauses in the narration */
const CUES=[
 [0.3,4.9,'הצלצול האחרון. נפרדים מהחברים, ויוצאים לדרך.'],
 [5.9,9.2,'הולכים יחד לאורך הים, כמו בכל יום.'],
 [11.2,14.6,'יושבים על הדשא, מדברים, צוחקים...'],
 [16.3,17.7,'ופתאום...'],
 [18.5,21.8,'מתוך הים עולה אי ענק!'],
 [25.2,28.6,'Hey kids! Are you ready for an adventure?\nהיי ילדים! מוכנים להרפתקה?'],
 [29.0,31.0,'Yeah, let\'s go!\nכן, יאללה!']];
/* the closing title, "ברוכים הבאים לניצני אופק!", is in the film itself from 34.2 s (it flies in from the front), so
   there is no live title and no caption for it */
const el=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!=null)e.textContent=txt;return e};

export function showIntro(){
 if(document.getElementById('wi-intro'))return;
 const box=el('div','wi-intro');box.id='wi-intro';box.setAttribute('role','dialog');box.setAttribute('aria-modal','true');box.setAttribute('aria-label','סרטון פתיחה');
 const v=el('video','wi-intro__film');v.setAttribute('playsinline','');v.preload='none';v.poster=POSTER;v.muted=false;v.setAttribute('aria-hidden','true');
 const cap=el('p','wi-intro__cap');cap.dir='auto';
 const skip=el('button','wi-intro__skip','דלגו');skip.type='button';
 const play=el('button','wi-intro__play','צפייה בסרטון');play.type='button';
 const done=el('button','wi-intro__done','מתחילים');done.type='button';done.hidden=true;
 box.append(v,cap,play,done,skip);document.body.appendChild(box);
 let closed=false;
 function close(){
  if(closed)return;closed=true;
  try{localStorage.setItem('wi_intro','1')}catch(e){}
  try{v.pause();v.removeAttribute('src');v.load()}catch(e){}
  document.removeEventListener('keydown',key);box.remove();
 }
 function key(e){if(e.key==='Escape')close()}
 document.addEventListener('keydown',key);
 skip.addEventListener('click',close);done.addEventListener('click',close);
 play.addEventListener('click',()=>{
  play.hidden=true;v.src=light()?FILM_LIGHT:FILM;
  const p=v.play();if(p&&p.catch)p.catch(()=>{play.hidden=false});
 });
 v.addEventListener('timeupdate',()=>{
  const t=v.currentTime,c=CUES.find(q=>t>=q[0]&&t<q[1]);
  cap.textContent=c?c[2]:'';cap.hidden=!c;
 });
 v.addEventListener('ended',()=>{cap.hidden=true;done.hidden=false;done.focus()});
 cap.hidden=true;play.focus();
 return box;
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',showIntro);else showIntro();
