/* Extra practice games over the same words as the islands, each behind the same switch, which is off unless a device
   was given it (open the game once with ?games=1; ?games=0 takes it away).
   They are practice only: no stars, no points, nothing added to the pupil's saved progress and nothing sent anywhere.
   A wrong answer never ends a round: it is explained, and the card comes back.
   One line per game in EXTRA; the island screen shows one button for each. */
import {SET,saveSet,esc} from './state.js';
import * as tf from './tf.js';
import * as pairs from './pairs.js';

export const EXTRA={tf:{name:'נכון או לא?',mod:tf},pairs:{name:'זוגות',mod:pairs}};
export const extraOn=()=>SET.games===true;
export function initExtra(){let v=null;try{v=new URLSearchParams(location.search).get('games')}catch(e){}
 if(v==='1'||v==='0'){SET.games=v==='1';saveSet()}}
/* the row of buttons on an island */
export const extraRow=i=>extraOn()?`<p class="xtr"><small>עוד תרגול, בלי כוכבים:</small>${Object.keys(EXTRA).map(k=>`<button class="xtb" data-a="nav" data-to="extra/${i.id}/${k}">${esc(EXTRA[k].name)}</button>`).join('')}</p>`:'';
/* the parts (word lists) an island practises */
export const partsOf=i=>[...new Set(i.levels.map(l=>l[1]))];
