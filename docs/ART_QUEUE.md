# Art queue: briefs ready for caps A, B and C (nothing generated yet)

Status: prepared at zero credits, waiting for the owner's approval of each spend in the designer's session. Caps and
totals are in `docs/ART_LEDGER.md` (budget 750, caps A 25, B 20, C 45; D held). Every batch below is quoted with the
estimate tool first, its job ids go into the file names and `assets/al/sources.tsv`, its cost into the ledger, and
the running total per cap is reported to the lead after each batch. A batch never starts if its quote would cross its
cap. No characters, brands or real people; voices are the preset Kaia, never a clone. **Every brief carries the line
"must not resemble any existing character, mascot or toy"**, and every result is checked against it (species details,
colours and shapes chosen so nothing evokes a known one).

Style reference for every image: the night-sea look of batch h (the six English islands) and the HUD icons of batch e
(job `81064ec7-…`, the bolt): glossy, soft-shaded, thick friendly silhouettes, the Arcade Lagoon palette.

## A. Secret pictures for the pupil sign-in (cap 25; spec `docs/SIGNIN.md` section 2)

**Images: 5 sheets of 4** (gpt_image_2_5, high, 1:1, image reference: the bolt icon), 1.25 each = **6.25**; up to two
retake sheets = 8.75. Each sheet is a 2 x 2 grid of separate rounded navy tiles; the build cuts each sheet into four
192 x 192 WebP tiles (and 128 for the slots) with a local script, no credits.

Shared prompt text (every sheet): "A 2x2 grid of four separate square icon tiles, evenly spaced with clear gaps, on a
plain dark navy background (#0B1E3F). Each tile: a rounded square, slightly lighter navy (#18376B), with ONE single
object centred, large, filling about 70% of the tile, painted in the same glossy, soft-shaded, friendly game-icon style
as the reference image, bright saturated colours, thick flat shapes with a clean silhouette readable at 56 px, no thin
lines. No text, no letters, no numbers, no faces, no characters, no logos or brand marks, no shadows outside the tiles.
Must not resemble any existing character, mascot, toy or game item."

| Sheet | Top right | Top left | Bottom right | Bottom left |
|---|---|---|---|---|
| 1 | תפוח: a shiny red apple with one green leaf | בננה: a single yellow banana | אבטיח: a watermelon wedge, green rind, red flesh, black seeds | קקטוס: a green cactus in a small terracotta pot |
| 2 | ענבים: a bunch of purple grapes | פרח: one pink flower with a yellow centre on a green stem | מטריה: an open blue umbrella | עפיפון: an orange diamond kite with a short tail of bows |
| 3 | תוף: a red and white drum with two sticks | כובע: a brown wide-brimmed hat | נעל: a single light-blue sneaker with white laces | פיל: a grey elephant, whole body, side view, simple, no human expression |
| 4 | ג׳ירפה: a giraffe, yellow with brown spots, whole body, tall, simple, no human expression | בית: a small house, cream walls, red roof, blue door | עיפרון: one blue pencil, straight, sharpened tip | ספר: a closed blue-green book, thick |
| 5 | פעמון: a gold bell | מכונית: a small yellow car seen from the side, no logo | מספריים: a pair of scissors, orange handles, silver blades, open | פטרייה: a plain field mushroom, smooth orange-brown cap, no spots, cream stalk |

Checks before use (frame by frame, at 56 px on navy): each object alone in its tile, no letters, no face on the
animals, colours as listed, no pair confusable (apple and mushroom, banana and pencil, umbrella and mushroom, elephant
and giraffe), and nothing that reads as a known game or film item (the mushroom has no spots). A failing sheet is retaken once.

**Voice: 22 clips** (text2speech_v2, ElevenLabs, preset Kaia; quoted 0.75 each = **16.5**; the account has charged
0.15 a take so far). Each clip is checked by speech recognition before use. **For the teacher's review** (our words):

| # | Text | Use |
|---|---|---|
| 1 | קודם תמונה אחת, אחר כך עוד אחת. | A3, played once |
| 2 | אמרו את זה בקול. | A4 |
| 3 to 22 | תפוח · בננה · אבטיח · קקטוס · ענבים · פרח · מטריה · עפיפון · תוף · כובע · נעל · פיל · ג׳ירפה · בית · עיפרון · ספר · פעמון · מכונית · מספריים · פטרייה | a tile's name on tap |

Nikud where Kaia may misread: מְטְרִיָּה, עֲפִיפוֹן, מִסְפָּרַיִם, פִּטְרִיָּה, קַקְטוּס (sent with nikud, written without).

**Total A: 22.75 quoted** (6.25 + 16.5), inside 25. If a retake sheet is needed, the clips are recorded in the
account's real price first and the quote re-checked against what is left of the cap.

**Done (batch l1, 2026-11-26):** the 20 pictures are in `assets/al/secret/` (192 px tiles, each with its own navy
tile) and the 22 clips in `assets/al/voice/`, listed in `assets/al/sources.tsv`. Speech recognition agrees with every
clip except **ספר (book)**, which it hears as "ספל" in all three takes; **a person listens to it** (and to the rest)
before the screens go live. 11.05 charged of cap A.

## B. Fraction Bay islands in the new look (cap 20)

Today the math map (`js/mdata.js`, 4 islands) reuses the English island art under CSS (`css/ds-game.css`, art 2, 3,
4, 6), so the two maps look the same. Four new islands, one per math island, in the style of batch h (transparent,
1:1, medium, image reference: the English island `isl-1`), each with an idea a child links to its topic without any
number or letter on it:

| Island | Idea |
|---|---|
| 1 אי השלמים (whole numbers and improper fractions) | a round island like a whole pie seen from above, with one wedge-shaped cove; a small path round it |
| 2 אי החיבור (adding) | two half-islands joined by a little wooden bridge, together making one round shape |
| 3 אי החיסור (subtracting with borrowing) | a round island with a wedge-shaped lagoon cut out of it and a small rock floating next to it |
| 4 אי המבחן (the exam) | a taller island with stepped terraces up to a lantern at the top, the "final" island |

Locked versions are made locally from the same files (desaturated, darker, as the English `-locked` ones), so they cost
nothing. **Estimate:** 4 images at the medium price (0.5 each in batch h) = **2.0**, with one retake each 4.0; at the
high price 5.0 to 10.0. Inside 20 either way. Wiring: the client engineer swaps the four `isl_N` overrides for the
math screens to the new files (or `js/mdata.js` gets its own art keys).

## C. Ten more avatars with their tap animations (cap 45)

Recipe and checks as batches a and i: portrait first (gpt_image_2_5, medium, 1:1, style reference the approved picker
frame), then a 2 s tap animation from the portrait (grok_video, 2 s, 1:1, start image the portrait): closed-mouth
smile, a small tilt, one blink, nothing else; every frame checked (reject distorted faces, teeth, extra limbs, a
changed outfit). No humans (the 8 children stay the open starters). Generic, original designs only: no known
character's look, colours or outfit.

| # | Character (grown, not a baby) | Look |
|---|---|---|
| 1 | a hedgehog | warm brown spines, cream face, no clothes |
| 2 | a koala | grey, round ears, a eucalyptus leaf |
| 3 | a raccoon | grey, ringed tail, no clothes, no mask-like costume |
| 4 | a capybara | warm brown, calm, a small orange flower on its head |
| 5 | an otter | brown, holding a smooth grey pebble |
| 6 | a flamingo | coral pink, standing on one leg |
| 7 | a zebra | plain black and white stripes, no clothes |
| 8 | a badger | grey with a black-and-white striped face |
| 9 | a kangaroo | sandy brown, standing |
| 10 | a griffin (from old myths, not a film's) | eagle head and wings, lion body, brown and gold, friendly eyes |

Every prompt adds: "an adult animal, not a baby; must not resemble any existing character, mascot or toy". Rejected
when a result evokes a known character (a lion cub, a white unicorn with a pastel mane, a round teal dragon, a blue
furry monster, a green frog with big eyes: dropped for that reason).

Not used on purpose: anything in the secret-picture set (elephant, giraffe), any crab, any existing avatar.

**Estimate:** portraits 10 x 0.5 = 5.0; animations 10 x 3.0 = 30.0; together **35.0**, leaving 10 for retakes (three
animations). If more than three animations fail, the rest get the CSS tilt-and-bounce the owl has, at no cost; the cap
is not raised. Unlock levels beyond 13 are the engineer's (the ladder in `js/avatar.js`).

## Order

A (unblocks the sign-in screens), then B, then C, each only after the owner's yes in the designer's session.
