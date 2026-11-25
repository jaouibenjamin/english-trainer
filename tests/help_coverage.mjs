// suite: full=--check   // picked up by tests/all.py
/* What word help can and cannot translate, counted from the game's own data.
     node tests/help_coverage.mjs            # print the numbers
     node tests/help_coverage.mjs --write    # also write docs/WORD_HELP_COVERAGE.md (the lists, for the teacher)
     node tests/help_coverage.mjs --check    # fail if that file is out of date
   Counted: every English word and sentence a pupil can see in the four island levels and in the mock exam. A meaning is
   "from the teacher's list" (the Unit 1 word list) or "in the reading glossary" (the story level's own list, which word
   help does not use while GLOSSARY in js/helpdata.js is false); a word in neither has no help. A sentence has Hebrew
   only if the data already holds its translation. The texts are cut into words the way they would be with the glossary
   on, so the glossary's own phrases ("years old") are counted as it would show them. */
import {WORDS,TEXTS,SENT,TOBE_BY,BUILD} from '../js/data.js';
import {POOL,TRIP,KIDS,INVITE} from '../js/xdata.js';
import {meaning,tokensAll,glossary,sentenceHe,GLOSSARY} from '../js/helpdata.js';
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const OUT=path.join(path.dirname(path.dirname(fileURLToPath(import.meta.url))),'docs','WORD_HELP_COVERAGE.md');
const latin=s=>/[A-Za-z]/.test(s);
/* text = sentences and questions (where a word can be tapped); answers = words on answer buttons (never tappable) */
const text=new Map(),answers=new Map(),sents=new Map(),seenIn=new Map();
const add=(m,s,where)=>{for(const t of tokensAll(s))if(latin(t)){const k=t.toLowerCase();if(!m.has(k))m.set(k,new Set());m.get(k).add(where);
  if(m===text){if(!seenIn.has(k))seenIn.set(k,new Set());seenIn.get(k).add(String(s).replace(/\s+/g,' ').trim())}}};
const sentence=(s,where)=>{s=String(s).trim();if(!latin(s)||!/\s/.test(s))return;if(!sents.has(s))sents.set(s,new Set());sents.get(s).add(where)};
const split=t=>t.match(/[^.!?]+[.!?]+["”]?\s*/g)||[t];
for(const w of WORDS)add(answers,w.en,'word levels');
for(const t of TEXTS){add(text,t.title,'reading');for(const s of split(t.text)){add(text,s,'reading');sentence(s,'reading story')}
 for(const q of t.qs){add(text,q[0],'reading');sentence(q[0],'reading question');for(const o of q[1])add(answers,o,'reading')}}
for(const p in SENT)for(const [en] of SENT[p]){add(answers,en,'bridge');sentence(en,'bridge: build')}
for(const p in TOBE_BY)for(const [s,a] of TOBE_BY[p]){add(text,s.replace('___',' '),'bridge');add(answers,a,'bridge');sentence(s.replace('___',a),'bridge: am / is / are')}
const items=Object.values(POOL).flatMap(g=>Array.isArray(g)?g:Object.values(g).flat());
for(const it of items){const full=s=>it.a&&/^[A-Za-z' ]+$/.test(it.a)?s.replace('___',it.a):s;
 if(it.sent){add(text,it.sent.replace('___',' '),'mock exam');sentence(full(it.sent),'mock exam')}
 if(it.raw){add(text,it.raw,'mock exam')}
 for(const l of it.lines||[]){add(text,l,'mock exam');sentence(l,'mock exam')}
 if(it.big&&latin(it.big))add(answers,it.big,'mock exam');
 if(it.a&&latin(String(it.a))){add(answers,String(it.a),'mock exam');if(it.type==='sentence'||it.type==='order')sentence(String(it.a),'mock exam')}
 for(const t of it.tiles||[])add(answers,t,'mock exam');
 if(typeof it.opts==='function')for(let i=0;i<25;i++)for(const o of it.opts())if(latin(String(o)))add(answers,String(o),'mock exam');
 for(const o of it.o||[])if(latin(String(o)))add(answers,String(o),'mock exam')}
add(text,TRIP.title,'mock exam');for(const l of TRIP.lines){add(text,l,'mock exam');sentence(l,'mock exam')}
for(const k of KIDS){add(text,k.n,'mock exam');for(const l of k.likes||[])add(text,l,'mock exam');if(k.month)add(text,k.month,'mock exam')}
for(const v of Object.values(INVITE))if(latin(String(v)))add(text,String(v),'mock exam');

const all=new Set([...text.keys(),...answers.keys()]);
/* list = the teacher's word list; gl = only in the reading glossary; none = in neither */
const src=k=>{const m=meaning(k);return m&&m.src==='list'?'list':glossary(k)?'gl':'none'};
const shown=k=>src(k)==='list'||(GLOSSARY&&src(k)==='gl');
const count=keys=>{const c={list:0,gl:0,none:0};for(const k of keys)c[src(k)]++;return c};
const cAll=count(all),cText=count(text.keys());
const miss=[...text.keys()].filter(k=>src(k)==='none').sort();
const missAns=[...all].filter(k=>!text.has(k)&&src(k)==='none').sort();
const gl=[...text.keys()].filter(k=>src(k)==='gl').sort();
const yes=[...sents.keys()].filter(s=>sentenceHe(s)).sort(),no=[...sents.keys()].filter(s=>!sentenceHe(s)).sort();
const pct=(a,b)=>b?Math.round(a/b*100)+'%':'0%';
const use=GLOSSARY?'shown too (GLOSSARY is on)':'not shown (GLOSSARY is off until the teacher has gone over it)';
const line1=`English words on screen in the four island levels and the mock exam: ${all.size} distinct. In the teacher's word list: ${cAll.list}. Only in the reading glossary, ${use}: ${cAll.gl}. In neither: ${cAll.none}.`;
const line2=`Of those, the words inside sentences and questions (the ones a pupil could tap): ${text.size} distinct. In the teacher's word list, so they can be tapped today: ${cText.list}. Only in the reading glossary, ${use}: ${cText.gl}. In neither: ${cText.none}.`;
const line3=`English sentences on screen: ${sents.size} distinct. With a Hebrew translation in the data: ${yes.length}. Without: ${no.length}.`;
const where=(m,k)=>[...m.get(k)].join(', ');
const md=`# Word help: what the data can translate

Built by \`node tests/help_coverage.mjs --write\` from the game's data. Do not edit by hand.

Word help shows only meanings that are already in the game's data. This page lists what is covered and what is not, so
the missing meanings and sentence translations can be asked from the teacher. Nothing here was translated for this page.

- ${line1}
- ${line2}
- ${line3}

"The teacher's word list" is her Unit 1 list (\`RAW\` in \`js/data.js\`). "The reading glossary" is the list the story
level has always used for a tap on a word (\`GL\` in \`js/data.js\`). It was written for the game's own stories, and some
of its meanings are wrong outside them (for example "a", "is", "plays", "can", "old"). So word help does not use it:
\`GLOSSARY\` in \`js/helpdata.js\` is ${GLOSSARY?'true':'false'}. The table below is for the teacher: every glossary entry that word help
would show, with the sentences it would appear in. An entry she approves as it is can be switched on; one she corrects
goes into the data with her wording.

## Words in sentences and questions that have no meaning yet (${miss.length})

These are in neither list. They are not help words.

${miss.map(k=>`- \`${k}\` (${where(text,k)})`).join('\n')}

## Reading glossary entries, for the teacher to go over (${gl.length})

${GLOSSARY?'Shown today.':'Not shown today.'} Each row: the word, the meaning the glossary holds, and up to four of the sentences and lines it would appear in.

| Word | Glossary meaning | Would appear in |
|---|---|---|
${gl.map(k=>`| \`${k}\` | ${glossary(k)} | ${[...seenIn.get(k)].slice(0,4).map(x=>x.replace(/\|/g,'/')).join(' · ')}${seenIn.get(k).size>4?` · and ${seenIn.get(k).size-4} more`:''} |`).join('\n')}

## Words that appear only on answer buttons and have no meaning (${missAns.length})

Answer buttons are never help words, so nothing is missing on screen; listed for completeness.

${missAns.map(k=>`\`${k}\``).join(', ')}

## Sentences that have a Hebrew translation in the data (${yes.length})

| Sentence | Hebrew in the data | Where |
|---|---|---|
${yes.map(s=>`| ${s} | ${sentenceHe(s)} | ${[...sents.get(s)].join(', ')} |`).join('\n')}

The button "the sentence in Hebrew" is offered for these only where showing it does not give the answer away: in the
mock exam's practice, for a complete sentence or one whose gap is am / is / are. In the bridge level the Hebrew of a
build sentence is already the question itself.

## Sentences without a Hebrew translation (${no.length})

${no.map(s=>`- ${s} (${[...sents.get(s)].join(', ')})`).join('\n')}
`;
console.log(line1);console.log(line2);console.log(line3);
if(process.argv.includes('--write')){writeFileSync(OUT,md);console.log('wrote docs/WORD_HELP_COVERAGE.md')}
if(process.argv.includes('--check')){const ok=existsSync(OUT)&&readFileSync(OUT,'utf8')===md;console.log(ok?'ALL PASSED':'FAIL docs/WORD_HELP_COVERAGE.md is out of date: node tests/help_coverage.mjs --write');process.exit(ok?0:1)}
