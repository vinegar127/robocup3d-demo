"""Export a personal Ubuntu handoff with source, candidates and retained evidence.

Does not install dependencies, execute opponents, or mark Linux as validated.
The local opponent cache belongs to this personal backup, not the public source release.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ITEMS = ['team', 'tools', 'tests', 'docs', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
                'requirements.txt', 'requirements-opponents.txt', 'requirements-gru-opponent.txt',
                'requirements-windows-lock.txt', 'setup_ubuntu.sh', 'start.sh', 'start_team.sh',
                'kill.sh', 'start_penalty.sh', 'run_player.py', 'run_match_windows.cmd',
                'run_public_match_windows.cmd', 'start_server_windows.cmd', 'start_team_windows.cmd']
KINDS = ['apollo', 'bahia', 'my3d', 'aspen', 'retricato', 'jenny', 'freeloap', 'gru2', 'passing']


def local_reference(value):
    normalized = value.replace('\\', '/')
    historical_prefix = 'E:/3d仿真/'
    if normalized.casefold().startswith(historical_prefix.casefold()):
        return ROOT/normalized[len(historical_prefix):]
    path = Path(normalized)
    return path if path.is_absolute() else ROOT/path


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def plan():
    files = {}

    def add(path, relative=None):
        path = path.resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f'Path outside workspace: {path}')
        if path.is_dir():
            for child in sorted(path.rglob('*')):
                if child.is_file() and '__pycache__' not in child.parts and child.suffix != '.pyc':
                    add(child)
        elif path.is_file():
            name = relative or path.relative_to(ROOT).as_posix()
            if name.startswith('/') or '..' in Path(name).parts:
                raise ValueError('Unsafe archive path')
            if name in files and files[name] != path:
                raise ValueError(f'Archive collision: {name}')
            files[name] = path
        else:
            raise FileNotFoundError(path)

    for name in SOURCE_ITEMS:
        add(ROOT/name)

    # Every cached upstream file is checked before it enters the personal backup.
    for kind in KINDS:
        manifest = json.loads((ROOT/f'docs/opponents/{kind}.json').read_text(encoding='utf-8'))
        for item in manifest['files']:
            path = ROOT/'third_party'/kind/item['path']
            if digest(path) != item['sha256']:
                raise ValueError(f'Modified cached source: {path}')
            add(path)
        add(ROOT/'third_party'/kind/'PROVENANCE.json')

    # Store complete agent/test snapshots, without relying on tmp surviving a reboot.
    for label, folder in [('progress', 'candidate-progress'), ('self-filter', 'candidate-self-filter')]:
        candidate = ROOT/'tmp'/folder
        if not (candidate/'team').is_dir():
            candidate = ROOT/'handoff/candidates'/label
        spec = json.loads((ROOT/f'docs/experiments/{label}-source.json').read_text(encoding='utf-8'))
        for name, expected in spec['files'].items():
            if digest(candidate/name) != expected:
                raise ValueError(f'Candidate changed since validation: {folder}/{name}')
        for group in ['team', 'tests']:
            for path in sorted((candidate/group).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    add(path, f'handoff/candidates/{label}/' + path.relative_to(candidate).as_posix())

    # Collect directories cited by the durable reports and research diagnostics.
    for label, folder in [('legacy-hybrid', 'candidate-hybrid'), ('unrun-intercept', 'candidate-intercept')]:
        candidate = ROOT/'tmp'/folder
        if not (candidate/'team').is_dir():
            candidate = ROOT/'handoff/candidates'/label
        for group in ['team', 'tests']:
            for path in sorted((candidate/group).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    add(path, f'handoff/candidates/{label}/' + path.relative_to(candidate).as_posix())

    evidence = set()

    def references(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ('directory', 'series_result', 'source_manifest', 'unpacked_directory') and isinstance(item, str):
                    path = local_reference(item)
                    if path.is_relative_to(ROOT) and path.exists():
                        relative = path.relative_to(ROOT).as_posix()
                        if (relative.startswith(('output/evaluations/', 'output/benchmarks/'))
                                or (relative.startswith('tmp/candidate-') and '/output/' in relative)):
                            evidence.add(path if path.is_dir() else path.parent)
                references(item)
        elif isinstance(value, list):
            for item in value:
                references(item)

    for path in (ROOT/'docs').glob('*validation*.json'):
        references(json.loads(path.read_text(encoding='utf-8')))
    for folder in ['output/research/public-search-20261102', 'output/research/public-search-20261103']:
        add(ROOT/folder)
        for path in (ROOT/folder).rglob('*.json'):
            references(json.loads(path.read_text(encoding='utf-8')))
    add(ROOT/'output/benchmarks')
    if (ROOT/'output/linux-validation').is_dir():
        add(ROOT/'output/linux-validation')
    for name in ['match-4dra3hpm', 'match-9q2ifn0w']:
        evidence.add(ROOT/'output/evaluations'/name)
    for path in sorted(evidence):
        add(path)
    for name in ['search_public_20261103.py', 'fetch_more_public.py', 'self_filter_skill_regression.py',
                 'finalize_evidence_20261103.py', 'validate_self_filter.py', 'continue_gru_series.py']:
        add(ROOT/'tmp'/name)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'output/releases/RoboCupStudy-Ubuntu-handoff-20261104-v2.tar.gz')
    parser.add_argument('--list-only', action='store_true')
    args = parser.parse_args()
    files = plan()
    print(json.dumps({'files':len(files), 'uncompressed_bytes':sum(p.stat().st_size for p in files.values())}), flush=True)
    if args.list_only:
        return
    destination = args.output.resolve()
    if not destination.is_relative_to(ROOT):
        raise ValueError('Handoff output must remain in the workspace')
    if destination.exists() or destination.with_suffix(destination.suffix+'.partial').exists():
        raise FileExistsError('Choose a new output filename; existing handoffs are not overwritten')
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {'linux_verified':False, 'default_team_changed':False,
                'scope':'personal backup including pinned local opponents; not the public source distribution',
                'entry_document':'docs/AGENT_HANDOFF.md', 'files':{}}
    partial = destination.with_suffix(destination.suffix+'.partial')
    with tarfile.open(partial, 'w:gz') as archive:
        for name, path in sorted(files.items()):
            expected = digest(path)
            info = archive.gettarinfo(str(path), arcname='RoboCupStudy/'+name)
            info.mode = 0o755 if path.suffix == '.sh' else 0o644
            with path.open('rb') as stream:
                archive.addfile(info, stream)
            if digest(path) != expected:
                raise RuntimeError(f'File changed while exporting: {path}')
            manifest['files'][name] = {'sha256':expected, 'bytes':info.size}
        import io
        data = json.dumps(manifest, indent=2).encode('utf-8')
        info = tarfile.TarInfo('RoboCupStudy/HANDOFF_MANIFEST.json')
        info.size, info.mode = len(data), 0o644
        archive.addfile(info, io.BytesIO(data))
    partial.replace(destination)
    receipt = {'archive':str(destination), 'sha256':digest(destination), 'bytes':destination.stat().st_size,
               'files':len(files), 'linux_verified':False, 'entry_document':'RoboCupStudy/docs/AGENT_HANDOFF.md'}
    destination.with_name(destination.name.removesuffix('.tar.gz')+'.receipt.json').write_text(
        json.dumps(receipt, indent=2), encoding='utf-8')
    destination.with_name(destination.name+'.sha256').write_text(
        receipt['sha256']+'  '+destination.name+'\n', encoding='ascii')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
