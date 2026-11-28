"""The corrected teaching placement policy adapted to the physical T1 gait.

World coordinates are metres/radians, not the Demo's degrees. Team roles,
restarts, passing and measured walk/strike policies remain the T1 controller's.
The T1 stages 0.80 m behind the ball with its measured left-foot offset, then
walks through the real strike window; no synthetic impulse enters MuJoCo.
"""
import math

from .geometry import distance, rotate2, wrap
from .strategy import Plan, Strategy, navigate


class DemoCorrectedStrategy(Strategy):
    def __init__(self, config, number):
        super().__init__(config, number)
        self.orbit_sign = 0.

    def attack(self, world, restart=False, clear=False):
        base = super().attack(world, restart, clear)
        heading = base.face
        c, s = math.cos(heading), math.sin(heading)
        ball, position = world.ball_position, world.position
        setup = (ball[0] - .80*c + .10*s, ball[1] - .80*s - .10*c)
        local_ball = rotate2((ball[0]-position[0], ball[1]-position[1]), -world.heading)
        heading_error = abs(wrap(heading-world.heading))
        ball_angle = abs(math.atan2(local_ball[1], local_ball[0]))
        ready = (world.ball_fresh(.3) and distance(position, setup) <= .16
                 and heading_error <= math.radians(8) and ball_angle <= math.radians(10)
                 and .55 <= local_ball[0] <= 1.05)
        if not world.ball_fresh(.3) or heading_error > math.radians(10) or ball_angle > math.radians(25):
            self.push_ready = False
        elif ready:
            self.push_ready = True
        if self.push_ready:
            self.orbit_sign = 0.
            # Reuse the physical push-through target and pass-intent bookkeeping.
            return super().attack(world, restart, clear)

        dx, dy = setup[0]-position[0], setup[1]-position[1]
        rx, ry = position[0]-ball[0], position[1]-ball[1]
        length2 = dx*dx+dy*dy
        t = max(0., min(1., -(rx*dx+ry*dy)/max(length2, 1e-9)))
        clearance = math.hypot(rx+t*dx, ry+t*dy)
        if clearance < .50 and math.hypot(rx, ry) > .50:
            angle = math.atan2(ry, rx)
            delta = wrap(math.atan2(setup[1]-ball[1], setup[0]-ball[0])-angle)
            if not self.orbit_sign:
                self.orbit_sign = (1. if self.number % 2 == 0 else -1.) if abs(delta) > math.radians(150) else math.copysign(1., delta)
            delta = (delta*self.orbit_sign) % (2*math.pi)
            angle += min(math.radians(45), delta)*self.orbit_sign
            setup = (ball[0]+1.10*math.cos(angle), ball[1]+1.10*math.sin(angle))
        else:
            self.orbit_sign = 0.
        ball_heading = self.face_ball(world)
        face = heading if abs(wrap(ball_heading-heading)) < math.radians(45) else ball_heading
        state = base.state if base.state.startswith('ALIGN_') else 'ALIGN_'+base.state
        return Plan(state, setup, face, receiver=base.receiver)


def demo_navigate(plan, world):
    velocity = navigate(plan, world)
    if velocity is None or not plan.state.startswith('ALIGN_'):
        return velocity
    vx, vy, omega = velocity
    # The physical gait needs turn-first control at large heading errors.
    error = abs(wrap(plan.face-world.heading)) if plan.face is not None else 0.
    factor = max(0., min(1., (math.radians(32)-error)/math.radians(14)))
    return min(.9, vx)*factor, vy*factor, omega
