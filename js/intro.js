/* The welcome film (30 s), behind the design flag (?ds=1). js/dsflag.js imports this file only when the flag is on and
   this device has not seen the film yet (localStorage wi_intro); with the flag off nothing of it is fetched or stored.
   - Nothing plays by itself: the poster shows with two buttons, "watch" and "skip". The film (with sound) starts on
     the child's tap. "Skip" is there from the first second, 48 px, and Escape closes too.
   - Captions of the narration are live text on screen, for a child without sound; the closing title is live text.
   - Closing (skip, Escape, end) stores wi_intro=1 on this device and removes everything, the video's source included.
   - Calm mode or prefers-reduced-motion: the poster and the buttons show, the film still waits for a tap.
   DOM is built with createElement and textContent only. The narration text is flagged for the teacher (docs/INTRO.md). */
const FILM='assets/al/intro/intro.hf_20261125_131558_7621ea4f-5457-4816-a8dd-cd722b9e9af3.mp4';
const POSTER='assets/al/intro/poster.hf_20261125_131558_7621ea4f-5457-4816-a8dd-cd722b9e9af3.webp';
/* [from, to, text] in seconds of the film, from the pauses in the narration */
const CUES=[
 [0.3,4.7,'בלילה, באמצע הים, מחכים לכם איים מיוחדים.'],
 [5.5,8.2,'כל אי הוא עולם של מילים באנגלית.'],
 [9.1,12.2,'פיצי הסרטן כבר מחכה לכם על החוף:'],
 [12.8,15.3,'Hi! My name is Pitzi!'],
 [16.4,19.0,'בוחרים דמות, ויוצאים לדרך.'],
 [19.4,25.0,'משחקים, טועים, מתקנים, ומשתפרים כל יום עוד קצת.'],
 [26.2,29.9,'ברוכים הבאים לאיי המילים!']];
const TITLE_AT=25.4;
const el=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!=null)e.textContent=txt;return e};

export function showIntro(){
 if(document.getElementById('wi-intro'))return;
 const box=el('div','wi-intro');box.id='wi-intro';box.setAttribute('role','dialog');box.setAttribute('aria-modal','true');box.setAttribute('aria-label','סרטון פתיחה');
 const v=el('video','wi-intro__film');v.setAttribute('playsinline','');v.preload='none';v.poster=POSTER;v.muted=false;v.setAttribute('aria-hidden','true');
 const title=el('p','wi-intro__title','ברוכים הבאים לאיי המילים');title.hidden=true;
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
