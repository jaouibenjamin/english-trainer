# CLAUDE.md: Word Islands (איי המילים)

Practice games for one 5th-grade class (ה׳1). English (Fantastic 5, Unit 1 "All About Me") and math (fractions).
Built by a parent for his daughter's class, free, no profit. It may later grow to other classes in the grade.
Live: https://jaouibenjamin.github.io/english-trainer/

Read this file and `docs/PLAN.md` before changing anything.

## Who works on this

- **Lead (main session, Fable):** owns the plan, splits the work, reviews every change, talks to the owner (Benji).
- **Subagents** in `.claude/agents/`:
  - `engineer`: code, backend, tests, security and privacy review. Runs before anything ships.
  - `kids-ui-designer`: screens, copy and flow for 10 to 11 year olds, Hebrew RTL, accessibility.
  - `motion-designer`: animation, illustration, sound and voice direction.
- The lead does not ship a change the engineer has not reviewed. The engineer's review always includes a security code review, not only tests (see `.claude/agents/engineer.md`), and the `security` GitHub workflow (secret scan) must be green.

## Hard rules (owner's, do not relax)

- **Free only.** No paid plans, no credit card, never raise a cap. If a free limit is hit, stop and tell the owner.
- **Own accounts only.** Use the owner's own GitHub, Google, Supabase and Higgsfield. Never anything of his client Amit (his paid Base44 workspace is off limits).
- **Kids' privacy.** First name or nickname only. No email, no birth date, no photos of kids. No pupil names, codes, class codes or secrets in this public repo, ever.
- **The teacher's material is the source of truth.** Copy her words and translations exactly. Anything we write ourselves (stories, extra sentences) uses only the unit's vocabulary and is flagged for her review.
- **The goal is improvement, not scores.** Wrong answers never end a session; they explain, and the item comes back.
- No known characters, brands or real people in art or voices. Voices are generated presets, never clones.
- Don't break the live class. The class uses it daily; big changes go behind a flag or run side by side first.

## Stack today

- Static site on GitHub Pages. Vanilla JS ES modules, no build step, relative URLs. Hebrew RTL with LTR English runs.
- Portrait first (390x844, 360x740). Laptops show the portrait board centred.
- Backend: Google Apps Script + Google Sheet (`backend/Code.gs`), URL in `config.js`. Actions register, login, save, board, teacher, reset. Salted SHA-256 PIN, lockouts, roster tab. The whole pupil state is stored as one JSON blob per pupil (`pack()` / `merge()` in `js/state.js`). Being replaced, see `docs/PLAN.md`.
- Pages:
  - `index.html` + `js/main.js`: the island game (English), Fraction Bay (math, `js/math.js`, `mdata.js`, `msling.js`, `mui.js`), and the mock exam (`js/mock.js`, `js/xdata.js`).
  - `run.html` + `js/run.js`: Beach Run, a three.js runner (vendored in `vendor/`). Looks: anime (default) and `?style=lowpoly`. The runner models are Higgsfield GLBs served from the repo (`assets/3d/`, built by `tests/assets_local.py` from `assets/sources.tsv`); the procedural crab Pitzi is the fallback.
  - `trainer.html`: the older quiz trainer.
  - `worksheet.html` + `js/worksheet.js`: a printable worksheet of an island, light paper. Behind a device switch (`?sheet=1` once, `?sheet=0` to remove); off by default.
- Voice: recorded clips (Higgsfield; English via seed_audio, Hebrew narration via ElevenLabs, preset voice Kaia). Never browser speech for content.

## Branches and deploy

- Work on `game`. `main` is what Pages serves.
- Ship: merge `game` into `main`, and keep the real `/exec` URL in `config.js` on `main`. Then wait about a minute for Pages.
- Commit messages end with the session's attribution lines.

## Tests (run before every ship)

```
python3 tests/play.py --quick   # English islands, class login against the mock backend (tests/mock.js)
python3 tests/math.py --quick   # Fraction Bay
python3 tests/mock.py --quick   # mock exam
python3 tests/run.py            # Beach Run, phone and laptop sizes (needs WebGL: swiftshader flags inside); also tests/remote_guard.py (no URL of another host) and tests/credits.py check (assets/CREDITS.md covers every file)
node tests/mdata_check.mjs      # math content
python3 tests/worksheet.py     # the printable worksheet (worksheet.html), switch off and on
```

Playwright with Chrome. Look at the screenshots (`--shots DIR`), don't only trust green.

## Owner

Benji. Busy, often on his phone, dictates by voice (read garbled words in context). Wants the answer first, short, no preamble. Push back when something is a bad idea. Hebrew in the UI; he reads Hebrew, English and French.
