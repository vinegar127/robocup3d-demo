"""Search short leg-swing residuals while the public gait balances the body."""
import argparse
import json
import math
from pathlib import Path

import mujoco
import numpy as np

from team.motion import GAINS, Policy
from team.world import World
from tools.optimize_kick import KickLab


class WalkStrikeLab(KickLab):
    def __init__(self):
        super().__init__()
        self.policy = Policy('walk')

    def run(self, p, ball=(.8, .1), record=False):
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[:] = self.initial
        self.player.place_at((0., 0., .673))
        self.player.init_joints()
        self.sim.ball.place_at((*ball, .11))
        mujoco.mj_forward(m, d)
        prefix = self.player.agent_id.prefix
        world = World('Lab')
        sensors = list(self.config['joints'])
        min_z, speed, kicked = 1., 0., False
        kick_t = None
        samples = []
        for i in range(180):
            world.now = i * .02
            world.position = tuple(self.player.xpos)
            world.quaternion = tuple(self.player.xquat)
            world.gyro = tuple(np.degrees(d.sensor(prefix + 'torso_gyro').data))
            world.joints = {s: math.degrees(d.sensor(prefix + s).data[0]) for s in sensors}
            world.joint_velocities = {s: math.degrees(d.sensor(prefix + 'd' + s).data[0]) for s in sensors}
            # Fixed time trigger used only during search. Runtime will use
            # relative ball geometry and gait phase, with no trainer inputs.
            if not kicked and world.now >= p[0]:
                kicked, kick_t = True, world.now
            target = np.radians(self.policy.step(world, sensors, (p[6] if world.now < 1.5 else 0., 0., 0.), reset=i == 0))
            if kick_t is not None:
                t = world.now - kick_t
                if t < p[1]:
                    envelope = math.sin(math.pi * t / p[1])
                    target[[11, 14, 15]] += envelope * np.array(p[2:5])
                    target[[12, 18]] += envelope * p[5]
                    target[[16, 22]] -= envelope * p[5]
            for name, value, (kp, kd) in zip(self.names, target, GAINS):
                self.sim.ctrl_motor(name, float(value), 0., kp, kd, 0.)
            mujoco.mj_step(m, d, 10)
            speed = max(speed, float(np.linalg.norm(self.sim.ball._qvel[:2])))
            min_z = min(min_z, float(self.player.xpos[2]))
            if record:
                samples.append({'t': world.now, 'ball': self.sim.ball.xpos.tolist(), 'torso': self.player.xpos.tolist(),
                                'left_hip': world.joints['q_llj1'], 'left_hip_velocity': world.joint_velocities['q_llj1']})
        end = self.sim.ball.xpos.copy()
        score = float(end[0]-ball[0] - .7*abs(end[1]-ball[1]) - (8 if min_z < .45 else 0))
        return {'score': score, 'range': float(end[0]-ball[0]), 'end_ball': end.tolist(),
                'peak_speed': speed, 'min_height': min_z, 'parameters': list(p), 'samples': samples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=160)
    parser.add_argument('--seed', type=int, default=2)
    args = parser.parse_args()
    lab, rng = WalkStrikeLab(), np.random.default_rng(args.seed)
    low = np.array([.2, .1, -1.2, -.6, -.4, -.12, .3])
    high = np.array([.85, .5, -.1, .8, .5, .12, 1.])
    best, results = None, []
    for i in range(args.trials):
        if i < args.trials//3 or rng.random()<.2:
            p = rng.uniform(low,high)
        else:
            p = np.clip(np.array(best['parameters']) + rng.normal(size=7)*(high-low)*.10,low,high)
        r = lab.run(p)
        results.append(r)
        if best is None or r['score'] > best['score']:
            best = r
            print(json.dumps({'trial':i,**r}),flush=True)
    parent = Path(__file__).resolve().parents[1]/'output/walk-strike'
    parent.mkdir(parents=True,exist_ok=True)
    (parent/f'seed-{args.seed}.json').write_text(json.dumps({'best':best,'trials':results},indent=2))
    (parent/'best.json').write_text(json.dumps(lab.run(best['parameters'],record=True),indent=2))


if __name__ == '__main__':
    main()
