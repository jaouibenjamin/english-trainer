/* The pages' own record of what their Content-Security-Policy blocked: the last 10, on this device only
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
