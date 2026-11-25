/* Where a meaning comes from, for word help (js/help.js). Data only: nothing here touches the page or the network.
   Every meaning is an entry that is already in the game: the teacher's Unit 1 word list (WORDS, from RAW in js/data.js)
   and, only if GLOSSARY below is switched on, the reading glossary the story level has always shown (GL). The Hebrew of a whole sentence is only what
   BUILD and SENT in js/data.js already hold. Nothing is translated here and nothing is made up. */
import {WORDS,GL,BUILD,SENT} from './data.js';

/* GLOSSARY: also use the reading glossary. false = the teacher's word list only.
   It is false: the glossary was written for the game's own stories, and several of its meanings are wrong outside
   them ("a", "is", "plays", "can", "old"). It stays off until the teacher has gone over its entries;
   docs/WORD_HELP_COVERAGE.md lists every one of them with the sentences it would appear in. */
export const GLOSSARY=false;
const LIST=new Map();for(const w of WORDS){const k=w.en.toLowerCase();if(!LIST.has(k))LIST.set(k,w.he)}
const rx=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const tok=gl=>{const multi=[...new Set([...LIST.keys(),...(gl?Object.keys(GL):[])])].filter(k=>/[^a-z]/.test(k)).sort((a,b)=>b.length-a.length);
 return new RegExp('((?:'+multi.map(rx).join('|')+")(?![A-Za-z])|[A-Za-z]+(?:'[a-z]+)?|[^A-Za-z]+)",'gi')};
const TOK=tok(GLOSSARY),TOK_ALL=tok(true);
/* {he, src} for one word or fixed phrase as it is written, or null. src: 'list' = the teacher's word list, 'gl' = the reading glossary */
export function meaning(t){const k=String(t).toLowerCase(),k2=k.replace(/'s$/,'');
 for(const x of k===k2?[k]:[k,k2]){if(LIST.has(x))return{he:LIST.get(x),src:'list'};if(GLOSSARY&&GL[x])return{he:GL[x],src:'gl'}}
 return null}
export const tokens=text=>String(text).match(TOK)||[];
/* for the coverage page only: how a text would be cut, and what would be shown, if the glossary were on */
export const tokensAll=text=>String(text).match(TOK_ALL)||[];
export function glossary(t){const k=String(t).toLowerCase(),k2=k.replace(/'s$/,'');
 for(const x of k===k2?[k]:[k,k2]){if(LIST.has(x))return null;if(GL[x])return GL[x]}return null}
/* the Hebrew of a whole sentence, only when the data already holds it (BUILD and SENT in js/data.js) */
const norm=s=>String(s).trim().replace(/\s+/g,' ');
const SENTS=new Map([...BUILD,...Object.values(SENT).flat()].map(([e,h])=>[norm(e),h]));
export const sentenceHe=en=>SENTS.get(norm(en))||null;
/* a sentence's place in that list: what a button on the page carries instead of the sentence itself */
const SKEYS=[...SENTS.keys()];
export const sentKey=en=>SKEYS.indexOf(norm(en));
export const sentByKey=k=>{const e=SKEYS[+k];return e===undefined?null:SENTS.get(e)};

