# Lessons: read before writing or reviewing code

Each entry is a bug class that cost us more than one review round. An engineer reads this before starting; a reviewer checks the change against it. When a review finds a new class (not just a new instance), add an entry in the same PR that fixes it.

## 1. An await that outlives the pupil (gates 2, 3, 4; PRs #39, #41)

- **What happened:** on a shared device, pupil A's request was still in flight when A logged out and B signed in. When it came back, the code went on as if nothing had changed: it sent A's data with B's token, wrote A's state as B's base, or stored A's session again. Three rounds each closed one await and the review found the next.
- **Rule:** after every `await`, the world may have changed. Anything that reads "who is signed in" (token, session, owner, base, queue) must capture an identity before the await and check it after, before any write or send.
- **How to build it:** one guard that every storage write and every tokened call goes through. Do not patch call sites one by one. In the PR, list every `await` in the file and which guard covers it.
- **How to test it:** hold a response, switch pupil, release the response. Also: a second tab on the same storage; logout right after the last answer; a response that arrives after logout.
- **In memory too:** a logout must clear everything held in variables (a queued save, a code waiting for a retry), not only what is in storage.

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

- **What happened:** an import tool printed refused rows, with names, to the server log (#27, twice).
- **Rule:** logs carry counts and kinds only. Check every `print`, `console.log` and error message on a path that handles a row about a pupil.

## 7. Crossed messages cause duplicate work

- **What happened:** two sessions fixed the same thing (#34 and #36).
- **Rule:** before starting, list the open PRs and the files they touch; stay inside the scope the lead gave; say which files you touched when you report.
