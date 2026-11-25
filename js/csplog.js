/* This file does two things, each in its own block, because it is the first script on every page:
   1. The pages' own record of what their Content-Security-Policy blocked (below).
   2. On the game page (index.html) only: the early request for the Latin font of the look in use (at the end). It was a
      static <link rel=preload> in index.html, which made the new look (?ds=1) download the old look's 191 KB font too.
      With the design flag off it adds exactly the tag index.html had; with it on, the new look's font.

   1. The pages' own record of what their Content-Security-Policy blocked: the last 10, on this device only
   (localStorage wi_csp), shown on the settings screen so the owner can read them on a phone. Each entry is the
   directive, the blocked ORIGIN only (or a keyword such as "inline", "data", "blob"; "?" for anything else) and the day
   (days since 1970, so the settings screen can leave out entries older than 14 days): never a path, a query or a name.
   Nothing is sent anywhere. A classic script, loaded right after the policy so it hears everything that comes after it. */
(function(){
 var KEY='wi_csp';
 function where(u){u=String(u||'');
  /* Chrome and WebKit report some sources as a bare word ("data", "blob", "inline"...): kept as it is */
  if(/^(inline|eval|wasm-eval|trusted-types-sink|self|data|blob|about|filesystem)$/.test(u))return u;
  if(u.indexOf('://')<0)return'?';   // anything else without a scheme would be read as relative to this page: not stored
  try{var x=new URL(u);return x.origin&&x.origin!=='null'?x.origin:x.protocol.replace(':','')}catch(e){return'?'}}
 function read(){var l;try{l=JSON.parse(localStorage.getItem(KEY)||'[]')}catch(e){l=[]}   // a damaged log starts over
  if(!Array.isArray(l))return[];
  return l.filter(function(x){return x&&typeof x==='object'&&typeof x.d==='string'&&typeof x.o==='string'})
   .map(function(x){return{d:x.d.slice(0,40),o:x.o.slice(0,120),t:typeof x.t==='number'&&isFinite(x.t)?Math.floor(x.t):0}})}
 document.addEventListener('securitypolicyviolation',function(e){
  try{var l=read();l.push({d:String(e.effectiveDirective||e.violatedDirective||'?').slice(0,40),o:where(e.blockedURI).slice(0,120),t:Math.floor(Date.now()/864e5)});
   localStorage.setItem(KEY,JSON.stringify(l.slice(-10)))}catch(_){}});
})();

/* 2. The game page's Latin font, asked for as early as index.html's static tag asked for it (this script runs first, so
   the request starts at the same moment). The flag is read exactly as js/dsflag.js reads it (?ds=1 / ?ds=0, else
   localStorage wi_ds); nothing is written here (dsflag.js remembers it). With the flag off the link is the old tag to
   the letter (same URL, rel, as, type and crossorigin), so the font that game.css asks for is the same request and is
   downloaded once. If anything here fails, nothing is added: the font still arrives through game.css's @font-face. Its
   own try/catch, so it can never touch the record above. */
(function(){
 try{
  if(!/(^|\/)(index\.html)?$/.test(location.pathname))return;
  var q=null,on=false;
  try{q=new URLSearchParams(location.search).get('ds')}catch(e){}
  try{on=q==='1'||(q!=='0'&&localStorage.getItem('wi_ds')==='1')}catch(e){on=q==='1'}
  var l=document.createElement('link');l.rel='preload';
  l.href=on?'assets/font/rubik-latin.woff2':'assets/font/playpen-latin.woff2';
  l.setAttribute('as','font');l.setAttribute('type','font/woff2');l.setAttribute('crossorigin','');
  document.head.appendChild(l);
 }catch(e){}
})();
