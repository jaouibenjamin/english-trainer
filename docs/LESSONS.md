# Lessons: read before writing or reviewing code

Each entry is a bug class that cost us more than one review round. An engineer reads this before starting; a reviewer checks the change against it. When a review finds a new class (not just a new instance), add an entry in the same PR that fixes it.

## 1. An await that outlives the pupil (PRs #21, #39, #41, #50; gate 5)

- **What happened:** on a shared device, pupil A's request was still in flight when A logged out and B signed in. When it came back, the code went on as if nothing had changed: it sent A's data with B's token, wrote A's state as B's base, or stored A's session again. Three rounds each closed one await and the review found the next. Gate 4 bound every operation to the session (`op()`: generation and session id); the review of #50 still found three paths, because the data was not bound to the pupil: the Sheet's late answer still carried A's request (with A's code), the in-memory queue was handed to whatever session was current when a timer or a page listener fired in another tab, and "no session yet" is the same for every pupil.
- **Rule:** after every `await`, and in every timer and event listener, the world may have changed. Bind the operation to the session **and the data to the pupil**: anything that reads "who is signed in" (token, session, owner, base, queue) captures an identity before the await and checks it after, before any write or send; anything held for later (a queued state, a waiting request, a record of what was sent) carries its owner and is used only for that owner. An empty identity ("no session") is not an identity: check the owner too.
- **How to build it:** one guard that every storage write and every tokened call goes through. Do not patch call sites one by one. In the PR, list every `await` in the file and which guard covers it, **and every timer, listener and callback that re-dispatches work** (they run with whatever is current when they fire).
- **How to test it:** hold a response, switch pupil, release the response. Hold the answer of the request that starts the work too (here the Sheet's), not only the later ones. Also: a second tab on the same storage, with its timers and page listeners firing after the other tab changed pupil; two tabs signing in at the same time; logout right after the last answer; a response that arrives after logout.
- **In memory too:** a logout must clear everything held in variables (a queued save, a code waiting for a retry), not only what is in storage; and what must survive a closed tab (what was already sent) must be in storage, not in a variable, written **when it happens** (the save is sent), not when its answer comes: a page that closes never sees the answer (review of #55, G2).

## 2. A test that passes because it waits

- **What happened:** the "logout copies first" test passed with a 5 ms pause between saves; the real game flow copied 0 of 8 answers.
- **Rule:** test through the real entry point (`state.js`'s `logout()`, the real screen), with the timings a child produces: taps 200 to 500 ms apart, logout straight after the last answer.

## 3. The tests do not reach what the live class uses

- **What happened:** suites run against `tests/mock.js` on localhost. The real backend is another host with a redirect, and a real phone has a slow network.
- **Rule:** for any change that is not behind a flag, say in the PR what the tests cannot prove and what must be checked by hand on a real phone after deploy.

## 4. "Flag off is identical" is a claim to prove

- **Rule:** run the same scripted session on `game` and on the branch and compare every request (URL, method, body, order) and every storage key. This has caught a real difference more than once (#47: a route that fell through to the wrong screen).

## 5. Suites that share a port or a checkout lie

- **What happened:** two suites run in parallel tested each other's checkout (#20).
- **Rule:** free ports only, paths relative to the suite's own checkout, run through `tests/all.py`.

## 6. A pupil's data must not reach a log

- **What happened:** an import tool leaked pupil rows (names, salts, code hashes) into the database server log, first through the logged statement on an error, then through COPY's CONTEXT line on a bad row; it also printed names to stdout (#27: B3, B3-bis, S-f).
- **Rule:** logs carry counts and kinds only. Check every `print`, `console.log` and error message on a path that handles a pupil row, and also what the database logs on its own: statements logged on error, COPY CONTEXT, "Failing row contains". Test with strict log settings and a malformed row.

## 7. Crossed messages cause duplicate work

- **What happened:** two sessions fixed the same thing (#34 and #36).
- **Rule:** before starting, list the open PRs and the files they touch; stay inside the scope the lead gave; say which files you touched when you report.

## 8. Switches that are fine alone and broken together (#28)

- **What happened:** with the new look plus `?games=1` the text was white on cream (1.04:1). Later the same thing on the teacher screen's toast (#43), which sat outside the element the test scanned.
- **Rule:** test a flag-on screen together with the other switches (games, sheet, help, card). Check contrast and 48 px targets on each combination, and scan the whole page, including toasts and overlays, not only the screen's own container.

## 9. Free-plan pacing, and a refusal that skips the next step (#21)

- **What happened:** saves went out every 4 s, half were refused `wait`, and an early `return` after `wait` or `daycap` skipped `record_events`, so a day's events were lost.
- **Rule:** count the calls a child produces in 2 minutes and in 2 hours against the free caps. Check that a refusal never skips the work that comes after it.

## 10. Exports, backups and probes hold only what is needed (#27)

- **What happened:** the backup included address salts, typed names and old hashes, and the live check could have created users.
- **Rule:** every export has an explicit, tested exclusion list. A check against the live backend never writes.

## 11. A difference of merged records counts someone else's work (gate 4, S3)

- **What happened:** the adapter derives events from the difference between the last record it copied and the next one. On a second device, the game joins the other device's record into its own at sign-in, so the next difference held the other device's answers too, and they were counted twice. Lifting the base to the whole joined record would have been wrong too: it also held this device's own answers that were not copied yet, which would then never be counted.
- **Rule:** when a count is derived from a record that is merged from several sources, subtract what the other sources brought (what the merged record holds beyond what this source itself sent), not the merged record. A base never goes down.
- **How to test it:** two devices on two storages, one pupil: play on one, sign in on the other, play there. Also a pull that arrives while this device still holds answers it has not sent. Total counted = answers actually played.

## 12. An object you were handed is not yours: copy it before you keep it (review of #55, G1)

- **What happened:** the adapter kept the Sheet's answer to use later as a pupil's starting point. The game kept the same object as its own state (`S.st` is the answer's `s.st`) and added the pupil's new answers to it. When the delayed copy finally stored it, the new answers were already inside, so they were never counted (A→B→A: 0 of 2).
- **Rule:** anything kept past the current synchronous step (a request, an answer, a record handed in or out) is copied at the moment it is taken: `JSON.parse(JSON.stringify(x))`, or `structuredClone`. That applies both ways: what you hand back (the game's own object stays the game's) and what you were given (a caller may keep editing it).
- **How to test it:** take the object the call returned and change it in place right after the call, before any background work runs; then check that what was stored or counted is what was sent or answered, not the edited object.

## 13. An audio filter that resamples and lifts the pauses (welcome film, #58)

- **What happened:** the welcome film's voice crackled and hissed on the owner's phone. The `loudnorm` filter outputs 192 kHz; nothing resampled it, so the AAC came out at 96 kHz and only 48 kbps. Its dynamic mode also raised the quiet pauses, so the room noise of the take sat under the whole film. The numbers looked fine (duration, pauses counted); nobody listened before it was sent.
- **Rule:** after every audio step, check the output's sample rate and codec, and measure the noise floor in the pauses (silencedetect, astats). Encode once at 44.1 or 48 kHz with a fixed bitrate; use a plain linear gain, not a dynamic loudness filter, on speech. A person listens before it ships.
- **How to test it:** `ffprobe` shows 44100 or 48000 Hz; silencedetect at -45 dB finds every pause; the pauses' RMS is far below the voice.
