# English Trainer

Practice app for a 5th-grade English exam (Fantastic 5, Unit 1 "All About Me"): flashcards, translation quiz, listening, reading, sentence writing, a class game, a class leaderboard and a teacher screen.

- `index.html` is the whole app. `config.js` holds the backend URL.
- `backend/Code.gs` is a Google Apps Script that stores names, salted PIN hashes and scores in a Google Sheet.
- No pupil data is stored in this repository.

## Connect the class (one time, about 10 minutes)

1. Create a new Google Sheet in your own Google account.
2. In the Sheet: **Extensions > Apps Script**. Delete the sample code, paste all of `backend/Code.gs`, save.
3. In the script editor choose the function `setup` and press **Run**. Approve the permission prompt. The Sheet now has two tabs: `config` (class code and teacher code, editable) and `kids`.
4. **Deploy > New deployment > Web app**. Execute as: **Me**. Who has access: **Anyone**. Deploy and copy the web-app URL (it ends in `/exec`).
5. Put that URL in `config.js` between the quotes and commit.

With `config.js` empty the app still works, without login, and progress stays on each device.

## For the teacher

- Pupils open the site, type the class code, their first name and a 4-digit code they choose. No email.
- The teacher screen is at the bottom of the home page ("כניסת מורה") and needs the teacher code from the `config` tab.
- To reset a pupil's forgotten code, delete their row in the `kids` tab; they register again.
