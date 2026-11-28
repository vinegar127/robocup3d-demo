"""Run one T1 player: python -m team.agent --team StudyBlue --number 1."""

import argparse
import json
from pathlib import Path
import re
import time

from .behavior import Controller
from .protocol import Connection
from .world import World

CONFIG = Path(__file__).with_name("config.json")


def run(args) -> dict:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    world = World(args.team)
    strategy = getattr(args, 'strategy', 'baseline')
    controller = Controller(config, args.number, args.team, args.behavior, args.walk_target, strategy=strategy)
    connection = Connection(args.host, args.port)
    started = time.monotonic()
    next_log = 0.0
    summary = {"team": args.team, "number": args.number, "role": controller.formation["role"],
               "strategy": strategy,
               "frames": 0, "joint_commands": 0, "beams": 0, "fallen_frames": 0,
               "error": None, "side": "unknown", "min_height": None,
               "distance_walked": 0., "ball_observations": 0, "start_position": None,
               "end_position": None, "states": {}, "score": [0, 0]}
    previous_position = None
    try:
        connection.send(f"(init {config['model']} {args.team} {args.number})")
        while (args.duration is None or time.monotonic() - started < args.duration) and not (args.stop_file and args.stop_file.exists()):
            world.update(connection.receive())
            action = controller.act(world)
            connection.send(action)
            summary.update(frames=world.frames, joint_commands=controller.commands,
                           beams=controller.beams, side=world.side)
            summary["fallen_frames"] += int(world.fallen)
            if world.position:
                height = world.position[2]
                summary["min_height"] = height if summary["min_height"] is None else min(height, summary["min_height"])
                if world.frames > 10:
                    if summary['start_position'] is None:
                        summary['start_position'] = world.position
                    if previous_position is not None:
                        gap = ((world.position[0] - previous_position[0]) ** 2 + (world.position[1] - previous_position[1]) ** 2) ** .5
                        if gap < .5:
                            summary['distance_walked'] += gap
                    previous_position = world.position
                summary['end_position'] = world.position
            summary.update(states=controller.states, score=world.score,
                           recoveries=controller.motion.recoveries if controller.motion else 0,
                           recovery_attempts=controller.motion.recovery_attempts if controller.motion else 0,
                           kicks=controller.motion.strike.count if controller.motion else 0,
                           messages_sent=controller.communication.sent,
                           messages_received=controller.communication.received)
            summary['ball_observations'] += int(world.ball_time == world.now)
            if world.now >= next_log:
                print(json.dumps({"team": args.team, "number": args.number, "t": world.now,
                                  "state": controller.state, "mode": world.play_mode,
                                  "side": world.side, "position": world.position,
                                  "joints": len(world.joints), "ball": world.ball,
                                  "ball_age": world.now - world.ball_time if world.ball else None,
                                  "ball_world": world.ball_position, "active_player": controller.strategy.active,
                                  "receiver": controller.plan.receiver, "role": controller.formation['role'],
                                  "walk_command": controller.velocity, "target": controller.plan.target,
                                  "desired_heading": controller.plan.face}), flush=True)
                next_log = world.now + 1
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, ConnectionError, KeyError) as error:
        if not (args.stop_file and args.stop_file.exists()):
            summary["error"] = f"{type(error).__name__}: {error}"
    finally:
        connection.close()
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if args.summary:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=60000)
    parser.add_argument("--team", default="StudyBlue")
    parser.add_argument("--number", type=int, choices=range(1, 8), default=1)
    parser.add_argument("--duration", type=float, help="Stop after this many wall-clock seconds")
    parser.add_argument("--summary", type=Path)
    parser.add_argument('--behavior', choices=['match', 'stand', 'walk'], default='match')
    parser.add_argument('--walk-target', type=float, nargs=2)
    parser.add_argument('--strategy', choices=['baseline', 'demo-corrected', 'demo-fast-chase', 'demo-team-press'], default='baseline')
    parser.add_argument('--stop-file', type=Path, help='Training harness shutdown signal only')
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", args.team):
        parser.error("Team name must use 1-32 ASCII letters, digits, underscores or hyphens")
    if args.duration is not None and args.duration <= 0:
        parser.error("Duration must be positive")
    return args


if __name__ == "__main__":
    result = run(arguments())
    print(json.dumps({"summary": result}), flush=True)
    raise SystemExit(1 if result["error"] or not result["frames"] else 0)
