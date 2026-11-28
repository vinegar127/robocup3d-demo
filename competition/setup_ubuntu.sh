#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
python3 -c 'import sys; assert (3,12) <= sys.version_info[:2] < (3,14), "The pinned NumPy requires Python 3.12+; Ubuntu 24.04 / Python 3.12 is recommended"'
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m tools.patch_rcssmj_021
.venv/bin/python -m tools.patch_recompile_controls
echo 'Ready. Run: .venv/bin/python -m tools.evaluate --scenario walk'
