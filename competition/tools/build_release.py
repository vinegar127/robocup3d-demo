"""Build a Linux player bundle on Ubuntu, including ONNX models and notices.

First install PyInstaller in the active environment: python -m pip install pyinstaller
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

if sys.platform != 'linux':
    raise SystemExit('Run this build on Ubuntu. Windows cannot produce the Linux competition executable.')
root = Path(__file__).resolve().parents[1]
output = root / 'output/linux-build'
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--name', 'robocup_player',
                '--distpath', str(output), '--workpath', str(root / 'tmp/pyinstaller'),
                '--specpath', str(root / 'tmp/pyinstaller'), '--collect-all', 'onnxruntime',
                '--add-data', str(root / 'team/config.json') + ':team',
                '--add-data', str(root / 'third_party/apollo/assets/networks') + ':third_party/apollo/assets/networks',
                str(root / 'run_player.py')], cwd=root, check=True)
release = output / 'RoboCupStudy'
release.mkdir(exist_ok=True)
shutil.copytree(output / 'robocup_player', release / 'robocup_player', dirs_exist_ok=True)
for name in ['start.sh', 'kill.sh', 'start_penalty.sh', 'LICENSE', 'THIRD_PARTY_NOTICES.md']:
    shutil.copy2(root / name, release / name)
    if name.endswith('.sh'):
        (release / name).chmod(0o755)
# Include corresponding adapted source and the original upstream reference.
for name in ['team', 'third_party/apollo']:
    shutil.copytree(root / name, release / 'source' / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
destination = root / 'output/releases/RoboCupStudy-linux.tar.gz'
destination.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(destination, 'w:gz') as archive:
    archive.add(release, arcname='RoboCupStudy')
print(destination)
