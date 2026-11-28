"""Fetch and hash-check the pinned public opponent for local benchmarking.

The source release contains the manifest only. The public code is downloaded
from its author's GitLab, without assuming permission to redistribute it.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def main():
    root = Path(__file__).resolve().parents[1]
    manifest_path = root/'docs/opponents/bahia.json'
    manifest = json.loads(manifest_path.read_text())
    destination = root/'third_party/bahia'
    destination.mkdir(parents=True,exist_ok=True)
    for item in manifest['files']:
        path = destination/item['path']
        assert path.resolve().is_relative_to(destination.resolve()), 'Unsafe source path'
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError(f'Local file differs from pinned source: {path}')
            continue
        url = f"{manifest['repository']}/-/raw/{manifest['commit']}/{quote(item['path'],safe='/')}"
        request = Request(url,headers={'User-Agent':'RoboCupStudy-public-baseline/1.0'})
        with urlopen(request,timeout=30) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError(f'Unexpected bytes from {url}')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
    (destination/'PROVENANCE.json').write_bytes(manifest_path.read_bytes())
    print(f"Verified {len(manifest['files'])} files at {manifest['commit']}")


if __name__ == '__main__':
    main()
