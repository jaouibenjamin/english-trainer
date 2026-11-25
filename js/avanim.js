/* A character's short animation (2 s, animated WebP in assets/al/avanim/), played once when the character is tapped or
   chosen, and on hover where there is a mouse. The still portrait shows the rest of the time.
   - The animation file is requested only at that moment, never before (nothing is preloaded).
   - With prefers-reduced-motion or calm mode (html.calm) nothing moves and nothing is requested.
   - It ends on the still portrait: retakes play forward and back (so the last frame is the first), the older files fade
     their last frames back to the first, and the <img> gets its still picture back.
   - A character with no animation file (the owl: two takes changed its expression) gets a small CSS tilt-and-bounce of
     the still portrait instead (.wi-av__art--bob in css/ds.css), under the same motion rules.
   DOM only: it changes one <img>'s src, nothing else. */
import {ART} from './world_art.js';

const PLAY_MS=2450;   // 29 frames at 83 ms, plus a little
export function canMove(){
 try{if(matchMedia('(prefers-reduced-motion: reduce)').matches)return false}catch(e){}
 return !document.documentElement.classList.contains('calm');
}
let n=0;
const BOB_MS=900;
export function playAv(img,id){
 const anim=ART['avanim/'+id],still=ART['av/'+id];
 if(!img||!still||!canMove())return false;
 if(!anim){   // no file: move the still portrait itself, once
  img.classList.remove('wi-av__art--bob');void img.offsetWidth;img.classList.add('wi-av__art--bob');
  clearTimeout(img.__avT);img.__avT=setTimeout(()=>img.classList.remove('wi-av__art--bob'),BOB_MS);
  return true;
 }
 clearTimeout(img.__avT);
 img.src=anim+'#p'+(++n);   // a new address each time, so the animation starts again from its first frame
 img.__avT=setTimeout(()=>{img.src=still},PLAY_MS);
 return true;
}
