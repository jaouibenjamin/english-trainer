# Word help: what the data can translate

Built by `node tests/help_coverage.mjs --write` from the game's data. Do not edit by hand.

Word help shows only meanings that are already in the game's data. This page lists what is covered and what is not, so
the missing meanings and sentence translations can be asked from the teacher. Nothing here was translated for this page.

- English words on screen in the four island levels and the mock exam: 236 distinct. In the teacher's word list: 88. Only in the reading glossary, not shown (GLOSSARY is off until the teacher has gone over it): 116. In neither: 32.
- Of those, the words inside sentences and questions (the ones a pupil could tap): 206 distinct. In the teacher's word list, so they can be tapped today: 65. Only in the reading glossary, not shown (GLOSSARY is off until the teacher has gone over it): 113. In neither: 28.
- English sentences on screen: 191 distinct. With a Hebrew translation in the data: 33. Without: 158.

"The teacher's word list" is her Unit 1 list (`RAW` in `js/data.js`). "The reading glossary" is the list the story
level has always used for a tap on a word (`GL` in `js/data.js`). It was written for the game's own stories, and some
of its meanings are wrong outside them (for example "a", "is", "plays", "can", "old"). So word help does not use it:
`GLOSSARY` in `js/helpdata.js` is false. The table below is for the teacher: every glossary entry that word help
would show, with the sentences it would appear in. An entry she approves as it is can be switched on; one she corrects
goes into the data with her wording.

## Words in sentences and questions that have no meaning yet (28)

These are in neither list. They are not help words.

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

## Reading glossary entries, for the teacher to go over (113)

Not shown today. Each row: the word, the meaning the glossary holds, and up to four of the sentences and lines it would appear in.

| Word | Glossary meaning | Would appear in |
|---|---|---|
| `a` | (מילת יידוע) | I kick the ball and I get a goal! · A Special School · This is a story about a special school. · Every year the students go on a trip. · and 34 more |
| `am` | (אני) am | I am ten years old. · I am from Israel. · I am thirteen years old. · I am fourteen years old. · and 3 more |
| `and` | ו- | I kick the ball and I get a goal! · Every day the students study English and music. · The other students wait for the bus and go to a farm. · There is a small bathroom and a toilet. · and 5 more |
| `are` | הם / הן (are) | There are forty students in the school. · How many students are in the school? · The flowers are a present. · There are twenty students in my . · and 9 more |
| `at` | ב- | My favorite subject at school is English. · At one o'clock they eat in the dining room. · At the end of the day, Lia is late. · I English at school. · and 4 more |
| `ball` | כדור | I kick the ball and I get a goal! · They throw a ball and play games. · I can the ball. · Please me the ball. |
| `big` | גדול | Their classroom is big. · The flat is in a big building. · Their classroom big. |
| `birthday` | יום הולדת | My favorite song is "Happy Birthday". · A Birthday Party · Tom's birthday is in July. · What do you do on your birthday? · and 8 more |
| `blue` | כחול | There is a blue sofa in the living room. · The sofa blue. |
| `bus` | אוטובוס | The other students wait for the bus and go to a farm. · I for the bus every morning. |
| `buy` | לקנות | What does Lia buy? |
| `buys` | קונה | Lia buys red flowers and a card for her grandma. |
| `cake` | עוגה | Tom's dad makes a cake. · The cake is very sweet. · Who makes the cake? · Is it a cake? |
| `can` | יכולה | Grandma can hear the song. · I can the ball. · True or False: Maya can hear music. · Maya can hear music, too. |
| `children` | ילדים | Then the children go outside. · Where do the children play games? |
| `coming` | באה | Noa is coming soon to see the new flat. |
| `dad` | אבא | Tom's dad makes a cake. |
| `dana` | דנה (שם) | Dana is eleven. · Dana has a new flat. · Dana plays the guitar in her room. · Noa plays the guitar like Dana. · and 1 more |
| `dana's` | דנה (שם) | Dana's New Home · Dana's mother is a teacher. · What does Dana's mother teach? |
| `day` | יום | Every day the students study English and music. · What do the students study every day? · At the end of the day, Lia is late. |
| `does` | (מילת שאלה) | What does Maya play? · What does Dana's mother teach? · Where does Lia live? · Where does Lia go? · and 3 more |
| `eat` | לאכול | At one o'clock they eat in the dining room. · Where do the students eat? |
| `eggs` | ביצים | He has flour, eggs and sugar. |
| `english` | אנגלית | My favorite subject at school is English. · Every day the students study English and music. · I English at school. · My favorite is English. |
| `farm` | חווה | The other students wait for the bus and go to a farm. |
| `favorite` | אהוב ביותר | My favorite song is "Happy Birthday". · My favorite subject at school is English. · What is her favorite subject? · Music is my favorite . · and 4 more |
| `flowers` | פרחים | A man sells pretty flowers there. · Lia buys red flowers and a card for her grandma. · The flowers are a present. · She gives Grandma the flowers and the card. · and 4 more |
| `football` | כדורגל | I play football with my friends. · My hobby football. · I like football. · football |
| `friend` | חבר / חברה | Her friend Noa is the same age. · You my friend. |
| `friends` | חברים | I play football with my friends. · Tom's friends give him candy. · What do Tom's friends give him? · Are they friends? |
| `from` | מ- | I am from Israel. · My school is not far from my home. · Where is Maya from? · Is her school far from her home? · and 4 more |
| `games` | משחקים | They throw a ball and play games. · Where do the children play games? |
| `get` | להשיג, לקבל | I kick the ball and I get a goal! |
| `gives` | נותנת | She gives Grandma the flowers and the card. |
| `go` | ללכת, לנסוע | Every year the students go on a trip. · Some students go to the sea. · The other students wait for the bus and go to a farm. · Then the children go outside. · and 2 more |
| `goes` | הולכת | Lia goes to the market. |
| `grandma` | סבתא | A Present for Grandma · Lia buys red flowers and a card for her grandma. · "I'm sorry, Grandma," she says. · She gives Grandma the flowers and the card. · and 4 more |
| `grandma's` | סבתא | Today is her grandma's birthday. |
| `happy` | שמח | My favorite song is "Happy Birthday". · She is happy. · Happy birthday! Here is a for you. · At the end of the trip, the students are tired but happy. |
| `has` | יש לו / לה | Dana has a new flat. · He has flour, eggs and sugar. |
| `have` | יש לי | I have a lot of hobbies. |
| `he` | הוא | He has flour, eggs and sugar. · He ten years old. |
| `hi` | היי | Hi! |
| `him` | לו | Tom's friends give him candy. · What do Tom's friends give him? |
| `hobbies` | תחביבים | Maya's Hobbies · I have a lot of hobbies. |
| `home` | בית | My school is not far from my home. · Is her school far from her home? · Dana's New Home |
| `how` | איך / כמה | How old is Maya? · How old is Noa? · How do the students feel at the end? |
| `how many` | כמה | How many students are in the school? |
| `i` | אני | I am ten years old. · I am from Israel. · I have a lot of hobbies. · I play football with my friends. · and 22 more |
| `in` | ב- | There are forty students in the school. · At one o'clock they eat in the dining room. · How many students are in the school? · The flat is in a big building. · and 12 more |
| `is` | הוא / היא (is) | My name is Maya. · My favorite song is "Happy Birthday". · My favorite subject at school is English. · My school is not far from my home. · and 49 more |
| `it` | זה | It a special present. · Is it a building? · Is it a dining room? · Is it a piano? · and 4 more |
| `it's` | זה | It's my birthday! I'm years old. |
| `late` | מאחרת | At the end of the day, Lia is late. |
| `lia` | ליה (שם) | Lia lives in a small village. · Lia goes to the market. · Lia buys red flowers and a card for her grandma. · At the end of the day, Lia is late. · and 6 more |
| `live` | לגור | Where does Lia live? |
| `lives` | גרה | Lia lives in a small village. |
| `living room` | סלון | There is a blue sofa in the living room. · What is in the living room? |
| `makes` | מכין | Tom's dad makes a cake. · Who makes the cake? |
| `man` | איש | A man sells pretty flowers there. |
| `maya` | מאיה (שם) | My name is Maya. · How old is Maya? · Where is Maya from? · What does Maya play? · and 6 more |
| `maya's` | מאיה (שם) | Maya's Hobbies · Maya's favorite subject is . |
| `mother` | אמא | Dana's mother is a teacher. · What does Dana's mother teach? |
| `music` | מוזיקה | Every day the students study English and music. · She teaches music. · Music is my favorite . · I like music. · and 3 more |
| `my` | שלי | My name is Maya. · I play football with my friends. · My favorite song is "Happy Birthday". · My favorite subject at school is English. · and 11 more |
| `name` | שם | My name is Maya. |
| `new` | חדש | Dana's New Home · Dana has a new flat. · Noa is coming soon to see the new flat. · Her flat new. |
| `noa` | נועה (שם) | Her friend Noa is the same age. · Noa plays the guitar like Dana. · Noa is coming soon to see the new flat. · How old is Noa? · and 3 more |
| `not` | לא | My school is not far from my home. |
| `o'clock` | בשעה | At one o'clock they eat in the dining room. · Time: o'clock · 4 o'clock |
| `of` | של | At the end of the day, Lia is late. · At the end of the trip, the students are tired but happy. |
| `old` | ישן, בן כמה | How old is Maya? · How old is Noa? |
| `on` | על, ב- | Every year the students go on a trip. · What do you do on your birthday? · Are they on a trip? · Today they are on a special trip to a market. |
| `one` | אחת | At one o'clock they eat in the dining room. |
| `party` | מסיבה | A Birthday Party · Everyone is ready for the party. |
| `plays` | מנגנת / משחקת | Dana plays the guitar in her room. · Noa plays the guitar like Dana. · Who plays the guitar? · ben plays the piano |
| `red` | אדום | Lia buys red flowers and a card for her grandma. |
| `room` | חדר | Dana plays the guitar in her room. |
| `say` | לומר | Why does Lia say "I'm sorry"? |
| `says` | אומרת | "I'm sorry, Grandma," she says. · "This is a special thing," says Grandma. |
| `school` | בית ספר | My favorite subject at school is English. · My school is not far from my home. · Is her school far from her home? · A Special School · and 5 more |
| `sea` | ים | Some students go to the sea. |
| `see` | לראות | Noa is coming soon to see the new flat. |
| `sells` | מוכר | A man sells pretty flowers there. |
| `she` | היא | She teaches music. · "I'm sorry, Grandma," she says. · She gives Grandma the flowers and the card. · She is happy. · and 1 more |
| `sings` | שרה | Then Lia sings a song. |
| `small` | קטן | There is a small bathroom and a toilet. · Lia lives in a small village. |
| `some` | כמה, חלק | Some students go to the sea. |
| `story` | סיפור | This is a story about a special school. |
| `students` | תלמידים | There are forty students in the school. · Every day the students study English and music. · Every year the students go on a trip. · Some students go to the sea. · and 10 more |
| `sugar` | סוכר | He has flour, eggs and sugar. |
| `teacher` | מורה | Dana's mother is a teacher. · Is Maya a teacher? · Every Friday, her teacher takes the class outside. |
| `teaches` | מלמדת | She teaches music. |
| `ten` | עשר | I am ten years old. · He ten years old. |
| `the` | ה- | I kick the ball and I get a goal! · I also play the piano. · There are forty students in the school. · Every day the students study English and music. · and 59 more |
| `there` | שם / יש | There are forty students in the school. · There is a blue sofa in the living room. · There is a small bathroom and a toilet. · A man sells pretty flowers there. · and 2 more |
| `they` | הם | At one o'clock they eat in the dining room. · They throw a ball and play games. · They ready. · Are they on a trip? · and 4 more |
| `this` | זה | This is a story about a special school. · "This is a special thing," says Grandma. |
| `to` | אל, ל- | Some students go to the sea. · The other students wait for the bus and go to a farm. · Noa is coming soon to see the new flat. · Lia goes to the market. · and 5 more |
| `today` | היום | Today is her grandma's birthday. · Where are they today? · Today they are on a special trip to a market. |
| `tom` | תום (שם) | tom is thirteen years old · Tom |
| `tom's` | תום (שם) | Tom's birthday is in July. · Tom's dad makes a cake. · Tom's friends give him candy. · When is Tom's birthday? · and 1 more |
| `very` | מאוד | The cake is very sweet. |
| `what` | מה | What does Maya play? · What is her favorite subject? · What do the students study every day? · What do the students do every year? · and 6 more |
| `when` | מתי | When is Tom's birthday? · When does the class go outside? Every . |
| `where` | איפה | Where is Maya from? · Where do the students eat? · Where is the flat? · Where do the children play games? · and 4 more |
| `who` | מי | Who plays the guitar? · Who makes the cake? · Who takes the class outside? |
| `why` | למה | Why does Lia say "I'm sorry"? |
| `with` | עם | I play football with my friends. |
| `year` | שנה | Every year the students go on a trip. · What do the students do every year? |
| `years old` | בן / בת (גיל) | I am ten years old. · He ten years old. · I eleven years old. · I am thirteen years old. · and 3 more |
| `you` | אתה / את | What do you do on your birthday? · You my friend. · Happy birthday! Here is a for you. |
| `your` | שלך | What do you do on your birthday? |

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
