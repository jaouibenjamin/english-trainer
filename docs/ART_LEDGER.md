# Art ledger: Arcade Lagoon

Owner's cap for all art and sound of the new look: **450 credits**, stop and report at 400. Tool: the owner's own
Higgsfield account, existing credits only. Every batch is quoted with the estimate tool first; "charged" is what the
account was charged for the batch. Files and their job ids: `assets/al/sources.tsv`. No account balance is written here.

| Batch | What | Model, settings | Jobs | Quoted | Charged | Running total | Left of 450 |
|---|---|---|---|---|---|---|---|
| a | 20 character portraits (8 animals, 4 robots / helmets, 4 girls, 4 boys) + 2 redos | gpt_image_2_5, medium, 1k, 1:1, style reference: the approved picker frame | 22 | 11.00 | 11.00 | 11.00 | 439.00 |
| b | Pitzi in the new look, 6 poses (wave, happy, listen, oops, star, walk) | gpt_image_2_5, medium, 1k, 1:1, transparent | 6 | 3.00 | 3.00 | 14.00 | 436.00 |
| c | World map background (no islands), 2 subject islands, 3 "not open yet" islands | background: high, 9:16; islands: medium, 1:1, transparent | 6 | 3.75 | 3.75 | 17.75 | 432.25 |
| d | Island path backdrops, English and maths | gpt_image_2_5, high, 1k, 9:16 | 2 | 2.50 | 2.50 | 20.25 | 429.75 |
| e | Mission stones (done, current, locked), HUD icons (star, bolt, lock, focus, gear, sound on / off) | gpt_image_2_5, medium, 1k, 1:1, transparent | 9 | 4.50 | 4.50 | 24.75 | 425.25 |
| g | Review fixes: robot portrait redone, Pitzi "listen" redone, world map sea from above | portrait and pose: medium, 1:1; sea: high, 9:16 | 3 | 2.25 | 2.25 | 27.00 | 423.00 |
| f | Sound: 2 island themes x 2 takes (30 s each, 4.36), 3 signature sounds x 2 takes (3 s each, 0.44) | elevenlabs_music_v2_5, instrumental | 10 | 20.08 | 20.08 | 47.08 | 402.92 |
| h | The six English map islands redrawn in the night-sea style; the map sea with quiet details (whale, lantern boats, lighthouse, jellyfish); painted frames: panel, gold button, HUD pill (9-slice) | islands and frames: gpt_image_2_5, medium, 1k, transparent, style reference: the English island of batch c; sea: high, 9:16, reference: the batch g sea | 10 | 5.75 | 5.75 | 52.83 | 397.17 |
| i | Character animations: 2 s per character, played once on tap (20 used); sample first (fox), then 19, then two retakes | grok_video, 2 s, 1:1, start image: the character's portrait (batch a/g) | 22 | 66.00 | 66.00 | 118.83 | 331.17 |
| i2 | Character animations, lead's frame review: retakes of penguin, fox, owl (one each); penguin and fox used, owl failed again and gets a CSS tilt-and-bounce instead | grok_video, 2 s, 1:1, same start images | 3 | 9.00 | 9.00 | 127.83 | 322.17 |
| j | Welcome film: 3 animated shots (5 s, 5 s, 2 s) and the Hebrew narration (preset voice Kaia); shots 1, 4, 6 cut here from our pictures | grok_video 720p (7.5 + 7.5 + 3); text2speech_v2 elevenlabs (0.75) | 4 | 23.25 | 23.25 | 151.08 | 298.92 |
| j2 | Welcome film: new narration with the platform's new name (preset voice Kaia, nikud on two words) | text2speech_v2 elevenlabs | 1 | 0.75 | 0.75 | 151.83 | 298.17 |
| j3 | Welcome film: music bed, original, instrumental, 30 s (the platform's own theme, for the film and later the map); one take, used | elevenlabs_music_v2_5 | 1 | 4.36 | 4.36 | 156.19 | 293.81 |
| k | Welcome film v2 (the owner's story, one continuous camera): 4 key images; 4 shots from them (gate used; path, grass, flight unused once he asked for no cuts); 5 chained shots (side, grass, faces, zoom-out, flight); narration and 2 voices for Pitzi's line (one used). Intro cap raised by the owner to 115 | gpt_image_2_5 high 9:16 (4 x 1.25); grok_video 5 s 9:16 (9 x 7.5); text2speech_v2 elevenlabs (3 x 0.75) | 16 | 74.75 | 74.75 | 230.94 | 219.06 |
| k2 | Welcome film v3 (the owner's notes): the island rising from the sea, Pitzi's key image, Pitzi's shot x 2 (the first showed pointed teeth: unused), a closing zoom-out (a second crab appeared: unused; a digital pull-back of Pitzi's last frame instead), one narration line. Intro cap raised by the owner to 140 | grok_video 5 s (4 x 7.5); gpt_image_2_5 high (1.25); text2speech_v2 (0.75) | 6 | 32.00 | 32.00 | 262.94 | 187.06 |
| k3 | Welcome film v4 (the owner's notes): the turn and the island rising in one camera move, Pitzi's key image in the same frame, Pitzi's lip-synced shot x 2 (the first made him a giant: unused). Intro cap raised by the owner to 160 | grok_video 5 s (3 x 7.5); gpt_image_2_5 high (1.25) | 4 | 23.75 | 23.75 | 286.69 | 163.31 |
| k4 | Welcome film v5 (the owner's notes): the laughs (each character its own, no words), the slow rise, Pitzi's leap out of the sea (key image and 6 s shot), the kids' answer and run. Intro cap raised by the owner to 200 | grok_video (5 s x 3 = 22.5, 6 s = 9); gpt_image_2_5 high (1.25) | 5 | 32.75 | 32.75 | 319.44 | 130.56 |
| k5 | Welcome film v6 (the owner's notes): the shocked faces and slower rise, small Pitzi's leap (key image and 6 s shot), the run again with Pitzi small. The owner approved spending within the 450 budget | grok_video (5 s x 2 = 15, 6 s = 9); gpt_image_2_5 high (1.25) | 4 | 25.25 | 25.25 | 344.69 | 105.31 |
| k6 | Welcome film v7 (the owner's notes): laughs with Pitzi peeking from the sea, the shock flowing into the camera turn as the island rises, Pitzi's leap (key image, 6 s shot x 2: the first turned him into a crab with a penguin's face, unused), the run to the same island | grok_video (5 s x 3 = 22.5, 6 s x 2 = 18); gpt_image_2_5 high (1.25) | 6 | 41.75 | 41.75 | 386.44 | 63.56 |
| k7 | Welcome film: the closing line re-recorded, 3 spellings (the take said "לנתני"); checked by speech recognition, the plain spelling used | text2speech_v2 elevenlabs (3 x 0.75) | 3 | 2.25 | 2.25 | 388.69 | 61.31 |
| k8 | Welcome film: a 5 s test of upscaling the finished film to 4K (Topaz, 2160p), to price a sharper sharing version. Not used | topaz_video 2160p, 5 s | 1 | (no quote offered) | 9.00 | 397.69 | 52.31 |
| k9 | Welcome film: the whole film (no title, 36 s) upscaled to 4K for sharing with the teacher; the title is then rendered at 4K over it. The owner asked for it | topaz_video 2160p, 36 s | 1 | (no quote offered; the test priced it about 65) | 51.00 | 448.69 | 1.31 |

Total charged so far: **448.69** of 450. Left: 1.31. (The account charges voice takes less than their quote, 0.15 for most; the ledger keeps the quote, so it errs on the safe side.) (Batches i and i2 together: 75.00, the cap set for the animations; the welcome film, j to k9: 320.86 (the owner approved spending within the 450 budget). Version 1's files, batches j and j2, are spent and no longer used; its music, j3, is reused.)

## Jobs

Batch a (in file order of `assets/al/av/`; the two not used are marked):

| Subject | Job id | Used |
|---|---|---|
| fox | 13666c83-348b-431b-b04d-d074564ab9fd | yes |
| owl | dc061f6f-695e-4b6c-a996-d0b4e74350d8 | yes |
| sea turtle | bd14c2df-0a0c-4503-913a-c618ad758171 | yes |
| octopus, first try | c920d9d0-4534-41b0-b2d9-8af3c0efbd99 | no: big lashed eyes, read babyish |
| shark | ebdc7601-0e4f-4db6-b376-84e91dd84f87 | yes |
| parrot | 8182976b-36b2-49bf-9bb6-8e79477af20e | yes |
| cat | 98c66024-7444-4d43-b85c-e32596bc0a82 | yes |
| penguin | b06fade6-d121-4d46-ba6d-dd434c30f3bc | yes |
| round white robot | 5e24ee72-0163-4447-9719-fbeab2128607 | no: too close to well-known white game robots with a black visor |
| robot, box head | 8e9be566-a832-4ec2-bc0a-46cbbed67678 | yes |
| diver, brass helmet | 9ef9220a-3ee3-43b5-b9b8-1dc8cd3e07c3 | yes |
| explorer, closed helmet | 947a73dd-7a75-4153-af79-eed8ba753557 | yes |
| girl, curls and headband | 038b25bc-891b-4454-8816-30bc402e16d8 | yes |
| girl, braids | e3e65a4e-765d-4e6c-a55e-bd82ecfed64a | yes |
| girl, glasses and headphones | 29e62949-8a89-4238-b6b5-82767b20433f | yes |
| girl, ponytail and goggles | 28c64740-7668-4b38-98e4-c4a154e32e30 | yes |
| boy, cap | 8963b8c9-566d-48e1-af0b-6821ec7db0f8 | yes |
| boy, curls and rain jacket | a05319fb-6024-40fa-83d0-004133d8b41f | yes |
| boy, glasses and vest | b8ec8cff-d393-4d2c-9f4d-a7148f64e7d4 | yes |
| boy, bandana | 431de75e-e64b-46fa-a0df-33ddf428cc62 | yes |
| robot, lantern (redo) | fb75c13b-cd6a-4301-8a9b-a58550679386 | no: orange and white stripes with one round lens read close to well-known film droids |
| octopus (redo) | b1c753c1-abca-4c2e-9a73-d209ae4faad3 | yes |

Batch g:

| Subject | Job id | Used |
|---|---|---|
| robot, green diving bell | 6c7fc276-a450-4cc4-930d-e689225044d4 | yes, replaces the lantern robot |
| Pitzi, listen (redo) | 1f234b5a-9ec8-4fcc-b2e2-772bb152ee73 | yes, replaces b9e9501a-74ed-448a-9404-5c28e1127b78 (eyes and mouth did not match the other poses) |
| sea from above | f6e9010a-f742-47cc-a849-a034fbb86389 | yes, the world map background; the horizon picture stays for the title screen |

Batch f, sound. The takes were chosen by measurement (even loudness over the 30 s, clean start and end), not by ear:
nobody has listened to them yet. **The owner or the lead must listen before any of it reaches pupils.**

| Sound | Job id | Used |
|---|---|---|
| English theme, take a | 871f8e07-2003-4dfb-b916-9477e1f872c2 | no: loudness wanders (7.7 dB between seconds) |
| English theme, take b | 0d3749f9-5b1f-41eb-9aad-ca3a2c664a3f | yes |
| maths theme, take a | a1f71038-a6ad-43c7-9ee2-3f3b2ccbfc01 | no: drops 14 dB in places and fades at the end |
| maths theme, take b | df140166-4701-433a-91a8-79dfe8618c63 | yes |
| animals, take a | dd0ee639-ca5a-40eb-ab25-1b7207a993b8 | no: 5 s long |
| animals, take b | b7364c03-16fe-42a0-9ef0-b85483a79c8c | yes |
| robots and helmets, take a | 32dd90d2-d557-408b-8a24-8f57e7e6ca18 | yes |
| robots and helmets, take b | 6b9d7e5c-3ff3-4815-9b9c-5a3c65313a5d | no: clips at the peak |
| kids, take a | 6517f4b3-2431-4fc7-9381-2508da43efb2 | yes |
| kids, take b | 4c608dbb-5c2a-47e3-a3a9-488ca4f3644e | no: half a second long |

Themes: mono MP3, 64 kbit/s, 28 s, about 224 KB, levelled to about -24 LUFS so they sit under a voice. Each file starts
and ends at second 15 of the original, with the original end crossfaded into the original start in the middle, so the
loop point is continuous. An MP3 still has a few milliseconds of silence at its edges; the player should crossfade or
use Web Audio to loop without a tick. Signature sounds: mono MP3, 2.4 s, under 20 KB.

Batch h (owner's go-ahead through the lead, about 20 to 30 credits for closing the gap to the concept frames). All ten jobs are used, first try. Locked islands are made here from the same pictures (80 % grey, half brightness, a cool mist), no extra jobs. Nine requests were first sent with a wrong reference id and refused before any job started; nothing was charged for them.

| Subject | Job id |
|---|---|
| island 1, hobbies | f1f77e6e-b4a9-4f6c-9eb3-53faf1fb46d5 |
| island 2, school | 015dc5a7-8cf0-4957-9a08-a0b036734301 |
| island 3, the new home | b74f0f8d-8612-409a-9938-2d53629d4086 |
| island 4, the birthday | 2c5654f8-c012-4de6-ab90-f80dd20c6f40 |
| island 5, presents | 4417a597-d43d-4c75-afbc-86525a35ac92 |
| island 6, treasure | 742bbc3a-52ff-4652-a1c9-b43679ba2e26 |
| sea with details | 17486f52-96ee-4372-9033-9dd45cfa5736 |
| panel frame | 18d17d0b-a2d1-4c77-a6fa-d9e5c3368dca |
| gold button | cc6e3e5f-f91a-4a1a-84fa-df545ab8aa3f |
| HUD pill | 050c516b-9715-499a-b981-3306dd6a4694 |

Batch i (owner's go-ahead through the lead, cap 75 including retakes). Every frame of every take was looked at; the human characters were checked for a changed face, teeth, hands or extra fingers. Two first takes were not used: the owl (it puffed up and the framing jumped in) and the parrot (its crest turned into blue spikes, it stopped looking like its portrait). Each file: animated WebP, 192 x 192, 12 fps, the 24 generated frames plus 4 that fade back to the first, so it ends on the still portrait; 91 to 146 KB.

| Character | Job id | Used |
|---|---|---|
| owl | d2d2b170-25ff-49b5-8d7d-0fcef6ed25d5 | no (lead's frame review): both eyes narrow into a scowl, f13 to f14 |
| turtle | e0c51c5f-6901-4c33-89bb-89313b26215c | yes |
| shark | d982cc13-a6f1-46e8-9d8f-9cca79ccfaf7 | yes |
| parrot | 9028e4dd-1693-4a0d-abd8-1a7219bcef28 | yes |
| cat | 2d6e7703-b127-467d-a053-b9b8ebd478c2 | yes |
| penguin | 52510732-c825-4c1c-a0b5-63d53da3ebfb | no (lead's frame review): pose cut f4 to f5, beak wide open, double image in the fade |
| robot-box | 079ba72f-84f8-488a-b4f2-c2993213ec78 | yes |
| diver | 47e0e32c-cfc8-416b-a766-4c9c11c9681d | yes |
| pilot | b554383f-e6e2-447f-814b-a2631f39a0b3 | yes |
| girl-curls | 71e97db1-4ff6-4158-b859-fe8aab0c0420 | yes |
| girl-braids | dc24c69f-f02f-4a62-8471-3446698fc491 | yes |
| girl-glasses | 36896b79-c6e7-4229-9bd4-94bfd3f9e073 | yes |
| girl-ponytail | ff0b06a1-c050-406a-bcbf-f839ca4b147c | yes |
| boy-cap | 28e1c89e-fa99-4ede-bd23-61b296bc3900 | yes |
| boy-curls | c2d74619-7816-46f9-af65-b8bf92836a8b | yes |
| boy-blond | b6caefca-93f5-4684-ac8a-c5336523c0dd | yes |
| boy-scarf | 29b9100c-d989-49ad-894b-ddcd03be8800 | yes |
| octopus | 719b4000-fc5c-460a-a244-508cc849d7ce | yes |
| robot-bell | c1de682e-ac27-40f8-b210-34792001ae2d | yes |
| fox | 4e6e410f-561b-45c3-92d3-8a7b72309d9a | no (lead's frame review): toothy grin, ears pinned back, ghost ears in the fade |
| owl, first take | cbd4da92-6c26-4777-8b1f-7fc7ed2a9553 | no: puffed up, framing jumped |
| parrot, first take | 73fbce94-1121-405b-82ff-8a1476aee2ff | no: crest turned into blue spikes |

Batches b to e: every job is used, except the first "listen" pose named above; the ids are in `assets/al/sources.tsv` (Pitzi's wave pose,
c2effc24-9597-44ee-9eb7-204c981203c3, was the reference for the other five poses).

Style references (approved frames, made before this ledger, not counted in the cap): world map
339d6b72-d680-4b39-86de-d4927d9cb120, island path 16f37d15-7965-43c3-9666-fb1ee2c49611, avatar picker
b1f0d687-5d18-4811-af95-f2aca8285246, first frame 34b3388f-09b1-4b65-93c7-8b0579be81a4.

Batch i2 (retakes; prompt: closed-mouth smile, small head tilt, one blink or wink, nothing new). Each take's frames were
all looked at. None returns to the starting pose, so the used ones play frames 1 to k and back (ending exactly on the still,
no blended frames):

| Character | Job | Used |
|---|---|---|
| penguin | 37bd5424-72a9-45fd-8b9e-4b44c36d7e3c | yes, frames 1 to 15 and back: smile, tilt, one blink, beak closed |
| fox | ab8ea61d-9a2c-4fe1-beda-89141de05554 | yes, frames 1 to 13 and back: closed-mouth smile, tilt, one wink |
| owl | 797aa225-841f-4c78-b8ef-7fc1f4e57e95 | no: one eye half-lidded into a side-eye (f7 to f9), then a frowning wink; CSS tilt-and-bounce instead |

Batch j jobs: shot 2 7621ea4f-5457-4816-a8dd-cd722b9e9af3, shot 3 970ab3ba-1efa-4c15-af1b-be2b890a8e29 (start frame: our sea picture, uploaded),
shot 5 d3df4296-1b5f-42b1-9c97-c8a8d09bb4dc, narration b87a763d-1a3c-481d-852e-87d9a69afa0f (replaced). Batch j2: narration 1ec486fb-379a-4ec2-9613-83ddce779343. Batch j3: music c9f440f8-64c5-4dfe-ac0c-db1ae20e57bd.

Batch k jobs. Key images: gate 5f2c23a8-7ac6-4f64-a6f3-ca1152e431a8, path 14f86136-3284-4ec4-b8fe-91dc0954e9a1, grass
c3ab51b6-1bcd-4ade-ab1f-a01102901f13, hill 5195d0a8-38e7-49a4-b517-5dafea99db55 (references: the portraits of girl-braids, boy-cap,
fox, penguin). Shots used: gate d69a525d-1314-4d96-984b-e04c7bd04658, side 95ba6021-a085-4b40-9954-04cff5e7c5da, to the grass
33b2a7ea-c94f-4a53-ac57-522ca9bd26e4 (first 1.8 s only: later frames drift, the penguin loses his goggles), faces
e1b88c79-d744-4a09-8724-6af2218648c1, zoom-out 9f533fd3-72c0-49aa-b65c-8b09bdf03b96, flight f47c0bff-0f28-4752-80da-32d4a42b4992.
Unused: b2acb6fc (path), 4ae25e54 (grass), e6aade1b (hill flight), Pitzi voice Dylan 13bb7b67. Narration dd64b78b-db60-4e55-9e97-e908bb1cd35a,
Pitzi (preset voice Archie) 7e57dcd5-6db4-4210-b861-97ad87358c78. Every shot's frames were looked at: generic illustrated gate, no
signs, names or logos; our four avatars as their portraits; the friends at the gate are generic.

Batch k2 jobs: island rising 43b94f4e-17f5-477e-b88f-fa5d5882b416 (from the faces shot's last frame), Pitzi key image
89744b75-fe4e-4e4c-9982-aa3636e2812f (references: Pitzi's wave pose c2effc24, the hill 5195d0a8, the grass c3ab51b6), Pitzi used
f7ce2658-a46d-4523-8a64-a33ebc88e245, unused 2c24bc12 (teeth) and e34ffa12 (two crabs), narration "ופתאום... מתוך הים עולה אי ענק!"
9e3d099a-f624-4dfb-a1b1-52a711fa9798. The shots' own generated sound is used as the background (no recordings of real children).

Batch k3 jobs: turn and rise a13d3fa0-7c64-4219-83d8-77f472592e21 (from the faces shot's last frame), Pitzi added to its last frame
dd2336d6-710e-4e93-a793-498bfcef58c1 (reference: Pitzi's wave pose), Pitzi speaking fdd4513c-1a7a-407c-83fc-f335f5abeb53 (used; his line
is the shot's own generated voice, not a clone), unused 197e8c49 (he grew to giant size). v3's shots 43b94f4e, 89744b75 and f7ce2658
and the narration line's v3 timing are no longer used.

Batch k4 jobs: laughs e2d71bef-ca94-46a4-b59f-64b44bf67b92, slow rise 70bf74cf-6116-46b1-b3a5-6e4bbdcaa93f, Pitzi leaping key image
e3e5f8d1-9338-4b86-93f6-3ce2ed9c2afe, Pitzi's leap and line 91f4e24c-8574-40a6-a385-e4d435b1f5c0, "Yeah, let's go!" and the run
30220de2-7942-4db5-bb82-9f99b71a615f. All used. v4's shots e1b88c79 (its fox said "break the ice"), a13d3fa0, dd2336d6, fdd4513c are
no longer used.

Batch k5 jobs: shock and slow rise 7c37a49d-aee3-4d11-a0e2-bc8b63dbb8c9, small Pitzi leaping key image 9e3ca1ab-c4ec-48df-8a40-5e5d6f07688a,
Pitzi's leap and line b9285b21-2c2a-42f5-abd2-bfe4f5ca614a, "Yeah, let's go!" and the run 00980a2b-0f5a-4695-b31f-982280cb406b. All used.
v5's 70bf74cf, e3e5f8d1, 91f4e24c and 30220de2 are no longer used. The title fonts (Rubik Bubbles, Rubik Moonrocks) are Google
Fonts under the SIL Open Font License; only rendered pictures of them are in the film.

Batch k6 jobs: laughs and the peek 61679f79-a354-4edb-abce-2831547d829d, shock and rise e0b4570c-6d40-4646-ad80-7edd7efeddd6, Pitzi
leaping key image c70906f9-77f4-4183-9011-a3855d1b53b5, Pitzi's leap and line 525c9966-647b-41e7-8339-a21560ef3c5d (unused:
122e47e5, his face turned into a penguin's), the run e78eef89-88e1-4b0e-ab69-1469ee330bf6. v6's e2d71bef, 7c37a49d, 9e3ca1ab,
b9285b21 and 00980a2b are no longer used.

Batch k7 jobs: b1e4b4c4-8238-4bd1-9f4b-be1a9e838dd5 (used, plain spelling "לניצני אופק"), 720437b1 (nikud, also heard right,
unused), 65fdf0c9 (heard as "הופק", unused). Checked with a local speech-recognition model (faster-whisper medium); a person
still listens.

## Review notes

- No known characters, brands, logos or real people. No pirate or ninja figures (the picker frame's were too close to
  known ones). Nothing religious or national.
- Kids: 4 girls, 4 boys, varied skin tones and hair, drawn as 10 to 11 year olds, no make-up, normal-sized eyes.
- Nothing has writing, letters or digits in it. The speech-bubble stones on the English island are blank on purpose.
- Glow is painted in. Sprites have transparent backgrounds with lossless alpha; faint haze under alpha 14 of 255 was
  removed, and the pale halo around Pitzi's "oops" pose was cut away.
- The open book on the English island backdrop had faint pseudo-writing; its pages were blanked.
- The world map uses the sea from above (`bg/sea`). The picture with a horizon and moon (`bg/world`) is kept for the
  title screen.
