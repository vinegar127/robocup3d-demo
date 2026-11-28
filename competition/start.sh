#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
server_host="${1:-127.0.0.1}"
team_name="${TEAM_NAME:-StudyBlue}"
[[ "$team_name" =~ ^[A-Za-z][A-Za-z0-9_-]{0,31}$ ]] || { echo 'Invalid TEAM_NAME' >&2; exit 1; }
runtime_dir="$PWD/.runtime/$team_name"
mkdir -p -- "$runtime_dir"
rm -f -- "$runtime_dir/stop"
for player_number in {1..7}; do
  if [[ -x ./robocup_player/robocup_player ]]; then
    ./robocup_player/robocup_player --host "$server_host" --team "$team_name" --number "$player_number" --stop-file "$runtime_dir/stop" >"$runtime_dir/player-$player_number.log" 2>&1 &
  else
    "${ROBOCUP_PYTHON:-$PWD/.venv/bin/python}" -m team.agent --host "$server_host" --team "$team_name" --number "$player_number" --stop-file "$runtime_dir/stop" >"$runtime_dir/player-$player_number.log" 2>&1 &
  fi
done
