#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
server_host="${1:-127.0.0.1}"
if [[ $# -gt 0 ]]; then shift; fi
exec "${ROBOCUP_PYTHON:-python3}" -m team.launch --host "$server_host" "$@"
