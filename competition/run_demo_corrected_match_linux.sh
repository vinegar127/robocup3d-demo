#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
echo "Strategy: corrected Demo placement adapted to physical T1 motion."
exec bash run_public_match_linux.sh --strategy demo-corrected "$@"
