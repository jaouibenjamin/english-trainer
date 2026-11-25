# Extra practice games (behind a switch, off by default)

`js/extra.js` lists extra games over the same words as the islands; an island shows one button for each. They are
practice only: no stars, no points, nothing added to the saved progress, nothing sent. A wrong answer explains and
the word comes back. A device gets the switch by opening the game once with `?games=1` (`?games=0` takes it away).

- **נכון או לא?** (`js/tf.js`): a card shows an English word and a Hebrew meaning from the teacher's list; the pupil
  says whether they belong together, by swiping the card, by two buttons or by the arrow keys.
- **זוגות** (`js/pairs.js`): twelve cards face down, six English words of the island and their six meanings from the
  teacher's list. A word and its own meaning stay open; two that do not belong together are shown for a moment, each
  with its own pair written under the board, and turn back. A closed card holds nothing to read.
- **אותיות** (`js/scramble.js`): the Hebrew meaning is shown and the English word is heard; its letters lie mixed
  up as tiles (lower case, since a capital I and a small l look alike in the game's font). The pupil taps them in
  order, or types them. A wrong letter is not placed and the line under the word says so; after two in a row the
  right tile glows. A word with a wrong letter comes back once later in the round.

`python3 tests/extra.py` plays it at phone and laptop sizes and for a signed-in pupil, and checks the cards against
the word list, the three ways to answer, the voice, the layout and that nothing is saved or sent.
