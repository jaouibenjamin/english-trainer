# Art ledger: Arcade Lagoon

Owner's cap for all art and sound of the new look: **450 credits**, stop and report at 400. Tool: the owner's own
Higgsfield account, existing credits only. Every batch is quoted with the estimate tool first; "charged" is the change in
the account balance after the batch. Files and their job ids: `assets/al/sources.tsv`.

| Batch | What | Model, settings | Jobs | Quoted | Charged | Running total | Left of 450 |
|---|---|---|---|---|---|---|---|
| a | 20 character portraits (8 animals, 4 robots / helmets, 4 girls, 4 boys) + 2 redos | gpt_image_2_5, medium, 1k, 1:1, style reference: the approved picker frame | 22 | 11.00 | 11.00 | 11.00 | 439.00 |
| b | Pitzi in the new look, 6 poses (wave, happy, listen, oops, star, walk) | gpt_image_2_5, medium, 1k, 1:1, transparent | 6 | 3.00 | 3.00 | 14.00 | 436.00 |
| c | World map background (no islands), 2 subject islands, 3 "not open yet" islands | background: high, 9:16; islands: medium, 1:1, transparent | 6 | 3.75 | 3.75 | 17.75 | 432.25 |
| d | Island path backdrops, English and maths | gpt_image_2_5, high, 1k, 9:16 | 2 | 2.50 | 2.50 | 20.25 | 429.75 |
| e | Mission stones (done, current, locked), HUD icons (star, bolt, lock, focus, gear, sound on / off) | gpt_image_2_5, medium, 1k, 1:1, transparent | 9 | 4.50 | 4.50 | 24.75 | 425.25 |
| f | Sound: not generated. Quote: 30 s island theme 4.36 each (elevenlabs_music_v2_5), 3 s signature sound 0.44 each | | 0 | | 0 | 24.75 | 425.25 |

Balance before batch a: 2294.74. After batch e: 2269.99. Difference: 24.75.

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
| robot, lantern (redo) | fb75c13b-cd6a-4301-8a9b-a58550679386 | yes |
| octopus (redo) | b1c753c1-abca-4c2e-9a73-d209ae4faad3 | yes |

Batches b to e: every job is used; the ids are in `assets/al/sources.tsv` (Pitzi's wave pose,
c2effc24-9597-44ee-9eb7-204c981203c3, was the reference for the other five poses).

Style references (approved frames, made before this ledger, not counted in the cap): world map
339d6b72-d680-4b39-86de-d4927d9cb120, island path 16f37d15-7965-43c3-9666-fb1ee2c49611, avatar picker
b1f0d687-5d18-4811-af95-f2aca8285246, first frame 34b3388f-09b1-4b65-93c7-8b0579be81a4.

## Review notes

- No known characters, brands, logos or real people. No pirate or ninja figures (the picker frame's were too close to
  known ones). Nothing religious or national.
- Kids: 4 girls, 4 boys, varied skin tones and hair, drawn as 10 to 11 year olds, no make-up, normal-sized eyes.
- Nothing has writing, letters or digits in it. The speech-bubble stones on the English island are blank on purpose.
- Glow is painted in. Sprites have transparent backgrounds; faint haze under alpha 14 of 255 was removed.
- Open point for the owner: the world map background has a horizon, a moon and a distant storm at the top, like the
  approved first frame; the islands are drawn from above.
