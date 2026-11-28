#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
echo "Strategy: close attacking support and measured faster stationary turns."
exec bash run_public_match_linux.sh --strategy demo-team-press "$@"
