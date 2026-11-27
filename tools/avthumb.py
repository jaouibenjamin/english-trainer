#!/usr/bin/env python3
"""Small thumbnails of the characters' waist-up stills, for the picker's locked tiles (docs/AVATAR_CHARACTER.md).

    python3 tools/avthumb.py          # writes assets/al/avthumb/<id>.webp and prints the credits_extra.tsv rows

A locked tile is dimmed and only says "level N": it does not need the 256 px still on open. Each thumbnail is the still
as it is shown on a tile (the designer's crop box, x 14% to 86%, y 0 to 72%), scaled to SIZE px and saved as WebP. Made
here from the generated stills, so it is credited in assets/credits_extra.tsv ("local", with its sha256)."""
import hashlib, os, re
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE, QUALITY = 112, 60
BOX = (0.14, 0.0, 0.86, 0.72)


def main():
    art = open(os.path.join(ROOT, 'js', 'world_art.js'), encoding='utf-8').read()
    out = os.path.join(ROOT, 'assets', 'al', 'avthumb')
    os.makedirs(out, exist_ok=True)
    rows = []
    for cid, path in sorted(re.findall(r"'av/([a-z-]+)':'([^']+)'", art)):
        im = Image.open(os.path.join(ROOT, path)).convert('RGBA')
        w, h = im.size
        im = im.crop((round(BOX[0] * w), round(BOX[1] * h), round(BOX[2] * w), round(BOX[3] * h))).resize((SIZE, SIZE), Image.LANCZOS)
        dst = os.path.join(out, cid + '.webp')
        im.save(dst, 'WEBP', quality=QUALITY, method=6)
        sha = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
        rows.append(f"local\tassets/al/avthumb/{cid}.webp\tthe picker's locked-tile thumbnail of {cid}: its waist-up still, the tile's crop box, {SIZE} x {SIZE}\ttools/avthumb.py from {path}\t{sha}")
    print('\n'.join(rows))


if __name__ == '__main__':
    main()
