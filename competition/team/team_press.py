"""One ball carrier with close second-ball cover and a forward passing option."""
from dataclasses import replace
import math

from .chase_navigation import ChaseNavigator
from .demo_strategy import DemoCorrectedStrategy
from .geometry import distance
from .strategy import Plan


class TeamPressStrategy(DemoCorrectedStrategy):
    def formation(self, world):
        # Keep restart clearances and the two defenders' original safety shape.
        if world.play_mode != 'PlayOn' or self.number <= 3:
            return super().formation(world)
        positions = {self.number: world.position}
        positions.update({n: d['position'] for n, d in world.teammates.items()
                          if 4 <= n <= 7 and world.now-d.get('heard_at', -math.inf) < 2.})
        candidates = {n: p for n, p in positions.items() if 4 <= n <= 7 and n != self.active and p is not None}
        if not candidates:
            return super().formation(world)
        ball = world.ball_position
        bx, by, *_ = world.normalize(ball)
        # Half-metre bins reduce role swaps caused by centimetre-level reports.
        secondary = min(candidates, key=lambda n: (round(distance(candidates[n], ball)*2), n))
        secondary_y = world.normalize(candidates[secondary])[1]
        lane = 1. if secondary_y >= by else -1.
        forward_goal = (world.attack_sign*(bx+3.), world.attack_sign*(by-lane*4.))
        remaining = [n for n in candidates if n != secondary]
        runner = min(remaining, key=lambda n: (round(distance(candidates[n], forward_goal)*2), n)) if remaining else None
        if self.number == secondary:
            # Stay outside the primary's foot corridor, ready for a loose ball.
            x, y, state = bx-2.2, by+lane*2.4, 'PRESS_COVER'
        elif self.number == runner:
            defenders = sorted((world.normalize(d['position'])[0] for d in world.opponents.values()
                                if world.now-d['time'] < 1.), reverse=True)
            if len(defenders) >= 2:
                onside = max(bx, defenders[1])-.8
            else:
                # With incomplete opponents, stay behind the ball in their half.
                onside = bx-.6 if bx > 0 else -.5
            x, y, state = min(bx+3., onside), by-lane*4., 'ATTACK_RUN'
        else:
            beam_y = self.config['formation'][str(self.number)]['beam'][1]
            x, y, state = bx-6., by+max(-6., min(6., beam_y)), 'ATTACK_SUPPORT'
        x = max(-18.2, min(25.5, x))
        y = max(-16., min(16., y))
        sign = world.attack_sign
        return Plan(state, (sign*x, sign*y), self.face_ball(world))


class TeamPressNavigator(ChaseNavigator):
    def __call__(self, plan, world):
        if plan.state in ('PRESS_COVER', 'ATTACK_RUN', 'ATTACK_SUPPORT'):
            # This only changes navigation; these states never enable a leg swing.
            return super().__call__(replace(plan, state='ALIGN_PASS'), world)
        return super().__call__(plan, world)
