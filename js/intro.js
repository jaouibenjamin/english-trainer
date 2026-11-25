/* The welcome film (34 s), behind the design flag (?ds=1). js/dsflag.js imports this file only when the flag is on and
   this device has not seen the film yet (localStorage wi_intro); with the flag off nothing of it is fetched or stored.
   - Nothing plays by itself: the poster shows with two buttons, "watch" and "skip". The film (with sound) starts on
     the child's tap. "Skip" is there from the first second, 48 px, and Escape closes too.
   - Captions of the narration are live text on screen, for a child without sound; the closing title is live text.
   - Closing (skip, Escape, end) stores wi_intro=1 on this device and removes everything, the video's source included.
   - Calm mode or prefers-reduced-motion: the poster and the buttons show, the film still waits for a tap.
   DOM is built with createElement and textContent only. The narration text is flagged for the teacher (docs/INTRO.md). */
const FILM='assets/al/intro/intro.hf_20261125_152954_f47c0bff-0f28-4752-80da-32d4a42b4992.mp4';
const POSTER='assets/al/intro/poster.hf_20261125_152813_9f533fd3-72c0-49aa-b65c-8b09bdf03b96.webp';
/* [from, to, text] in seconds of the film, from the pauses in the narration */
const CUES=[
 [0.3,4.9,'הצלצול האחרון. נפרדים מהחברים, ויוצאים לדרך.'],
 [5.9,9.2,'הולכים יחד לאורך הים, כמו בכל יום.'],
 [11.2,14.6,'יושבים על הדשא, מדברים, צוחקים...'],
 [15.5,16.6,'ופתאום...'],
 [17.5,20.3,'באופק נדלק אי ענק!'],
 [26.4,29.2,'Hey kids! Are you ready for an adventure?\nהיי ילדים! מוכנים להרפתקה?'],
 [29.9,33.6,'ברוכים הבאים לניצני אופק!']];
const TITLE_AT=29.8;
const el=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!=null)e.textContent=txt;return e};

export function showIntro(){
 if(document.getElementById('wi-intro'))return;
 const box=el('div','wi-intro');box.id='wi-intro';box.setAttribute('role','dialog');box.setAttribute('aria-modal','true');box.setAttribute('aria-label','סרטון פתיחה');
 const v=el('video','wi-intro__film');v.setAttribute('playsinline','');v.preload='none';v.poster=POSTER;v.muted=false;v.setAttribute('aria-hidden','true');
 const title=el('p','wi-intro__title','ברוכים הבאים לניצני אופק!');title.hidden=true;
 const cap=el('p','wi-intro__cap');cap.dir='auto';
 const skip=el('button','wi-intro__skip','דלגו');skip.type='button';
 const play=el('button','wi-intro__play','צפייה בסרטון');play.type='button';
 const done=el('button','wi-intro__done','מתחילים');done.type='button';done.hidden=true;
 box.append(v,title,cap,play,done,skip);document.body.appendChild(box);
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
  play.hidden=true;v.src=FILM;
  const p=v.play();if(p&&p.catch)p.catch(()=>{play.hidden=false});
 });
 v.addEventListener('timeupdate',()=>{
  const t=v.currentTime,c=CUES.find(q=>t>=q[0]&&t<q[1]);
  cap.textContent=c?c[2]:'';cap.hidden=!c;title.hidden=t<TITLE_AT;
 });
 v.addEventListener('ended',()=>{title.hidden=false;cap.hidden=true;done.hidden=false;done.focus()});
 cap.hidden=true;play.focus();
 return box;
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',showIntro);else showIntro();
