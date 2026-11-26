#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""Voice clips of the Arcade Lagoon art (assets/al/voice/): every clip is levelled the same, so no word is louder than
the next one.

    python3 tests/voice_level.py

Every clip listed in assets/al/sources.tsv as al-voice exists, matches its sha256, is mono MP3 at 44.1 or 48 kHz (a
96 kHz track crackled on phones, docs/LESSONS.md), at most 5 s, and measures -16 LUFS within 1 LU with a true peak at
or below -1 dBTP (ffmpeg's ebur128). Needs ffmpeg."""
import hashlib, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check(label, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + label + (f' {extra}' if extra != '' and not ok else ''))
    if not ok:
        fails.append(label)


def main():
    lines = open(os.path.join(ROOT, 'assets/al/sources.tsv'), encoding='utf-8').read().split('\n')
    head = lines[0].split('\t')
    rows = [dict(zip(head, ln.split('\t'))) for ln in lines[1:] if ln]
    clips = [r for r in rows if r['kind'] == 'al-voice']
    check('there are voice clips to check', len(clips) > 0, len(clips))
    for r in clips:
        p = os.path.join(ROOT, 'assets', r['file'])
        name = os.path.basename(p).split('.')[0]
        if not os.path.isfile(p):
            check(f'{name}: the file exists', False, r['file'])
            continue
        check(f'{name}: sha256 as listed', hashlib.sha256(open(p, 'rb').read()).hexdigest() == r['sha256'])
        info = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,sample_rate,channels:format=duration',
                               '-of', 'default=nw=1', p], capture_output=True, text=True).stdout
        kv = dict(ln.split('=', 1) for ln in info.split('\n') if '=' in ln)
        check(f'{name}: mono MP3 at 44.1 or 48 kHz, at most 5 s', kv.get('codec_name') == 'mp3' and kv.get('channels') == '1'
              and kv.get('sample_rate') in ('44100', '48000') and float(kv.get('duration', 99)) <= 5, kv)
        err = subprocess.run(['ffmpeg', '-nostats', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                             capture_output=True, text=True).stderr
        i = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', err)[-1])
        tp = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', err)[-1])
        check(f'{name}: -16 LUFS within 1 LU, true peak at most -1 dBTP', abs(i + 16) <= 1 and tp <= -1, [i, tp])
    print('ALL PASSED' if not fails else f'{len(fails)} FAILED: ' + '; '.join(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
