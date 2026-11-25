/* The new look ("Arcade Lagoon") for the title, login and settings screens, behind a flag. Default: off.
   world.html?ds=1 or index.html?ds=1 turns it on for this device and remembers it; ?ds=0 turns it off again.
   With the flag off this file does nothing: no class, no extra stylesheet, no storage write.
   With it on, it adds the class "ds" to <html> and loads css/ds.css, css/ds-game.css and css/ds-teacher.css. Styling only: it never
   touches the login form, its fields, the pupil's data or any request. */
(function(){
 var q=null,on=false;
 try{q=new URLSearchParams(location.search).get('ds')}catch(e){}
 try{
  if(q==='1')localStorage.setItem('wi_ds','1');
  else if(q==='0')localStorage.removeItem('wi_ds');
  on=localStorage.getItem('wi_ds')==='1';
 }catch(e){on=q==='1'}
 if(!on)return;
 document.documentElement.classList.add('ds');
 ['css/ds.css','css/ds-game.css','css/ds-teacher.css'].forEach(function(h){var l=document.createElement('link');l.rel='stylesheet';l.href=h;document.head.appendChild(l)});
})();
