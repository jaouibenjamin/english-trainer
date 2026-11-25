/* The progress card: one screen a pupil can show, and one picture of it they can save or pass on themselves.
   Behind a switch that is off unless a device was given it (open the game once with ?card=1; ?card=0 takes it away).
   - It shows what the settings screen already shows (stars, words learned, stories read), by island, with today's date.
   - The only personal detail is the first name the pupil is signed in with on this device. Without a class sign-in
     there is no name at all.
   - Nothing is sent by the game and nothing new is saved: the picture is drawn on this device and handed to the
     browser, either as a download or to the device's own share sheet when the pupil presses "share". */
import {ISLANDS,MAX_STARS,WORDS} from './data.js';
import {S,SET,saveSet,API,islandStars,totalStars,wordsKnown,esc} from './state.js';
import {view,spr,btn,num,toast} from './ui.js';

export const cardOn=()=>SET.card===true;
export function initCard(){let v=null;try{v=new URLSearchParams(location.search).get('card')}catch(e){}
 if(v==='1'||(v==='0'&&typeof SET.card==='boolean')){SET.card=v==='1';saveSet()}}   // ?card=0 on a device that never had the switch writes nothing

const WORDS_MAX=WORDS.filter(w=>w.p<6).length;
const today=()=>{const d=new Date(),p=n=>String(n).padStart(2,'0');return `${p(d.getDate())}.${p(d.getMonth()+1)}.${d.getFullYear()}`};
/* everything the card shows, as plain data (the screen and the picture are both drawn from this) */
export function cardData(){return{
 name:API&&S.u&&typeof S.u.n==='string'?S.u.n.trim().split(/\s+/)[0].slice(0,24):'',   // the first word of the name only: a first name, never a family name
 date:today(),stars:totalStars(),max:MAX_STARS,
 islands:ISLANDS.map(i=>({he:i.he,got:islandStars(i),max:i.levels.length*3})),
 words:wordsKnown(),wordsMax:WORDS_MAX,
 reads:Object.values(S.read||{}).filter(v=>v>0).length,readsMax:5,
 /* a pupil who is only starting gets a kind word, not a row of zeros to feel bad about */
 kind:totalStars()<=LOW?KIND:''}}
const LOW=3,KIND='כל כוכב מתחיל במשחק אחד. יאללה, מתחילים!';

const canShare=f=>{try{return!!(navigator.share&&navigator.canShare&&navigator.canShare({files:[f]}))}catch(e){return false}};
const probe=()=>{try{return canShare(new File([new Blob(['x'],{type:'image/png'})],'x.png',{type:'image/png'}))}catch(e){return false}};

export function cardScreen(top){const d=cardData();
 view.innerHTML=`<section class="scr rcard">${top('הכרטיס שלי','settings')}
  <div class="rc" id="rc">
   <p class="rch">${spr('crab_star','rcc')}<span>${d.name?`<b>${esc(d.name)}</b>`:''}<small>ההתקדמות שלי באנגלית · ${num(d.date)}</small></span></p>
   <p class="rct">${spr('star','rs')}<b>${num(d.stars+' / '+d.max)}</b><small>כוכבים</small></p>${d.kind?`<p class="rck">${esc(d.kind)}</p>`:''}
   <ul class="rcl">${d.islands.map(i=>`<li><span>${esc(i.he)}</span><i class="rcb"><em style="width:${Math.round(i.got/i.max*100)}%"></em></i>${num(i.got+' / '+i.max)}</li>`).join('')}</ul>
   <p class="rcf"><span><b>${num(d.words+' / '+d.wordsMax)}</b><small>מילים שנלמדו</small></span><span><b>${num(d.reads+' / '+d.readsMax)}</b><small>סיפורים שנקראו</small></span></p>
  </div>
  <div class="rcbtns">${btn('cardsave','לשמור כתמונה','green')}${probe()?btn('cardshare','לשתף','cream'):''}</div>
  <p class="credit">התמונה נוצרת במכשיר הזה. המשחק לא שולח אותה לאף אחד.</p></section>`}

/* ---------- the picture: drawn from the same data, text and simple shapes only ---------- */
const FONT="'Playpen Sans Hebrew',Arial,sans-serif",W=1080,H=1350;
function star(c,x,y,r,fill){c.beginPath();for(let k=0;k<10;k++){const a=-Math.PI/2+k*Math.PI/5,q=k%2?r*.45:r;c[k?'lineTo':'moveTo'](x+Math.cos(a)*q,y+Math.sin(a)*q)}c.closePath();c.fillStyle=fill;c.fill()}
function rr(c,x,y,w,h,r){c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath()}
export async function cardCanvas(d=cardData()){
 try{if(document.fonts)await Promise.all([document.fonts.load("700 40px 'Playpen Sans Hebrew'",'אב'),document.fonts.load("700 40px 'Playpen Sans Hebrew'",'12')])}catch(e){}
 const cv=document.createElement('canvas');cv.width=W;cv.height=H;const c=cv.getContext('2d');
 const ink='#3d2d20',ink2='#6b5746',R=W-90,L=90;
 c.fillStyle='#fffaf0';c.fillRect(0,0,W,H);
 rr(c,30,30,W-60,H-60,36);c.lineWidth=6;c.strokeStyle='#8a6f57';c.stroke();
 const he=(t,x,y,font,color)=>{c.direction='rtl';c.textAlign='right';c.font=font;c.fillStyle=color;c.fillText(t,x,y)};
 const ltr=(t,x,y,font,color,al='left')=>{c.direction='ltr';c.textAlign=al;c.font=font;c.fillStyle=color;c.fillText(t,x,y)};
 he('איי המילים',R,130,`800 64px ${FONT}`,ink);
 ltr(d.date,L,126,`600 36px ${FONT}`,ink2);
 he('ההתקדמות שלי באנגלית',R,190,`500 36px ${FONT}`,ink2);
 let y=280;
 if(d.name){   // the name is made smaller until it fits between the margins; one that still does not fit is cut with "…"
  let px=76,name=d.name;const fits=()=>{c.font=`800 ${px}px ${FONT}`;return c.measureText(name).width<=R-L};
  while(px>40&&!fits())px-=4;
  while(name.length>1&&!fits())name=name.slice(0,-2)+'…';
  he(name,R,y,`800 ${px}px ${FONT}`,ink);y+=36}
 c.fillStyle='#8a6f57';c.fillRect(L,y,W-180,3);y+=90;
 star(c,R-38,y-26,40,'#f2b632');ltr(`${d.stars} / ${d.max}`,R-100,y,`800 72px ${FONT}`,ink,'right');
 he('כוכבים',L+190,y,`600 40px ${FONT}`,ink2);
 if(d.kind){y+=62;c.direction='rtl';c.textAlign='center';c.font=`600 34px ${FONT}`;c.fillStyle=ink2;c.fillText(d.kind,W/2,y)}
 y+=d.kind?40:56;
 for(const i of d.islands){y+=74;he(i.he,R,y,`700 40px ${FONT}`,ink);
  ltr(`${i.got} / ${i.max}`,L,y,`700 40px ${FONT}`,ink);
  const bx=L+170,bw=330,by=y-28;rr(c,bx,by,bw,24,12);c.fillStyle='#eadfc8';c.fill();
  if(i.got>0){const fw=Math.max(24,bw*i.got/i.max);rr(c,bx+bw-fw,by,fw,24,12);c.fillStyle='#f2b632';c.fill()}}   // fills from the right, as on the screen
 y+=56;c.fillStyle='#8a6f57';c.fillRect(L,y,W-180,3);y+=84;
 he('מילים שנלמדו',R,y,`600 40px ${FONT}`,ink2);ltr(`${d.words} / ${d.wordsMax}`,L,y,`800 50px ${FONT}`,ink);y+=76;
 he('סיפורים שנקראו',R,y,`600 40px ${FONT}`,ink2);ltr(`${d.reads} / ${d.readsMax}`,L,y,`800 50px ${FONT}`,ink);
 /* the last row ends at y (plus the tails of its letters); the footer keeps clear of it whatever is on the card */
 ltr('Fantastic 5 · Unit 1',W/2,Math.max(y+74,H-58),`500 28px ${FONT}`,ink2,'center');
 cv.rows={last:y,footer:Math.max(y+74,H-58)};
 return cv}
const blobOf=cv=>new Promise(res=>cv.toBlob(res,'image/png'));
const FILE='word-islands-card.png';   // the same name for everyone: no pupil's name in a file name

export async function cardSave(){const b=await blobOf(await cardCanvas());if(!b)return toast('לא הצלחנו ליצור תמונה. נסו שוב',2600);
 const u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download=FILE;document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(u),4000);toast('התמונה נשמרה במכשיר',2200)}
export async function cardShare(){const b=await blobOf(await cardCanvas());if(!b)return;
 const f=new File([b],FILE,{type:'image/png'});if(!canShare(f))return cardSave();
 try{await navigator.share({files:[f]})}catch(e){}}   // the pupil closed the share sheet: nothing to do
