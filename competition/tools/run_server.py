"""Run the server with bounded cleanup when Ctrl+C is pressed on Windows."""
import os
import subprocess
import sys

options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {}
process = subprocess.Popen([sys.executable, '-m', 'rcsssmj', *sys.argv[1:]], **options)
try:
    code = process.wait()
except KeyboardInterrupt:
    process.terminate()
    try:
        code = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    code = 0
raise SystemExit(code)
