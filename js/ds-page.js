/* The design-system preview page (ds.html), moved out of the page unchanged for the Content-Security-Policy. */
/* preview only: build the avatar grid and the contrast table from the live CSS tokens. DOM nodes and textContent only. */
(function(){
 var SVG='http://www.w3.org/2000/svg';
 function el(tag,cls,txt){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}
 function icon(id,px){var s=document.createElementNS(SVG,'svg');s.setAttribute('class','wi-icon');
  if(px){s.style.inlineSize=px+'px';s.style.blockSize=px+'px'}
  var u=document.createElementNS(SVG,'use');u.setAttribute('href','#'+id);s.appendChild(u);return s}
 var g=document.getElementById('avgrid');
 if(g){for(var i=0;i<20;i++){
  var locked=i>=16,sel=i===10,hue=(i*37+10)%360;
  var b=el('button','wi-av'+(locked?' wi-av--locked':'')+(sel?' is-selected':''));b.type='button';
  if(!locked)b.setAttribute('aria-pressed',sel?'true':'false');
  b.setAttribute('aria-label','דמות '+(i+1)+(locked?', נעולה':sel?', נבחרה':''));
  var art=el('span','wi-av__art tile');art.style.background='hsl('+hue+' 55% 42%)';b.appendChild(art);
  if(sel){var bd=el('span','wi-av__badge');bd.appendChild(icon('i-check'));b.appendChild(bd)}
  if(locked){var lk=el('span','wi-av__lock');lk.appendChild(icon('i-lock',26));b.appendChild(lk)}
  var w=el('div');w.appendChild(b);g.appendChild(w);}}
 var cs=getComputedStyle(document.documentElement);
 function v(n){return cs.getPropertyValue('--wi-'+n).trim()}
 function lum(h){h=h.replace('#','');var c=[0,2,4].map(function(i){var x=parseInt(h.substr(i,2),16)/255;return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4)});return .2126*c[0]+.7152*c[1]+.0722*c[2]}
 function cr(a,b){var x=lum(a),y=lum(b);if(x<y){var t=x;x=y;y=t}return (x+.05)/(y+.05)}
 /* [foreground token, background token, where it is used, kind]. kind: t = text (4.5), s = shape or outline (3), d = decoration (no bar),
    p = fails by design on bare art, so the component brings a plate or a keyline (counted on its own in the total).
    Every colour pair that css/ds.css or this page puts together is listed. */
 var P=[
 ['text','navy-900','טקסט ראשי על הרקע','t'],['text','navy-800','טקסט ראשי על כרטיס','t'],['text','navy-700','טקסט על כרטיס מורם, תגית','t'],
 ['text-dim','navy-900','טקסט משני על הרקע, על לוחית','t'],['text-dim','navy-800','טקסט משני על כרטיס','t'],['text-dim','navy-700','טקסט משני על מורם, כפתור כבוי','t'],
 ['aqua','navy-900','אקווה על הרקע: תווית "כאן עכשיו" על לוחית, מילוי פס','t'],['aqua','navy-800','אקווה על כרטיס: כותרת, סמל','t'],['aqua','navy-700','אקווה על מורם: אבן נוכחית, כפתור שקט לחוץ','t'],
 ['gold','navy-900','זהב על הרקע: כוכבים על לוחית','t'],['gold','navy-800','זהב על כרטיס','t'],['gold','navy-700','זהב על מורם','t'],['gold','gold-deep','אבן שהושלמה: סימן וטבעת','t'],
 ['navy-900','gold','כפתור ראשי, תגית זהב, תג נבחר','t'],['navy-900','gold-press','כפתור ראשי לחוץ','t'],['navy-900','aqua','תגית אקווה, מסנן פעיל','t'],['navy-900','aqua-press','אקווה לחוץ','t'],
 ['text','azure','כפתור משני, תגית "בקרוב"','t'],['text','azure-press','כפתור משני לחוץ','t'],['aqua','azure','טבעת כפתור משני (צורה)','s'],['aqua','azure-press','טבעת כפתור משני לחוץ (צורה)','s'],
 ['text','magenta','כפתור מיוחד, תגית נדירה','t'],['text','magenta-press','כפתור מיוחד לחוץ','t'],
 ['good','navy-800','נכון, על כרטיס','t'],['good','navy-900','נכון, על הרקע','t'],['fix','navy-800','בוא נתקן, על כרטיס','t'],['fix','navy-900','בוא נתקן, על הרקע','t'],
 ['locked','navy-800','נעול: מנעול וטקסט על כרטיס ועל אבן','t'],['locked','navy-900','נעול: תווית על לוחית','t'],
 ['locked','navy-700','טבעת כפתור כבוי (צורה). לא לטקסט','s'],['locked','scrim','טבעת אבן נעולה מול קו המתאר הכהה שסביבה (צורה)','s'],
 ['locked-line','navy-800','קו שקט בתוך כרטיס: כוכב ריק, דמות נעולה (צורה)','s'],['locked-line','navy-900','קו שקט על לוחית: כוכב ריק (צורה)','s'],
 ['gold','scrim','טבעת אבן שהושלמה מול קו המתאר (צורה)','s'],['aqua','scrim','טבעת אבן נוכחית מול קו המתאר (צורה)','s'],
 ['line','navy-900','מסגרת על הרקע, מסילת הפס (צורה)','s'],['line','navy-800','מסגרת על כרטיס (צורה)','s'],['line','navy-700','מסגרת על כרטיס מורם (צורה)','s'],
 ['focus','navy-900','טבעת מיקוד על הרקע (צורה)','s'],['focus','navy-800','טבעת מיקוד על כרטיס (צורה)','s'],['focus','navy-700','טבעת מיקוד על מורם (צורה)','s'],
 ['text','sea-hi','ים בהיר (מקום שמור): טקסט לבן','t'],['text-dim','sea-hi','ים בהיר: טקסט משני','t'],['aqua','sea-hi','ים בהיר: קו המסלול (צורה)','s'],
 ['locked','sea-hi','ים בהיר: נעול בלי לוחית','p'],['line','sea-hi','ים בהיר: מסגרת בלי מילוי מאחוריה','p'],
 ['ink','paper','נייר: טקסט','t'],['ink','paper-2','נייר 2: טקסט','t'],['ink-2','paper','נייר: טקסט משני','t'],['ink-2','paper-2','נייר 2: טקסט משני','t'],
 ['good-ink','paper','נייר: נכון','t'],['good-ink','paper-2','נייר 2: נכון','t'],['fix-ink','paper','נייר: לתיקון','t'],['fix-ink','paper-2','נייר 2: לתיקון','t'],
 ['paper','ink','נייר: כפתור','t'],['focus-paper','paper','נייר: טבעת מיקוד, כותרת','t'],['focus-paper','paper-2','נייר 2: טבעת מיקוד','t'],
 ['paper-line','paper','נייר: קו כרטיס','d'],['paper','navy-900','כרטיס נייר על הרקע הכהה (צורה)','s']];
 var o=document.getElementById('sw');if(!o)return;
 var bad=0,n=0,plate=0;
 P.forEach(function(p){var f=v(p[0]),b=v(p[1]),r=cr(f,b),k=p[3];
  var ok=k==='d'||k==='p'||(k==='s'?r>=3:r>=4.5);if(k==='p')plate++;else if(k!=='d'){n++;if(!ok)bad++}
  var verdict=k==='d'?'קישוט':k==='p'?'לא עובר לבד: חייב לוחית':ok?(r>=7&&k==='t'?'AAA':'AA'):'לא עובר';
  var d=el('div','sw');d.style.background=b;d.style.color=f;d.dataset.pair=p[0]+'/'+p[1];d.dataset.ok=ok?'1':'0';d.dataset.kind=k;
  d.appendChild(el('b',null,p[2]));d.appendChild(el('span','r',r.toFixed(2)+' : 1 '+verdict));d.appendChild(el('code',null,f+' on '+b));
  o.appendChild(d);});
 var sum=document.getElementById('swsum');if(sum)sum.textContent=(bad?(bad+' זוגות לא עוברים מתוך '+n+'.'):('כל '+n+' הזוגות עוברים.'))+' ועוד '+plate+' זוגות שלא עוברים על תמונה חשופה, ולכן הרכיב מביא לוחית או קו מתאר.';
})();
