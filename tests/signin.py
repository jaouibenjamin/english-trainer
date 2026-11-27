#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The pupil's sign-in screens for 'supabase' mode (js/signin.js, docs/SIGNIN.md) in a real browser.

The screens are mounted on a test page with a stand-in for js/state.js enter() (the seam with PHASE3 step 6) that
answers as supabase/functions/_shared/core.ts does: input, weak, class, roster, taken, full, pin, picture, otc, and
locked with wait / by / help. The whole flow through the game (main.js, state.js, js/api.js and a stand-in project on
the project's address) is tests/supabase_mode.py's, once step 6 is in.
Checked:
  - register, the 5 steps: the class code and name, a weak code and two codes that differ (refused on the screen), the
    two pictures (tap order, a slot emptied), the story with the child's own pair, recall (a wrong order, three misses
    send the child back to choose new pictures), and what reaches enter() (no more, no less);
  - the server's refusals at the end of registration send the child back to the right step, with what was typed kept;
  - sign in: a wrong code, each wait (by / help, wait -1), and a sign-in that works;
  - "I forgot my code": wrong pictures (2 tries left, 1 left, then closed), the teacher's one-time code, wrong and right,
    the new code and new pictures, what reaches enter();
  - recovery never shows the old pictures (dots in the slots, no mark on a tapped tile); every picture screen is
    shuffled again; nothing secret is left in storage, the page or the address when the flow ends;
  - Hebrew right to left at 390 x 844, 360 x 740 and 320 x 568: no sideways scroll, the main button on screen, every
    target at least 44 px (48 in the spec, 44 the floor), 4 tiles across at 390 and 360, 3 at 320.
    python3 tests/signin.py [--shots DIR]
    python3 tests/signin.py --video DIR    # a recording of the three flows at a child's pace, for the owner (needs ffmpeg)"""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
import play as P
from play import check, fails

SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
VIDEO = sys.argv[sys.argv.index('--video') + 1] if '--video' in sys.argv else None
CLASS = 'EN4K7Q2M'      # made up, as every name and code here
PAGE = f'http://127.0.0.1:{P.PORT}/__signin_test.html'
HTML = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;background:#0B1E3F}</style></head><body><div id="view"></div>
<script type="module">
import * as M from './js/signin.js';
window.__M = M;
const W = window;
/* the stand-in for js/state.js enter(): core.ts's answers, a class of made-up first names */
W.__calls = []; W.__next = []; W.__done = 0;
const K = c => 'k' + [...String(c)].reverse().join('');   // the stand-in keeps codes only in this form: a heap scan then finds what the screens keep
const roster = new Set(['נועה', 'יואב', 'דנה', 'דנה ב', 'נועה כ.', 'בת-אל מ.', 'דנה כ.']), pupils = new Map([['דנה', {code: K('5831'), pics: [3, 9]}], ['דנה כ.', {code: K('5831'), pics: [3, 9]}]]);
/* W.__form = 'first_initial': the class takes first name + one letter (docs/GRADES_V1.md 0011), checked once the class code is right */
const formOk = n => { const w = n.split(' '); return w.length === 2 && !w[0].includes('.') && [...w[1]].length === 2 && w[1].endsWith('.'); };
const otc = {'דנה': 'k319284'}, tries = {};   // the teacher's code, already in the stand-in's form (the code itself written here would stay in the page's own source)
W.__enter = async (kind, f) => {
  if (!W.__quiet) W.__calls.push({kind, f: JSON.parse(JSON.stringify(f))});
  await new Promise(r => setTimeout(r, 120));
  if (W.__next.length) return W.__next.shift();
  if (f.c !== '""" + CLASS + """') return {ok: false, e: 'class'};
  if (W.__form === 'first_initial' && !formOk(f.n)) return {ok: false, e: 'name', form: 'first_initial'};
  if (kind === 'register') {
    if (!roster.has(f.n)) return {ok: false, e: 'roster'};
    if (pupils.has(f.n)) return {ok: false, e: 'taken'};
    pupils.set(f.n, {code: K(f.code), pics: f.pics}); return {ok: true};
  }
  const p = pupils.get(f.n);
  if (kind === 'login') return p && p.code === K(f.code) ? {ok: true} : {ok: false, e: 'pin'};
  if (kind === 'recover') {
    if (f.otc !== undefined) { if (!p || otc[f.n] !== K(f.otc)) return {ok: false, e: 'otc'}; }
    else {
      if ((tries[f.n] || 0) >= 3) return {ok: false, e: 'locked', wait: -1, by: 'name', help: 'teacher'};
      if (!p || p.pics.join('>') !== f.pics.join('>')) { tries[f.n] = (tries[f.n] || 0) + 1; return tries[f.n] >= 3 ? {ok: false, e: 'locked', wait: -1, by: 'name', help: 'teacher'} : {ok: false, e: 'picture'}; }
    }
    p.code = K(f.newCode); p.pics = f.newPics; return {ok: true};
  }
  return {ok: false, e: 'net'};
};
W.__clips = []; W.Audio = function (src) { W.__clips.push(String(src).split('/').pop().split('.')[0]); return {play: () => Promise.resolve(), pause() {}}; };
W.__mount = () => { if (W.__si) W.__si.destroy(); W.__si = M.mount(document.getElementById('view'), {enter: W.__enter, done: () => { W.__done++; }, sound: () => true, lastC: ''}); };
W.__mount();
</script></body></html>"""
NO = {'apple': 1, 'banana': 2, 'watermelon': 3, 'cactus': 4, 'grapes': 5, 'flower': 6, 'umbrella': 7, 'kite': 8, 'drum': 9, 'hat': 10}


async def page(b, w=390, h=844, touch=False):
    # a laptop (fine pointer, the on-screen keypad) unless touch: a phone, where the system keyboard types the code
    c = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, has_touch=touch, locale='he-IL')
    errs = []
    pg = await c.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    await pg.route(PAGE, lambda r: r.fulfill(content_type='text/html', body=HTML))
    await pg.goto(PAGE)
    await pg.wait_for_selector('.si[data-scr="entry"]')
    return c, pg, errs


async def scr(pg):
    return await pg.get_attribute('.si', 'data-scr')


async def tap(pg, sel, pause=0):
    await pg.locator(sel).first.click()
    if pause: await pg.wait_for_timeout(pause)


async def typ(pg, id_, text, pause=0):
    await pg.fill(f'#si-{id_}', '')
    await pg.type(f'#si-{id_}', text, delay=60 if pause else 0)
    if pause: await pg.wait_for_timeout(pause)


async def keys(pg, digits, pause=0):
    for d in digits:
        await tap(pg, f'.si-key[data-k="{d}"]', 90 if pause else 0)


async def main_btn(pg, pause=0):
    await tap(pg, '.si-bar .wi-btn--block', pause)
    await pg.wait_for_function("!document.querySelector('.si-bar .wi-btn--block')||!document.querySelector('.si-bar .wi-btn--block').textContent.includes('רגע')", timeout=5000)


async def pick(pg, *names, pause=0):
    for n in names:
        await tap(pg, f'.si-tile[data-no="{NO[n]}"]', pause)


async def err(pg):
    e = pg.locator('.si-err')
    return (await e.inner_text()) if await e.count() else ''


async def shot(pg, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True); await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))


async def register_flow(b):
    c, pg, errs = await page(b)
    await shot(pg, '01-entry')
    await tap(pg, '[data-si="start"][data-f="reg"]')
    check('register: step 1 of 5, "מי אתם?"', await scr(pg) == 'a1' and 'שלב 1 מתוך 5' in await pg.inner_text('.si-prog') and await pg.inner_text('.si-h') == 'מי אתם?')
    await typ(pg, 'c', 'abc'); await typ(pg, 'n', 'נועה'); await main_btn(pg)
    check('a class code that cannot be one is refused on the screen, in the warm colour, read out', await scr(pg) == 'a1' and await err(pg) == 'קוד הכיתה לא נכון. בדקו שוב מול הלוח.' and await pg.get_attribute('.si-err', 'role') == 'alert')
    await typ(pg, 'c', CLASS.lower()); await shot(pg, '02-a1'); await main_btn(pg)
    check('step 2: the secret code', await scr(pg) == 'a2' and 'שלב 2 מתוך 5' in await pg.inner_text('.si-prog'))
    a = await pg.evaluate("[...document.querySelectorAll('.si-pinin')].map(i=>[i.inputMode,i.getAttribute('pattern'),i.maxLength,i.autocomplete,i.type])")
    check('the code fields are numeric, 4 digits, nothing to save (inputmode, pattern, maxlength, autocomplete off, not a password field)', a == [['numeric', '[0-9]*', 4, 'off', 'text']] * 2, a)
    await keys(pg, '1234'); await keys(pg, '1234'); await shot(pg, '03-a2-dots')
    dots = await pg.evaluate("[...document.querySelectorAll('[data-box=\"p\"] .si-d')].map(d=>d.textContent).join('')")
    check('the keypad fills the first code, then the second; digits show as dots', dots == '●●●●', dots)
    await main_btn(pg)
    check('a weak code (1234) is refused on the screen, both fields emptied', await err(pg) == 'קל מדי לנחש. לא 1234 ולא ספרות חוזרות. נסו קוד אחר.' and await pg.evaluate("document.querySelector('#si-p').value+document.querySelector('#si-p2').value") == '')
    await typ(pg, 'p', '5831'); await typ(pg, 'p2', '5832'); await main_btn(pg)
    check('two codes that differ are refused', await err(pg) == 'שני הקודים לא זהים. נסו שוב.' and await pg.input_value('#si-p') == '5831')
    await tap(pg, '[data-si="show"][data-id="p"]')
    check('"הצגה" shows the digits', await pg.evaluate("[...document.querySelectorAll('[data-box=\"p\"] .si-d')].map(d=>d.textContent).join('')") == '5831')
    await typ(pg, 'p2', '5831'); await main_btn(pg)
    check('step 3: two secret pictures, 20 tiles', await scr(pg) == 'a3' and await pg.locator('.si-tile').count() == 20)
    order3 = await pg.evaluate("[...document.querySelectorAll('.si-tile')].map(t=>+t.dataset.no)")
    await pick(pg, 'apple', 'kite')
    s = await pg.evaluate("[...document.querySelectorAll('.si-slot')].map(s=>s.getAttribute('aria-label'))")
    check('the slots fill in tap order: first, then second (named for a screen reader)', s == ['תמונה ראשונה: תפוח. הקישו כדי להוריד', 'תמונה שנייה: עפיפון. הקישו כדי להוריד'], s)
    await tap(pg, '.si-slot[data-k="1"]'); await pick(pg, 'drum')
    s = await pg.evaluate("[...document.querySelectorAll('.si-slot .si-w')].map(s=>s.textContent)")
    check('tapping a slot empties it; the next tap fills the free place', s == ['עפיפון', 'תוף'], s)
    await shot(pg, '04-a3'); await main_btn(pg)
    check('step 4: the story shows the child\'s own pair, in order', await scr(pg) == 'a4' and await pg.inner_text('.si-pair') == 'עפיפון, ואחר כך תוף')
    await shot(pg, '05-a4'); await main_btn(pg)
    order5 = await pg.evaluate("[...document.querySelectorAll('.si-tile')].map(t=>+t.dataset.no)")
    check('step 5: recall, the tiles in a new order', await scr(pg) == 'a5' and order5 != order3 and sorted(order5) == list(range(1, 21)))
    await pick(pg, 'drum', 'kite'); await main_btn(pg)
    check('the right pictures in the wrong order: "לא בדיוק", the slots emptied, nothing sent', await err(pg) == 'לא בדיוק. נסו שוב, אתם קרובים.' and await pg.locator('.si-slot.on').count() == 0 and await pg.evaluate('__calls.length') == 0)
    for _ in range(2):
        await pick(pg, 'apple', 'hat'); await main_btn(pg)
    check('after three misses: back to step 3 with "אפשר לבחור תמונות חדשות.", nothing chosen', await scr(pg) == 'a3' and 'אפשר לבחור תמונות חדשות.' in await pg.inner_text('.si') and await pg.locator('.si-slot.on').count() == 0)
    await pick(pg, 'kite', 'drum'); await main_btn(pg); await main_btn(pg)
    await pick(pg, 'kite', 'drum'); await shot(pg, '06-a5'); await main_btn(pg)
    await pg.wait_for_selector('.si[data-scr="done"]')
    calls = await pg.evaluate('__calls')
    check('one request, at the end: register with the class code (upper case), the name, the code and the pictures as numbers 1-20 in order',
          calls == [{'kind': 'register', 'f': {'c': CLASS, 'n': 'נועה', 'code': '5831', 'pics': [8, 9]}}], calls)
    check('"נרשמתם!" and "יוצאים לדרך"', await pg.inner_text('.si-h') == 'נרשמתם!' and await pg.inner_text('.si-bar .wi-btn') == 'יוצאים לדרך')
    await shot(pg, '07-done')
    await main_btn(pg)
    check('"יוצאים לדרך" hands over to the game', await pg.evaluate('__done') == 1)
    left = await pg.evaluate("JSON.stringify({ls:{...localStorage},ss:{...sessionStorage},url:location.href})")
    check('nothing of the code or the pictures is left in storage or the address', '5831' not in left and '8>9' not in left and '[8,9]' not in left, left)
    await pg.evaluate('__si.destroy()')
    check('destroy removes everything it drew', await pg.evaluate("document.getElementById('view').textContent.trim()===''||!document.querySelector('.si')") is not None)
    check('no page error', not errs, errs)
    await c.close()


async def register_refusals(b):
    c, pg, errs = await page(b)
    async def through(name):
        await tap(pg, '[data-si="start"][data-f="reg"]'); await typ(pg, 'c', CLASS); await typ(pg, 'n', name); await main_btn(pg)
        await typ(pg, 'p', '5831'); await typ(pg, 'p2', '5831'); await main_btn(pg)
        await pick(pg, 'apple', 'kite'); await main_btn(pg); await main_btn(pg); await pick(pg, 'apple', 'kite'); await main_btn(pg)
    await through('גלעד')
    check('a name not on the class list: back to step 1 with the message, the name kept', await scr(pg) == 'a1' and await err(pg) == 'השם הזה לא ברשימת הכיתה. בדקו את השם ואת האות, או בקשו מהמורה.' and await pg.input_value('#si-n') == 'גלעד')
    await typ(pg, 'n', 'דנה'); await main_btn(pg)
    check('the code typed before is kept when going on again', await pg.input_value('#si-p') == '5831')
    await main_btn(pg); await main_btn(pg); await main_btn(pg); await pick(pg, 'apple', 'kite'); await main_btn(pg)
    check('a name already taken: back to step 1, the message points to "כבר נרשמתי" and the teacher', await scr(pg) == 'a1' and await err(pg) == 'מישהו כבר נרשם בשם הזה. אם זה אתם, הקישו "כבר נרשמתי". אם יש בכיתה שני ילדים בשם הזה, בקשו מהמורה.')
    await pg.evaluate("__next.push({ok:false,e:'weak'})"); await typ(pg, 'n', 'יואב'); await main_btn(pg)
    await main_btn(pg); await main_btn(pg); await main_btn(pg); await pick(pg, 'apple', 'kite'); await main_btn(pg)
    check('a code the server finds weak: back to step 2, both fields empty', await scr(pg) == 'a2' and await err(pg) == 'קל מדי לנחש. לא 1234 ולא ספרות חוזרות. נסו קוד אחר.' and await pg.input_value('#si-p') == '')
    await pg.evaluate("__mount()")
    await pg.evaluate("__next.push({ok:false,e:'locked',by:'system',help:'wait',wait:-1})"); await through('יואב')
    check('registration closed (system / wait): its message, on the same step', await scr(pg) == 'a5' and await err(pg) == 'אי אפשר להירשם כרגע. נסו שוב מאוחר יותר. מי שכבר רשום יכול להיכנס.')
    check('no page error', not errs, errs)
    await c.close()


WAITS = [
    ({'by': 'name', 'help': 'teacher', 'wait': 900}, 'הכניסה בשם הזה נעצרה ל-15 דקות. בינתיים אפשר ללחוץ "שכחתי את הקוד", או לבקש מהמורה לשחרר.'),
    ({'by': 'name', 'help': 'teacher', 'wait': -1}, 'הכניסה בשם הזה נעצרה. בקשו מהמורה לשחרר אותה.'),
    ({'by': 'device', 'help': 'teacher', 'wait': 3600}, 'הכניסה מהמכשיר הזה נעצרה עד {T}. אפשר להיכנס ממכשיר אחר, או לבקש מהמורה לשחרר.'),
    ({'by': 'address', 'help': 'teacher', 'wait': 3600}, 'זה לא בגללכם: הכניסה מהמחשבים כאן עוצרת לכולם עד {T}. אפשר לבקש מהמורה לשחרר. מי שכבר מחובר ממשיך לשחק.'),
    ({'by': 'address', 'help': 'wait', 'wait': 3600}, 'זה לא בגללכם: הכניסה מכאן עוצרת לכולם עד {T}. נסו שוב אז.'),
    ({'by': 'class', 'help': 'teacher', 'wait': 3600}, 'זה לא בגללכם: הכניסה לכיתה עוצרת עד {T}. אפשר לבקש מהמורה לשחרר.'),
    ({'by': 'everyone', 'help': 'wait', 'wait': 3600}, 'יש עכשיו עומס. נסו שוב ב-{T}.'),
    ({'by': 'system', 'help': 'wait', 'wait': -1}, 'אי אפשר להירשם כרגע. נסו שוב מאוחר יותר. מי שכבר רשום יכול להיכנס.'),
    ({'by': 'moon', 'help': 'pizza', 'wait': 3600}, 'הכניסה עוצרת לכמה דקות. נסו שוב ב-{T}.'),
    ({'by': 'name', 'help': 'pizza', 'wait': 3600}, 'הכניסה עוצרת לכמה דקות. נסו שוב ב-{T}.'),     # help not teacher: no promise of the teacher
    ({'by': 'constructor', 'help': 'teacher', 'wait': 3600}, 'הכניסה עוצרת לכמה דקות. נסו שוב ב-{T}.'),
]


async def sign_in(b):
    c, pg, errs = await page(b)
    await tap(pg, '[data-si="start"][data-f="in"]')
    check('sign in: "נכנסים", class code, name, code and keypad on one screen', await scr(pg) == 'b' and await pg.inner_text('.si-h') == 'נכנסים' and await pg.locator('.si-key').count() == 11 and await pg.locator('.si-pad').is_visible())
    await typ(pg, 'c', CLASS); await typ(pg, 'n', 'דנה'); await keys(pg, '1111'); await shot(pg, '10-b'); await main_btn(pg)
    check('a wrong code: "השם או הקוד לא נכונים", the code emptied', await err(pg) == 'השם או הקוד לא נכונים. נסו שוב.' and await pg.input_value('#si-p') == '')
    T = await pg.evaluate("(()=>{const at=new Date(Date.now()+3600e3);return String(at.getHours()).padStart(2,'0')+':'+String(at.getMinutes()).padStart(2,'0')})()")
    for ans, want in WAITS:
        await pg.evaluate(f"__next.push({json.dumps(dict(ans, ok=False, e='locked'))})")
        await keys(pg, '1111'); await main_btn(pg)
        got = await err(pg)
        check(f'wait {ans["by"]}/{ans["help"]} {ans["wait"]}: its own message', got in (want.replace('{T}', T), want.replace('{T}', T[:-1] + str((int(T[-1]) + 1) % 10))), (got, want))
    await keys(pg, '5831'); await main_btn(pg)
    check('the right code: handed over to the game; the request had no more than class, name and code', await pg.evaluate('__done') == 1 and (await pg.evaluate('__calls'))[-1] == {'kind': 'login', 'f': {'c': CLASS, 'n': 'דנה', 'code': '5831'}})
    check('no page error', not errs, errs)
    await c.close()


async def recover(b):
    c, pg, errs = await page(b)
    await tap(pg, '[data-si="start"][data-f="rec"]')
    check('"שכחתם את הקוד? זה קורה.", step 1 of 3', await pg.inner_text('.si-h') == 'שכחתם את הקוד? זה קורה.' and 'שלב 1 מתוך 3' in await pg.inner_text('.si-prog'))
    await typ(pg, 'c', CLASS); await typ(pg, 'n', 'דנה'); await main_btn(pg)
    check('step 2: the secret pictures, in order', await scr(pg) == 'e2' and await pg.inner_text('.si-h') == 'התמונות הסודיות, לפי הסדר')
    await pick(pg, 'drum', 'apple')
    seen = await pg.evaluate("({img:document.querySelectorAll('.si-slot img').length,dots:document.querySelectorAll('.si-slot .si-dot').length,marked:document.querySelectorAll('.si-tile [id^=si-picked]').length,text:document.querySelector('.si-slots').textContent.replace('←','')})")
    check('recovery shows dots in the slots, no picture and no name, and no mark on the tapped tiles', seen == {'img': 0, 'dots': 2, 'marked': 0, 'text': ''}, seen)
    await shot(pg, '20-e2'); await main_btn(pg)
    check('step 3: a new code', await scr(pg) == 'a2' and 'שלב 3 מתוך 3' in await pg.inner_text('.si-prog'))
    async def new_secrets():
        await typ(pg, 'p', '7302'); await typ(pg, 'p2', '7302'); await main_btn(pg)
        await pick(pg, 'hat', 'grapes'); await main_btn(pg); await main_btn(pg); await pick(pg, 'hat', 'grapes'); await main_btn(pg)
    await new_secrets()
    check('wrong pictures: back to step 2, "לא התאים" with no count kept on the device (the server decides when it is over)', await scr(pg) == 'e2' and await err(pg) == 'לא התאים. קחו רגע לחשוב על הסדר ונסו שוב.')
    call = (await pg.evaluate('__calls'))[-1]
    check('the request: class, name, the old pictures, the new code and pictures', call == {'kind': 'recover', 'f': {'c': CLASS, 'n': 'דנה', 'pics': [9, 1], 'newCode': '7302', 'newPics': [10, 5]}}, call)
    await pick(pg, 'apple', 'drum'); await main_btn(pg)
    check('the new code is kept for the next try', await pg.input_value('#si-p') == '7302')
    await main_btn(pg); await main_btn(pg); await main_btn(pg); await pick(pg, 'hat', 'grapes'); await main_btn(pg)
    check('second wrong try: the same words', await err(pg) == 'לא התאים. קחו רגע לחשוב על הסדר ונסו שוב.')
    await pick(pg, 'kite', 'apple'); await main_btn(pg); await main_btn(pg); await main_btn(pg); await main_btn(pg); await pick(pg, 'hat', 'grapes'); await main_btn(pg)
    check('third: the server closes the pictures (locked by name, -1): the teacher will help; no pictures to tap, only "קיבלתי קוד מהמורה"', await err(pg) == 'הפעם התמונות לא עבדו. המורה תעזור לכם עם קוד חדש.' and await pg.locator('.si-tile').count() == 0 and await pg.locator('[data-si="otc"]').count() == 1)
    await shot(pg, '21-e2-closed')
    await tap(pg, '[data-si="otc"]')
    check('the teacher\'s code: six digits, the same keypad', await scr(pg) == 'e3' and await pg.get_attribute('#si-otc', 'maxlength') == '6')
    await keys(pg, '111111'); await main_btn(pg); await new_secrets()
    check('a wrong one-time code: back to it, "פג תוקפו", emptied', await scr(pg) == 'e3' and await err(pg) == 'הקוד לא נכון או שפג תוקפו. בקשו מהמורה קוד חדש.' and await pg.input_value('#si-otc') == '')
    await keys(pg, '482913'); await shot(pg, '22-e3'); await main_btn(pg); await new_secrets()
    await pg.wait_for_selector('.si[data-scr="done"]')
    call = (await pg.evaluate('__calls'))[-1]
    check('the right one: "הקוד החדש מוכן!", the request had the one-time code and no pictures', await pg.inner_text('.si-h') == 'הקוד החדש מוכן!' and call == {'kind': 'recover', 'f': {'c': CLASS, 'n': 'דנה', 'otc': '482913', 'newCode': '7302', 'newPics': [10, 5]}}, call)
    await shot(pg, '23-done')
    # a pupil who already changed the code this month, and a class where recovery is paused today
    for ans, want in (({'by': 'name', 'help': 'teacher', 'wait': 86400}, 'כבר החלפתם קוד החודש. המורה תעזור לכם עם קוד חדש.'),
                      ({'by': 'class', 'help': 'teacher', 'wait': 3600}, 'היום אי אפשר לשחזר עם תמונות. המורה תעזור לכם עם קוד חדש, או נסו מחר.')):
        await pg.evaluate('__mount()'); await tap(pg, '[data-si="start"][data-f="rec"]'); await typ(pg, 'c', CLASS); await typ(pg, 'n', 'דנה'); await main_btn(pg)
        await pick(pg, 'drum', 'apple'); await main_btn(pg)
        await pg.evaluate(f"__next.push({json.dumps(dict(ans, ok=False, e='locked'))})"); await new_secrets()
        check(f'recovery locked by {ans["by"]}: "{want[:22]}…", only the teacher\'s code offered', await err(pg) == want and await pg.locator('.si-tile').count() == 0, await err(pg))
    check('no page error', not errs, errs)
    await c.close()


async def traces(pg, secrets):
    """where a code could still be read once the screens are done with it: the RegExp statics (docs/LESSONS.md 17) and
    the whole heap after a garbage collection. The stand-in keeps codes only in another form and its call log is
    emptied first, so a hit is the screens'."""
    await pg.evaluate('__calls.length = 0')
    statics = await pg.evaluate('String(RegExp.$_) + "|" + String(RegExp.lastMatch) + "|" + String(RegExp.input) + "|" + String(RegExp.leftContext) + "|" + String(RegExp.rightContext)')
    cdp = await pg.context.new_cdp_session(pg); chunks = []
    cdp.on('HeapProfiler.addHeapSnapshotChunk', lambda e: chunks.append(e['chunk']))
    await cdp.send('HeapProfiler.enable'); await cdp.send('HeapProfiler.collectGarbage')
    await cdp.send('HeapProfiler.takeHeapSnapshot', {'reportProgress': False}); await cdp.detach()
    # only the heap's string objects count: the snapshot's own table of names also holds numbers (node ids, indexes), so
    # any four digits, typed or not, are in it (checked: 1234 and 5555 were there in a run that never typed them)
    snap = json.loads(''.join(chunks)); m = snap['snapshot']['meta']; N, S = snap['nodes'], snap['strings']
    nf = m['node_fields']; w, ti, ni = len(nf), nf.index('type'), nf.index('name')
    kinds = {k for k, t in enumerate(m['node_types'][0]) if t in ('string', 'concatenated string', 'sliced string')}
    strings = [S[N[i + ni]] for i in range(0, len(N), w) if N[i + ti] in kinds]
    return [(x, 'RegExp statics') for x in secrets if x in statics] + [(x, 'heap') for x in secrets if any(x in v for v in strings)]


async def secrets_gone(b):
    c, pg, errs = await page(b)
    # a stray letter in a code field: no regexp runs on it (it would leave the digits in RegExp.$_)
    await tap(pg, '[data-si="start"][data-f="reg"]'); await typ(pg, 'c', CLASS); await typ(pg, 'n', 'נועה'); await main_btn(pg)
    await pg.type('#si-p', '48x2'); await pg.type('#si-p2', '48x2')
    check('a letter typed in a code field is dropped, the digits kept', await pg.input_value('#si-p') == '482')
    st = await pg.evaluate('String(RegExp.$_) + "|" + String(RegExp.lastMatch) + "|" + String(RegExp.input)')
    check('no regexp ran on what was typed in a code field (RegExp.$_, lastMatch, input)', '48' not in st and '482' not in st, st)
    await c.close()
    # each flow, to its end: the code, the new code and the one-time code are nowhere in the page any more
    c, pg, errs = await page(b)
    await tap(pg, '[data-si="start"][data-f="reg"]'); await typ(pg, 'c', CLASS); await typ(pg, 'n', 'יואב'); await main_btn(pg)
    await keys(pg, '7395'); await keys(pg, '7395'); await main_btn(pg)
    await pick(pg, 'apple', 'kite'); await main_btn(pg); await main_btn(pg); await pick(pg, 'apple', 'kite'); await main_btn(pg)
    await pg.wait_for_selector('.si[data-scr="done"]')
    found = await traces(pg, ['7395'])
    check('after registering, the code is nowhere: not in RegExp statics, not in the heap', not found, found)
    await pg.evaluate('__mount()'); await tap(pg, '[data-si="start"][data-f="in"]'); await typ(pg, 'c', CLASS); await typ(pg, 'n', 'יואב'); await keys(pg, '7395'); await main_btn(pg)
    found = await traces(pg, ['7395'])
    check('after signing in, the code is nowhere', not found and await pg.evaluate('__done') >= 1, found)
    await pg.evaluate('__mount()'); await tap(pg, '[data-si="start"][data-f="rec"]'); await typ(pg, 'c', CLASS); await typ(pg, 'n', 'דנה'); await main_btn(pg)
    await tap(pg, '[data-si="otc"]'); await keys(pg, '482913'); await main_btn(pg)
    await keys(pg, '6174'); await keys(pg, '6174'); await main_btn(pg); await pick(pg, 'hat', 'grapes'); await main_btn(pg); await main_btn(pg); await pick(pg, 'hat', 'grapes'); await main_btn(pg)
    await pg.wait_for_selector('.si[data-scr="done"]')
    found = await traces(pg, ['482913', '6174'])
    check('after recovery with the teacher\'s code, neither it nor the new code is anywhere', not found, found)
    # a code typed, then the page left; Back (from the back-forward cache when the browser keeps the page)
    await pg.evaluate('__mount()'); await tap(pg, '[data-si="start"][data-f="in"]'); await typ(pg, 'c', CLASS); await typ(pg, 'n', 'דנה'); await keys(pg, '4827')
    await tap(pg, '[data-si="show"][data-id="p"]')
    await pg.evaluate("window.__kept = 1")
    await pg.goto(f'http://127.0.0.1:{P.PORT}/docs/mock/signin.html'); await pg.go_back(wait_until='commit'); await pg.wait_for_timeout(800); await pg.wait_for_selector('.si')
    back = await pg.evaluate("({kept: window.__kept === 1, scr: document.querySelector('.si').dataset.scr, values: [...document.querySelectorAll('.si input')].map(i => i.value).join(''), text: document.querySelector('.si').textContent})")
    check('leaving the page with a code typed and shown, then Back from the back-forward cache: the entry screen, no code anywhere on it',
          back['kept'] and back['scr'] == 'entry' and '4827' not in back['values'] and '4827' not in back['text'], back)
    found = await traces(pg, ['4827'])
    check('and the left code is not in the page either', not found, found)
    check('no page error', not errs, errs)
    await c.close()


async def quiet_names(b):
    c, pg, errs = await page(b)
    await tap(pg, '[data-si="start"][data-f="reg"]'); await typ(pg, 'c', CLASS); await typ(pg, 'n', 'נועה'); await main_btn(pg)
    await typ(pg, 'p', '5831'); await typ(pg, 'p2', '5831'); await main_btn(pg)
    await pg.evaluate('__clips.length = 0'); await pick(pg, 'apple', 'kite')
    clips = await pg.evaluate('__clips')
    check('by default a tapped picture is not said aloud (in a classroom the neighbours would hear the pair)', clips == [], clips)
    check('the names switch is there, off', await pg.get_attribute('[data-si="names"]', 'aria-pressed') == 'false')
    await tap(pg, '[data-si="names"]'); await tap(pg, '.si-slot[data-k="2"]'); await pick(pg, 'drum')
    clips = await pg.evaluate('__clips')
    check('turned on, the tapped picture\'s name is said', clips == ['drum'], clips)
    await main_btn(pg)
    check('the story step says "אמרו את זה בלב" and plays no clip (a secret is not said aloud in a classroom)', 'אמרו את זה בלב.' in await pg.inner_text('.si') and 'בקול' not in await pg.inner_text('.si') and 'line-say' not in await pg.evaluate('__clips.join()'), await pg.evaluate('__clips'))
    await main_btn(pg); await pg.evaluate('__clips.length = 0'); await pick(pg, 'apple', 'drum')
    check('recall stays silent whatever the switch', await pg.evaluate('__clips') == [])
    r = await pg.evaluate("(()=>{const h=document.createElement('div'),g=document.createElement('div');document.body.append(h,g);__M.notMe(h,{name:'Newbie',inline:true,out(){}});__M.notMe(g,{name:'<b>x</b>',out(){}});return h.innerHTML+g.innerHTML})()")
    check('the name next to "זה לא אני · יציאה" sits in one <bdi> (a Latin name in Hebrew), and is shown as text',
          '<bdi class="si-hi"><span class="si-fn">Newbie</span></bdi>' in r and '<span class="si-fn">&lt;b&gt;x&lt;/b&gt;</span>' in r and 'זה לא אני · יציאה' in r, r[:300])
    # a long Latin name in the pill at 320: only the first name is cut, the letter stays whole, the button whole
    await pg.set_viewport_size({'width': 320, 'height': 568})
    m = await pg.evaluate("""(()=>{const h=document.createElement('div');h.style.cssText='position:relative;width:320px;height:80px';document.body.append(h);
      const box=__M.notMe(h,{name:'Alexandrina-Maximiliana K.',inline:true,out(){}}),fn=box.querySelector('.si-fn'),ln=box.querySelector('.si-ln'),b=box.querySelector('.si-nm');
      return {cut:fn.scrollWidth>fn.clientWidth,ln:ln.textContent,lnw:ln.scrollWidth<=ln.clientWidth+1,bw:b.scrollWidth<=b.clientWidth+1,bh:b.getBoundingClientRect().height,fits:box.getBoundingClientRect().right<=320,
        ltr:getComputedStyle(box.querySelector('bdi')).direction,text:box.querySelector('bdi').textContent}})()""")
    check('320: "Alexandri… K.": the first name cut, the letter and the button whole, the name LTR, its whole text there for a screen reader',
          m['cut'] and m['ln'] == '\u00a0K.' and m['lnw'] and m['bw'] and m['bh'] >= 44 and m['fits'] and m['ltr'] == 'ltr' and m['text'] == 'Alexandrina-Maximiliana\u00a0K.', m)
    check('no page error', not errs, errs)
    await c.close()


async def letter_form(b):
    """a class that takes first name + one letter of the surname (form 'first_initial'): the server's e:'name' brings the
    child back to the name with the letter field asked for, everything else kept; the trial class (form 'first') takes the
    first name alone, so one screen serves both"""
    c, pg, errs = await page(b)
    await pg.evaluate("__form='first_initial'")
    await tap(pg, '[data-si="start"][data-f="reg"]')
    check('A1: first name and the letter side by side, the hint says one letter, Hebrew or Latin',
          await pg.inner_text('label[for="si-n"]') == 'השם הפרטי' and await pg.inner_text('label[for="si-l"]') == 'אות משפחה'
          and await pg.get_attribute('#si-l', 'aria-label') == 'האות הראשונה של שם המשפחה'
          and await pg.inner_text('#si-n-h') == 'השם הפרטי והאות הראשונה של שם המשפחה, כמו ברשימה של המורה.' and await pg.get_attribute('#si-l', 'maxlength') == '2' and await pg.get_attribute('#si-n', 'maxlength') == '17')
    await typ(pg, 'c', CLASS); await typ(pg, 'n', 'נועה')
    check('the name as it will appear, while typing (no letter yet: the first name)', await pg.inner_text('.si-as') == 'כך יופיע במשחק: נועה')
    await main_btn(pg)
    await typ(pg, 'p', '5831'); await typ(pg, 'p2', '5831'); await main_btn(pg)
    await pick(pg, 'apple', 'kite'); await main_btn(pg); await main_btn(pg); await pick(pg, 'apple', 'kite'); await main_btn(pg)
    check('the server answers e:name, form first_initial: back to step 1, gently, the letter field asked for and in focus',
          await scr(pg) == 'a1' and await err(pg) == 'חסרה האות הראשונה של שם המשפחה. אות אחת, למשל כ.'
          and await pg.evaluate("document.activeElement&&document.activeElement.id") == 'si-l' and await pg.get_attribute('#si-l', 'aria-required') == 'true'
          and await pg.input_value('#si-n') == 'נועה' and await pg.input_value('#si-c') == CLASS)
    await shot(pg, '40-a1-letter')
    await main_btn(pg)
    check('the letter asked for: going on without it is refused on the screen, no request', await scr(pg) == 'a1' and await err(pg) == 'חסרה האות הראשונה של שם המשפחה. אות אחת, למשל כ.' and len(await pg.evaluate('__calls')) == 1)
    await typ(pg, 'l', '.'); v1 = await pg.input_value('#si-l')
    await typ(pg, 'l', 'K')
    check('a Latin letter for a Hebrew name: the hint says the letter takes the name\'s language, and going on is refused there',
          await pg.inner_text('#si-n-h') == 'האות צריכה להיות באותה שפה של השם.')
    await main_btn(pg)
    check('... refused on the screen, no request', await err(pg) == 'האות צריכה להיות באותה שפה של השם.' and len(await pg.evaluate('__calls')) == 1)
    await typ(pg, 'l', 'ך')
    check('the hint is back', await pg.inner_text('#si-n-h') == 'השם הפרטי והאות הראשונה של שם המשפחה, כמו ברשימה של המורה.')
    check('the letter field keeps only a letter, and a final form as its plain one', v1 == '' and await pg.input_value('#si-l') == 'כ')
    check('the name as it will appear: "נועה כ."', await pg.inner_text('.si-as') == 'כך יופיע במשחק: נועה כ.')
    await main_btn(pg)
    check('the code and the pictures typed before are kept', await pg.input_value('#si-p') == '5831')
    await main_btn(pg); await main_btn(pg); await main_btn(pg); await pick(pg, 'apple', 'kite'); await main_btn(pg)
    call = (await pg.evaluate('__calls'))[-1]
    check('registered; the request: "נועה כ.", the same code and pictures', await pg.inner_text('.si-h') != 'מי אתם?' and call == {'kind': 'register', 'f': {'c': CLASS, 'n': 'נועה כ.', 'code': '5831', 'pics': [1, 8]}}, call)
    # a two-word first name: a space becomes a hyphen, and the child sees it
    await pg.evaluate('__mount()'); await tap(pg, '[data-si="start"][data-f="reg"]')
    await typ(pg, 'c', CLASS); await typ(pg, 'n', 'בת אל'); await typ(pg, 'l', 'מ')
    check('a two-word first name: shown with a hyphen before going on', await pg.inner_text('.si-as') == 'כך יופיע במשחק: בת-אל מ.')
    await main_btn(pg)
    await pg.locator('#si-p').wait_for()
    await typ(pg, 'p', '7302'); await typ(pg, 'p2', '7302'); await main_btn(pg)
    await pick(pg, 'hat', 'drum'); await main_btn(pg); await main_btn(pg); await pick(pg, 'hat', 'drum'); await main_btn(pg)
    call = (await pg.evaluate('__calls'))[-1]
    check('the request: "בת-אל מ."', call['f']['n'] == 'בת-אל מ.', call)
    # sign in without the letter
    await pg.evaluate('__mount()'); await tap(pg, '[data-si="start"][data-f="in"]')
    await typ(pg, 'c', CLASS); await typ(pg, 'n', 'דנה'); await keys(pg, '5831'); await main_btn(pg)
    check('sign in, no letter: the letter asked for on the same screen, the code kept, the letter field in focus',
          await scr(pg) == 'b' and await err(pg) == 'חסרה האות הראשונה של שם המשפחה. אות אחת, למשל כ.' and await pg.input_value('#si-p') == '5831'
          and await pg.evaluate("document.activeElement&&document.activeElement.id") == 'si-l')
    await typ(pg, 'l', 'כ'); await main_btn(pg)
    check('with the letter: in, the request "דנה כ."', await pg.evaluate('__done') == 1 and (await pg.evaluate('__calls'))[-1] == {'kind': 'login', 'f': {'c': CLASS, 'n': 'דנה כ.', 'code': '5831'}})
    # the letter typed with a wrong form of the first name (a dot in it): the general line, the first name in focus
    await pg.evaluate('__mount()'); await tap(pg, '[data-si="start"][data-f="in"]')
    await typ(pg, 'c', CLASS); await typ(pg, 'n', 'ד.נה'); await typ(pg, 'l', 'כ'); await keys(pg, '5831'); await main_btn(pg)
    check('a letter typed, the name still not in the form: "כתבו את השם כמו ברשימה של המורה", the first name in focus',
          await err(pg) == 'כתבו את השם כמו ברשימה של המורה: השם הפרטי, ואות אחת משם המשפחה.' and await pg.evaluate("document.activeElement&&document.activeElement.id") == 'si-n')
    # forgot, no letter: back to E1
    await pg.evaluate('__mount()'); await tap(pg, '[data-si="start"][data-f="rec"]')
    await typ(pg, 'c', CLASS); await typ(pg, 'n', 'דנה'); await main_btn(pg)
    await pick(pg, 'watermelon', 'drum'); await main_btn(pg)
    await typ(pg, 'p', '4096'); await typ(pg, 'p2', '4096'); await main_btn(pg)
    await pick(pg, 'hat', 'kite'); await main_btn(pg); await main_btn(pg); await pick(pg, 'hat', 'kite'); await main_btn(pg)
    check('forgot, no letter: back to step 1 with the letter asked for', await scr(pg) == 'e1' and await err(pg) == 'חסרה האות הראשונה של שם המשפחה. אות אחת, למשל כ.')
    await typ(pg, 'l', 'כ'); await main_btn(pg); await pick(pg, 'watermelon', 'drum'); await main_btn(pg)
    check('the new code typed before is kept', await pg.input_value('#si-p') == '4096')
    await main_btn(pg); await main_btn(pg); await main_btn(pg); await pick(pg, 'hat', 'kite'); await main_btn(pg)
    call = (await pg.evaluate('__calls'))[-1]
    check('recovered; the request: "דנה כ.", the new code and pictures', await pg.inner_text('.si-h') == 'הקוד החדש מוכן!' and call['f']['n'] == 'דנה כ.' and call['f']['newPics'] == [10, 8], call)
    # the page is left: the name and the letter go too (the next child at a class computer)
    await pg.evaluate('__mount()'); await tap(pg, '[data-si="start"][data-f="in"]'); await typ(pg, 'n', 'דנה'); await typ(pg, 'l', 'כ')
    await pg.evaluate("dispatchEvent(new PageTransitionEvent('pagehide'))"); await tap(pg, '[data-si="start"][data-f="in"]')
    check('after pagehide: no name and no letter left in the fields', await pg.input_value('#si-n') == '' and await pg.input_value('#si-l') == '')
    # the trial class (form 'first'): the first name alone, as before
    await pg.evaluate("__form=''; __mount()"); await tap(pg, '[data-si="start"][data-f="in"]')
    await typ(pg, 'c', CLASS); await typ(pg, 'n', 'דנה'); await keys(pg, '5831'); await main_btn(pg)
    check('a class of form "first": the first name alone goes, as before', (await pg.evaluate('__calls'))[-1] == {'kind': 'login', 'f': {'c': CLASS, 'n': 'דנה', 'code': '5831'}})
    check('no page error', not errs, errs)
    await c.close()


async def sizes(b):
    for w, h, cols in ((390, 844, 4), (360, 740, 4), (320, 568, 3)):
        c, pg, errs = await page(b, w, h, touch=True)
        for start, steps in (('reg', ['a1', 'a2', 'a3']), ('in', ['b']), ('rec', ['e1', 'e2'])):
            await pg.evaluate('__mount()'); await tap(pg, f'[data-si="start"][data-f="{start}"]')
            if start == 'reg':
                # A1 at its fullest: the name row, the hint, the name as it will appear, and the letter asked for
                await pg.evaluate("__form='first_initial'"); await typ(pg, 'c', CLASS); await typ(pg, 'n', 'נועה')
                await pg.evaluate("__next.push({ok:false,e:'name',form:'first_initial'})")
                await main_btn(pg); await typ(pg, 'p', '5831'); await typ(pg, 'p2', '5831'); await main_btn(pg)
                await pick(pg, 'apple', 'kite'); await main_btn(pg); await main_btn(pg); await pick(pg, 'apple', 'kite'); await main_btn(pg)
                m = await pg.evaluate("""()=>{const W=innerWidth,H=innerHeight,b=document.querySelector('.si-bar .wi-btn--block').getBoundingClientRect(),
                  n=document.querySelector('#si-n').getBoundingClientRect(),l=document.querySelector('#si-l').getBoundingClientRect(),e=document.querySelector('.si-err').getBoundingClientRect();
                  return {sideways:document.documentElement.scrollWidth>W,bar:b.bottom<=H,err:e.bottom<=b.top,row:Math.abs(n.top-l.top)<2&&l.right<=n.left,lw:Math.round(l.width),lh:Math.round(l.height)}}""")
                check(f'{w}x{h} a1 with the letter asked for: one row (first name at the right, the letter at its left), the message and the main button on screen, the letter field at least 44 px',
                      not m['sideways'] and m['bar'] and m['err'] and m['row'] and m['lw'] >= 44 and m['lh'] >= 44, m)
                await shot(pg, f'31-a1-letter-{w}')
                await typ(pg, 'l', 'כ'); await pg.evaluate("__form=''"); await main_btn(pg)
            for s in steps:
                if s == 'a3':
                    await typ(pg, 'p', '5831'); await typ(pg, 'p2', '5831'); await main_btn(pg)
                if s == 'e2':
                    await typ(pg, 'c', CLASS); await typ(pg, 'n', 'דנה'); await main_btn(pg)
                if await scr(pg) != s: continue
                m = await pg.evaluate("""()=>{const W=innerWidth,H=innerHeight,b=document.querySelector('.si-bar .wi-btn--block')?.getBoundingClientRect();
                  const small=[...document.querySelectorAll('.si button,.si input')].filter(e=>{const r=e.getBoundingClientRect(),cs=getComputedStyle(e);
                    return r.width&&cs.opacity!=='0'&&e.type!=='checkbox'&&(r.height<44||r.width<44)}).map(e=>(e.className||e.id)+':'+Math.round(e.getBoundingClientRect().width)+'x'+Math.round(e.getBoundingClientRect().height));
                  const tiles=[...document.querySelectorAll('.si-tile')].map(t=>Math.round(t.getBoundingClientRect().top)),row=tiles.length?tiles.filter(t=>t===tiles[0]).length:0;
                  return {sideways:document.documentElement.scrollWidth>W,bar:!!b&&b.bottom<=H&&b.top>=0,small,row,dir:getComputedStyle(document.querySelector('.si')).direction}}""")
                check(f'{w}x{h} {s}: right to left, no sideways scroll, the main button on screen, every target at least 44 px' + (f', {cols} tiles across' if s in ('a3', 'e2') else ''),
                      m['dir'] == 'rtl' and not m['sideways'] and m['bar'] and not m['small'] and (s not in ('a3', 'e2') or m['row'] == cols), m)
                if s in ('a2', 'a3') and w == 320: await shot(pg, f'30-{s}-320')
                if s == 'b':
                    check(f'{w}x{h} b on a phone: no on-screen keypad (the system keyboard types the code)', not await pg.locator('.si-pad').is_visible())
                    await shot(pg, f'32-b-phone-{w}')
        check(f'{w}x{h}: no page error', not errs, errs)
        await c.close()


async def unit(b):
    c, pg, errs = await page(b)
    r = await pg.evaluate("""()=>{const M=__M;return {
      weak:['1234','4321','0000','1212','1122','2015','1990','2512','1225','2580','7890','8901'].map(M.weak),
      ok:['5831','7302','4096','8574'].map(M.weak),
      pics:M.PICS.map(p=>[p.no,p.en,p.he]).slice(0,3).concat(M.PICS.map(p=>[p.no,p.en,p.he]).slice(-1)),
      n:M.PICS.length,unique:new Set(M.PICS.map(p=>p.en)).size,
      letters:['כ','ך','ם','k','K','.','7','','כה','ß','כ2','2כ','k.','כהן','כ1','k3'].map(M.letter),
      script:[['נועה','כ'],['נועה','K'],['Noa','K'],['Noa','כ'],['','K'],['נועה','']].map(([a,b])=>M.sameScript(a,b)),
      names:[['נועה','כ'],['בת אל','מ'],[' בת  אל ','ם'],['נועה כ.',''],['Noa k',''],['נועה',''],['בת אל',''],['נועה.','כ'],['דנה','ab'],['נועה כ2',''],['בת אל','']].map(([a,b])=>M.whoName(a,b).n)}}""")
    check('the screen refuses the codes the server calls weak (runs also across 9-0, repeats, abab, aabb, years, dates, keypad lines)', all(r['weak']) and not any(r['ok']), r)
    check('20 pictures, numbered 1 to 20 in the order of docs/SIGNIN.md (a contract with the server: never reorder)',
          r['n'] == 20 and r['unique'] == 20 and r['pics'] == [[1, 'apple', 'תפוח'], [2, 'banana', 'בננה'], [3, 'watermelon', 'אבטיח'], [20, 'mushroom', 'פטרייה']], r)
    check('the box: one Hebrew letter (a final form as its plain one) or one Latin capital, then only a digit 2-9 (the teacher\'s "כ2"); never a second letter, a dot, or a digit first',
          r['letters'] == ['כ', 'כ', 'מ', 'K', 'K', '', '', '', 'כ', '', 'כ2', 'כ', 'K', 'כ', 'כ', 'K3'], r['letters'])
    check('the letter takes the name\'s script', r['script'] == [True, False, True, False, True, True], r['script'])
    check('the name sent: "first letter." with the letter, the first name alone without; a space in the first name is a hyphen; a letter typed into the first name moves to its place',
          r['names'] == ['נועה כ.', 'בת-אל מ.', 'בת-אל מ.', 'נועה כ.', 'Noa K.', 'נועה', 'בת-אל', 'נועה כ.', 'דנה A.', 'נועה כ2.', 'בת-אל'], r['names'])
    files = await pg.evaluate("Promise.all(__M.PICS.flatMap(p=>[p.img,p.vox]).map(u=>fetch(u).then(r=>r.ok?0:u)))")
    check('every picture and every name clip is there', not [f for f in files if f], [f for f in files if f])
    await c.close()


async def record(b):
    """the whole flow at a child's pace, for the owner: register, sign in, forgot"""
    # frames from Chrome's screencast, joined by ffmpeg (Playwright's own recorder needs a binary it may not have)
    import base64, shutil, subprocess, time
    c, pg, errs = await page(b, 390, 844)
    frames = os.path.join(VIDEO, 'frames'); shutil.rmtree(frames, ignore_errors=True); os.makedirs(frames)
    cdp = await c.new_cdp_session(pg); got = []
    async def frame(e):
        n = len(got); open(os.path.join(frames, f'{n:05d}.jpg'), 'wb').write(base64.b64decode(e['data'])); got.append(time.monotonic())
        await cdp.send('Page.screencastFrameAck', {'sessionId': e['sessionId']})
    cdp.on('Page.screencastFrame', lambda e: asyncio.ensure_future(frame(e)))
    await cdp.send('Page.startScreencast', {'format': 'jpeg', 'quality': 85, 'maxWidth': 780, 'maxHeight': 1688, 'everyNthFrame': 1})
    P_ = 700
    await pg.wait_for_timeout(1200)
    await tap(pg, '[data-si="start"][data-f="reg"]', P_)
    await typ(pg, 'c', CLASS, P_); await typ(pg, 'n', 'נועה', P_); await main_btn(pg, P_)
    await keys(pg, '1234', 1); await keys(pg, '1234', 1); await main_btn(pg, 1800)
    await keys(pg, '5831', 1); await keys(pg, '5831', 1); await main_btn(pg, P_)
    await pick(pg, 'kite', 'drum', pause=P_); await main_btn(pg, 3500)
    await main_btn(pg, P_)
    await pick(pg, 'drum', 'kite', pause=P_); await main_btn(pg, 1800)
    await pick(pg, 'kite', 'drum', pause=P_); await main_btn(pg, 2500)
    await main_btn(pg, 800)
    await pg.evaluate('__mount()'); await pg.wait_for_timeout(1000)
    await tap(pg, '[data-si="start"][data-f="in"]', P_)
    await typ(pg, 'c', CLASS, 300); await typ(pg, 'n', 'נועה', 300); await keys(pg, '5830', 1); await main_btn(pg, 1800)
    await pg.evaluate("__next.push({ok:false,e:'locked',by:'name',help:'teacher',wait:300})"); await keys(pg, '5830', 1); await main_btn(pg, 3000)
    await keys(pg, '5831', 1); await main_btn(pg, 800)
    await pg.evaluate('__mount()'); await pg.wait_for_timeout(1000)
    await tap(pg, '[data-si="start"][data-f="rec"]', P_)
    await typ(pg, 'c', CLASS, 300); await typ(pg, 'n', 'נועה', 300); await main_btn(pg, P_)
    await pick(pg, 'drum', 'kite', pause=P_); await main_btn(pg, P_)
    await keys(pg, '7302', 1); await keys(pg, '7302', 1); await main_btn(pg, P_)
    await pick(pg, 'hat', 'grapes', pause=P_); await main_btn(pg, 2500); await main_btn(pg, P_)
    await pick(pg, 'hat', 'grapes', pause=P_); await main_btn(pg, 2000)
    await pick(pg, 'kite', 'drum', pause=P_); await main_btn(pg, P_)
    await main_btn(pg, P_); await main_btn(pg, P_); await main_btn(pg, P_); await pick(pg, 'hat', 'grapes', pause=P_); await main_btn(pg, 3000)
    await pg.wait_for_timeout(500); await cdp.send('Page.stopScreencast'); await c.close()
    got.append(got[-1] + 1.5)
    lst = os.path.join(VIDEO, 'frames.txt')
    with open(lst, 'w') as f:
        for i in range(len(got) - 1):
            f.write(f"file 'frames/{i:05d}.jpg'\nduration {got[i + 1] - got[i]:.3f}\n")
        f.write(f"file 'frames/{len(got) - 2:05d}.jpg'\n")
    out = os.path.join(VIDEO, 'signin-flow.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf', 'scale=780:-2,fps=30', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '24', out], cwd=VIDEO, check=True)
    print('video:', out, len(got) - 1, 'frames')


async def main():
    procs = P.start_servers(mock=False)
    try:
        async with async_playwright() as pw:
            # the back-forward cache on (Playwright turns it off by default): Back must find no code typed (secrets_gone)
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'], ignore_default_args=['--disable-back-forward-cache'])
            if VIDEO:
                await record(b)
            else:
                await unit(b); await register_flow(b); await register_refusals(b); await sign_in(b); await recover(b); await letter_form(b); await secrets_gone(b); await quiet_names(b); await sizes(b)
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
