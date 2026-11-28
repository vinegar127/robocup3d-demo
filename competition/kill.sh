#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
team_name="${TEAM_NAME:-StudyBlue}"
[[ "$team_name" =~ ^[A-Za-z][A-Za-z0-9_-]{0,31}$ ]] || exit 1
mkdir -p -- ".runtime/$team_name"
touch -- ".runtime/$team_name/stop"
