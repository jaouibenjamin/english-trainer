// Node stand-in for the Google Apps Script runtime, for tests only. `node mock.js unit` runs backend checks; `node mock.js` serves the API on :8765
// (class code EN-1234, teacher code 654321; both are test values).
const fs=require('fs'),http=require('http'),crypto=require('crypto'),vm=require('vm');
class Sheet{constructor(){this.d=[]}
 getLastRow(){return this.d.length}
 appendRow(r){this.d.push(r.slice())}
 getRange(a,b,c,d){const self=this;
  if(typeof a==='string'){ if(a==='B1')return{getValue:()=> (self.d[0]||[])[1]||''};return{setNumberFormat(){}}}
  return{getValues(){const o=[];for(let i=0;i<c;i++){const r=self.d[a-1+i]||[];o.push(Array.from({length:d},(_,j)=>r[b-1+j]??''))}return o},
   setValues(v){for(let i=0;i<c;i++){self.d[a-1+i]=self.d[a-1+i]||[];for(let j=0;j<d;j++)self.d[a-1+i][b-1+j]=v[i][j]}}}}}
const sheets={};
const ctx={SpreadsheetApp:{getActive:()=>({getSheetByName:n=>sheets[n]||null,insertSheet:n=>sheets[n]=new Sheet})},
 Utilities:{DigestAlgorithm:{SHA_256:1},Charset:{UTF_8:1},getUuid:()=>crypto.randomUUID(),computeDigest:(a,s)=>[...crypto.createHash('sha256').update(s,'utf8').digest()].map(x=>x>127?x-256:x)},
 LockService:{getScriptLock:()=>({waitLock(){},releaseLock(){}})},
 ContentService:{MimeType:{JSON:1},createTextOutput:t=>({t,setMimeType(){return this}})},console};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(require('path').join(__dirname,'../backend/Code.gs'),'utf8')+';this.setup=setup;this.doPost=doPost;',ctx);
ctx.setup();sheets.config.d=[['class code','EN-1234'],['teacher code','654321']];
const call=d=>JSON.parse(ctx.doPost({postData:{contents:JSON.stringify(d)}}).t);
if(process.argv[2]==='unit'){
 const B={c:'en-1234',n:'נועה',p:'1234'};
 const t=(l,r,exp)=>console.log(JSON.stringify(r)===JSON.stringify(exp)?'PASS':'FAIL',l,JSON.stringify(r).slice(0,120));
 t('wrong class',call({...B,c:'x',a:'login'}),{ok:false,e:'class'});
 t('nouser',call({...B,a:'login'}),{ok:false,e:'nouser'});
 t('register',call({...B,a:'register'}),{ok:true,s:{}});
 t('taken',call({...B,a:'register'}),{ok:false,e:'taken'});
 t('bad name',call({...B,n:'=1+1',a:'register'}),{ok:false,e:'input'});
 t('bad pin',call({...B,p:'9999',a:'login'}),{ok:false,e:'pin'});
 t('save',call({...B,a:'save',s:{pts:130,day:'2026-11-11',streak:2,st:{their:[4,3]},k:{words:7,reads:1}}}),{ok:true});
 t('login state',call({...B,a:'login'}).s.pts,130);
 call({...B,n:'איתי',a:'register'});call({...B,n:'איתי',a:'save',s:{pts:500,k:{words:20}}});
 t('board',call({...B,a:'board'}).rows.map(r=>r.n+r.pts),['איתי500','נועה130']);
 t('teacher bad',call({c:'EN-1234',a:'teacher',t:'1'}),{ok:false,e:'teacher'});
 t('teacher',call({c:'EN-1234',a:'teacher',t:'654321'}).hard,[['their',75,4]]);
 call({...B,n:'איתי',a:'save',s:{pts:500,st:{goal:null,kick:[2,1]},k:{words:20}}});
 t('teacher survives a damaged record',call({c:'EN-1234',a:'teacher',t:'654321'}).ok,true);
 /* the mock exam on the teacher screen: read from the saved record, nothing else */
 const kidOf=n=>call({c:'EN-1234',a:'teacher',t:'654321'}).kids.find(k=>k.n===n);
 t('teacher: no mock paper yet gives null',kidOf('נועה').mock,null);
 call({...B,a:'save',s:{pts:130,day:'2026-11-11',streak:2,st:{their:[4,3]},k:{words:7,reads:1},x:{tries:[
  {at:1000,total:[9,20],sc:{words:[3,5],grammar:[2,5],reading:[2,5],writing:[2,5]},miss:['a:1'],wrong:[['a:1','zzz']]},
  {at:2000,total:[15,20],sc:{words:[5,5],grammar:[4,5],reading:[3,5],writing:[3,5]},miss:[],wrong:[]}],prac:{grammar:1},seen:['a:1']}}});
 t('teacher: papers, first and last total, last paper by skill',kidOf('נועה').mock,{n:2,first:[9,20],last:[15,20],sc:{words:[5,5],grammar:[4,5],reading:[3,5],writing:[3,5]},at:2000});
 t('teacher: the answers a pupil typed are not sent to the teacher screen',/zzz|wrong|miss|seen|prac/.test(JSON.stringify(kidOf('נועה').mock)),false);
 call({...B,n:'איתי',a:'save',s:{pts:500,k:{words:20},x:{tries:['junk',{total:'no'},{total:[1,0]},null,{at:'x',total:['7','10'],sc:{words:'bad',grammar:[9,'x']}}]}}});
 t('teacher: a damaged mock record gives clean numbers or nothing',kidOf('איתי').mock,{n:1,first:[7,10],last:[7,10],sc:{},at:0});
 call({...B,n:'איתי',a:'save',s:{pts:500,k:{words:20},x:'broken'}});
 t('teacher: a broken mock record gives null',kidOf('איתי').mock,null);
 t('login state is untouched by the teacher view',call({...B,a:'login'}).s.x.tries.length,2);
 for(let i=0;i<10;i++)call({c:'EN-1234',a:'teacher',t:'000000'});
 t('teacher locked after 10 wrong codes',call({c:'EN-1234',a:'teacher',t:'654321'}),{ok:false,e:'locked'});
 for(let i=0;i<5;i++)call({...B,p:'0000',a:'login'});
 t('locked',call({...B,a:'login'}),{ok:false,e:'locked'});
 t('empty roster: anyone with the class code registers',call({...B,n:'עומר',a:'register'}).ok,true);
 sheets.roster.d.push(['מאיה'],[' רוני  ']);
 t('roster: a name not on the list is refused',call({...B,n:'שחר',a:'register'}),{ok:false,e:'roster'});
 t('roster: a listed name registers',call({...B,n:'רוני',a:'register'}).ok,true);
 t('roster: pupils registered earlier still log in',call({...B,n:'עומר',a:'login'}).ok,true);
 sheets.config.d[1][2]=0;sheets.config.d[1][3]=0;   // the teacher-code guard, left locked by the checks above
 t('reset: wrong teacher code is refused',call({c:'EN-1234',a:'reset',t:'000000',n:'עומר'}).e,'teacher');
 t('reset: the teacher resets a pupil code',call({c:'EN-1234',a:'reset',t:'654321',n:'עומר'}).ok,true);
 t('reset: a device still signed in with the old code must sign in again',call({c:'EN-1234',n:'עומר',p:'1234',a:'save',s:{pts:1}}).e,'pin');
 const np=call({c:'EN-1234',n:'עומר',p:'8642',a:'login'});
 t('reset: the next sign-in sets the new code and keeps the progress',!!(np.ok&&np.newpin&&typeof np.s==='object'),true);
 t('reset: the old code no longer works',call({c:'EN-1234',n:'עומר',p:'1234',a:'login'}).e,'pin');
 t('reset: the new code works, and is no longer new',(()=>{const x=call({c:'EN-1234',n:'עומר',p:'8642',a:'login'});return x.ok&&!x.newpin})(),true);
 t('pin hash not plain',/1234/.test(sheets.kids.d[1][2])===false&&sheets.kids.d[1][2].length===64,true);
}else http.createServer((q,s)=>{let b='';q.on('data',c=>b+=c);q.on('end',()=>{s.writeHead(200,{'Access-Control-Allow-Origin':'*','Content-Type':'application/json'});const d=q.method==='POST'?JSON.parse(b):null;
  /* test only: tidy a pupil's name in the sheet, as a teacher or parent might */
  if(d&&d.a==='__rename'){const r=sheets.kids.d.find(x=>x[0]===d.from);if(r)r[0]=d.to;return s.end(JSON.stringify({ok:!!r}))}
  s.end(d?JSON.stringify(call(d)):'{}')})}).listen(8765);
