"""Download a pinned public opponent and verify every manifest digest."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request,urlopen
from tools.opponents import PUBLIC_KINDS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=[k for k in PUBLIC_KINDS if k not in ('apollo','bahia')])
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    manifest_path=root/f'docs/opponents/{args.kind}.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    destination=root/'third_party'/args.kind
    destination.mkdir(parents=True,exist_ok=True)
    repository=manifest['repository'].removeprefix('https://github.com/')
    def fetch(item):
        target=destination/item['path']
        assert target.resolve().is_relative_to(destination.resolve()),'Unsafe manifest path'
        if target.exists():
            assert hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256'],f'Local source modified: {target}'
            return
        url=f"https://raw.githubusercontent.com/{repository}/{manifest['commit']}/{quote(item['path'],safe='/')}"
        with urlopen(Request(url,headers={'User-Agent':'RoboCupStudy-public-opponent'}),timeout=30) as response:
            data=response.read()
        assert hashlib.sha256(data).hexdigest()==item['sha256'],f'Download differs from pinned source: {url}'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(fetch,manifest['files']))
    (destination/'PROVENANCE.json').write_bytes(manifest_path.read_bytes())
    print(f"Verified {len(manifest['files'])} {args.kind} files at {manifest['commit']}")


if __name__=='__main__':
    main()
