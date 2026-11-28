"""Role selection, formations, safe lanes, and physical ball approach."""
from dataclasses import dataclass
import math

from .geometry import distance, rotate2, unit, wrap


@dataclass
class Plan:
    state: str
    target: tuple | None = None
    face: float | None = None
    velocity: tuple | None = None
    receiver: int | None = None


class Strategy:
    def __init__(self, config, number):
        self.number = number
        self.config = config
        self.active = 7
        self.chosen_at = -1.
        self.push_ready = False
        self.push_direction = None
        self.pass_receiver = None
        self.pass_origin = None
        self.pass_target = None
        self.pass_started = -math.inf

    def lane_clear(self, start, end, world):
        vector = (end[0] - start[0], end[1] - start[1])
        length = max(distance(start, end), .01)
        axis = unit(vector)
        for opponent in world.opponents.values():
            if world.now - opponent['time'] > 1.5:
                continue
            p = opponent['position']
            rel = (p[0] - start[0], p[1] - start[1])
            along = rel[0] * axis[0] + rel[1] * axis[1]
            perpendicular = abs(rel[0] * axis[1] - rel[1] * axis[0])
            if 0 < along < length and perpendicular < .8 + .12 * along:
                return False
        return True

    def select_active(self, world) -> int:
        candidates = {self.number: world.position}
        candidates.update({n: p['position'] for n, p in world.teammates.items()
                           if 1 <= n <= 7 and world.now - p.get('heard_at', -math.inf) < 2.})
        ball = world.ball_position
        field = {n: p for n, p in candidates.items() if n != 1 and p is not None}
        if not field:
            return self.number
        costs = {n: distance(p, ball) + (.5 if n != self.active else 0) + n * .001 for n, p in field.items()}
        selected = min(costs, key=costs.get)
        if selected != self.active and (world.now - self.chosen_at > .6 or self.active not in costs):
            self.active, self.chosen_at = selected, world.now
            self.push_ready = False
        return self.active

    def plan(self, world) -> Plan:
        if world.position is None:
            return Plan('LOCALIZE')
        if world.play_mode in ('BeforeKickOff', 'GameOver', 'Goal_Left', 'Goal_Right'):
            self.push_ready = False
            self.pass_receiver = None
            return Plan('READY' if world.play_mode != 'GameOver' else 'GAME_OVER')
        if not world.ball_fresh():
            return Plan('SEARCH_BALL', velocity=(0., 0., .35))
        sign = world.attack_sign
        ball = world.ball_position
        if self.pass_receiver is not None:
            if world.now - self.pass_started > 5:
                self.pass_receiver = None
                self.push_ready = False
            elif distance(ball, self.pass_origin) > .6 and world.now - self.pass_started > .3:
                return Plan('PASS_RELEASE', receiver=self.pass_receiver)
        bx, by, *_ = world.normalize(ball)
        position = world.position
        active = self.select_active(world)
        ours = world.play_mode.lower().endswith('_' + world.side)
        set_play = world.play_mode != 'PlayOn'
        if world.play_mode.lower().startswith('offside_'):
            ours = not ours
        if set_play and not ours:
            # Keep clear of the opponent's restart, including the centre circle.
            away = unit((position[0] - ball[0], position[1] - ball[1]))
            clearance = 6.2 if 'kickoff' in world.play_mode.lower() else 2.5
            if distance(position, ball) < clearance:
                target = (ball[0] + away[0] * clearance, ball[1] + away[1] * clearance)
                return Plan('RESTART_CLEARANCE', target)
            return self.formation(world)
        if self.number == 1:
            if (set_play and ours and 'goal_kick' in world.play_mode.lower()) or (bx < -22 and distance(position, ball) < 4):
                return self.attack(world, clear=True)
            return Plan('GOALKEEPER', (sign * -25.5, sign * max(-1.3, min(1.3, by * .16))), self.face_ball(world))
        if set_play and ours and 'goal_kick' in world.play_mode.lower():
            return self.formation(world)
        if self.number != active and world.play_mode == 'PlayOn':
            called = any(p['receiver'] == self.number and world.now - p['time'] < 1.2 for p in world.pass_intents.values())
            speed = math.hypot(*world.ball_velocity)
            if called and distance(position, ball) < 7:
                towards_receiver = unit((position[0] - ball[0], position[1] - ball[1]))
                target = (ball[0] - towards_receiver[0] * .15 + .3 * world.ball_velocity[0],
                          ball[1] - towards_receiver[1] * .15 + .3 * world.ball_velocity[1])
                return Plan('RECEIVE_PASS', target, self.face_ball(world))
        if self.number != active:
            return self.formation(world)
        return self.attack(world, restart=set_play)

    def face_ball(self, world):
        b, p = world.ball_position, world.position
        return math.atan2(b[1] - p[1], b[0] - p[0])

    def formation(self, world):
        sign = world.attack_sign
        ball = world.normalize(world.ball_position)
        beam = self.config['formation'][str(self.number)]['beam']
        # A continuous ball-dependent shape; only the selected player leaves it.
        x = max(-23, min(19, beam[0] + .45 * (ball[0] + 8)))
        y = max(-15.5, min(15.5, beam[1] + .3 * ball[1]))
        if self.number in (2, 3):
            x = min(x, ball[0] - 4)
        if x < -18.5:
            x = -18.2  # only the goalkeeper enters the penalty area by default
        return Plan('SUPPORT' if self.number >= 4 else 'DEFEND', (sign * x, sign * y), self.face_ball(world))

    def attack(self, world, restart=False, clear=False):
        ball, position, sign = world.ball_position, world.position, world.attack_sign
        goal = (sign * 27.7, 0.)
        action, receiver = ('CLEAR' if clear else 'DRIBBLE'), None
        destination = goal
        bx = sign * ball[0]
        if bx > 17:
            action = 'SHOOT'
            # Choose an open part of the actual 3.66 m goal, rather than
            # refusing to shoot whenever its centre is covered by the keeper.
            candidates = [(sign * 27.95, y) for y in (-1.15, 0., 1.15)]
            def opening(point):
                axis = unit((point[0] - ball[0], point[1] - ball[1]))
                gaps = []
                for data in world.opponents.values():
                    if world.now - data['time'] < 1.:
                        rel = (data['position'][0] - ball[0], data['position'][1] - ball[1])
                        along = rel[0] * axis[0] + rel[1] * axis[1]
                        if 0 < along < distance(ball, point):
                            gaps.append(abs(rel[0] * axis[1] - rel[1] * axis[0]))
                return min(gaps, default=3.) - .06 * abs(point[1] - ball[1])
            destination = max(candidates, key=opening)
        else:
            choices = []
            for n, data in world.teammates.items():
                point = data['position']
                advance = sign * (point[0] - ball[0])
                if n != 1 and world.now - data['time'] < 1.4 and advance > 2 and 3 < distance(ball, point) < 13 and self.lane_clear(ball, point, world):
                    choices.append((advance - .15 * distance(ball, point), n, point))
            if choices and (restart or bx < 17):
                _, receiver, destination = max(choices)
                action = 'PASS'
        if self.pass_receiver is not None:
            action, receiver, destination = 'PASS', self.pass_receiver, self.pass_target
        direction = unit((destination[0] - ball[0], destination[1] - ball[1]))
        heading = math.atan2(direction[1], direction[0])
        rel = (position[0] - ball[0], position[1] - ball[1])
        along = rel[0] * direction[0] + rel[1] * direction[1]
        lateral = rel[0] * -direction[1] + rel[1] * direction[0]
        setup = (ball[0] - .80 * direction[0] + .10 * direction[1], ball[1] - .80 * direction[1] - .10 * direction[0])
        if self.push_direction is not None and abs(wrap(heading - self.push_direction)) > .5:
            self.push_ready = False
        self.push_direction = heading
        if distance(position, setup) < .13 and abs(wrap(heading - world.heading)) < .14:
            self.push_ready = True
        if along > .2 or abs(lateral) > .4 or distance(position, ball) > 1.3:
            self.push_ready = False
        if self.push_ready:
            if action == 'PASS' and self.pass_receiver is None:
                self.pass_receiver, self.pass_target = receiver, destination
                self.pass_origin, self.pass_started = ball, world.now
            target = (ball[0] + direction[0] * 1.2 + .09 * direction[1], ball[1] + direction[1] * 1.2 - .09 * direction[0])
            return Plan(action, target, heading, receiver=receiver)
        if along > -.1 and abs(lateral) < .65:
            side = -1 if lateral < 0 else 1
            setup = (ball[0] - direction[1] * side * .85 - direction[0] * .3,
                     ball[1] + direction[0] * side * .85 - direction[1] * .3)
        return Plan('ALIGN_' + action, setup, heading, receiver=receiver)


def navigate(plan, world):
    if plan.velocity is not None:
        return plan.velocity
    if plan.target is None or world.position is None:
        return None
    target = list(plan.target)
    # A shot must be able to follow the ball across the goal line. Clamping the
    # striker to 1 m before the line can leave a slow ball stuck on the line.
    x_limit = 28.1 if plan.state in ('SHOOT', 'ALIGN_SHOOT', 'DRIBBLE', 'ALIGN_DRIBBLE', 'CLEAR', 'ALIGN_CLEAR') else 26.5
    target[0], target[1] = max(-x_limit, min(x_limit, target[0])), max(-17, min(17, target[1]))
    dx, dy = target[0] - world.position[0], target[1] - world.position[1]
    dist = math.hypot(dx, dy)
    heading = math.atan2(dy, dx) if dist > .1 else world.heading
    close = dist < 1.8 or plan.state.startswith('ALIGN_')
    face = plan.face if plan.face is not None and close else heading
    vx, vy = rotate2((dx, dy), -world.heading)
    tolerance = .045 if plan.state.startswith('ALIGN_') else .12
    speed = min(1., math.sqrt(max(0., 1.5 * (dist - tolerance))))
    if dist > 1e-6:
        vx, vy = vx / dist * speed, vy / dist * speed
    if not close:
        vx *= max(.1, math.cos(wrap(heading - world.heading)))
    if dist < tolerance:
        vx, vy = 0., 0.
    # Local collision avoidance based only on current perceptions/reports.
    if plan.state not in ('PASS', 'SHOOT', 'DRIBBLE', 'CLEAR'):
        for other in list(world.teammates.values()) + list(world.opponents.values()):
            if world.now - other['time'] > 1:
                continue
            ox, oy = rotate2((other['position'][0] - world.position[0], other['position'][1] - world.position[1]), -world.heading)
            gap = math.hypot(ox, oy)
            if .05 < gap < .9:
                vx -= .3 * ox / gap
                vy -= .3 * oy / gap
    # The learned gait has a measured dead band at small commands, especially
    # while the head is pitched down. Compensate it to finish fine alignment.
    if plan.state.startswith('ALIGN_') and dist > .12:
        if abs(vx) > .06:
            vx += math.copysign(.22, vx)
        if abs(vy) > .06:
            vy += math.copysign(.12, vy)
    omega = .8 * wrap(face - world.heading)
    if plan.state.startswith('ALIGN_') and abs(wrap(face-world.heading)) > .10:
        omega += math.copysign(.10, omega)
    return (max(-.5, min(1., vx)), max(-.5, min(.5, vy)), max(-.5, min(.5, omega)))
