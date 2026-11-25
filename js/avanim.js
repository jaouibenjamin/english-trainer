/* A character's short animation (2 s, animated WebP in assets/al/avanim/), played once when the character is tapped or
   chosen, and on hover where there is a mouse. The still portrait shows the rest of the time.
   - The animation file is requested only at that moment, never before (nothing is preloaded).
   - With prefers-reduced-motion or calm mode (html.calm) nothing moves and nothing is requested.
   - It ends on the still portrait: the last frames fade back to the first, and the <img> gets its still picture back.
   DOM only: it changes one <img>'s src, nothing else. */
import {ART} from './world_art.js';

const PLAY_MS=2450;   // 29 frames at 83 ms, plus a little
export function canMove(){
 try{if(matchMedia('(prefers-reduced-motion: reduce)').matches)return false}catch(e){}
 return !document.documentElement.classList.contains('calm');
}
let n=0;
export function playAv(img,id){
 const anim=ART['avanim/'+id],still=ART['av/'+id];
 if(!img||!anim||!still||!canMove())return false;
 clearTimeout(img.__avT);
 img.src=anim+'#p'+(++n);   // a new address each time, so the animation starts again from its first frame
 img.__avT=setTimeout(()=>{img.src=still},PLAY_MS);
 return true;
}
