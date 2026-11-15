/* Builds tests/voice_texts.json: every English text the game can speak, by category, deduped by exact text.
   Run: node tests/voice_texts.mjs   (js/voice.js maps these texts to recorded clips) */
import {WORDS,TEXTS,SENT,TOBE_BY,BUILD,TOBE,TOKRE,glossKey} from '../js/data.js';
import {writeFileSync} from 'node:fs';
const norm=s=>String(s).trim().replace(/\s+/g,' ');
export const sentences=t=>(t.match(/[^.!?]+[.!?]+["”]?\s*/g)||[t]).map(norm);
const seen=new Map(),add=(t,c)=>{t=norm(t);if(t&&!seen.has(t))seen.set(t,c)};
for(const w of WORDS)add(w.en,'vocab');
for(const p in SENT)for(const s of SENT[p])add(s[0],'sentence');
for(const s of BUILD)add(s[0],'sentence');
for(const p in TOBE_BY)for(const s of TOBE_BY[p])add(s[0].replace('___',s[1]),'sentence');
for(const s of TOBE)add(s[0].replace('___',s[1]),'sentence');
for(const t of TEXTS){add(t.title,'passage');for(const s of sentences(t.text))add(s,'passage')}
const taps=s=>{for(const t of s.match(TOKRE)||[])if(/[A-Za-z]/.test(t)&&glossKey(t))add(t,'tap')};
for(const t of TEXTS){taps(t.text);for(const q of t.qs)taps(q[0])}
for(const t of TEXTS)for(const q of t.qs)add(q[0],'question');
for(const t of TEXTS)for(const q of t.qs)for(const o of q[1])add(o,'option');
const list=[...seen].map(([text,cat])=>({text,cat}));
if(process.argv[1]&&process.argv[1].endsWith('voice_texts.mjs')){
 writeFileSync(new URL('./voice_texts.json',import.meta.url),JSON.stringify(list,null,0).replace(/\},/g,'},\n')+'\n');
 const n={};for(const x of list)n[x.cat]=(n[x.cat]||0)+1;console.log(list.length,n)}
