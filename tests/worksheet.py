#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The printable worksheet (worksheet.html), behind its switch.

    python3 tests/worksheet.py              # phone, laptop
    python3 tests/worksheet.py --shots DIR  # also save PNGs of the screens and of every printed page

Checks: with the switch off nothing of it shows; with it on, every island's sheet holds exactly the words, story and
sentences of js/data.js and its answer page is right; it prints on light paper in at most two pages (three with the
answers) with nothing cut off; it shows nothing of the pupil, saves nothing and asks no other host for anything."""
import asyncio, json, os, subprocess, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, port_open, fails

ROOT_URL = f'http://127.0.0.1:{P.PORT}/'
SET_KEY = 'word-islands-settings-v1'
PUPIL = 'זזטופעזז'      # a made-up name that is in no content: it must never reach the sheet

# the sheet's model against the game's content, computed in the page from the same modules
MODEL = """(async id=>{const D=await import('/js/data.js'),W=await import('/js/worksheet.js');
 const m=W.build(id),isl=D.ISLANDS.find(i=>i.id===id),bad=[];
 const parts=isl.bonus?[6,7]:[id],same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),sorted=a=>[...a].sort();
 const L='אבגדהוזחטיכלמנסעפצקרשת';
 const match=m.ex.filter(x=>x.kind==='match');
 if(match.length!==parts.length)bad.push('match count');
 parts.forEach((p,k)=>{const w=D.RAW[p].split(';').map(s=>s.split('|')),x=match[k];
  if(!same(x.left,w.map(a=>a[0])))bad.push('english words of part '+p);
  if(!same(sorted(x.right),sorted(w.map(a=>a[1]))))bad.push('hebrew words of part '+p);
  if(same(x.right,w.map(a=>a[1])))bad.push('part '+p+' is not mixed');
  w.forEach((a,i)=>{const ls=x.key[i].split(' / ');if(!ls.length||!ls.every(l=>x.right[L.indexOf(l)]===a[1]))bad.push('key of '+a[0])})});
 const kinds=m.ex.map(x=>x.kind).join();
 if(isl.bonus){if(kinds!=='match,match')bad.push('kinds '+kinds)}
 else{if(kinds!=='match,read,tobe,order')bad.push('kinds '+kinds);
  const t=D.TEXTS.find(x=>x.p===id),r=m.ex[1];
  if(r.text!==t.text||r.name!==t.title||r.qs.length!==t.qs.length)bad.push('story');
  t.qs.forEach(([q,o,a],k)=>{const y=r.qs[k];if(y.q!==q||!same(sorted(y.o),sorted(o))||y.o[y.a]!==o[a])bad.push('question '+k)});
  if(new Set(r.qs.map(q=>q.a)).size<2)bad.push('the right answer is always in the same place');
  const tb=D.TOBE_BY[id],f=m.ex[2];
  if(!same(f.items.map(i=>[i.s,i.a]),tb))bad.push('am is are');
  const st=D.SENT[id],o=m.ex[3];
  st.forEach(([s,he],k)=>{const y=o.items[k],plain=s.replace(/[.?!]$/,'');
   if(y.a!==s||y.he!==he||!same(sorted(y.words),sorted(plain.split(' ')))||y.words.join(' ')+y.end===s)bad.push('sentence '+k)})}
 return {bad,again:same(m,W.build(id))}})"""

LAYOUT = """(()=>{const de=document.documentElement,cs=e=>getComputedStyle(e);
 const lum=c=>{const m=c.match(/[\\d.]+/g).map(Number);return m.length>3&&m[3]===0?null:(.2126*m[0]+.7152*m[1]+.0722*m[2])/255};
 const dark=[...document.querySelectorAll('#sheet,#sheet *')].filter(e=>{const l=lum(cs(e).backgroundColor);return l!==null&&l<.85}).length;
 const pics=[...document.querySelectorAll('#sheet *')].filter(e=>cs(e).backgroundImage!=='none').length+document.querySelectorAll('#sheet img,#sheet svg,#sheet canvas').length;
 const pale=[...document.querySelectorAll('#sheet *')].filter(e=>e.children.length===0&&e.textContent.trim()&&lum(cs(e).color)>.45).length;
 const P=document.querySelector('.page').getBoundingClientRect();
 const out=[...document.querySelectorAll('#sheet *')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&(r.left<P.left-1||r.right>P.right+1)}).length;
 return {over:de.scrollWidth-de.clientWidth,dark,pics,pale,out,body:lum(cs(document.body).backgroundColor),bar:cs(document.getElementById('bar')).display}})()"""


def pdf_pages(data):
    import re
    return len(re.findall(rb'/Type\s*/Page(?![s])', data))


async def run(b, w, h, errs, tag, do_print):
    c, pg = await new_page(b, w, h, errs=errs)
    dialogs = []
    pg.on('dialog', lambda d: (dialogs.append(d.message), asyncio.ensure_future(d.dismiss())))

    # ---- switch off: the game and the page show nothing of it ----
    await pg.goto(P.BASE + '#island/1')
    await pg.wait_for_selector('.scr.island')
    check(f'{tag} off: the island has no worksheet link', await pg.locator('.wsl').count() == 0)
    await pg.goto(ROOT_URL + 'worksheet.html?i=1')
    await pg.wait_for_selector('#off:not([hidden])')
    check(f'{tag} off: the page says it is not open here and draws no sheet',
          await pg.evaluate("document.getElementById('sheet').children.length===0&&getComputedStyle(document.getElementById('bar')).display==='none'&&document.getElementById('bar').getBoundingClientRect().height===0&&getComputedStyle(document.getElementById('off')).display!=='none'"))
    back = await pg.get_attribute('#off a', 'href')
    check(f'{tag} off: it links back to the game', back == 'index.html#island/1', back)

    # ---- the switch: ?sheet=1 once ----
    await pg.goto(P.BASE + '?sheet=1#island/1')
    await pg.wait_for_selector('.scr.island')
    check(f'{tag} ?sheet=1 gives the device the switch', await pg.evaluate(f"JSON.parse(localStorage.getItem('{SET_KEY}')).sheet===true"))
    await pg.goto(P.BASE + '#island/1')
    await pg.wait_for_selector('.wsl')
    link = await pg.evaluate("(()=>{const a=document.querySelector('.wsl'),r=a.getBoundingClientRect(),s=document.getElementById('stage').getBoundingClientRect();return {href:a.getAttribute('href'),h:r.height,w:r.width,inside:r.left>=s.left&&r.right<=s.right,text:a.textContent}})()")
    check(f'{tag} on: the island links to its own sheet', link['href'] == 'worksheet.html?i=1' and link['text'] == 'דף עבודה להדפסה', link)
    check(f'{tag} on: the link is big enough to press and inside the screen', link['h'] >= 44 and link['w'] >= 44 and link['inside'], link)
    over = await pg.evaluate("(()=>{const v=document.getElementById('view');return [...v.querySelectorAll('.lvrow,.wsl,.chip,.guide')].filter(e=>{const r=e.getBoundingClientRect(),s=document.getElementById('stage').getBoundingClientRect();return r.bottom>s.bottom+1||r.top<s.top-1}).length})()")
    check(f'{tag} on: the island screen still fits', over == 0, over)
    await P.shot(pg, f'{tag}-island-link')

    # a pupil is known on this device: nothing of them may reach the sheet
    await pg.evaluate(f"(()=>{{const s=JSON.parse(localStorage.getItem('{P_KEY}')||'{{}}');s.u={{c:'x',n:'{PUPIL}',p:'0000'}};s.me=['{PUPIL}'];localStorage.setItem('{P_KEY}',JSON.stringify(s))}})()")
    before = await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())")
    await pg.goto(ROOT_URL + 'worksheet.html?i=1')
    await pg.wait_for_selector('#sheet .page')
    await pg.evaluate('document.fonts.ready')

    # ---- every island ----
    for i in range(1, 7):
        await pg.goto(ROOT_URL + f'worksheet.html?i={i}')
        await pg.wait_for_selector('#sheet .page')
        await pg.evaluate('document.fonts.ready')
        m = await pg.evaluate(MODEL + f'({i})')
        check(f'{tag} island {i}: the sheet holds exactly the content of js/data.js and its answers are right', not m['bad'], m['bad'][:5])
        check(f'{tag} island {i}: the same sheet every time', m['again'])
        html1 = await pg.inner_html('#sheet')
        await pg.reload()
        await pg.wait_for_selector('#sheet .page')
        await pg.evaluate('document.fonts.ready')
        check(f'{tag} island {i}: drawn the same after a reload', await pg.inner_html('#sheet') == html1)
        lay = await pg.evaluate(LAYOUT)
        check(f'{tag} island {i}: on screen nothing is cut off or outside the paper', lay['over'] <= 0 and lay['out'] == 0, lay)
        check(f'{tag} island {i}: light paper, dark text, no pictures', lay['dark'] == 0 and lay['pics'] == 0 and lay['pale'] == 0, lay)
        if i < 6:
            g = await pg.evaluate("""(()=>{const bad=[];for(const gp of document.querySelectorAll('.fill .gap')){const t=gp.previousSibling,r=document.createRange();
              if(!t||!t.textContent.trim())continue;const n=t.textContent.replace(/\\s+$/,'').length;r.setStart(t,n-1);r.setEnd(t,n);const a=r.getBoundingClientRect(),b=gp.getBoundingClientRect();
              if(b.bottom<a.top||b.bottom>a.bottom+2)bad.push(gp.parentElement.textContent)}
             const o=[...document.querySelectorAll('.ord>li')],nums=o.map(l=>getComputedStyle(l.querySelector('.he'),'::before').content);
             const r0=o[0].getBoundingClientRect(),r1=o[1].getBoundingClientRect();
             return {bad,numbered:nums.every(c=>/counter\\(o\\)|\\d/.test(c)),rtl:r0.top!==r1.top||r0.left>r1.left,n:document.querySelectorAll('.fill .gap').length}})()""")
            check(f'{tag} island {i}: every gap sits on the line of the words before it, also when the sentence wraps', g['n'] >= 4 and not g['bad'], g)
            check(f'{tag} island {i}: the sentences to order are numbered and run from the right', g['numbered'] and g['rtl'], g)
        text = await pg.inner_text('body')
        check(f'{tag} island {i}: nothing of the pupil is on the page', PUPIL not in text and PUPIL not in await pg.content())
        check(f'{tag} island {i}: no answer page unless asked', await pg.locator('#key').count() == 0)
        if i in (1, 6):
            await P.shot(pg, f'{tag}-sheet-{i}')
        if do_print:
            await pg.emulate_media(media='print')
            lay = await pg.evaluate(LAYOUT)
            check(f'{tag} island {i}: in print the bar is gone, the page is white and nothing is outside the paper',
                  lay['bar'] == 'none' and lay['body'] > .99 and lay['out'] == 0 and lay['dark'] == 0, lay)
            n = pdf_pages(await pg.pdf(prefer_css_page_size=True, print_background=True))
            check(f'{tag} island {i}: prints on at most two pages', 1 <= n <= 2, n)
            await pg.emulate_media(media='screen')
            await pg.check('#key-on')
            await pg.wait_for_selector('#key')
            await pg.emulate_media(media='print')
            data = await pg.pdf(prefer_css_page_size=True, print_background=True)
            n2 = pdf_pages(data)
            check(f'{tag} island {i}: the answers start on their own page', n2 == n + 1, (n, n2))
            if P.SHOTS:
                os.makedirs(P.SHOTS, exist_ok=True)
                open(os.path.join(P.SHOTS, f'sheet-{i}.pdf'), 'wb').write(data)
            await pg.emulate_media(media='screen')

    # ---- the bar ----
    await pg.goto(ROOT_URL + 'worksheet.html?i=2')
    await pg.wait_for_selector('#sheet .page')
    small = await pg.evaluate("[...document.querySelectorAll('#bar a,#bar button,#bar label')].filter(e=>e.getBoundingClientRect().height<44).length")
    check(f'{tag} bar: every control is at least 44 px high', small == 0, small)
    await pg.select_option('#pick', '4')
    await pg.wait_for_function("document.querySelector('#sheet h1').textContent==='אי יום ההולדת'")
    check(f'{tag} bar: choosing another island draws its sheet and keeps the way back',
          await pg.get_attribute('#bar a', 'href') == 'index.html#island/4' and pg.url.endswith('?i=4'), pg.url)
    await pg.evaluate("window.__printed=0;window.print=()=>{window.__printed++};0")
    await pg.click('#go')
    check(f'{tag} bar: the print button asks the browser to print', await pg.evaluate('window.__printed') == 1)

    # ---- odd addresses ----
    for q in ('', '?i=99', '?i=0', '?i=abc', '?i=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E', '?i=1%27%22%3E%3Cscript%3Ealert(1)%3C/script%3E'):
        await pg.goto(ROOT_URL + 'worksheet.html' + q)
        await pg.wait_for_selector('#sheet .page')
        ok = await pg.evaluate("document.querySelector('#sheet h1').textContent==='אי התחביבים'&&!document.querySelector('#sheet img,#sheet script')")
        check(f'{tag} address "{q}": the first island, and nothing from the address is drawn', ok and not dialogs, dialogs)

    after = await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())")
    check(f'{tag} the worksheet saved nothing on the device', before == after)

    # ---- taking the switch away ----
    await pg.goto(P.BASE + '?sheet=0#island/1')
    await pg.wait_for_selector('.scr.island')
    check(f'{tag} ?sheet=0 takes the switch away', await pg.locator('.wsl').count() == 0 and await pg.evaluate(f"JSON.parse(localStorage.getItem('{SET_KEY}')).sheet===false"))
    await pg.goto(ROOT_URL + 'worksheet.html?i=1')
    await pg.wait_for_selector('#off:not([hidden])')
    check(f'{tag} and the page is closed again, with no bar', await pg.evaluate("document.getElementById('sheet').children.length===0&&getComputedStyle(document.getElementById('bar')).display==='none'"))
    await c.close()


P_KEY = 'aam-unit1-v1'


async def main():
    procs = P.start_servers(mock=False)      # its own servers on free ports (tests/play.py)
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            await run(b, 390, 844, errs, 'phone', False)
            await run(b, 1366, 768, errs, 'laptop', True)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors, failed requests or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
