"""Offline keyframe search on the unmodified official T1, turf and ball.

Training resets are confined here. The resulting trajectory uses ordinary PD
joint targets; it has no ball forces or simulation access in the team client.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np

from rcsssmj.games.soccer.sim.soccer_sim import SoccerSimulation
from rcsssmj.games.soccer.soccer_fields import FIFA7vs7SoccerField
from rcsssmj.games.soccer.soccer_rules import SSim2026Rules


def trajectory(p):
    # All angles are radians. Left foot kicks, right leg supports.
    neutral = np.zeros(23)
    neutral[3], neutral[7] = -1.57, 1.57
    shift = neutral.copy()
    shift[[11, 17]] = -.12
    shift[[14, 20]] = .24
    shift[[15, 21]] = -.12
    shift[[12, 18]] = p[0]
    shift[[16, 22]] = -p[0]
    back = shift.copy()
    back[11], back[14], back[15] = p[1], p[2], -p[1] - p[2]
    strike = shift.copy()
    strike[11], strike[14], strike[15] = p[3], p[4], p[5]
    return [(0., neutral), (.35, shift), (.35 + p[6], back),
            (.35 + p[6] + p[7], strike), (.65 + p[6] + p[7], shift),
            (1. + p[6] + p[7], neutral)]


def sample(frames, t):
    for (t0, a), (t1, b) in zip(frames, frames[1:]):
        if t <= t1:
            u = np.clip((t - t0) / (t1 - t0), 0, 1)
            return a + u * (b - a)
    return frames[-1][1]


class KickLab:
    def __init__(self):
        self.sim = SoccerSimulation(FIFA7vs7SoccerField(), SSim2026Rules())
        assert self.sim.init()
        self.player = self.sim.add_players([SimpleNamespace(model_name='T1', team_name='Lab', player_no=7)])[0]
        self.model, self.data = self.sim.mj_model, self.sim.mj_data
        self.config = json.loads((Path(__file__).resolve().parents[1] / 'team/config.json').read_text())
        prefix = self.player.agent_id.prefix
        self.names = [prefix + v[0] for v in self.config['joints'].values()]
        self.qidx = [int(self.model.sensor(prefix + s).objid[0]) for s in self.config['joints']]
        self.sensor_names = [prefix + s for s in self.config['joints']]
        self.initial = self.data.qpos.copy()
        self.dt = .02

    def run(self, p, ball=(.34, .10), record=False):
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[:] = self.initial
        self.player.place_at((0., 0., .673))
        self.player.init_joints()
        self.sim.ball.place_at((*ball, .11))
        mujoco.mj_forward(m, d)
        frames = trajectory(p)
        peak_speed, min_z, max_x = 0., 1., ball[0]
        samples = []
        for i in range(200):
            t = i * self.dt
            target = sample(frames, t)
            for name, value in zip(self.names, target):
                self.sim.ctrl_motor(name, float(value), 0., 150., 3., 0.)
            mujoco.mj_step(m, d, 10)
            peak_speed = max(peak_speed, float(np.linalg.norm(self.sim.ball._qvel[:2])))
            min_z = min(min_z, float(self.player.xpos[2]))
            max_x = max(max_x, float(self.sim.ball.xpos[0]))
            if record:
                samples.append({'t': t, 'ball': self.sim.ball.xpos.tolist(), 'torso': self.player.xpos.tolist()})
        end = self.sim.ball.xpos.copy()
        # Prefer forward range, direction and a player that can keep playing.
        score = float(end[0] - ball[0] - .6 * abs(end[1] - ball[1]) - (3 if min_z < .4 else 0))
        return {'score': score, 'range': float(end[0] - ball[0]), 'end_ball': end.tolist(),
                'peak_speed': peak_speed, 'min_height': min_z, 'parameters': list(p), 'samples': samples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=200)
    parser.add_argument('--seed', type=int, default=1)
    args = parser.parse_args()
    lab, rng = KickLab(), np.random.default_rng(args.seed)
    initial = np.array([.12, .2, .9, -.8, .6, .1, .3, .12])
    low = np.array([.02, -.1, .3, -1.4, .1, -.5, .15, .06])
    high = np.array([.25, .6, 1.4, -.3, 1., .5, .5, .3])
    best = None
    results = []
    for i in range(args.trials):
        if i == 0:
            p = initial
        elif i < args.trials // 3 or rng.random() < .2:
            p = rng.uniform(low, high)
        else:
            p = np.clip(np.array(best['parameters']) + rng.normal(size=8) * (high-low) * .12, low, high)
        result = lab.run(p)
        results.append(result)
        if best is None or result['score'] > best['score']:
            best = result
            print(json.dumps({'trial': i, **best}), flush=True)
    parent = Path(__file__).resolve().parents[1] / 'output/kick-search'
    parent.mkdir(parents=True, exist_ok=True)
    (parent / f'seed-{args.seed}.json').write_text(json.dumps({'best': best, 'trials': results}, indent=2))
    (parent / 'best.json').write_text(json.dumps(lab.run(best['parameters'], record=True), indent=2))


if __name__ == '__main__':
    main()
