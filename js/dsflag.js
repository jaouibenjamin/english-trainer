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
 /* the welcome film, once per device (js/intro.js, loaded as a module script: a bare import() here would be a syntax
    error that stops this whole file on very old browsers): only the game page, only if not seen; ?intro=1 shows it again.
    An automated browser (navigator.webdriver, the test suites) does not get it unless ?intro=1 asks for it. */
 var seen=true;try{var iq=new URLSearchParams(location.search).get('intro');if(iq==='1')localStorage.removeItem('wi_intro');seen=localStorage.getItem('wi_intro')==='1'||(navigator.webdriver&&iq!=='1')}catch(e){}
 if(!seen&&/(^|\/)(index\.html)?$/.test(location.pathname)){
  /* the opening flow's cover (docs/INTRO.md): navy from the first paint, the game laid out but hidden behind it, so the
     title never flashes before the logo; and the game's sound held (html.wi-intro-open: js/audio.js, js/state.js) until
     the film closes. js/intro.js takes over the cover once its overlay is in the page.
     - If js/intro.js has not arrived after 4 s (a failed or very slow load), the cover and the hold go and the game is
       there as usual. If it has arrived, its overlay is on the way and the cover stays.
     - The hold is also let go here, by this file, as soon as the overlay leaves the page, whatever js/intro.js does: an
       older js/intro.js (from the browser's cache) would not release it, and the game would stay silent.
     - ?v=2: the intro's files as of this version, never an older cached copy next to this file. */
  var H=document.documentElement,seen0=false;H.classList.add('wi-intro-pending','wi-intro-open');
  var free=function(){if(H.classList.contains('wi-intro-open')){H.classList.remove('wi-intro-open');try{dispatchEvent(new Event('wi-intro-closed'))}catch(e){}}};
  var cv=document.createElement('style');cv.id='wi-intro-cover';cv.textContent='html.wi-intro-pending{background:#050E22}html.wi-intro-pending body>*:not(#wi-intro){visibility:hidden}';document.head.appendChild(cv);
  try{var wo=new MutationObserver(function(){var o=document.getElementById('wi-intro');if(o)seen0=true;else if(seen0){wo.disconnect();H.classList.remove('wi-intro-pending');free()}});wo.observe(H,{childList:true,subtree:true})}catch(e){}
  var drop=function(){if(!document.getElementById('wi-intro')){H.classList.remove('wi-intro-pending');free()}};
  setTimeout(function(){if(!window.__wiIntro)drop()},4000);setTimeout(drop,15000);   // arrived but no overlay after 15 s (an error in it): never a blank page
  var l=document.createElement('link');l.rel='stylesheet';l.href='css/ds-intro.css?v=2';document.head.appendChild(l);var m=document.createElement('script');m.type='module';m.src='js/intro.js?v=2';document.head.appendChild(m)}
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
