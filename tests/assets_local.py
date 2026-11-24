#!/usr/bin/env python3
"""Builds our own copies of the 3D models and pictures, from the manifest assets/sources.tsv.

    python3 tests/assets_local.py build  --cache DIR   # download (into DIR, outside the repo), shrink, write the files and their sha256
    python3 tests/assets_local.py verify --cache DIR   # compare every local file with its original again
    python3 tests/assets_local.py check                # no download: every file is on disk and matches its sha256

The manifest is the source of truth. One row per local file, tab-separated, columns:
    kind     model-glb (a Beach Run runner), hero-pic (its picture on the menu), word-pic (the source of one word picture)
    file     the local file, relative to assets/
    src_url  where the generator put the original (Higgsfield storage; used only by this script, never by the game)
    sha256   of the local file as it is served (written by build)
    note     what was done to the original
Every local file keeps the generator's job id (hf_<date>_<time>_<uuid>) in its name, for the credits.

model-glb: only the one texture inside the file is made smaller (2048 px JPEG to TEX px JPEG). Every other byte range
           of the file (mesh, skin, joints, animation keys) is copied as it is; verify proves that range by range.
hero-pic:  PNG to WebP, HERO px.
word-pic:  PNG to WebP, WORD px (small copies; tools/sheet.html draws them at 256 px).
Downloaded files are untrusted: only the one storage host is fetched, a redirect is refused (never followed), the size is
capped, and a file is only ever parsed (JSON, Pillow), never run. Pictures are decoded and re-encoded, so no metadata of
the original survives. build and verify need Pillow (free); check and the tests do not."""
import hashlib, io, json, os, re, struct, sys, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')
MANIFEST = os.path.join(ASSETS, 'sources.tsv')
COLS = ['kind', 'file', 'src_url', 'sha256', 'note']
HOST = 'https://d8j0ntlcm91z4.cloudfront.net/'
NAME = r'hf_\d{8}_\d{6}_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
KINDS = {'model-glb': (re.compile(f'3d/{NAME}\\.glb'), '.glb'),
         'hero-pic': (re.compile(f'x/{NAME}\\.webp'), '.png'),
         'word-pic': (re.compile(f'x/src/{NAME}\\.webp'), '.png')}
TEX, TEX_Q = 1024, 90      # the runner's texture: side in px, JPEG quality
HERO, HERO_Q = 512, 90     # the menu picture
WORD, WORD_Q = 512, 82     # a word-picture source
MAX_BYTES = 30_000_000
GLB_LIMIT = 3_000_000      # a model must stay under this


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_manifest():
    """plain tab-separated text, no quoting"""
    lines = open(MANIFEST, encoding='utf-8').read().split('\n')
    assert lines[0].split('\t') == COLS and lines[-1] == '', 'bad manifest header'
    rows = [dict(zip(COLS, ln.split('\t'))) for ln in lines[1:-1]]
    seen = set()
    for r in rows:
        assert len(r) == len(COLS), r
        # every command trusts these as paths below assets/ and as URLs to fetch, so they are checked wherever the manifest is read
        assert r['kind'] in KINDS and KINDS[r['kind']][0].fullmatch(r['file']), r['file']
        stem = os.path.basename(r['file']).rsplit('.', 1)[0]
        assert re.fullmatch(re.escape(HOST) + r'[A-Za-z0-9_]+/' + re.escape(stem) + re.escape(KINDS[r['kind']][1]), r['src_url']), r['src_url']
        assert re.fullmatch(r'[0-9a-f]{64}|', r['sha256']), r['sha256']
        assert r['file'] not in seen, r['file']
        seen.add(r['file'])
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


def fetch(url, cache):
    """the original's bytes, from the cache or downloaded into it (the URL was checked by read_manifest)"""
    assert url.startswith(HOST), url
    path = os.path.join(cache, os.path.basename(url))
    if not os.path.exists(path):
        with OPENER.open(url, timeout=120) as r:
            assert r.status == 200 and r.geturl() == url, (url, r.status, r.geturl())
            data = r.read(MAX_BYTES + 1)
        assert len(data) <= MAX_BYTES, (url, 'larger than the cap')
        with open(path + '.part', 'wb') as f:
            f.write(data)
        os.replace(path + '.part', path)
    return open(path, 'rb').read()


# ---------- GLB (binary glTF 2.0): a header, one JSON chunk, one binary chunk ----------
def glb_read(data):
    magic, ver, total = struct.unpack('<4sII', data[:12])
    assert magic == b'glTF' and ver == 2 and total == len(data), 'not a GLB 2.0 file'
    n, t = struct.unpack('<I4s', data[12:20])
    assert t == b'JSON'
    doc = json.loads(data[20:20 + n])
    o = 20 + n
    m, t = struct.unpack('<I4s', data[o:o + 8])
    assert t == b'BIN\x00' and o + 8 + m == len(data), 'expected exactly one binary chunk'
    bin_ = data[o + 8:o + 8 + m]
    assert len(doc['buffers']) == 1 and 'uri' not in doc['buffers'][0], 'expected one embedded buffer'
    assert not doc.get('extensionsRequired'), doc.get('extensionsRequired')
    return doc, bin_


def glb_views(doc, bin_):
    """the bytes of every bufferView, in order"""
    return [bin_[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']] for v in doc['bufferViews']]


def glb_write(doc, views):
    out = bytearray()
    for v, d in zip(doc['bufferViews'], views):
        out += b'\0' * (-len(out) % 4)
        v['byteOffset'], v['byteLength'] = len(out), len(d)
        out += d
    out += b'\0' * (-len(out) % 4)
    doc['buffers'][0]['byteLength'] = len(out)
    js = json.dumps(doc, separators=(',', ':'), ensure_ascii=True).encode()
    js += b' ' * (-len(js) % 4)
    body = struct.pack('<I4s', len(js), b'JSON') + js + struct.pack('<I4s', len(out), b'BIN\x00') + bytes(out)
    return struct.pack('<4sII', b'glTF', 2, 12 + len(body)) + body


def image_view(doc):
    """the model carries exactly one picture, embedded: its bufferView index"""
    assert len(doc.get('images', [])) == 1 and doc['images'][0].get('mimeType') == 'image/jpeg' and 'bufferView' in doc['images'][0], doc.get('images')
    return doc['images'][0]['bufferView']


def open_image(data, formats):
    from PIL import Image
    im = Image.open(io.BytesIO(data), formats=formats)
    assert im.width * im.height <= 4096 * 4096, im.size
    im.load()
    return im.convert('RGB')


def build_glb(data):
    doc, bin_ = glb_read(data)
    views, iv = glb_views(doc, bin_), image_view(doc)
    from PIL import Image
    im = open_image(views[iv], ['JPEG'])
    assert im.size[0] == im.size[1] and im.size[0] >= TEX, im.size
    buf = io.BytesIO()
    im.resize((TEX, TEX), Image.LANCZOS).save(buf, 'JPEG', quality=TEX_Q, optimize=True, subsampling='4:4:4')
    views[iv] = buf.getvalue()
    out = glb_write(doc, views)
    assert len(out) < GLB_LIMIT, len(out)
    return out, f'texture {im.size[0]} px JPEG to {TEX} px JPEG q{TEX_Q}; mesh, rig and animation bytes untouched'


def same_glb(orig, local):
    """True when local is orig with only the picture replaced: every other byte range and the whole scene description equal"""
    d0, b0 = glb_read(orig)
    d1, b1 = glb_read(local)
    v0, v1, iv = glb_views(d0, b0), glb_views(d1, b1), image_view(d0)
    if image_view(d1) != iv or len(v0) != len(v1) or any(a != b for i, (a, b) in enumerate(zip(v0, v1)) if i != iv):
        return False
    for d in (d0, d1):          # the only things allowed to differ: where each range sits, and the total length
        for v in d['bufferViews']:
            v.pop('byteOffset', None)
        d['bufferViews'][iv].pop('byteLength')
        d['buffers'][0].pop('byteLength')
    im = open_image(v1[iv], ['JPEG'])
    return d0 == d1 and im.size == (TEX, TEX)


def build_pic(data, side, q):
    from PIL import Image
    im = open_image(data, ['PNG'])
    assert im.size[0] == im.size[1] and im.size[0] >= side, im.size
    buf = io.BytesIO()
    im.resize((side, side), Image.LANCZOS).save(buf, 'WEBP', quality=q, method=6)
    return buf.getvalue(), f'PNG {im.size[0]} px to WebP {side} px q{q}'


def make(kind, data):
    if kind == 'model-glb':
        return build_glb(data)
    return build_pic(data, *((HERO, HERO_Q) if kind == 'hero-pic' else (WORD, WORD_Q)))


def build(cache):
    rows = read_manifest()
    for r in rows:
        out, r['note'] = make(r['kind'], fetch(r['src_url'], cache))
        path = os.path.join(ASSETS, r['file'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(out)
        r['sha256'] = sha256(out)
    # nothing stale stays behind in the folders this script owns
    keep = {r['file'] for r in rows}
    for d, ext in (('3d', '.glb'), ('x/src', '.webp')):
        for f in os.listdir(os.path.join(ASSETS, d)):
            if f.endswith(ext) and f'{d}/{f}' not in keep:
                os.remove(os.path.join(ASSETS, d, f))
    write_manifest(rows)
    print(len(rows), 'files,', sum(os.path.getsize(os.path.join(ASSETS, r['file'])) for r in rows), 'bytes')


def check():
    bad = []
    for r in read_manifest():
        path = os.path.join(ASSETS, r['file'])
        if not os.path.isfile(path) or not r['sha256'] or sha256(open(path, 'rb').read()) != r['sha256']:
            bad.append(r['file'])
    print('files that are missing or differ from their sha256:', bad or 'none')
    return not bad


def verify(cache):
    """every model is its original with only the picture replaced; every picture decodes to the size it should have
    and looks like its original (mean absolute difference per channel, against the original scaled the same way)"""
    from PIL import Image
    bad = []
    for r in read_manifest():
        local, orig = open(os.path.join(ASSETS, r['file']), 'rb').read(), fetch(r['src_url'], cache)
        if sha256(local) != r['sha256']:
            bad.append((r['file'], 'sha256 differs from the manifest'))
        if r['kind'] == 'model-glb':
            ok = same_glb(orig, local) and len(local) < GLB_LIMIT
            print(r['file'], len(orig), '->', len(local), 'bytes; everything but the texture identical:', ok)
            d0, b0 = glb_read(orig); d1, b1 = glb_read(local)
            a, b = open_image(glb_views(d0, b0)[image_view(d0)], ['JPEG']).resize((TEX, TEX), Image.LANCZOS), open_image(glb_views(d1, b1)[image_view(d1)], ['JPEG'])
        else:
            side = HERO if r['kind'] == 'hero-pic' else WORD
            b = open_image(local, ['WEBP'])
            ok = b.size == (side, side)
            a = open_image(orig, ['PNG']).resize((side, side), Image.LANCZOS)
        diff = sum(abs(x - y) for x, y in zip(a.tobytes(), b.tobytes())) / len(a.tobytes())
        if not ok or diff > 4:
            bad.append((r['file'], round(diff, 2)))
        if r['kind'] != 'model-glb':
            print(r['file'], len(orig), '->', len(local), 'bytes; mean difference', round(diff, 2), 'of 255')
        else:
            print('   texture mean difference', round(diff, 2), 'of 255')
    print('suspicious:', bad or 'none')
    return not bad


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'check':
        sys.exit(0 if check() else 1)
    cache = sys.argv[sys.argv.index('--cache') + 1] if '--cache' in sys.argv else None
    if cmd not in ('build', 'verify') or not cache:
        sys.exit(__doc__)
    os.makedirs(cache, exist_ok=True)
    cache = os.path.realpath(cache)
    assert os.path.commonpath([cache, os.path.realpath(ROOT)]) != os.path.realpath(ROOT), 'keep the downloads outside the repo'
    if cmd == 'build':
        build(cache)
    else:
        sys.exit(0 if verify(cache) else 1)
