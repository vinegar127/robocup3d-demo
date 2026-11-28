"""A short T1 leg swing on top of the balancing walk policy.

Parameters measured in tools.optimize_walk_strike on official physics. Trigger
uses only the ball perception, joint sensors and gyro; no simulator handles.
"""
import math

from .geometry import rotate2


class Strike:
    DURATION = .3071790728880539
    RESIDUAL = (-.4546640913219392, .09044873321358504, .4223694568046157)
    ROLL = .05685551668835001

    def __init__(self):
        self.started = -math.inf
        self.last = -math.inf
        self.count = 0

    def active(self, world):
        return 0 <= world.now - self.started < self.DURATION

    def apply(self, target, world, enabled=False):
        if (enabled and not self.active(world) and world.now - self.last > 2.
                and world.ball_fresh(.2) and world.position is not None and not world.fallen):
            bx, by = rotate2((world.ball_position[0]-world.position[0], world.ball_position[1]-world.position[1]), -world.heading)
            hip, speed = world.joints.get('q_llj1', 0), world.joint_velocities.get('q_llj1', 0)
            if .37 < bx < .62 and .025 < by < .17 and -21 < hip < -2 and speed > 35 and world.position[2] > .56:
                self.started = self.last = world.now
                self.count += 1
        if not self.active(world):
            return target, False
        envelope = math.sin(math.pi * (world.now-self.started)/self.DURATION)
        target = list(target)
        for index, value in zip((11, 14, 15), self.RESIDUAL):
            target[index] += math.degrees(envelope*value)
        for index in (12, 18):
            target[index] += math.degrees(envelope*self.ROLL)
        for index in (16, 22):
            target[index] -= math.degrees(envelope*self.ROLL)
        return target, True
