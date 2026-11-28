"""Trainer-only physical navigation and gait-command measurements.

The trainer places the initial player/ball only. Chase clients use ordinary
perceptions and the selected competition strategy; calibration clients send a
fixed walk-policy command through the normal T1 motion controller.
"""
import argparse
import ctypes
import json
import math
from pathlib import Path
import sys


COMMANDS = {'forward': (1., 0., 0.), 'backward': (-.5, 0., 0.),
            'strafe': (0., .5, 0.), 'turn': (0., 0., .5),
            'turn075': (0., 0., .75), 'turn075right': (0., 0., -.75),
            'turn100': (0., 0., 1.), 'turn100right': (0., 0., -1.),
            'arc075': (.4, 0., .75), 'arc075right': (.4, 0., -.75)}
BALLS = {'front': (5., 0., .11), 'side': (0., 5., .11),
         'behind': (-5., 0., .11), 'retreat': (5., 0., .11)}


def client():
    index = sys.argv.index('--probe-client')
    kind = sys.argv[index+1]
    del sys.argv[index:index+2]
    from team import agent
    original = agent.Controller

    class CalibrationController(original):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.behavior, self.walk_target = 'walk', None
            self.navigate = lambda plan, world: COMMANDS[kind] if world.play_mode == 'PlayOn' else None

        def act(self, world):
            if self.motion is not None and abs(COMMANDS[kind][2]) > .5:
                self.motion.walk.turn_limit = abs(COMMANDS[kind][2])
            return super().act(world)

    agent.Controller = CalibrationController
    result = agent.run(agent.arguments())
    raise SystemExit(1 if result['error'] else 0)


def trainer():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout', choices=[*BALLS, *COMMANDS], required=True)
    parser.add_argument('--strategy', choices=['demo-corrected', 'demo-fast-chase', 'demo-team-press'], default='demo-corrected')
    parser.add_argument('--seconds', type=float, default=20.)
    parser.add_argument('--seed', type=int, default=62)
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    if args.result.exists():
        parser.error('Use a new result filename')
    ctypes.CDLL(None).prctl(4, 0)
    from tools import evaluate
    from team.geometry import wrap, yaw
    from rcsssmj.games.soccer.sim.soccer_commands import PlacePlayerCommand, PlaceBallCommand

    if args.layout in COMMANDS:
        original = evaluate.subprocess.Popen

        def launch(command, *a, **kw):
            if 'team.agent' in command:
                command = list(command)
                command[command.index('team.agent')] = 'tools.probe_navigation'
                command += ['--probe-client', args.layout]
            return original(command, *a, **kw)

        evaluate.subprocess.Popen = launch
    elif args.layout == 'retreat':
        # Replay the observed navigation conflict: face ball east, move west.
        # Use an ordinary Plan and the candidate navigator, not trainer velocity.
        original = evaluate.subprocess.Popen

        def launch(command, *a, **kw):
            if 'team.agent' in command:
                command = list(command)
                command[command.index('team.agent')] = 'tools.probe_navigation'
                command += ['--retreat-client']
            return original(command, *a, **kw)

        evaluate.subprocess.Popen = launch

    class NavigationProbe(evaluate.Evaluator):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.trace = []
            self.next_sample = 0.
            self.path_length = 0.

        def update(self, information, frame_id, recompilation):
            if self.done:
                super().update(information, frame_id, recompilation)
                return
            was_started = self.started
            super().update(information, frame_id, recompilation)
            if self.started and not was_started:
                self.command_queue.put(PlacePlayerCommand(7, 'StudyBlue', (0., 0., .673), (1., 0., 0., 0.)))
                self.command_queue.put(PlaceBallCommand(BALLS.get(args.layout, (10., 10., .11)), (0., 0., 0.)))
            if not self.started:
                return
            elapsed = self.sim.sim_time-self.start
            players = list(self.sim.sim_agents)
            if elapsed >= .3 and elapsed >= self.next_sample and players:
                subject = next(p for p in players if p.agent_id.player_no == 7)
                pos, quat = subject.xpos.tolist(), subject.xquat.tolist()
                heading = yaw(quat)
                ball = self.sim.ball.xpos.tolist()
                angle = abs(wrap(math.atan2(ball[1]-pos[1], ball[0]-pos[0])-heading))
                row = dict(t=round(elapsed, 3), pos=pos, heading=heading,
                           ball=ball, ball_distance=math.hypot(ball[0]-pos[0], ball[1]-pos[1]),
                           ball_angle_deg=math.degrees(angle),
                           upright=1-2*(quat[1]**2+quat[2]**2) > .5)
                if self.trace:
                    prev = self.trace[-1]
                    dt = elapsed-prev['t']
                    if dt > 0:
                        dx, dy = pos[0]-prev['pos'][0], pos[1]-prev['pos'][1]
                        row.update(forward_m_s=(dx*math.cos(heading)+dy*math.sin(heading))/dt,
                                   sideways_m_s=(-dx*math.sin(heading)+dy*math.cos(heading))/dt,
                                   yaw_deg_s=math.degrees(wrap(heading-prev['heading']))/dt)
                        if math.hypot(dx, dy) < .5:
                            self.path_length += math.hypot(dx, dy)
                self.trace.append(row)
                self.next_sample = elapsed+.095
            if self.done and self.report is not None:
                steady = [r for r in self.trace if r['t'] >= 2. and r['upright'] and 'forward_m_s' in r]
                def mean(field):
                    return sum(r[field] for r in steady)/max(1, len(steady))
                result = dict(directory=str(self.output), strategy=args.strategy, layout=args.layout,
                              seed=args.seed, seconds=args.seconds, trace=self.trace,
                              mean_forward_m_s=mean('forward_m_s'), mean_sideways_m_s=mean('sideways_m_s'),
                              mean_yaw_deg_s=mean('yaw_deg_s'), path_length_m=self.path_length,
                              sampled_falls=sum(not r['upright'] for r in self.trace),
                              time_to_ball_1_1m=next((r['t'] for r in self.trace if r['ball_distance'] <= 1.1), None),
                              time_to_face_ball_30deg=next((r['t'] for r in self.trace if r['ball_angle_deg'] <= 30), None),
                              time_to_retreat_target=next((r['t'] for r in self.trace if math.hypot(r['pos'][0]+5, r['pos'][1]) <= .4), None),
                              backward_samples=sum(r.get('forward_m_s', 0)<-.05 for r in self.trace))
                args.result.parent.mkdir(parents=True, exist_ok=True)
                args.result.write_text(json.dumps(result, indent=2)+'\n')

    evaluate.Evaluator = NavigationProbe
    sys.argv = [sys.argv[0], '--scenario', 'kick', '--strategy', args.strategy,
                '--seconds', str(args.seconds), '--seed', str(args.seed), '--wall-limit', '150']
    evaluate.main()


def retreat_client():
    sys.argv.remove('--retreat-client')
    from team import agent
    from team.strategy import Plan
    original = agent.Controller

    class RetreatController(original):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.strategy.plan = lambda world: (Plan('SUPPORT', (-5., 0.), 0.)
                                                if world.play_mode == 'PlayOn' else Plan('READY'))

    agent.Controller = RetreatController
    result = agent.run(agent.arguments())
    raise SystemExit(1 if result['error'] else 0)


if __name__ == '__main__':
    if '--probe-client' in sys.argv:
        client()
    elif '--retreat-client' in sys.argv:
        retreat_client()
    else:
        trainer()
