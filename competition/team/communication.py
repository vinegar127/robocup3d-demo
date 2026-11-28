"""Compact, server-routed team reports. No external inter-player channel."""
import base64
import hashlib
import struct

PACKET = struct.Struct('!BBhhhh')  # exactly 10 raw bytes: server's speech limit


class Communication:
    def __init__(self, team, number):
        self.tag = hashlib.sha256(team.encode()).digest()[0]
        self.number = number
        self.last_slot = -1
        self.sent = 0
        self.received = 0

    def receive(self, world):
        for text in world.messages:
            try:
                raw = base64.b64decode(text, validate=True)
                if len(raw) != PACKET.size:
                    continue
                tag, flags, px, py, bx, by = PACKET.unpack(raw)
                number = flags & 7
                if tag != self.tag or not flags & 128 or not 1 <= number <= 7 or number == self.number:
                    continue
                position = (px / 100, py / 100, .65)
                if abs(position[0]) > 34 or abs(position[1]) > 24:
                    continue
                world.teammates[number] = {'position': position, 'time': world.now, 'source': 'hear', 'heard_at': world.now}
                self.received += 1
                receiver = (flags >> 4) & 7
                if receiver:
                    world.pass_intents[number] = {'receiver': receiver, 'time': world.now}
                report_time = world.now - .12
                if flags & 8 and report_time > world.ball_estimate_time + .1:
                    world.ball_position = (bx / 100, by / 100, .11)
                    world.ball_velocity = (0., 0.)
                    world.ball_estimate_time = report_time
                    world.ball_source = 'hear'
            except (ValueError, struct.error):
                continue

    def send(self, world, receiver=0):
        slot = int(world.now / .12)
        if slot == self.last_slot or slot % 7 != self.number - 1 or world.position is None:
            return ''
        self.last_slot = slot
        ball = world.ball_position or (0., 0., .11)
        fresh = world.ball_source == 'vision' and world.now - world.ball_time < .6
        flags = 128 | ((receiver & 7) << 4) | self.number | (8 if fresh else 0)
        values = world.position[:2] + ball[:2]
        quantized = [max(-32768, min(32767, round(v * 100))) for v in values]
        encoded = base64.b64encode(PACKET.pack(self.tag, flags, *quantized)).decode('ascii')
        self.sent += 1
        return f'(SPK say 100 {encoded})'
