# Word help: what the data can translate

Built by `node tests/help_coverage.mjs --write` from the game's data. Do not edit by hand.

Word help shows only meanings that are already in the game's data. This page lists what is covered and what is not, so
the missing meanings and sentence translations can be asked from the teacher. Nothing here was translated for this page.

- English words on screen in the four island levels and the mock exam: 236 distinct. With a meaning in the data: 204 (86%): 88 from the teacher's word list, 116 from the reading glossary. Without: 32.
- Of those, the words inside sentences and questions (the ones a pupil can tap): 206 distinct. With a meaning: 178 (86%): 65 from the teacher's word list, 113 from the reading glossary. Without: 28.
- English sentences on screen: 191 distinct. With a Hebrew translation in the data: 33. Without: 158.

"The teacher's word list" is her Unit 1 list (`RAW` in `js/data.js`). "The reading glossary" is the list the story
level has always used for a tap on a word (`GL` in `js/data.js`); it was written for the game's own stories, so its
entries are the ones to show the teacher first.

## Words in sentences and questions that have no meaning yet (28)

A tap on these does nothing today.

- `art` (mock exam)
- `ben` (mock exam)
- `books` (mock exam)
- `but` (mock exam)
- `city` (mock exam)
- `class` (mock exam)
- `false` (mock exam)
- `feel` (mock exam)
- `friday` (mock exam)
- `here` (mock exam)
- `i'm` (mock exam)
- `likes` (mock exam)
- `me` (mock exam)
- `morning` (mock exam)
- `or` (mock exam)
- `please` (mock exam)
- `read` (mock exam)
- `reading` (mock exam)
- `rose` (mock exam)
- `sorry` (bridge)
- `street` (mock exam)
- `takes` (mock exam)
- `things` (mock exam)
- `time` (mock exam)
- `tired` (mock exam)
- `too` (mock exam)
- `true` (mock exam)
- `we` (bridge, mock exam)

## Words in sentences and questions whose meaning comes from the reading glossary, not the teacher's list (113)

| Word | Meaning shown | Where |
|---|---|---|
| `a` | (מילת יידוע) | reading, bridge, mock exam |
| `am` | (אני) am | reading, mock exam |
| `and` | ו- | reading, bridge, mock exam |
| `are` | הם / הן (are) | reading, mock exam |
| `at` | ב- | reading, mock exam |
| `ball` | כדור | reading, mock exam |
| `big` | גדול | reading, bridge |
| `birthday` | יום הולדת | reading, mock exam |
| `blue` | כחול | reading, bridge |
| `bus` | אוטובוס | reading, mock exam |
| `buy` | לקנות | reading |
| `buys` | קונה | reading |
| `cake` | עוגה | reading, mock exam |
| `can` | יכולה | reading, mock exam |
| `children` | ילדים | reading |
| `coming` | באה | reading |
| `dad` | אבא | reading |
| `dana` | דנה (שם) | reading, bridge, mock exam |
| `dana's` | דנה (שם) | reading |
| `day` | יום | reading |
| `does` | (מילת שאלה) | reading, mock exam |
| `eat` | לאכול | reading |
| `eggs` | ביצים | reading |
| `english` | אנגלית | reading, mock exam |
| `farm` | חווה | reading |
| `favorite` | אהוב ביותר | reading, mock exam |
| `flowers` | פרחים | reading, bridge, mock exam |
| `football` | כדורגל | reading, bridge, mock exam |
| `friend` | חבר / חברה | reading, bridge, mock exam |
| `friends` | חברים | reading, mock exam |
| `from` | מ- | reading, bridge, mock exam |
| `games` | משחקים | reading |
| `get` | להשיג, לקבל | reading |
| `gives` | נותנת | reading |
| `go` | ללכת, לנסוע | reading, mock exam |
| `goes` | הולכת | reading |
| `grandma` | סבתא | reading, bridge, mock exam |
| `grandma's` | סבתא | reading |
| `happy` | שמח | reading, mock exam |
| `has` | יש לו / לה | reading |
| `have` | יש לי | reading |
| `he` | הוא | reading, bridge, mock exam |
| `hi` | היי | reading |
| `him` | לו | reading |
| `hobbies` | תחביבים | reading |
| `home` | בית | reading |
| `how` | איך / כמה | reading, mock exam |
| `how many` | כמה | reading |
| `i` | אני | reading, bridge, mock exam |
| `in` | ב- | reading, bridge, mock exam |
| `is` | הוא / היא (is) | reading, mock exam |
| `it` | זה | bridge, mock exam |
| `it's` | זה | mock exam |
| `late` | מאחרת | reading |
| `lia` | ליה (שם) | reading, mock exam |
| `live` | לגור | reading |
| `lives` | גרה | reading |
| `living room` | סלון | reading |
| `makes` | מכין | reading |
| `man` | איש | reading |
| `maya` | מאיה (שם) | reading, mock exam |
| `maya's` | מאיה (שם) | reading, mock exam |
| `mother` | אמא | reading |
| `music` | מוזיקה | reading, mock exam |
| `my` | שלי | reading, bridge, mock exam |
| `name` | שם | reading |
| `new` | חדש | reading, bridge, mock exam |
| `noa` | נועה (שם) | reading, bridge, mock exam |
| `not` | לא | reading |
| `o'clock` | בשעה | reading, mock exam |
| `of` | של | reading, mock exam |
| `old` | ישן, בן כמה | reading |
| `on` | על, ב- | reading, mock exam |
| `one` | אחת | reading |
| `party` | מסיבה | reading |
| `plays` | מנגנת / משחקת | reading, mock exam |
| `red` | אדום | reading |
| `room` | חדר | reading |
| `say` | לומר | reading |
| `says` | אומרת | reading |
| `school` | בית ספר | reading, mock exam |
| `sea` | ים | reading |
| `see` | לראות | reading |
| `sells` | מוכר | reading |
| `she` | היא | reading, bridge, mock exam |
| `sings` | שרה | reading |
| `small` | קטן | reading |
| `some` | כמה, חלק | reading |
| `story` | סיפור | reading |
| `students` | תלמידים | reading, bridge, mock exam |
| `sugar` | סוכר | reading |
| `teacher` | מורה | reading, mock exam |
| `teaches` | מלמדת | reading |
| `ten` | עשר | reading, bridge, mock exam |
| `the` | ה- | reading, bridge, mock exam |
| `there` | שם / יש | reading, mock exam |
| `they` | הם | reading, bridge, mock exam |
| `this` | זה | reading |
| `to` | אל, ל- | reading, mock exam |
| `today` | היום | reading, mock exam |
| `tom` | תום (שם) | mock exam |
| `tom's` | תום (שם) | reading |
| `very` | מאוד | reading |
| `what` | מה | reading, mock exam |
| `when` | מתי | reading, mock exam |
| `where` | איפה | reading, mock exam |
| `who` | מי | reading, mock exam |
| `why` | למה | reading |
| `with` | עם | reading |
| `year` | שנה | reading |
| `years old` | בן / בת (גיל) | reading, bridge, mock exam |
| `you` | אתה / את | reading, bridge, mock exam |
| `your` | שלך | reading |

## Words that appear only on answer buttons and have no meaning (4)

Answer buttons are never help words, so nothing is missing on screen; listed for completeness.

`aren't`, `isn't`, `sad`, `sunday`

## Sentences that have a Hebrew translation in the data (33)

| Sentence | Hebrew in the data | Where |
|---|---|---|
| Everyone is ready. | כולם מוכנים. | bridge: build |
| Her sofa is blue. | הספה שלה כחולה. | bridge: build |
| I also play football. | אני גם משחק/ת כדורגל. | bridge: build |
| I am from Israel. | אני מישראל. | reading story, bridge: build, bridge: am / is / are, mock exam |
| I am ten years old. | אני בן / בת עשר. | reading story |
| I hear a song. | אני שומע/ת שיר. | bridge: build |
| I kick the ball. | אני בועט/ת בכדור. | bridge: build |
| I play the guitar. | אני מנגן/ת בגיטרה. | bridge: build, mock exam |
| I play the piano. | אני מנגן/ת בפסנתר. | bridge: build, mock exam |
| I study every day. | אני לומד/ת כל יום. | bridge: build |
| I throw the ball. | אני זורק/ת את הכדור. | bridge: build |
| My birthday is in July. | יום ההולדת שלי ביולי. | bridge: build |
| My favorite subject is English. | המקצוע האהוב עליי הוא אנגלית. | mock exam |
| My hobby is music. | התחביב שלי הוא מוזיקה. | bridge: build |
| She is a student. | היא תלמידה. | bridge: build, bridge: am / is / are, mock exam |
| She is coming soon. | היא באה בקרוב. | bridge: build |
| The building is big. | הבניין גדול. | bridge: build |
| The candy is sweet. | הממתק מתוק. | bridge: build, bridge: am / is / are |
| The card is for you. | הכרטיס בשבילך. | bridge: build |
| The flat is in a big building. | הדירה נמצאת בבניין גדול. | reading story |
| The flat is new. | הדירה חדשה. | bridge: build |
| The flowers are pretty. | הפרחים יפים. | bridge: build, mock exam |
| The goal is far. | השער רחוק. | bridge: build, bridge: am / is / are |
| The market is far. | השוק רחוק. | bridge: build, mock exam |
| The trip is special. | הטיול מיוחד. | bridge: build |
| The village is pretty. | הכפר יפה. | bridge: build, bridge: am / is / are, mock exam |
| Their classroom is big. | הכיתה שלהם גדולה. | reading story, bridge: build, bridge: am / is / are |
| They give me candy. | הם נותנים לי ממתק. | bridge: build |
| This is a present. | זאת מתנה. | bridge: build |
| We are in the classroom. | אנחנו בכיתה. | bridge: build |
| We are outside. | אנחנו בחוץ. | bridge: build, mock exam |
| We are the same age. | אנחנו באותו הגיל. | bridge: build |
| We wait for the bus. | אנחנו מחכים לאוטובוס. | bridge: build |

The button "the sentence in Hebrew" is offered for these only where showing it does not give the answer away: in the
mock exam's practice, for a complete sentence or one whose gap is am / is / are. In the bridge level the Hebrew of a
build sentence is already the question itself.

## Sentences without a Hebrew translation (158)

- "I'm sorry, Grandma," she says. (reading story)
- "This is a special thing," says Grandma. (reading story)
- A man sells pretty flowers there. (reading story)
- Are the flowers pretty? (mock exam)
- Are they flowers? (mock exam)
- Are they friends? (mock exam)
- Are they on a trip? (mock exam)
- Are they outside? (mock exam)
- Are you ready? (mock exam)
- At one o'clock they eat in the dining room. (reading story)
- At the end of the day, Lia is late. (reading story)
- At the end of the trip, the students are tired but happy. (mock exam)
- Ben plays the piano. (mock exam)
- Dana and Noa are the same age. (bridge: am / is / are, mock exam)
- Dana has a new flat. (reading story)
- Dana is eleven. (reading story)
- Dana plays the guitar in her room. (reading story)
- Dana's mother is a teacher. (reading story)
- Date: ___ (mock exam)
- Every Friday, her teacher takes the class outside. (mock exam)
- Every day the students study English and music. (reading story)
- Every year the students go on a trip. (reading story)
- Everyone is ready for the party. (reading story)
- From: Lia (mock exam)
- Grandma can hear the song. (reading story)
- Happy birthday! Here is a present for you. (mock exam)
- He has flour, eggs and sugar. (reading story)
- He is ten years old. (bridge: am / is / are, mock exam)
- Her favorite subject is art. (mock exam)
- Her flat is new. (bridge: am / is / are, mock exam)
- Her friend Noa is the same age. (reading story)
- How do the students feel at the end? (mock exam)
- How many students are in the school? (reading question)
- How old is Maya? (reading question)
- How old is Noa? (reading question)
- I also play the piano. (reading story)
- I am eleven years old. (mock exam)
- I am eleven. (bridge: am / is / are)
- I am fourteen years old. (mock exam)
- I am fourteen. (mock exam)
- I am outside. (bridge: am / is / are)
- I am sorry. (bridge: am / is / are)
- I am thirteen years old. (mock exam)
- I am thirteen. (mock exam)
- I can kick the ball. (mock exam)
- I have a lot of hobbies. (reading story)
- I kick the ball and I get a goal! (reading story)
- I like books. (mock exam)
- I like football. (mock exam)
- I like music. (mock exam)
- I like to play the piano. (mock exam)
- I like to read. (mock exam)
- I play football with my friends. (reading story)
- I study English at school. (mock exam)
- I wait for the bus every morning. (mock exam)
- Is Maya a teacher? (mock exam)
- Is her school far from her home? (reading question)
- Is it a building? (mock exam)
- Is it a cake? (mock exam)
- Is it a classroom? (mock exam)
- Is it a dining room? (mock exam)
- Is it a piano? (mock exam)
- Is it a present? (mock exam)
- Is it a sofa? (mock exam)
- Is it a village? (mock exam)
- Is she a student? (mock exam)
- Is the candy sweet? (mock exam)
- Is the market far? (mock exam)
- Is the village far? (mock exam)
- Is your flat big? (mock exam)
- It is a special present. (bridge: am / is / are, mock exam)
- It's my birthday! I'm ___ years old. (mock exam)
- Lia buys red flowers and a card for her grandma. (reading story)
- Lia goes to the market. (reading story)
- Lia lives in a small village. (reading story)
- Maya can hear music, too. (mock exam)
- Maya is a student. (mock exam)
- Maya is a student. Her favorite subject is art. (mock exam)
- Maya's favorite subject is art. (mock exam)
- Music is my favorite hobby. (mock exam)
- My birthday is in August. (mock exam)
- My birthday is in June. (mock exam)
- My birthday is in May. (mock exam)
- My favorite song is "Happy Birthday". (reading story)
- My favorite subject at school is English. (reading story)
- My hobby is football. (bridge: am / is / are, mock exam)
- My name is Maya. (reading story)
- My school is not far from my home. (reading story)
- Noa is coming soon to see the new flat. (reading story)
- Noa likes to read. (mock exam)
- Noa plays the guitar like Dana. (reading story)
- Please throw me the ball. (mock exam)
- She gives Grandma the flowers and the card. (reading story)
- She is happy. (reading story)
- She teaches music. (reading story)
- Some students go to the sea. (reading story)
- The cake is very sweet. (reading story)
- The date is July 15. (reading story)
- The flowers are a present. (reading story)
- The flowers are for Grandma. (bridge: am / is / are)
- The other students wait for the bus and go to a farm. (reading story)
- The sofa is blue. (bridge: am / is / are)
- The students are in the classroom. (mock exam)
- The students are outside. (bridge: am / is / are)
- The village is far from the city. (mock exam)
- Then Lia sings a song. (reading story)
- Then the children go outside. (reading story)
- There are a lot of pretty things at the market. (mock exam)
- There are forty students in the school. (reading story)
- There are twenty students in my classroom. (mock exam)
- There is a blue sofa in the living room. (reading story)
- There is a small bathroom and a toilet. (reading story)
- They are ready. (bridge: am / is / are, mock exam)
- They throw a ball and play games. (reading story)
- This is a story about a special school. (reading story)
- Time: ___ o'clock (mock exam)
- Today is her grandma's birthday. (reading story)
- Today they are on a special trip to a market. (mock exam)
- Tom is thirteen years old. (mock exam)
- Tom's birthday is in July. (reading story)
- Tom's dad makes a cake. (reading story)
- Tom's friends give him candy. (reading story)
- True or False: Maya can hear music. (mock exam)
- True or False: The trip is to a village. (mock exam)
- We are in the dining room. (bridge: am / is / are)
- We are ready. (bridge: am / is / are)
- We give Grandma a present. (mock exam)
- What do Tom's friends give him? (reading question)
- What do the students do every year? (reading question)
- What do the students study every day? (reading question)
- What do you do on your birthday? (reading story)
- What does Dana's mother teach? (reading question)
- What does Lia buy? (reading question)
- What does Maya play? (reading question)
- What is at the market? (mock exam)
- What is her favorite subject? (reading question)
- What is in the living room? (reading question)
- When does the class go outside? Every Friday. (mock exam)
- When is Tom's birthday? (reading question)
- Where are they today? (mock exam)
- Where do the children play games? (reading question)
- Where do the students eat? (reading question)
- Where does Lia go? (reading question)
- Where does Lia live? (reading question)
- Where is Maya from? (reading question)
- Where is the flat? (reading question)
- Where: ___ (mock exam)
- Who makes the cake? (reading question)
- Who plays the guitar? (reading question)
- Who takes the class outside? (mock exam)
- Why does Lia say "I'm sorry"? (reading question)
- You are my friend. (bridge: am / is / are, mock exam)
- give a present (mock exam)
- kick a ball (mock exam)
- play the piano (mock exam)
- study English (mock exam)
- throw a ball (mock exam)
- wait for a friend (mock exam)
