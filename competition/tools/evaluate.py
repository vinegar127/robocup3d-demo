"""Privileged training fixtures only. Competition agents never import this module.

Run: python -m tools.evaluate --scenario walk|recover|shoot|match
"""
import argparse
from dataclasses import asdict
import json
import logging
import math
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import random
import hashlib
import shutil
import numpy as np

from rcsssmj.games.soccer.game_phase import GamePhase
from rcsssmj.games.soccer.server.soccer_server import SoccerSimServer
from rcsssmj.games.soccer.sim.soccer_commands import DropBallCommand, PlaceBallCommand, PlacePlayerCommand, KickOffCommand
from rcsssmj.games.soccer.sim.soccer_referee import SoccerReferee
from rcsssmj.games.soccer.sim.soccer_sim import SoccerSimulation
from rcsssmj.games.soccer.soccer_fields import FIFA7vs7SoccerField
from rcsssmj.games.soccer.soccer_rules import SSim2026Rules, SoccerRules
from rcsssmj.server.remote_monitor import SimMonitor
from tools.opening import inspect_opening
from tools.opponents import PUBLIC_KINDS, configuration


class Evaluator(SimMonitor):
    def __init__(self, sim, args, output):
        super().__init__()
        self.sim, self.args, self.output = sim, args, output
        self.server = None
        self.ready = None
        self.started = False
        self.start = 0.
        self.samples = []
        self.contacts = set()
        self.contact_history = []
        self.previous_contact = None
        self.max_ball_x = -math.inf
        self.max_attack_progress = -math.inf
        self.max_ball_speed = 0.
        self.second_half = False
        self.done = False
        self.score = (0, 0)
        self.states = set()
        self.peak_height = 0.
        self.report = None
        self.next_progress = 0.
        self.startup_error = None
        self.opening = None

    def update(self, information, frame_id, recompilation):
        sim, args = self.sim, self.args
        players = list(sim.sim_agents)
        if self.done:
            if not players:
                self.server.shutdown()
            return
        expected = args.players * 2 if args.scenario == 'match' else (2 if args.mirror or args.scenario == 'pass' else 1)
        if len(players) < expected:
            return
        now = sim.sim_time
        if self.ready is None:
            self.ready = now
        if not self.started and now - self.ready > 1.:
            if args.scenario=='match':
                self.opening = inspect_opening([{'side':p.agent_id.team_id,'number':p.agent_id.player_no,
                    'pos':p.xpos.tolist()} for p in players])
                (self.output/'opening.json').write_text(json.dumps(self.opening,indent=2))
                if not self.opening['legal']:
                    logging.warning('Opening placement is not legal: %s',self.opening['issues'])
                    if args.require_legal_opening:
                        if now-self.ready<args.startup_timeout:
                            return
                        self.startup_error = 'Opening placement never became legal; inspect opening.json'
                        self.server.shutdown()
                        return
            self.started, self.start = True, now
            if args.scenario == 'match':
                self.command_queue.put(KickOffCommand(0))
            else:
                pos = (-2., 2., .673) if args.scenario == 'walk' else (0., 0., .673) if args.scenario == 'pass' else (18., 0., .673) if args.scenario == 'kick' else (24., 0., .673)
                quat = (1., 0., 0., 0.)
                if args.scenario == 'recover':
                    pos, quat = (0., 3., .40), (.70710678, 0., .70710678, 0.)
                if args.mirror and args.scenario != 'recover':
                    pos = (-pos[0], -pos[1], pos[2])
                    quat = (0., 0., 0., 1.)
                self.command_queue.put(PlacePlayerCommand(7, 'StudyBlue', pos, quat))
                if args.mirror:
                    self.command_queue.put(PlacePlayerCommand(1, 'StudyOrange', (0., 12., .673), (1., 0., 0., 0.)))
                if args.scenario == 'pass':
                    self.command_queue.put(PlacePlayerCommand(6, 'StudyBlue', (4.5, .8, .673), (0., 0., 0., 1.)))
                ball = (24.7, 0., .11) if args.scenario == 'shoot' else (18.8, .10, .11) if args.scenario == 'kick' else (.7, 0., .11) if args.scenario == 'pass' else (10., 10., .11)
                if args.mirror:
                    ball = (-ball[0], -ball[1], ball[2])
                self.command_queue.put(DropBallCommand(ball[:2]))
                self.command_queue.put(PlaceBallCommand(ball, (0., 0., 0.)))
        if not self.started:
            return
        elapsed = now - self.start
        mode = sim.game_state.play_mode.value
        self.states.add(mode)
        self.score = (sim.game_state.left_team_score, sim.game_state.right_team_score)
        if elapsed >= self.next_progress:
            (self.output/'progress.json').write_text(json.dumps({'sim_seconds':round(elapsed,2),
                'score':self.score,'mode':mode,'second_half':self.second_half}),encoding='utf-8')
            self.next_progress = elapsed+10
        if sim.ball.last_contact is not None:
            contact = sim.ball.last_contact
            self.contacts.add((contact.team_id, contact.player_no))
            identity = (contact.team_id, contact.player_no)
            if identity != self.previous_contact:
                self.contact_history.append({'time': round(elapsed, 3), 'side': identity[0], 'number': identity[1], 'ball': sim.ball.xpos.tolist()})
                self.previous_contact = identity
        self.max_ball_x = max(self.max_ball_x, float(sim.ball.xpos[0]))
        self.max_ball_speed = max(self.max_ball_speed, float(np.linalg.norm(sim.ball._qvel[:2])))
        our_side = sim.game_state.get_team_side('StudyBlue').value
        self.max_attack_progress = max(self.max_attack_progress, (-1 if our_side else 1) * float(sim.ball.xpos[0]))
        if args.scenario == 'recover' and elapsed > 2:
            subject = next(p for p in players if p.agent_id.player_no == 7)
            self.peak_height = max(self.peak_height, float(subject.xpos[2]))
        if frame_id % 10 == 0:
            sample = {'time': round(elapsed, 3), 'mode': mode, 'game_time': sim.game_state.play_time,
                      'score': self.score, 'ball': sim.ball.xpos.tolist(),
                      'players': [{'side': p.agent_id.team_id, 'number': p.agent_id.player_no,
                                   'pos': p.xpos.tolist(), 'quat': p.xquat.tolist()} for p in players]}
            self.samples.append(sample)
        if args.scenario == 'match' and mode == 'GameOver' and not self.second_half:
            # The training referee advances the phase; clients retain their own state.
            sim.game_state.switch_phase(GamePhase.SECOND_HALF, args.half)
            sim.request_kick_off(1)
            self.second_half = True
        complete = args.scenario == 'match' and mode == 'GameOver' and self.second_half and sim.game_state.play_time > args.half
        if (args.scenario != 'match' and elapsed >= args.seconds) or complete or elapsed > args.half * 2 + 150:
            self.done = True
            self.report = {'scenario': args.scenario, 'sim_seconds': round(elapsed, 3), 'score': self.score,
                           'max_ball_x': self.max_ball_x, 'contacts': sorted(self.contacts),
                           'max_attack_progress': self.max_attack_progress, 'mirror': args.mirror,
                           'max_ball_speed': self.max_ball_speed,
                           'contact_history': self.contact_history,
                           'modes': sorted(self.states), 'recovery_peak_height': self.peak_height,
                           'completed_two_halves': bool(complete), 'half_seconds': args.half,
                           'official_half_length': args.half == 300, 'samples': len(self.samples)}
            self.report.update(opponent=args.opponent, our_side=our_side,
                               strategy=args.strategy,
                               requested_our_side=int(args.swap_teams if args.scenario=='match' else args.mirror),
                               seed=args.seed, initial_sim_time=self.start,
                               field_dimensions=list(sim.field.field_dim), goal_dimensions=list(sim.field.goal_dim),
                               rules={k:getattr(v, 'value', v) for k,v in asdict(sim.rules).items()},
                               public_configuration=configuration(args.opponent),
                               source_manifest='source_manifest.json')
            if self.opening is not None:
                self.report['opening_legal'] = self.opening['legal']
            (self.output / 'telemetry.json').write_text(json.dumps(self.samples), encoding='utf-8')
            (self.output / 'report.json').write_text(json.dumps(self.report, indent=2), encoding='utf-8')
            (self.output / 'stop').touch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=['walk', 'recover', 'shoot', 'kick', 'pass', 'match'], default='walk')
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--players', type=int, default=7, choices=range(1, 8))
    parser.add_argument('--half', type=int, default=30, help='Training half length; use 300 for full regulation length')
    parser.add_argument('--opponent', choices=('match', 'stand', *PUBLIC_KINDS), default='match')
    parser.add_argument('--swap-teams', action='store_true', help='Start the public opponent on the left and our team on the right')
    parser.add_argument('--strategy', choices=['baseline', 'demo-corrected', 'demo-fast-chase', 'demo-team-press'], default='baseline')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--realtime', action='store_true')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--mirror', action='store_true', help='Evaluate on the right team for a single-player fixture')
    parser.add_argument('--wall-limit', type=float, default=1200)
    parser.add_argument('--require-legal-opening',action='store_true',help='Refuse to start if any player is outside or opening placement violates rules')
    parser.add_argument('--startup-timeout',type=float,default=10.)
    args = parser.parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    root = Path(__file__).resolve().parents[1]
    parent = root / 'output/evaluations'
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=args.scenario + '-', dir=parent))
    snapshot = output / 'source'
    snapshot.mkdir()
    shutil.copytree(root / 'team', snapshot / 'team', ignore=shutil.ignore_patterns('__pycache__'))
    manifest = {}
    for path in sorted((snapshot / 'team').rglob('*')):
        if path.is_file():
            manifest[path.relative_to(snapshot).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for relative in ['tools/evaluate.py', 'tools/public_opponent.py', 'tools/bahia_opponent.py',
                     'tools/gru_opponent.py','tools/opening.py','tools/opponents.py',
                     'third_party/apollo/PROVENANCE.json', 'third_party/bahia/PROVENANCE.json',
                     f'third_party/{args.opponent}/PROVENANCE.json']:
        path = root / relative
        if path.exists():
            manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    (output / 'source_manifest.json').write_text(json.dumps(manifest, indent=2))
    logging.basicConfig(filename=output / 'server.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', force=True)
    with socket.socket() as a, socket.socket() as b:
        a.bind(('127.0.0.1', 0)); b.bind(('127.0.0.1', 0))
        aport, mport = a.getsockname()[1], b.getsockname()[1]
    values = asdict(SSim2026Rules())
    if args.scenario == 'match':
        values.update(half_time=args.half)
    sim = SoccerSimulation(FIFA7vs7SoccerField(), SoccerRules(**values), SoccerReferee())
    evaluator = Evaluator(sim, args, output)
    server = SoccerSimServer(sim, agent_port=aport, monitor_port=mport, render=args.render,
                             real_time=args.realtime, sync_mode=not args.realtime)
    evaluator.server = server
    server._monitors.append(evaluator)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    processes, logs = [], []
    try:
        time.sleep(.5)
        specs = [('StudyBlue', n, 'match') for n in range(1, args.players + 1)] if args.scenario == 'match' else [('StudyBlue', 7, 'walk' if args.scenario == 'walk' else 'stand' if args.scenario == 'recover' else 'match')]
        if args.mirror and args.scenario != 'match':
            specs.insert(0, ('StudyOrange', 1, 'stand'))
        if args.scenario == 'pass':
            specs += [('StudyBlue', 6, 'match')]
        if args.scenario == 'match':
            specs += [('StudyOrange', n, args.opponent) for n in range(1, args.players + 1)]
            if args.swap_teams:
                specs = specs[args.players:] + specs[:args.players]
        for team, number, behavior in specs:
            log = (output / f'{team}-{number}.log').open('w', encoding='utf-8'); logs.append(log)
            command = [sys.executable, '-m', 'team.agent', '--team', team, '--number', str(number),
                       '--behavior', behavior, '--port', str(aport), '--summary', str(output / f'{team}-{number}.json'),
                       '--stop-file', str(output / 'stop')]
            if behavior in PUBLIC_KINDS:
                command = [sys.executable, '-m', 'tools.public_opponent', '--kind', behavior,
                           '--team', team, '--number', str(number), '--port', str(aport),
                           '--summary', str(output / f'{team}-{number}.json'), '--stop-file', str(output / 'stop')]
            elif team == 'StudyBlue':
                command += ['--strategy', args.strategy]
            if args.scenario == 'walk':
                command += ['--walk-target', '-3' if args.mirror else '3', '-2' if args.mirror else '2']
            processes.append(subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT))
            if args.scenario == 'match' and team == specs[0][0] and number == args.players:
                # The Python opponent imports SciPy before sending init. A
                # fixed sleep can let the second team register first and swap
                # the intended sides. Wait for actual server registration.
                registration_deadline = time.monotonic()+45
                while len(list(sim.sim_agents)) < args.players:
                    if time.monotonic()>registration_deadline or any(p.poll() is not None for p in processes):
                        raise RuntimeError(f'First team failed to register: {output}')
                    time.sleep(.05)
            if args.mirror and team == 'StudyOrange':
                registration_deadline = time.monotonic()+45
                while not list(sim.sim_agents):
                    if time.monotonic()>registration_deadline:
                        raise RuntimeError('Mirror fixture first player failed to register')
                    time.sleep(.05)
        deadline = time.monotonic() + args.wall_limit
        while thread.is_alive() and time.monotonic() < deadline:
            if evaluator.startup_error:
                raise RuntimeError(f'{evaluator.startup_error}: {output}')
            if evaluator.done and all(p.poll() is not None for p in processes):
                break
            if any(p.poll() not in (None, 0) for p in processes):
                raise RuntimeError(f'Agent failed; logs: {output}')
            time.sleep(.2)
        if thread.is_alive() and not evaluator.done:
            raise TimeoutError(f'Evaluation wall limit exceeded: {output}')
        if not evaluator.done:
            if evaluator.startup_error:
                raise RuntimeError(f'{evaluator.startup_error}: {output}')
            raise RuntimeError(f'Server stopped before the evaluation completed: {output}')
        print(json.dumps({'output': str(output), **evaluator.report}), flush=True)
    finally:
        server.shutdown()
        for process in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
        # Removing fourteen robots can keep MuJoCo recompiling beyond two
        # seconds. Let its thread finish before Python destroys native objects.
        # Stopping the clients first also releases pending synchronous actions.
        thread.join()
        for log in logs:
            log.close()


if __name__ == '__main__':
    main()
