"""Legal action selection, learned motion, and server-routed communication."""

import math

from .world import World
from .motion import Motion
from .strategy import Strategy, Plan, navigate
from .communication import Communication
from .geometry import rotate, wrap


class Controller:
    def __init__(self, config: dict, player: int, team='StudyBlue', behavior='match', walk_target=None,
                 strategy='baseline'):
        self.joints = config["joints"]
        self.formation = config["formation"][str(player)]
        self.previous_mode = "Unknown"
        self.state = "WAIT_FOR_SENSORS"
        self.beams = 0
        self.commands = 0
        self.motion = None
        self.turn_limit = .5
        self.strategy = Strategy(config, player)
        self.navigate = navigate
        if strategy in ('demo-corrected', 'demo-fast-chase'):
            from .demo_strategy import DemoCorrectedStrategy, demo_navigate
            self.strategy = DemoCorrectedStrategy(config, player)
            self.navigate = demo_navigate
            if strategy == 'demo-fast-chase':
                from .chase_navigation import ChaseNavigator
                self.navigate = ChaseNavigator()
        elif strategy == 'demo-team-press':
            from .team_press import TeamPressStrategy, TeamPressNavigator
            self.strategy = TeamPressStrategy(config, player)
            self.turn_limit = .75
            self.navigate = TeamPressNavigator(turn_limit=self.turn_limit)
        self.communication = Communication(team, player)
        self.behavior = behavior
        self.walk_target = walk_target
        self.plan = Plan('READY')
        self.velocity = None
        self.states = {}

    def act(self, world: World) -> str:
        commands = []
        self.communication.receive(world)
        # Beam once on entry, never as a substitute for walking during PlayOn.
        if world.play_mode in ('BeforeKickOff', 'Goal_Left', 'Goal_Right') and self.previous_mode != world.play_mode:
            x, y, angle = self.formation["beam"]
            scored_by_us = world.play_mode == ('Goal_Left' if world.side == 'left' else 'Goal_Right')
            if self.strategy.number == 7 and (scored_by_us or (world.play_mode == 'BeforeKickOff' and world.side == 'right')):
                x = -6.5  # give the opponent's next kickoff its centre-circle clearance
            commands.append(f"(beam {x} {y} {angle})")
            self.beams += 1
        self.previous_mode = world.play_mode
        ready = all(name in world.joints for name in self.joints) and world.quaternion is not None
        stale = world.now - world.joint_time > 0.2
        if not ready or stale:
            self.state = "WAIT_FOR_SENSORS"
            return "".join(commands) + "(syn)"
        if self.motion is None:
            self.motion = Motion(list(self.joints), turn_limit=self.turn_limit)
        self.plan = self.strategy.plan(world)
        if self.behavior == 'stand':
            self.plan = Plan('STAND')
        elif self.behavior == 'walk' and world.play_mode == 'PlayOn':
            self.plan = Plan('WALK_TEST', tuple(self.walk_target)) if self.walk_target else Plan('WALK_TEST', velocity=(.7, 0., 0.))
        head = (55 * math.sin(world.now * .8), 10.)
        if world.ball_fresh(.6) and world.position is not None:
            vector = tuple(a - b for a, b in zip(world.ball_position, world.position))
            q = world.quaternion
            body = rotate(vector, (q[0], -q[1], -q[2], -q[3]))
            head = (max(-80, min(80, math.degrees(math.atan2(body[1], body[0])))),
                    max(-15, min(65, -math.degrees(math.atan2(body[2] - .35, math.hypot(body[0], body[1]))))))
        strike = self.plan.state in ('SHOOT', 'PASS', 'CLEAR', 'DRIBBLE') and abs(wrap((self.plan.face or 0.) - world.heading)) < .18
        self.velocity = self.navigate(self.plan, world)
        targets, gains, motion_state = self.motion.step(world, self.velocity, head, strike=strike)
        self.state = motion_state if motion_state in ('GET_UP', 'KICK') else self.plan.state
        self.states[self.state] = self.states.get(self.state, 0) + 1
        for (sensor, (actuator, *_)), target, (kp, kd) in zip(self.joints.items(), targets, gains):
            commands.append(f"({actuator} {target:.3f} 0 {kp} {kd} 0)")
        self.commands += len(self.joints)
        commands.append(self.communication.send(world, self.plan.receiver or 0))
        return "".join(commands) + "(syn)"
