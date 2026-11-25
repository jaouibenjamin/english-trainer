# Mock exam results on the teacher screen (behind a switch; needs a backend deploy)

The pupil's saved record already holds the mock exam papers. `teacherView` in `backend/Code.gs` now also returns, for
each pupil, how many papers were taken (of the last 20 the device keeps), the oldest and the last total among them,
and the last paper by skill (`mockOf`). It only reads; nothing new is saved and the sheet is not written. What a pupil
typed in the exam is not sent to the screen. A pupil's record is written by their own browser, so every value is read
as a plain number and clamped (`nv()`), and a damaged record gives nothing rather than an error. The same `nv()` now
also guards the word and star counts the teacher view already read: before, one crafted record could make the whole
teacher screen fail. The scores themselves come from the pupil's browser and could be made up.

**The owner has to deploy a new version of the Apps Script for this to reach the class.** Until then the backend
sends no such field, and the teacher screen is drawn as before. Do not ship this part to `main` as "done" before the
deploy.

The rows on the pupil cards are behind a switch on the teacher's device: open the game once with `?tmock=1`
(`?tmock=0` takes it away). `node tests/mock.js unit` checks the backend part; `python3 tests/teacher_mock.py` checks
the screen, an older backend, rubbish from a backend and that looking changes nothing.
