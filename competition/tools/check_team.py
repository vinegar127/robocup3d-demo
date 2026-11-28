"""Run this project against a disposable real RCSSServerMJ server."""

import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--two-teams", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work_parent = root / "tmp" / "team-checks"
    work_parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=work_parent))
    with socket.socket() as probe1, socket.socket() as probe2:
        probe1.bind(("127.0.0.1", 0))
        probe2.bind(("127.0.0.1", 0))
        agent_port, monitor_port = probe1.getsockname()[1], probe2.getsockname()[1]
    team_names = ["StudyBlue", "StudyOrange"] if args.two_teams else ["StudyBlue"]
    processes = []
    with (work / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([sys.executable, "-m", "rcsssmj", "--host", "127.0.0.1",
                                   "--aport", str(agent_port), "--mport", str(monitor_port),
                                   "--rules", "ssim26", "--no-render"],
                                  cwd=work, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 20
            while True:
                if server.poll() is not None:
                    raise RuntimeError("Server exited during startup")
                try:
                    with socket.create_connection(("127.0.0.1", agent_port), timeout=.2):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Server startup timed out")
                    time.sleep(.1)
            # Initialize one complete team first to make team-side assignment deterministic.
            for name in team_names:
                processes.append(subprocess.Popen(
                    [sys.executable, "-m", "team.launch", "--team", name,
                     "--port", str(agent_port), "--duration", str(args.duration),
                     "--log-dir", str(work / name)], cwd=root))
                if len(team_names) > 1:
                    time.sleep(1.5)
            for process in processes:
                if process.wait(timeout=args.duration + 30) != 0:
                    raise RuntimeError("Team launcher failed; inspect player logs")
        finally:
            for process in processes:
                stop(process)
            stop(server)
    summaries = [json.loads(p.read_text(encoding="utf-8"))
                 for name in team_names for p in sorted((work / name).glob("player-*.json"))]
    if len(summaries) != 7 * len(team_names):
        raise RuntimeError("Not every player produced a summary")
    for summary in summaries:
        if (summary["error"] or summary["frames"] < 30 or summary["joint_commands"] < 23 * 30
                or summary["beams"] != 1 or summary["fallen_frames"]):
            raise RuntimeError(f"Player failed: {summary}")
        expected_side = "left" if summary["team"] == "StudyBlue" else "right"
        if summary["side"] != expected_side:
            raise RuntimeError(f"Unexpected side: {summary}")
    server_log = (work / "server.log").read_text(encoding="utf-8", errors="replace")
    if any(text in server_log for text in ("Traceback", "Exception in thread", "simulation is unstable")):
        raise RuntimeError("Server raised an exception or instability warning; inspect server.log")
    report = {"success": True, "players": len(summaries), "min_frames": min(s["frames"] for s in summaries),
              "joint_commands": sum(s["joint_commands"] for s in summaries),
              "fallen_frames": sum(s["fallen_frames"] for s in summaries), "logs": str(work),
              "server_instability_warnings": server_log.count("simulation is unstable")}
    (work / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
