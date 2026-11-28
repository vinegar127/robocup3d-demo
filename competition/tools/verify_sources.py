"""Verify pinned opponent files and record the Windows binary identity."""
import hashlib
import json
import os
from pathlib import Path
import sys
import argparse
from tools.opponents import PUBLIC_KINDS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(kinds=('apollo','bahia')):
    root = Path(__file__).resolve().parents[1]
    result = {}
    for kind in kinds:
        directory = root/'third_party'/kind
        provenance = json.loads((directory/'PROVENANCE.json').read_text())
        for item in provenance['files']:
            assert digest(directory/item['path']) == item['sha256'], f"Modified {kind}: {item['path']}"
        result[kind] = {'repository':provenance['repository'],'commit':provenance['commit'],
                        'verified_files':len(provenance['files'])}
    for kind in [k for k in kinds if k in ('apollo','my3d') and sys.platform=='win32']:
        runtime = Path(os.environ.get('MY3D_HOME' if kind=='my3d' else 'APOLLO_HOME',f'E:/RoboCup3D/opponents/{kind}'))
        provenance = json.loads((root/f'third_party/{kind}/PROVENANCE.json').read_text())
        changed = []
        for item in provenance['files']:
            relative=item['path']
            if kind=='my3d':
                if not relative.startswith('runtime/apollo/'):
                    continue
                relative=relative.removeprefix('runtime/apollo/')
            file = runtime/relative
            if file.exists() and digest(file) != item['sha256']:
                changed.append(relative)
            if relative.startswith(('src/','assets/')):
                assert file.exists(), f'Missing opponent runtime file: {file}'
        assert sorted(changed) == ['src/server/tcp_lpm_client.cc','src/server/tcp_lpm_client.h'], changed
        result[kind]['windows_changed_files'] = changed
        result[kind]['windows_binary_sha256'] = digest(runtime/'ApolloCodeBase.exe')
        result[kind]['onnxruntime_dll_sha256'] = digest(runtime/'onnxruntime.dll')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kinds',nargs='+',choices=PUBLIC_KINDS,default=['apollo','bahia'])
    args=parser.parse_args()
    result = verify(args.kinds)
    root = Path(__file__).resolve().parents[1]
    output = root/'output/benchmarks/source-verification.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
