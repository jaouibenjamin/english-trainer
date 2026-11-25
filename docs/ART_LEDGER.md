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
| j | Welcome film: 3 animated shots (5 s, 5 s, 2 s) and the Hebrew narration (preset voice Kaia); shots 1, 4, 6 cut here from our pictures | grok_video 720p (7.5 + 7.5 + 3); text2speech_v2 elevenlabs (0.75); running total counts batch i of PR #56 | 4 | 23.25 | 23.25 | 142.08 | 307.92 |
| j2 | Welcome film: new narration with the platform's new name (preset voice Kaia, nikud on two words) | text2speech_v2 elevenlabs | 1 | 0.75 | 0.75 | 151.83 | 298.17 |

Total charged so far: **151.83** of 450 (with batches i and i2 of PR #56). Left: 298.17.

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

Batches b to e: every job is used, except the first "listen" pose named above; the ids are in `assets/al/sources.tsv` (Pitzi's wave pose,
c2effc24-9597-44ee-9eb7-204c981203c3, was the reference for the other five poses).

Style references (approved frames, made before this ledger, not counted in the cap): world map
339d6b72-d680-4b39-86de-d4927d9cb120, island path 16f37d15-7965-43c3-9666-fb1ee2c49611, avatar picker
b1f0d687-5d18-4811-af95-f2aca8285246, first frame 34b3388f-09b1-4b65-93c7-8b0579be81a4.

Batch j jobs: shot 2 7621ea4f-5457-4816-a8dd-cd722b9e9af3, shot 3 970ab3ba-1efa-4c15-af1b-be2b890a8e29 (start frame: our sea picture, uploaded),
shot 5 d3df4296-1b5f-42b1-9c97-c8a8d09bb4dc, narration b87a763d-1a3c-481d-852e-87d9a69afa0f (replaced). Batch j2: narration 1ec486fb-379a-4ec2-9613-83ddce779343.

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
