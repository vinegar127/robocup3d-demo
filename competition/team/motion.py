# SPDX-License-Identifier: GPL-3.0-or-later
# Policy observation/action contract adapted from Apollo Codebase, copyright
# 2026 HKUST (Guangzhou), Humanoid Computing & Learning Lab. See third_party/apollo.
"""CPU inference for the pinned public T1 walk and get-up models."""
import math
from pathlib import Path

import numpy as np
import onnxruntime as ort

from .geometry import rotate
from .strike import Strike

HOME = np.array([0, 0, 0, -1.4, 0, -.4, 0, 1.4, 0, .4, 0,
                 -.2, 0, 0, .4, -.2, 0, -.2, 0, 0, .4, -.2, 0], dtype=np.float32)
GAINS = [(10, 1), (20, 1), (45, 2.5), (45, 2.5), (30, 1.2), (30, 1.2),
         (45, 2.5), (45, 2.5), (30, 1.2), (30, 1.2), (85, 5),
         (130, 10), (90, 8), (70, 3), (140, 6), (45, 2), (40, 1.8),
         (130, 10), (90, 8), (70, 3), (140, 6), (45, 2), (40, 1.8)]


class Policy:
    def __init__(self, kind, turn_limit=.5):
        self.kind = kind
        self.turn_limit = turn_limit
        path = Path(__file__).resolve().parents[1] / 'third_party/apollo/assets/networks' / kind / 'policy.onnx'
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(path.read_bytes(), options, providers=['CPUExecutionProvider'])
        self.name = self.session.get_inputs()[0].name
        expected = 78 if kind == 'walk' else 75
        if self.session.get_inputs()[0].shape != [1, expected] or self.session.get_outputs()[0].shape != [1, 23]:
            raise ValueError(f'Unexpected {kind} model contract')
        self.previous = np.zeros(23, dtype=np.float32)

    def step(self, world, sensors, velocity=(0., 0., 0.), reset=False):
        if reset:
            self.previous.fill(0)
        q = world.quaternion or (1., 0., 0., 0.)
        gravity = rotate((0., 0., -1.), (q[0], -q[1], -q[2], -q[3]))
        imu = [math.radians(v) for v in world.gyro] + list(gravity)
        positions = np.radians([world.joints[s] for s in sensors]).astype(np.float32)
        velocities = np.radians([world.joint_velocities.get(s, 0.) for s in sensors]).astype(np.float32)
        centered = positions - HOME
        previous = self.previous.copy()
        if self.kind == 'walk':
            centered[:2], velocities[:2], previous[:2] = 0, 0, 0
            command = np.clip(velocity, [-.5, -.5, -self.turn_limit], [1., .5, self.turn_limit])
            observation = np.concatenate([imu, command, centered, velocities, previous])
        else:
            observation = np.concatenate([imu, centered, velocities, previous])
        action = self.session.run(None, {self.name: observation.astype(np.float32)[None, :]})[0][0]
        if not np.isfinite(action).all():
            raise ValueError('Motion policy produced non-finite targets')
        action = np.clip(action, -5., 5.)
        self.previous = action
        target = HOME + .25 * action if self.kind == 'walk' else positions + .6 * action
        return np.degrees(target).tolist()


class Motion:
    def __init__(self, sensors, turn_limit=.5):
        self.sensors = sensors
        self.walk = Policy('walk', turn_limit=turn_limit)
        self.getup = Policy('getup')
        self.kind = 'neutral'
        self.recovery_start = 0.
        self.upright_start = None
        self.recoveries = 0
        self.recovery_attempts = 0
        self.strike = Strike()

    def step(self, world, velocity=None, head=(0., 0.), strike=False):
        needs_recovery = world.fallen or (world.position is not None and world.position[2] < .40)
        if needs_recovery and self.kind != 'getup':
            self.kind = 'getup'
            self.recovery_start = world.now
            self.upright_start = None
            self.recovery_attempts += 1
            reset = True
        else:
            reset = False
        if self.kind == 'getup':
            target = self.getup.step(world, self.sensors, reset=reset)
            upright = not world.fallen and world.position is not None and world.position[2] > .55
            self.upright_start = (world.now if self.upright_start is None else self.upright_start) if upright else None
            if self.upright_start is not None and world.now - self.upright_start > .3:
                self.recoveries += 1
                self.kind = 'neutral'
            elif world.now - self.recovery_start > 12:
                self.getup.previous.fill(0)
                self.recovery_start = world.now
                self.recovery_attempts += 1
            return target, GAINS, 'GET_UP'
        if velocity is None:
            self.kind = 'neutral'
            # Zero legs and arms lowered; proven static starting pose.
            target = [0.] * 23
            target[3], target[7] = -90., 90.
            target[:2] = head
            return target, [(150, 1)] * 23, 'STAND'
        if self.strike.active(world):
            velocity = (.9175, 0., 0.)
        target = self.walk.step(world, self.sensors, velocity, reset=self.kind != 'walk')
        self.kind = 'walk'
        target[:2] = head
        target, kicking = self.strike.apply(target, world, enabled=strike)
        return target, GAINS, 'KICK' if kicking else 'WALK'
