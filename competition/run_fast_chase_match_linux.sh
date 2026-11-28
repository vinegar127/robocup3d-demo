#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
echo "Strategy: faster active ball approach; existing T1 motion policies."
exec bash run_public_match_linux.sh --strategy demo-fast-chase "$@"
