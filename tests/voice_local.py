#!/usr/bin/env python3
"""Builds the voice files the game plays from our own site, from the manifest assets/voice/sources.tsv.

    python3 tests/voice_local.py build  --cache DIR [--base URL]   # download (into DIR, outside the repo), trim, encode, write js/voice.js
    python3 tests/voice_local.py verify --cache DIR   # decode every local file and check it holds the same stretch as the source
    python3 tests/voice_local.py pin                  # only rewrite the sha256 column from the files on disk (no download)

The manifest is the source of truth. One row per spoken text, columns:
    kind     voice-en (an English clip) or narr-he (a Hebrew narration line of the mock exam)
    file     the local file, relative to assets/voice/
    src_sha256  of the original (written by the first build; after that a download or a cached file that differs is refused).
             The original has the local file's name with .wav (English) or .mp3 (Hebrew), in the owner's storage;
             the address of that storage is not kept in this repo (tests/storage.py: --base or WI_STORAGE_BASE)
    src_s, src_e  the measured clean stretch inside the original, in ms (0,0 = the whole file); written by tests/voice_map.py
    s, e     the same stretch inside the local file, in ms (written by build)
    sha256   of the local file as it is served (written by build; tests/play.py fails if a file on disk differs)
    text     what the clip says
English: the original (24 kHz stereo WAV) is mixed to mono the way the player mixes it (mean of the channels), cut to
the stretch plus PAD ms on each side (clamped to the file) and encoded as mono MP3 (plays on old iPhones and cheap
Androids). The player cuts [s-30 ms, e+80 ms] out of the decoded file (js/state.js), so the pad must stay above 80 ms;
it is 150 ms so a decoder that ignores the MP3 encoder delay (about 46 ms) still finds the whole stretch inside the file.
Two texts that share one original (e.g. "their" / "Their") share one local file.
Hebrew: the original MP3 is copied byte for byte.
Downloaded files are untrusted: only the one storage host is fetched, a redirect is refused (never followed), and only
real WAV / MP3 data is accepted. Every local file is pinned by its sha256 in the manifest.
Needs ffmpeg with libmp3lame (free) and numpy."""
import hashlib, json, os, re, subprocess, sys, urllib.error, urllib.request, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = os.path.join(ROOT, 'assets', 'voice')
MANIFEST = os.path.join(VOICE, 'sources.tsv')
COLS = ['kind', 'file', 'src_sha256', 'src_s', 'src_e', 's', 'e', 'sha256', 'text']
SRC_EXT = {'voice-en': '.wav', 'narr-he': '.mp3'}      # the original's extension
PAD = 150           # ms of the original kept on each side of the stretch
LEAD, TAIL = 30, 80  # what the player plays around the stretch (js/state.js)
RATE, KBPS = 24000, 64
FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
FILE_RE = re.compile(r'(en|he)/[A-Za-z0-9_-]+\.mp3')   # a local file: one plain name inside en/ or he/, nothing else
KINDS = {'voice-en': 'en/', 'narr-he': 'he/'}


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def read_manifest():
    """plain tab-separated text, no quoting: a text never holds a tab or a line break"""
    lines = open(MANIFEST, encoding='utf-8').read().split('\n')
    assert lines[0].split('\t') == COLS and lines[-1] == '', 'bad manifest header'
    rows = [dict(zip(COLS, ln.split('\t'))) for ln in lines[1:-1]]
    for r in rows:
        assert len(r) == len(COLS), r
        for k in ('src_s', 'src_e', 's', 'e'):
            r[k] = int(r[k] or 0)
        # every command trusts these names as paths below assets/voice/, so they are checked wherever the manifest is read
        assert r['kind'] in KINDS and FILE_RE.fullmatch(r['file']) and r['file'].startswith(KINDS[r['kind']]), r['file']
        assert re.fullmatch(r'[0-9a-f]{64}|', r['sha256']) and re.fullmatch(r'[0-9a-f]{64}|', r['src_sha256']), (r['sha256'], r['src_sha256'])
    return rows


def write_manifest(rows):
    for r in rows:
        assert not any(c in str(r[k]) for k in COLS for c in '\t\r\n'), r
    with open(MANIFEST, 'w', encoding='utf-8', newline='') as f:
        f.write('\t'.join(COLS) + '\n' + ''.join('\t'.join(str(r[k]) for k in COLS) + '\n' for r in rows))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """a redirect is an error: no request ever goes to a host the storage points us to"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, 'redirect refused: ' + str(newurl), headers, fp)


OPENER = urllib.request.build_opener(NoRedirect)


BASE = None      # the storage folder's address, when one was given (tests/storage.py)


def fetch(r, cache):
    """the path of a row's original: from the cache, or downloaded into it. Either way it must match the row's src_sha256
    when the list has one (the first build writes it)."""
    name = os.path.basename(r['file'])[:-4] + SRC_EXT[r['kind']]
    path = os.path.join(cache, name)
    if not os.path.exists(path):
        url = storage.url(BASE, name)
        with OPENER.open(url, timeout=60) as resp:
            if resp.status != 200 or resp.geturl() != url:
                raise SystemExit(f'{name}: the storage did not answer with the file')
            data = resp.read(50_000_001)
        if len(data) > 50_000_000:
            raise SystemExit(f'{name}: larger than the cap')
        open(path + '.part', 'wb').write(data)
        os.replace(path + '.part', path)
    if r['src_sha256'] and sha256(path) != r['src_sha256']:
        raise SystemExit(f'{name}: the original in the cache differs from src_sha256 in the list (delete it from the cache to download it again)')
    return path


def read_wav(path):
    """mono float samples, mixed like the player mixes them (mean of the channels)"""
    with open(path, 'rb') as f:
        head = f.read(12)
    assert head[:4] == b'RIFF' and head[8:12] == b'WAVE', path
    w = wave.open(path)
    assert w.getsampwidth() == 2 and w.getframerate() == RATE and w.getnchannels() in (1, 2), (path, w.getparams())
    x = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, w.getnchannels()).astype(np.float64) / 32768
    return x.mean(axis=1)


def decode(path):
    """mono float samples at RATE, as ffmpeg decodes the file (it honours the encoder delay in the LAME header, like Chrome)"""
    out = subprocess.run([FFMPEG, '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(RATE), '-'], check=True, capture_output=True).stdout
    return np.frombuffer(out, '<f4').astype(np.float64)


def encode(x, path):
    pcm = np.clip(np.round(x * 32768), -32768, 32767).astype('<i2').tobytes()
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-f', 's16le', '-ar', str(RATE), '-ac', '1', '-i', '-',
                    '-map_metadata', '-1', '-fflags', '+bitexact', '-flags:a', '+bitexact',
                    '-c:a', 'libmp3lame', '-b:a', f'{KBPS}k', '-id3v2_version', '0', '-write_id3v1', '0', path],
                   input=pcm, check=True)


def is_mp3(b):
    return b[:3] == b'ID3' or (len(b) > 1 and b[0] == 0xFF and (b[1] & 0xE0) == 0xE0)


def build(cache):
    rows = read_manifest()
    os.makedirs(os.path.join(VOICE, 'en'), exist_ok=True)
    os.makedirs(os.path.join(VOICE, 'he'), exist_ok=True)
    keep = set()
    groups = {}
    for r in rows:
        groups.setdefault(r['file'], []).append(r)
    for name, rs in groups.items():
        out = os.path.join(VOICE, name)
        keep.add(name)
        assert len({r['kind'] for r in rs}) == 1 and len({r['src_sha256'] for r in rs}) == 1, name
        src = fetch(rs[0], cache)
        for r in rs:
            r['src_sha256'] = sha256(src)      # the first build pins the original
        if rs[0]['kind'] == 'narr-he':
            data = open(src, 'rb').read()
            assert is_mp3(data) and name.endswith('.mp3'), name
            open(out, 'wb').write(data)
            continue
        assert all(r['kind'] == 'voice-en' for r in rs) and name.endswith('.mp3'), name
        x = read_wav(src)
        n = len(x) * 1000 // RATE
        whole = [r for r in rs if r['src_e'] <= r['src_s']]
        a = 0 if whole else max(0, min(r['src_s'] for r in rs) - PAD)
        b = n if whole else min(n, max(r['src_e'] for r in rs) + PAD)
        # sample exact (24 samples a ms); a cut that reaches the end of the original keeps its last partial ms too
        encode(x[a * RATE // 1000:len(x) if b == n else b * RATE // 1000], out)
        for r in rs:
            r['s'], r['e'] = (0, 0) if r['src_e'] <= r['src_s'] else (r['src_s'] - a, r['src_e'] - a)
            # the player's window [s-LEAD, e+TAIL] lies inside the new file wherever it lay inside the original
            assert r['e'] == 0 or (r['s'] >= min(LEAD, r['src_s']) and (b - a) - r['e'] >= min(TAIL, n - r['src_e'])), r
    # nothing stale stays behind
    for d in ('en', 'he'):
        for f in os.listdir(os.path.join(VOICE, d)):
            if f'{d}/{f}' not in keep:
                os.remove(os.path.join(VOICE, d, f))
    pin(rows)
    write_js(rows)
    print(len(groups), 'files,', len(rows), 'texts')


def pin(rows=None):
    """the sha256 of every local file, as it is on disk now, into the manifest"""
    rows = rows or read_manifest()
    for r in rows:
        r['sha256'] = sha256(os.path.join(VOICE, r['file']))
    write_manifest(rows)
    return rows


def write_js(rows):
    en = [r for r in rows if r['kind'] == 'voice-en']
    names = ['assets/voice/' + r['file'][:-4] for r in en]
    base = os.path.commonprefix(names)
    assert not base.startswith(('/', 'http')) and base.startswith('assets/voice/en/'), base
    body = ',\n'.join(json.dumps([r['text'], nm[len(base):], r['s'], r['e']], ensure_ascii=False, separators=(',', ':')) for r, nm in zip(en, names))
    out = f"""/* The recorded voice: one clip per English text the game can speak (list: tests/voice_texts.json, built by tests/voice_texts.mjs).
   Each row: text, file, and where the words start and end inside that file in milliseconds (0,0 = the whole file).
   The files are ours, served next to the game (assets/voice/en/, a relative URL); each was cut from its original
   around the measured clean stretch, which is the only part played. Sources: assets/voice/sources.tsv.
   Generated by tests/voice_local.py, do not edit by hand. Texts without a clip are spoken by the browser's own voice. */
const BASE={json.dumps(base)};
const ROWS=[
{body}];
export const norm=s=>String(s??'').trim().replace(/\\s+/g,' ');
const C=new Map(ROWS.map(r=>[r[0],r]));
const LOW=new Map();for(const [k,v] of C){{const l=k.toLowerCase();if(!LOW.has(l))LOW.set(l,v)}}
export const HAS_CLIPS=C.size>0;
/* exact text first (case matters: "May" the month and "may" could differ), then a lowercase match */
/* {{url, s, e}}: the file and the stretch to play, in seconds */
export function clipOf(text){{const k=norm(text),v=C.get(k)||LOW.get(k.toLowerCase());return v?{{url:BASE+v[1]+'.mp3',s:v[2]/1000,e:v[3]/1000}}:null}}
"""
    open(os.path.join(ROOT, 'js', 'voice.js'), 'w', encoding='utf-8').write(out)


def best_lag(ref, y, guess, span):
    """the offset of ref inside y (samples) near guess, by normalised waveform cross-correlation; and that correlation"""
    lo, hi = max(0, guess - span), min(len(y) - len(ref), guess + span)
    if hi < lo:
        return None, 0.0
    seg = y[lo:hi + len(ref)]
    nfft = 1 << int(np.ceil(np.log2(len(seg) + len(ref))))
    cc = np.fft.irfft(np.fft.rfft(seg, nfft) * np.conj(np.fft.rfft(ref, nfft)), nfft)[:hi - lo + 1]
    e = np.sqrt(np.convolve(seg * seg, np.ones(len(ref)), 'valid')[:hi - lo + 1] * (ref @ ref)) + 1e-12
    k = int(np.argmax(cc / e))
    return lo + k, float(cc[k] / e[k])


def env(x, hop=RATE // 200):
    n = len(x) // hop
    return np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1))


def verify(cache):
    """For every English text: the stretch the player plays today ([src_s-30 ms, src_e+80 ms] of the original) is looked
    up in the decoded local file. Error = where it really is minus where the new offsets say it is (ms). Also checks the
    envelope (5 ms frames) and that the Hebrew files are byte-identical to their originals."""
    rows = read_manifest()
    errs, env_errs, bad, cors = [], [], [], []
    dec = {}
    for r in rows:
        path = os.path.join(VOICE, r['file'])
        if sha256(path) != r['sha256']:
            bad.append((r['file'], 'sha256 differs from the manifest'))
        if r['kind'] == 'narr-he':
            same = open(path, 'rb').read() == open(fetch(r, cache), 'rb').read()
            print('he', r['file'], 'byte-identical' if same else 'DIFFERENT')
            if not same:
                bad.append(r['file'])
            continue
        x = read_wav(fetch(r, cache))
        y = dec.get(path)
        if y is None:
            y = dec[path] = decode(path)
        a0 = max(0, r['src_s'] - LEAD) * RATE // 1000
        a1 = min(len(x), (r['src_e'] + TAIL) * RATE // 1000)
        ref = x[a0:a1]
        # where the new offsets put that window: the original was cut at a = src_s - s
        want = (max(0, r['src_s'] - LEAD) - (r['src_s'] - r['s'])) * RATE // 1000
        lag, c = best_lag(ref, y, want, RATE // 10)
        err = (lag - want) * 1000 / RATE if lag is not None else 999
        hop = RATE // 200
        ex, sc = env(ref, hop), []
        for L in range(-20, 21):   # 5 ms frames, +-100 ms
            p = want + L * hop
            ey = env(y[p:p + len(ref)], hop) if p >= 0 else np.array([])
            sc.append(np.corrcoef(ex, ey)[0, 1] if len(ey) == len(ex) else -1)
        env_err = (int(np.nanargmax(sc)) - 20) * 5
        errs.append(abs(err)); env_errs.append(abs(env_err)); cors.append(c)
        # the played window must still fit inside the local file (else the player would clamp it shorter than today)
        fits = r['e'] == 0 or len(y) >= (r['e'] + TAIL) * RATE // 1000 or r['src_e'] + TAIL > len(x) * 1000 // RATE
        if abs(err) > 2 or c < .97 or not fits:
            bad.append((r['text'], r['file'], round(err, 2), round(c, 4), env_err, fits))
    errs, env_errs = np.array(errs), np.array(env_errs)
    print(f'english texts: {len(errs)}; waveform offset error ms: max {errs.max():.3f} median {np.median(errs):.3f}; '
          f'envelope offset error ms: max {env_errs.max()} median {np.median(env_errs)}; '
          f'waveform correlation: min {min(cors):.4f} median {np.median(cors):.4f}')
    print('suspicious:', bad or 'none')
    return not bad


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    cache = sys.argv[sys.argv.index('--cache') + 1] if '--cache' in sys.argv else None
    if cmd == 'pin':
        print(len(pin()), 'rows pinned')
        sys.exit(0)
    if cmd not in ('build', 'verify') or not cache:
        sys.exit(__doc__)
    os.makedirs(cache, exist_ok=True)
    assert not os.path.abspath(cache).startswith(ROOT + os.sep), 'keep the downloads outside the repo'
    BASE = storage.base(sys.argv)
    if cmd == 'build':
        build(cache)
    else:
        sys.exit(0 if verify(cache) else 1)
