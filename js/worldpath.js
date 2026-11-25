/* The island path of the new world: where the stones sit on an island's painted backdrop, and a stone button.
   Shared by the preview (world.html, js/world.js) and the live game behind ?ds=1 (js/avatar.js), so the two never
   drift apart. Styles: css/worldpath.css. DOM is built with createElement only. */
import {ART} from './world_art.js';

/* Where the stones sit on a backdrop, in percent of the picture (x from the left, y from the top), first stone at the
   bottom. A new backdrop needs its own eight points. */
export const PATHS={
 english:[[41,89],[47,79.1],[53,69.2],[52,59.3],[49,49.4],[56,39.5],[63,29.6],[66,19.7]],
 math:[[44,89],[51,79.1],[53,69.2],[52,59.3],[48,49.4],[44,39.5],[50,29.6],[58,19.7]]};

/* n stones spread over a backdrop's eight points, in order, the first at the bottom and the last at the top */
export function pathPoints(kind,n){const P=PATHS[kind];if(n<=1)return[P[0]];return Array.from({length:n},(_,k)=>P[Math.round(k*(P.length-1)/(n-1))])}

/* a stone: done, current or locked, with its accessible name; the caller adds the mark, the stars, a label */
export function stone(state,label,art=state){
 const b=document.createElement('button');b.type='button';b.className='w-st w-st--'+state;b.setAttribute('aria-label',label);
 if(state==='current')b.setAttribute('aria-current','step');
 const i=document.createElement('img');i.className='w-st__art';i.src=ART['ui/stone-'+art];i.alt='';i.decoding='async';i.draggable=false;
 b.appendChild(i);return b}
