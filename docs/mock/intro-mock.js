/* Mock of the opening flow (docs/INTRO.md). Not the game's code: it only switches classes and plays the light film. */
(function(){
 var q=new URLSearchParams(location.search),W=+q.get('w')||390,H={390:844,360:740,320:568}[W]||844;
 var FILM='../../assets/al/intro/intro-light.hf_20261125_164702_e78eef89-88e1-4b0e-ab69-1469ee330bf6.mp4';
 var ph=document.getElementById('ph'),film=document.getElementById('film'),cap=document.getElementById('cap'),note=document.getElementById('note');
 ph.style.width=W+'px';ph.style.height=H+'px';
 document.getElementById('under').src='intro-under-'+W+'.webp';
 var ctl=document.getElementById('ctl');
 function link(t,par,cur){var a=document.createElement('a');a.textContent=t;var u=new URLSearchParams(par);u.set('w',par.w||W);a.href='?'+u;if(cur)a.setAttribute('aria-current','true');ctl.appendChild(a)}
 if(q.get('bare')==='1')ctl.style.display='none';
 [390,360,320].forEach(function(w){link(w+' px',{w:w,auto:q.get('auto')||''},w===W)});
 link('הפעלה אוטומטית',{auto:1},q.get('auto')==='1');
 [['splash','פתיחה'],['load','טוען'],['film','סרטון'],['end','סוף'],['game','משחק']].forEach(function(s){link(s[1],{step:s[0]},q.get('step')===s[0])});
 link('מכשיר שכבר ראה',{ret:1},q.get('ret')==='1');
 function set(s,n){ph.className='phone s-'+s+(q.get('step')?' still':'');note.textContent=n||''}
 function tapAt(el){var r=el.getBoundingClientRect(),p=ph.getBoundingClientRect(),t=document.getElementById('tap');
  t.style.left=(r.left-p.left+r.width/2)+'px';t.style.top=(r.top-p.top+r.height/2)+'px';t.classList.remove('go');void t.offsetWidth;t.classList.add('go')}
 var timer=0;
 function cues(){var t=film.currentTime;cap.classList.toggle('on',t>=.3&&t<4.9)}
 film.addEventListener('timeupdate',cues);
 function start(){
  set('load','נגיעה אחת: הקול מותר מכאן. עד שהסרטון מוכן הלוגו נשאר.');
  film.src=FILM;film.currentTime=0;
  film.addEventListener('playing',function on(){film.removeEventListener('playing',on);set('film','הסרטון (בשרטוט מקוצר: 4 שניות, ואז הסוף)');
   if(q.get('auto')==='1')timer=setTimeout(function(){film.currentTime=31.5},4200)});
  var p=film.play();if(p&&p.catch)p.catch(function(){});
 }
 function end(){set('end','הסוף: הכותרת שבסרטון נשארת, "מתחילים" מופיע.');if(q.get('auto')==='1')setTimeout(function(){tapAt(document.getElementById('done'));setTimeout(out,250)},1600)}
 function out(){clearTimeout(timer);try{film.pause()}catch(e){}set('game','דהייה רכה אל המסך הראשון, שכבר מוכן מאחור. בלי הבהוב, בלי קפיצה.')}
 film.addEventListener('ended',end);
 document.getElementById('play').addEventListener('click',start);
 document.querySelector('.logo').addEventListener('click',start);
 document.getElementById('done').addEventListener('click',out);
 document.getElementById('skip').addEventListener('click',out);
 var st=q.get('step');
 if(q.get('ret')==='1'){set('game','מכשיר שכבר ראה את הסרטון: ישר למסך הראשון, בלי פתיחה.');return}
 if(st==='film'){film.preload='auto';film.src=FILM;film.addEventListener('loadedmetadata',function(){film.currentTime=2.2});set('film')}
 else if(st==='end'){film.preload='auto';film.src=FILM;film.addEventListener('loadedmetadata',function(){film.currentTime=film.duration-.3});set('end')}
 else if(st)set(st==='load'?'load':st);
 else set('splash','פתיחה: הלוגו קופץ (כשנייה), ואז הכפתור.');
 if(q.get('auto')==='1')setTimeout(function(){tapAt(document.getElementById('play'));setTimeout(start,200)},2200);
})();
