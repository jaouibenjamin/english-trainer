# Progress card (behind a switch, off by default)

`js/card.js` adds a screen, "הכרטיס שלי", that a pupil can show: stars by island, words learned, stories read and
today's date, and a button that saves the same card as a picture (and a share button where the device can share a
file). The only personal detail is the first name of a pupil who is signed in to the class; without a sign-in there
is no name. The picture is drawn on the device; the game sends it nowhere and saves nothing new. A device gets the
switch by opening the game once with `?card=1` (`?card=0` takes it away); settings then has a row for it.
`python3 tests/card.py` checks the numbers, the picture, the screens at four sizes and that nothing is sent or saved.
