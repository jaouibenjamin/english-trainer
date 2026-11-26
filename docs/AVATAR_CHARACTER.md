# A character for every avatar (DRAFT, for the owner's approval)

The owner's ask from the start: each avatar has its own nature, and its tap animation shows it ("one crosses arms, one
smiles, one grumpy face, each with its own nature"). Today all animations do the same smile, tilt and blink. This sheet
gives each of the 30 a nature in a word or two and **one distinct 2 s gesture**. **Nothing is generated until the owner
approves this sheet**; the cap then comes from the lead's held budget (D).

Contact sheet for the phone: `docs/mock/avatars.html` (the stills with the nature and gesture under each, in Hebrew).

## Rules for every gesture

- Readable at tile size (about 96 px): one big clear movement, not a small facial detail only.
- No two alike. Kind: nothing mocking or scary; a grumpy one is funny-grumpy, never mean.
- As before: no teeth, no open mouth that shows a tongue, no distortion, no new limbs beyond the hands or paws the
  gesture needs, the same art style and framing, a static camera.
- Ends on the still: the clip returns to the portrait pose (or its clean part is played forward and back), so the still
  comes back without a jump. Every frame is checked before use.
- Gestures with hands (wave, thumbs-up, salute, crossed arms, OK sign, "shh") are the riskiest for the model; they are
  marked in the estimate.

## The 30

| Avatar | Nature | Gesture (2 s, ends on the still) | Plan |
|---|---|---|---|
| `girl-braids` | cheerful leader (עליזה ומובילה) | a big friendly wave with one hand | new animation |
| `boy-cap` | sporty (ספורטיבי) | turns his cap round and gives a thumbs-up | new animation |
| `boy-blond` | clever (חכם) | pushes his glasses up his nose and gives a proud nod | new animation |
| `boy-curls` | curious (סקרן) | leans in wide-eyed, then raises one finger: "aha!" | new animation |
| `boy-scarf` | shy (ביישן) | tucks his chin into his bandana and peeks up with a small smile | new animation |
| `girl-curls` | dreamy (חולמנית) | closes her eyes and sways side to side as if humming | new animation |
| `girl-glasses` | music lover (אוהבת מוזיקה) | puts her headphones on and bobs her head to a beat | new animation |
| `girl-ponytail` | grumpy but kind (רוטנת אבל טובה) | crosses her arms and raises an eyebrow, then melts into a smile | new animation |
| `cat` | proud (גאה) | lifts his chin, closes his eyes smugly, flicks one ear | new animation |
| `fox` | cheeky (שובב) | a quick wink and a sly smile | keep (the existing animation already shows it) |
| `penguin` | clumsy and happy (מגושם ושמח) | flaps his flippers and wobbles side to side | new animation |
| `owl` | thoughtful (מהורהר) | turns his head to the side and back, one slow blink | new animation |
| `parrot` | show-off (שוויצר) | fluffs his feathers and puffs out his chest | new animation |
| `octopus` | playful (שובבה) | waves several arms one after another, like a wave | new animation |
| `shark` | nervous but friendly (לחוץ וחביב) | glances left, glances right, then a relieved smile | new animation |
| `turtle` | calm (רגוע) | a slow nod and a touch of his cap brim | new animation |
| `diver` | adventurous (הרפתקן) | bubbles rise from the helmet, then an OK sign with his hand | new animation |
| `pilot` | confident (בטוח בעצמו) | a crisp salute | new animation |
| `robot-bell` | polite (מנומס) | a small bow while its propeller spins | new animation |
| `robot-box` | excited (נלהב) | its screen face switches to a huge smile and it gives a little hop | new animation |
| `hedgehog` | careful (זהיר) | his spines puff up and he peeks out sideways | new animation |
| `koala` | sleepy (ישנוני) | eyelids droop, head nods down, wakes up with a blink | new animation |
| `raccoon` | sneaky (ערמומי) | glances both ways and puts a paw to his lips: "shh" | new animation |
| `capybara` | zen (שלווה) | closes her eyes slowly and takes a deep calm breath | keep (the existing animation already shows it) |
| `otter` | nimble (זריזה) | tosses her pebble up and catches it | new animation |
| `flamingo` | elegant (אלגנטית) | lifts her head high in one graceful curve | new animation |
| `zebra` | silly (מצחיק) | wiggles his ears one after the other | new animation |
| `badger` | brave (אמיצה) | puffs out her chest and gives a determined nod | new animation |
| `kangaroo` | bouncy (קופצני) | bounces up and down twice | new animation |
| `griffin` | noble (אציל) | half-opens his wings and bows his head | new animation |

## Estimate (not started)

- Keep as they are: **fox** (its retake already winks with a sly smile) and **capybara** (its slow eye close reads as
  calm). The owl has no animation today (a CSS bob) and gets one.
- New animations: **28** at 3.0 each (grok_video, 2 s, start image the portrait) = **84.0**.
- Retakes: the first batch of ten needed three in thirteen; the gestures with hands are harder, so plan for about one
  in four: **about 21**. Total **about 105**, with **90** as a tighter cap (then the hardest ones fall back to a still
  portrait with the CSS bob, as the owl has today).
- The ten provisional animations in #99 are replaced by these; the 18 kept-but-generic older ones too.
