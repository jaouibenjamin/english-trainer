/* The new look ("Arcade Lagoon") for the title, login and settings screens, behind a flag. Default: off.
   world.html?ds=1 or index.html?ds=1 turns it on for this device and remembers it; ?ds=0 turns it off again.
   With the flag off this file does nothing: no class, no extra stylesheet, no storage write.
   With it on, it adds the class "ds" to <html> and loads css/ds.css, css/ds-game.css and css/ds-teacher.css, and on the
   game page asks early for what the first screen needs (below). It never touches the login form, its fields, the
   pupil's data or any request the game makes. */
(function(){
 var q=null,on=false;
 try{q=new URLSearchParams(location.search).get('ds')}catch(e){}
 try{
  if(q==='1')localStorage.setItem('wi_ds','1');
  else if(q==='0')localStorage.removeItem('wi_ds');
  on=localStorage.getItem('wi_ds')==='1';
 }catch(e){on=q==='1'}
 if(!on)return;
 /* what the game page loads first: js/main.js and every module it imports (tests/weight.py keeps this list equal to the
    imports), the new world's modules (js/avatar.js and its own imports), and each first screen's background */
 var MODS=['main','data','state','help','audio','ui','sling','listen','read','bridge','math','mock','xdata','card','extra','voice','stretch','api','helpdata','mdata','mui','msling'];
 var WORLD=['avatar','worldpath','world_art','world_data','avanim'];
 var BG={title:'assets/al/bg/world.hf_20261124_204628_1e3550f7-2092-4fef-bb11-e3fd187d71bf.webp',login:'assets/al/bg/world.hf_20261124_204628_1e3550f7-2092-4fef-bb11-e3fd187d71bf.webp',
  map:'assets/al/bg/sea-details.hf_20261125_075052_17486f52-96ee-4372-9033-9dd45cfa5736.webp',math:'assets/al/bg/sea-details.hf_20261125_075052_17486f52-96ee-4372-9033-9dd45cfa5736.webp',
  avatar:'assets/al/bg/sea.hf_20261124_210013_f6e9010a-f742-47cc-a849-a034fbb86389.webp'};
 document.documentElement.classList.add('ds');
 if(/^איי המילים$/.test(document.title))document.title='ניצני אופק';   // the platform's new name (docs/PLAN.md), with the flag only; other pages keep their own title
 ['css/ds.css','css/ds-game.css','css/ds-teacher.css'].forEach(function(h){var l=document.createElement('link');l.rel='stylesheet';l.href=h;document.head.appendChild(l)});
 /* The game page only: start at once, side by side, what the first screen will ask for one file after another (the game's
    modules, the new look's Latin font, the screen's background, and on the map, island and picker the new world's code
    and styles). Only names the page goes on to use (tests/weight.py checks every one). Never without the flag. */
 if(!/(^|\/)(index\.html)?$/.test(location.pathname))return;
 var add=function(rel,href,as){var l=document.createElement('link');l.rel=rel;l.href=href;if(as)l.as=as;if(as==='font')l.crossOrigin='anonymous';document.head.appendChild(l)};
 MODS.forEach(function(f){add('modulepreload','js/'+f+'.js')});
 add('preload','assets/font/rubik-latin.woff2','font');
 var scr=((location.hash||'').slice(1).split('/')[0])||'title';
 if(scr==='map'||scr==='island'||scr==='avatar'){WORLD.forEach(function(f){add('modulepreload','js/'+f+'.js')});add('preload','css/worldpath.css','style');add('preload','css/avatar.css','style')}
 if(BG[scr])add('preload',BG[scr],'image');
})();
