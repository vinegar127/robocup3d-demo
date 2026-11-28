"""Launch separate player processes; Ctrl+C stops only this launcher's children."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=60000)
    parser.add_argument("--team", default="StudyBlue")
    parser.add_argument("--players", type=int, choices=range(1, 8), default=7)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument('--behavior', choices=['match', 'stand', 'walk'], default='match')
    parser.add_argument('--strategy', choices=['baseline', 'demo-corrected', 'demo-fast-chase', 'demo-team-press'], default='baseline')
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", args.team):
        parser.error("Invalid team name")
    if args.duration is not None and args.duration <= 0:
        parser.error("Duration must be positive")
    root = Path(__file__).resolve().parents[1]
    log_dir = args.log_dir or root / "logs" / f"{args.team}-{datetime.now():%Y%m%d-%H%M%S-%f}"
    log_dir.mkdir(parents=True, exist_ok=False)
    children, handles = [], []
    interrupted = False
    failed = False
    print(f"Starting {args.players} T1 players. Logs: {log_dir}", flush=True)
    try:
        for number in range(1, args.players + 1):
            command = [sys.executable, "-m", "team.agent", "--host", args.host,
                       "--port", str(args.port), "--team", args.team, "--number", str(number),
                       "--summary", str((log_dir / f"player-{number}.json").resolve())]
            command += ['--behavior', args.behavior]
            command += ['--strategy', args.strategy]
            if args.duration is not None:
                command += ["--duration", str(args.duration)]
            log = (log_dir / f"player-{number}.log").open("w", encoding="utf-8")
            handles.append(log)
            options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
            children.append(subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, **options))
            time.sleep(0.08)
        while any(child.poll() is None for child in children):
            if any(child.poll() not in (None, 0) for child in children):
                failed = True
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        for handle in handles:
            handle.close()
    failed = failed or (not interrupted and any(child.returncode != 0 for child in children))
    print(json.dumps({"team": args.team, "players": len(children), "interrupted": interrupted,
                      "success": not failed, "logs": str(log_dir)}), flush=True)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
