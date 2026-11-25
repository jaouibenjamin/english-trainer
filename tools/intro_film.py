#!/usr/bin/env python3
"""Builds the welcome film from its title-less master: renders the closing title, puts it on the frozen last shot, and
encodes the two files the game plays. Free to re-run (no generation), e.g. when the platform is renamed.

    python3 tools/intro_film.py MASTER OUTDIR [--l1 "ברוכים הבאים"] [--l2 "לניצני אופק!"] [--at 34.0]

MASTER is assets/al/intro/master.*.mp4 (540 x 982, the final sound mix, no title). Writes OUTDIR/full.mp4 (540 x 982,
about 1.8 Mbit/s, the default) and OUTDIR/light.mp4 (390 x 710, about 3 MB, for phones on slow or saved-data
connections), and prints their sizes and sha256 for assets/al/sources.tsv.

The title: "ברוכים הבאים" in Rubik Bubbles (aqua, glowing), "לניצני אופק!" in Rubik Moonrocks (gold with moon craters),
each letter popping in, then a glint passing over them. Fonts: Google Fonts, SIL Open Font License, loaded at render
time; only pictures of them end up in the film. Needs ffmpeg, Playwright and Chrome (/usr/bin/google-chrome).
"""
import argparse, asyncio, hashlib, os, subprocess, sys, tempfile

TPL = """<!doctype html><html dir="rtl"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Rubik+Bubbles&family=Rubik+Moonrocks&display=block" rel="stylesheet">
<style>
html,body{margin:0;background:transparent}
.box{width:540px;height:330px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;position:relative;overflow:hidden}
.r{white-space:nowrap;direction:rtl}
.a,.b{display:inline-block;opacity:0;animation:pop .55s cubic-bezier(.2,1.6,.4,1) both}
.r:first-child .sp{display:inline-block;width:16px}.r:nth-child(2) .sp{display:inline-block;width:26px}
.a{font:400 46px 'Rubik Bubbles';color:#9FFBEA;filter:drop-shadow(0 2px 0 #0b4f63) drop-shadow(0 0 10px rgba(46,230,197,.85))}
.b{font:400 74px 'Rubik Moonrocks';background:linear-gradient(#FFF6C8,#FFD23F 45%,#FF9A3C);-webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 4px 0 #7a2e0b) drop-shadow(0 0 2px #2a1000) drop-shadow(0 0 16px rgba(255,170,60,.8))}
@keyframes pop{0%{opacity:0;transform:translateY(-60px) scale(.2) rotate(-25deg)}60%{opacity:1;transform:translateY(6px) scale(1.18) rotate(6deg)}100%{opacity:1;transform:none}}
.shine{position:absolute;inset:0;background:linear-gradient(105deg,transparent 40%,rgba(255,255,255,.75) 50%,transparent 60%);mix-blend-mode:overlay;transform:translateX(-120%);animation:sh .7s ease-in-out 1.75s both}
@keyframes sh{to{transform:translateX(120%)}}
</style></head><body><div class="box" id="box"><div class="r">L1</div><div class="r">L2</div><div class="shine"></div></div></body></html>"""


def spans(s, cls, d0, step):
    out, i = [], 0
    for ch in s:
        if ch == ' ':
            out.append('<span class="sp"> </span>'); continue
        out.append(f'<span class="{cls}" style="animation-delay:{d0 + i * step:.3f}s">{ch}</span>'); i += 1
    return ''.join(out)


async def frames(html, outdir, n=78):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=os.environ.get('CHROME', '/usr/bin/google-chrome'))
        pg = await b.new_page(viewport={'width': 540, 'height': 330})
        await pg.set_content(html); await pg.wait_for_timeout(2500)
        await pg.evaluate("document.getAnimations().forEach(a=>a.pause())")
        for k in range(n):
            await pg.evaluate(f"document.getAnimations().forEach(a=>a.currentTime={k / 30 * 1000})")
            await pg.locator('#box').screenshot(path=os.path.join(outdir, f'{k:03d}.png'), omit_background=True)
        await b.close()


def run(*a):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *a], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('master'); ap.add_argument('outdir')
    ap.add_argument('--l1', default='ברוכים הבאים'); ap.add_argument('--l2', default='לניצני אופק!')
    ap.add_argument('--at', type=float, default=34.0, help='second at which the title starts')
    o = ap.parse_args()
    os.makedirs(o.outdir, exist_ok=True)
    html = TPL.replace('L1', spans(o.l1, 'a', 0, 0.05)).replace('L2', spans(o.l2, 'b', 0.55, 0.07))
    with tempfile.TemporaryDirectory() as td:
        asyncio.run(frames(html, td))
        y = int(982 * 0.2 - 165)
        ov = f"[1:v]format=rgba,setpts=PTS-STARTPTS+{o.at}/TB[t];[0:v][t]overlay=0:{y}:eof_action=repeat:format=auto,format=yuv420p"
        full = os.path.join(o.outdir, 'full.mp4'); light = os.path.join(o.outdir, 'light.mp4')
        run('-i', o.master, '-framerate', '30', '-i', os.path.join(td, '%03d.png'), '-filter_complex', ov + '[v]', '-map', '[v]', '-map', '0:a',
            '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-crf', '21', '-maxrate', '1800k', '-bufsize', '3600k',
            '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', full)
        run('-i', o.master, '-framerate', '30', '-i', os.path.join(td, '%03d.png'), '-filter_complex', ov + ',scale=390:710:flags=lanczos[v]', '-map', '[v]', '-map', '0:a',
            '-c:v', 'libx264', '-profile:v', 'main', '-preset', 'slow', '-b:v', '520k', '-maxrate', '700k', '-bufsize', '1400k',
            '-c:a', 'aac', '-b:a', '96k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', light)
    for f in (full, light):
        print(f, os.path.getsize(f), hashlib.sha256(open(f, 'rb').read()).hexdigest())


if __name__ == '__main__':
    sys.exit(main())
