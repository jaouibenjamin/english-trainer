/* The pages' own record of what their Content-Security-Policy blocked: the last 10, on this device only
   (localStorage wi_csp), shown on the settings screen so the owner can read them on a phone. Each entry is the
   directive and the blocked ORIGIN only (or a keyword such as "inline"): never a path, a query or a name. Nothing is
   sent anywhere. A classic script, loaded right after the policy so it hears everything that comes after it. */
(function(){
 var KEY='wi_csp';
 function where(u){u=String(u||'');if(/^(inline|eval|wasm-eval|trusted-types-sink|self)$/.test(u))return u;
  try{var x=new URL(u,location.href);return x.protocol==='data:'||x.protocol==='blob:'?x.protocol.slice(0,-1):x.origin}catch(e){return'?'}}
 document.addEventListener('securitypolicyviolation',function(e){
  try{var l=JSON.parse(localStorage.getItem(KEY)||'[]');if(!Array.isArray(l))l=[];
   l.push({d:String(e.effectiveDirective||e.violatedDirective||'?').slice(0,40),o:where(e.blockedURI).slice(0,120)});
   localStorage.setItem(KEY,JSON.stringify(l.slice(-10)))}catch(_){}});
})();
