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
const roster = new Set(['נועה', 'יואב', 'דנה', 'דנה ב']), pupils = new Map([['דנה', {code: '5831', pics: [3, 9]}]]);
const otc = {'דנה': '482913'}, tries = {};
W.__enter = async (kind, f) => {
  W.__calls.push({kind, f: JSON.parse(JSON.stringify(f))});
  await new Promise(r => setTimeout(r, 120));
  if (W.__next.length) return W.__next.shift();
  if (f.c !== '""" + CLASS + """') return {ok: false, e: 'class'};
  if (kind === 'register') {
    if (!roster.has(f.n)) return {ok: false, e: 'roster'};
    if (pupils.has(f.n)) return {ok: false, e: 'taken'};
    pupils.set(f.n, {code: f.code, pics: f.pics}); return {ok: true};
  }
  const p = pupils.get(f.n);
  if (kind === 'login') return p && p.code === f.code ? {ok: true} : {ok: false, e: 'pin'};
  if (kind === 'recover') {
    if (f.otc !== undefined) { if (!p || otc[f.n] !== f.otc) return {ok: false, e: 'otc'}; }
    else {
      if ((tries[f.n] || 0) >= 3) return {ok: false, e: 'locked', wait: -1, by: 'name', help: 'teacher'};
      if (!p || p.pics.join('>') !== f.pics.join('>')) { tries[f.n] = (tries[f.n] || 0) + 1; return {ok: false, e: 'picture'}; }
    }
    p.code = f.newCode; p.pics = f.newPics; return {ok: true};
  }
  return {ok: false, e: 'net'};
};
W.__mount = () => { if (W.__si) W.__si.destroy(); W.__si = M.mount(document.getElementById('view'), {enter: W.__enter, done: () => { W.__done++; }, sound: () => false, lastC: ''}); };
W.__mount();
</script></body></html>"""
NO = {'apple': 1, 'banana': 2, 'watermelon': 3, 'cactus': 4, 'grapes': 5, 'flower': 6, 'umbrella': 7, 'kite': 8, 'drum': 9, 'hat': 10}


async def page(b, w=390, h=844):
    c = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, has_touch=True, locale='he-IL')
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
    check('a name not on the class list: back to step 1 with the message, the name kept', await scr(pg) == 'a1' and await err(pg) == 'השם הזה לא ברשימת הכיתה. בקשו מהמורה להוסיף אותו.' and await pg.input_value('#si-n') == 'גלעד')
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
]


async def sign_in(b):
    c, pg, errs = await page(b)
    await tap(pg, '[data-si="start"][data-f="in"]')
    check('sign in: "נכנסים", class code, name, code and keypad on one screen', await scr(pg) == 'b' and await pg.inner_text('.si-h') == 'נכנסים' and await pg.locator('.si-key').count() == 11)
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
    check('wrong pictures: back to step 2, "אפשר לנסות עוד 2 פעמים"', await scr(pg) == 'e2' and await err(pg) == 'לא התאים. אפשר לנסות עוד 2 פעמים.')
    call = (await pg.evaluate('__calls'))[-1]
    check('the request: class, name, the old pictures, the new code and pictures', call == {'kind': 'recover', 'f': {'c': CLASS, 'n': 'דנה', 'pics': [9, 1], 'newCode': '7302', 'newPics': [10, 5]}}, call)
    await pick(pg, 'apple', 'drum'); await main_btn(pg)
    check('the new code is kept for the next try', await pg.input_value('#si-p') == '7302')
    await main_btn(pg); await main_btn(pg); await main_btn(pg); await pick(pg, 'hat', 'grapes'); await main_btn(pg)
    check('second wrong try: "ניסיון אחרון"', await err(pg) == 'ניסיון אחרון. קחו רגע לחשוב על הסדר.')
    await pick(pg, 'kite', 'apple'); await main_btn(pg); await main_btn(pg); await main_btn(pg); await main_btn(pg); await pick(pg, 'hat', 'grapes'); await main_btn(pg)
    check('third: closed, the teacher will help; no pictures to tap, only "קיבלתי קוד מהמורה"', await err(pg) == 'הפעם התמונות לא עבדו. המורה תעזור לכם עם קוד חדש.' and await pg.locator('.si-tile').count() == 0 and await pg.locator('[data-si="otc"]').count() == 1)
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


async def sizes(b):
    for w, h, cols in ((390, 844, 4), (360, 740, 4), (320, 568, 3)):
        c, pg, errs = await page(b, w, h)
        for start, steps in (('reg', ['a1', 'a2', 'a3']), ('in', ['b']), ('rec', ['e1', 'e2'])):
            await pg.evaluate('__mount()'); await tap(pg, f'[data-si="start"][data-f="{start}"]')
            if start == 'reg':
                await typ(pg, 'c', CLASS); await typ(pg, 'n', 'נועה'); await main_btn(pg)
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
        check(f'{w}x{h}: no page error', not errs, errs)
        await c.close()


async def unit(b):
    c, pg, errs = await page(b)
    r = await pg.evaluate("""()=>{const M=__M;return {
      weak:['1234','4321','0000','1212','1122','2015','1990','2512','1225','2580','7890','8901'].map(M.weak),
      ok:['5831','7302','4096','8574'].map(M.weak),
      pics:M.PICS.map(p=>[p.no,p.en,p.he]).slice(0,3).concat(M.PICS.map(p=>[p.no,p.en,p.he]).slice(-1)),
      n:M.PICS.length,unique:new Set(M.PICS.map(p=>p.en)).size}}""")
    check('the screen refuses the codes the server calls weak (runs also across 9-0, repeats, abab, aabb, years, dates, keypad lines)', all(r['weak']) and not any(r['ok']), r)
    check('20 pictures, numbered 1 to 20 in the order of docs/SIGNIN.md (a contract with the server: never reorder)',
          r['n'] == 20 and r['unique'] == 20 and r['pics'] == [[1, 'apple', 'תפוח'], [2, 'banana', 'בננה'], [3, 'watermelon', 'אבטיח'], [20, 'mushroom', 'פטרייה']], r)
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
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            if VIDEO:
                await record(b)
            else:
                await unit(b); await register_flow(b); await register_refusals(b); await sign_in(b); await recover(b); await sizes(b)
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
