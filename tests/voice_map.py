#!/usr/bin/env python3
"""Writes the English rows of assets/voice/sources.tsv from the generation log (text -> {job_id, status, url, s, e})
   for the texts in tests/voice_texts.json. s and e are where the words start and end inside the original file, in
   milliseconds (measured, see README "Recorded voice"); the game plays only that stretch. A log entry without them
   plays the whole file. The Hebrew narration rows are kept as they are.
   Then run tests/voice_local.py build, which downloads, trims and encodes the clips into assets/voice/en/ and writes js/voice.js.
   Run: python3 tests/voice_map.py /path/to/voice_jobs.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_local as V

ROOT = V.ROOT
log = json.load(open(sys.argv[1], encoding='utf-8'))
texts = [x['text'] for x in json.load(open(os.path.join(ROOT, 'tests', 'voice_texts.json'), encoding='utf-8'))]
urls = {t: log[t]['url'] for t in texts if log.get(t, {}).get('url')}
assert all(u.endswith('.wav') and u.startswith(V.HOST) for u in urls.values())
he = [r for r in V.read_manifest() if r['kind'] != 'voice-en'] if os.path.exists(V.MANIFEST) else []
en = [{'kind': 'voice-en', 'file': 'en/' + os.path.basename(u)[:-4] + '.mp3', 'src_url': u,
       'src_s': int(log[t].get('s', 0)), 'src_e': int(log[t].get('e', 0)), 's': 0, 'e': 0, 'text': t} for t, u in urls.items()]
assert not any('\t' in r['text'] or '\n' in r['text'] for r in en)
V.write_manifest(en + he)
print(len(urls), 'clips,', len(texts) - len(urls), 'texts without a clip:', [t for t in texts if t not in urls][:20])
print('next: python3 tests/voice_local.py build --cache DIR   (DIR outside the repo)')
