"""Package project sources, pinned public motion assets and license notices."""
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
destination = root / 'output/releases/RoboCupStudy-source.tar.gz'
destination.parent.mkdir(parents=True, exist_ok=True)
selected = ['team', 'tools', 'tests', 'third_party/apollo', 'docs', 'README.md', 'LICENSE',
            'THIRD_PARTY_NOTICES.md', 'requirements.txt', 'requirements-windows-lock.txt',
            'requirements-opponents.txt',
            'requirements-gru-opponent.txt',
            'setup_ubuntu.sh', 'start.sh', 'kill.sh', 'start_penalty.sh', 'start_team.sh',
            'run_player.py', 'start_server_windows.cmd', 'start_team_windows.cmd', 'run_match_windows.cmd',
            'run_public_match_windows.cmd']
with tarfile.open(destination, 'w:gz') as archive:
    for name in selected:
        path = root / name
        if not path.exists():
            raise FileNotFoundError(path)
        files = sorted(path.rglob('*')) if path.is_dir() else [path]
        for file in files:
            if not file.is_file() or '__pycache__' in file.parts or file.suffix == '.pyc':
                continue
            relative = file.relative_to(root)
            info = archive.gettarinfo(str(file), arcname='RoboCupStudy/' + relative.as_posix())
            info.mode = 0o755 if file.suffix == '.sh' else 0o644
            with file.open('rb') as stream:
                archive.addfile(info, stream)
print(destination)
