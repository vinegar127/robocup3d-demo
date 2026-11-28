#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
ulimit -c 0
exec "${ROBOCUP_PYTHON:-$PWD/.venv/bin/python}" -X faulthandler -m tools.evaluate \
  --scenario match --half 300 --players 7 --render --realtime "$@"
