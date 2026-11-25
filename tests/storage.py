"""Where the originals of the generated assets live: never written in this repo.

The public lists (assets/sources.tsv, assets/voice/sources.tsv) name each local file; the original has the same name
(hf_<date>_<time>_<job id>) with its own extension, in one folder of the owner's storage. The address of that folder is
private. The build scripts get it when they have to download something:
    --base https://HOST/FOLDER/        on the command line, or
    WI_STORAGE_BASE=https://HOST/FOLDER/   in the environment.
Nothing else needs it: an original that is already in the cache is used as it is, and every original is checked against
the sha256 the list holds for it, wherever it came from."""
import os, re

ENV = 'WI_STORAGE_BASE'
NAME = re.compile(r'hf_\d{8}_\d{6}_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(wav|mp3|glb|png)')
BASE = re.compile(r'https://[a-z0-9-]+(\.[a-z0-9-]+)+/([A-Za-z0-9_-]+/)*')


def base(argv):
    """the storage folder's address from --base or the environment, or None when neither is given"""
    b = argv[argv.index('--base') + 1] if '--base' in argv and argv.index('--base') + 1 < len(argv) else os.environ.get(ENV, '')
    if not b:
        return None
    if not BASE.fullmatch(b):
        raise SystemExit('the storage base must look like https://HOST/FOLDER/ (https, a trailing slash, no query)')
    return b


def url(b, name):
    """the address of one original; b is None when no base was given"""
    if not NAME.fullmatch(name):
        raise SystemExit(f'{name}: not the name of a generated file')
    if not b:
        raise SystemExit(f'{name} is not in the cache and has to be downloaded: give the storage folder with\n'
                         f'--base https://HOST/FOLDER/ or in the environment variable {ENV} (it is not kept in this repo)')
    return b + name
