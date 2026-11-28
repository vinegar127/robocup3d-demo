"""Turn toward distant destinations; retain ball-facing control near contact."""
from dataclasses import replace
import math

from .demo_strategy import demo_navigate
from .geometry import distance, wrap
from .strategy import navigate


class ChaseNavigator:
    def __init__(self, turn_limit=.5):
        self.travelling = False
        self.turn_limit = turn_limit

    def turn_cap(self, world, vx=0., vy=0.):
        near_ball = world.ball_position is not None and world.position is not None and distance(world.position, world.ball_position) < 1.2
        return .5 if near_ball or math.hypot(vx, vy) > .15 else self.turn_limit

    def __call__(self, plan, world):
        if plan.state == 'SEARCH_BALL' and plan.velocity is not None:
            self.travelling = False
            vx, vy, omega = plan.velocity
            return vx, vy, math.copysign(self.turn_cap(world, vx, vy), omega) if omega else 0.
        # The physical comparison found turn-first slower for defensive retreat.
        # Change active ball approach only; retain support, keeper and leg swing.
        if (not plan.state.startswith('ALIGN_') or plan.velocity is not None
                or plan.target is None or world.position is None):
            self.travelling = False
            return demo_navigate(plan, world)
        x_limit = 28.1 if plan.state in ('ALIGN_SHOOT', 'ALIGN_DRIBBLE', 'ALIGN_CLEAR') else 26.5
        tx = max(-x_limit, min(x_limit, plan.target[0]))
        ty = max(-17., min(17., plan.target[1]))
        dx, dy = tx-world.position[0], ty-world.position[1]
        distance = math.hypot(dx, dy)
        # Hysteresis avoids changing body orientation at every small target update.
        if distance > 1.6:
            self.travelling = True
        elif distance < .9:
            self.travelling = False
        if self.travelling:
            face = math.atan2(dy, dx)
            error = wrap(face-world.heading)
            vx, vy, _ = navigate(replace(plan, face=face), world)
            factor = max(0., min(1., (math.radians(32)-abs(error))/math.radians(14)))
            vx = max(0., min(1., vx))*factor
            vy = max(-.2, min(.2, vy))*factor
        else:
            velocity = demo_navigate(plan, world)
            if velocity is None:
                return None
            vx, vy, _ = velocity
            face = plan.face if plan.face is not None else (math.atan2(dy, dx) if distance > .1 else world.heading)
            error = wrap(face-world.heading)
        # Experimental profiles may use a measured larger stationary-turn cap.
        omega = 1.6*error
        if plan.state.startswith('ALIGN_') and abs(error) > .10:
            omega += math.copysign(.10, error)
        cap = self.turn_cap(world, vx, vy)
        return vx, vy, max(-cap, min(cap, omega))
