"""Update only from per-agent server perceptions; no privileged simulator API."""

from dataclasses import dataclass, field
import math

from .protocol import fields, parse
from .geometry import camera_to_world, distance, yaw


def numbers(values: list, count: int) -> tuple:
    if len(values) != count:
        raise ValueError("Unexpected perception dimensions")
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise ValueError("Non-finite sensor value")
    return result


@dataclass
class World:
    team_name: str
    now: float = 0.0
    play_mode: str = "Unknown"
    side: str = "unknown"
    joints: dict = field(default_factory=dict)
    joint_time: float = -math.inf
    joint_velocities: dict = field(default_factory=dict)
    joint_times: dict = field(default_factory=dict)
    gyro: tuple = (0., 0., 0.)
    accel: tuple = (0., 0., 0.)
    position: tuple | None = None
    quaternion: tuple | None = None
    ball: tuple | None = None  # camera-relative distance, azimuth, elevation
    ball_time: float = -math.inf
    frames: int = 0
    game_time: float = 0.
    score: tuple = (0, 0)
    ball_position: tuple | None = None
    ball_velocity: tuple = (0., 0.)
    ball_source: str = 'unknown'
    ball_estimate_time: float = -math.inf
    teammates: dict = field(default_factory=dict)
    opponents: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)
    pass_intents: dict = field(default_factory=dict)

    def update(self, message: str) -> None:
        expressions = parse(message)
        # Resolve time before attaching timestamps to other sensors.
        for node in expressions:
            if node and node[0] == "time":
                self.now = numbers(fields(node)["now"], 1)[0]
        for node in expressions:
            if not node:
                continue
            data = fields(node)
            if node[0] == "GS":
                self.play_mode = data.get("pm", [self.play_mode])[0]
                self.game_time = numbers(data.get('t', [self.game_time]), 1)[0]
                self.score = (int(data.get('sl', [self.score[0]])[0]), int(data.get('sr', [self.score[1]])[0]))
                if data.get("tl") == [self.team_name]:
                    self.side = "left"
                elif data.get("tr") == [self.team_name]:
                    self.side = "right"
            elif node[0] == "HJ":
                self.joints[data["n"][0]] = numbers(data["ax"], 1)[0]
                self.joint_velocities[data['n'][0]] = numbers(data.get('vx', [0]), 1)[0]
                self.joint_times[data['n'][0]] = self.now
                self.joint_time = self.now
            elif node[0] == 'GYR':
                self.gyro = numbers(data['rt'], 3)
            elif node[0] == 'ACC':
                self.accel = numbers(data['a'], 3)
            elif node[0] == "pos" and data.get("n") == ["torso_pos"]:
                self.position = numbers(data["p"], 3)
            elif node[0] == "quat" and data.get("n") == ["torso_quat"]:
                quaternion = numbers(data["q"], 4)
                norm = math.sqrt(sum(q * q for q in quaternion))
                if norm < 0.5:
                    raise ValueError("Invalid torso quaternion")
                self.quaternion = tuple(q / norm for q in quaternion)
        self.messages = []
        for node in expressions:
            if not node:
                continue
            if node[0] in ('hear', 'MIC'):
                # (hear (angle base64-message) ...), emitted by MicrophonePerception.
                self.messages.extend(x[-1] for x in node[1:] if isinstance(x, list) and len(x) >= 2)
            elif node[0] == "See":
                for item in node[1:]:
                    if isinstance(item, list) and item and item[0] == "B":
                        self.ball = numbers(fields(item)["pol"], 3)
                        self.ball_time = self.now
                        if self.position is not None and self.quaternion is not None:
                            observed = self.to_world(self.ball)
                            if abs(observed[0]) < 32 and abs(observed[1]) < 23 and -.3 < observed[2] < 5:
                                elapsed = self.now - self.ball_estimate_time
                                if self.ball_position is not None and self.ball_source == 'vision' and .015 < elapsed < .5 and distance(observed, self.ball_position) < 2:
                                    measured = tuple((observed[i] - self.ball_position[i]) / elapsed for i in range(2))
                                    self.ball_velocity = tuple(.25 * max(-12, min(12, v)) + .75 * self.ball_velocity[i] for i, v in enumerate(measured))
                                else:
                                    self.ball_velocity = (0., 0.)
                                self.ball_position = observed
                                self.ball_estimate_time = self.now
                                self.ball_source = 'vision'
                    elif isinstance(item, list) and item and item[0] == 'P' and self.position is not None and self.quaternion is not None:
                        other = fields(item)
                        if 'team' not in other or 'id' not in other:
                            continue
                        points = [self.to_world(numbers(fields(p)['pol'], 3)) for p in item[1:] if isinstance(p, list) and 'pol' in fields(p)]
                        if points:
                            point = tuple(sum(p[i] for p in points) / len(points) for i in range(3))
                            target = self.teammates if other['team'][0] == self.team_name else self.opponents
                            identity = int(other['id'][0])
                            heard = target.get(identity, {}).get('heard_at', -math.inf)
                            target[identity] = {'position': point, 'time': self.now, 'source': 'vision', 'heard_at': heard}
        self.frames += 1

    def to_world(self, polar):
        return camera_to_world(polar, self.position, self.quaternion,
                               math.radians(self.joints.get('q_hj1', 0)), math.radians(self.joints.get('q_hj2', 0)))

    @property
    def heading(self):
        return yaw(self.quaternion) if self.quaternion else 0.

    @property
    def attack_sign(self):
        return -1 if self.side == 'right' else 1

    def normalize(self, point):
        return tuple(self.attack_sign * x if i < 2 else x for i, x in enumerate(point))

    def ball_fresh(self, age=2.):
        return self.ball_position is not None and self.now - self.ball_estimate_time <= age

    @property
    def fallen(self) -> bool:
        if self.quaternion is None:
            return False
        _, qx, qy, _ = self.quaternion
        return 1 - 2 * (qx * qx + qy * qy) < math.cos(math.radians(60))
