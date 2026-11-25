# Printable worksheet (behind a switch, off by default)

`worksheet.html?i=<island>` draws one island as a worksheet on light paper: match the words to their meanings, the
story with its questions, am / is / are, and sentences to put in order. An answer page can be added. It holds only
what is in `js/data.js`, shows nothing of the pupil (the name line is filled in by hand), saves nothing and sends
nothing. A device gets the switch by opening the game once with `?sheet=1` (`?sheet=0` takes it away); the island
screen then shows a link to its sheet. `python3 tests/worksheet.py` checks the content against `js/data.js`, the
answers, the printed pages and the privacy of the page.
