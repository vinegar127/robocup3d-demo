#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
ulimit -c 0
python_bin="${ROBOCUP_PYTHON:-$PWD/.venv/bin/python}"
opponent_bin="$PWD/third_party/my3d/runtime/apollo/build/ApolloCodeBase"
if [[ ! -x "$opponent_bin" ]]; then
  echo "My3D Linux executable is missing: $opponent_bin" >&2
  echo "See docs/UBUNTU_MIGRATION.md for the native build commands." >&2
  exit 1
fi
echo "Blue/left: original My3D. Red/right: StudyBlue. Ctrl+C stops this match."
exec "$python_bin" -X faulthandler -m tools.evaluate \
  --scenario match --players 7 --half 300 --opponent my3d --swap-teams \
  --require-legal-opening --render --realtime "$@"
