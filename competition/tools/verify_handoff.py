"""Verify the exported handoff files on either Windows or Ubuntu."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads((root/'HANDOFF_MANIFEST.json').read_text(encoding='utf-8'))
    failures = []
    for relative, record in manifest['files'].items():
        path = (root/relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            failures.append({'path':relative,'error':'missing or outside root'})
            continue
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != record['sha256']:
            failures.append({'path':relative,'error':'SHA-256 mismatch'})
    print(json.dumps({'verified':not failures,'checked_files':len(manifest['files']),
                      'export_linux_verified':manifest['linux_verified'],'failures':failures},indent=2))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
