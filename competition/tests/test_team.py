import struct
import unittest

from team.behavior import Controller
from team.agent import CONFIG
from team.protocol import Connection, MAX_FRAME, parse
from team.world import World
import json


class FragmentedSocket:
    def __init__(self, data):
        self.data = bytearray(data)
        self.sent = b""

    def recv(self, count):
        count = min(count, 2, len(self.data))
        chunk = self.data[:count]
        del self.data[:count]
        return bytes(chunk)

    def sendall(self, data):
        self.sent += data


class ProtocolTests(unittest.TestCase):
    def test_tcp_fragmentation_and_back_to_back_frames(self):
        connection = Connection.__new__(Connection)
        connection.socket = FragmentedSocket(b"\0\0\0\5(syn)\0\0\0\3(x)")
        self.assertEqual(connection.receive(), "(syn)")
        self.assertEqual(connection.receive(), "(x)")
        connection.send("(syn)")
        self.assertEqual(connection.socket.sent, b"\0\0\0\5(syn)")

    def test_invalid_frame_and_truncated_connection(self):
        connection = Connection.__new__(Connection)
        for data, error in [(struct.pack("!I", MAX_FRAME + 1), ValueError),
                            (b"\0\0\0\5(ab", ConnectionError)]:
            connection.socket = FragmentedSocket(data)
            with self.assertRaises(error):
                connection.receive()

    def test_nested_and_malformed_expressions(self):
        self.assertEqual(parse('(See (B (pol 2 10 -5)))(syn)')[0][1],
                         ["B", ["pol", "2", "10", "-5"]])
        for message in ["(x", ")", "(x))", "outside(x)"]:
            with self.subTest(message=message), self.assertRaises(ValueError):
                parse(message)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.controller = Controller(self.config, 1)
        self.world = World("StudyBlue")
        self.world.joints = dict.fromkeys(self.config["joints"], 0)
        self.world.joint_time = 0

    def test_sparse_vision_ages_and_team_side(self):
        self.world.update('(time (now 1))(GS (pm PlayOn)(tl Opponent)(tr StudyBlue))'
                          '(See (B (pol 2 10 -5)))')
        self.world.update('(time (now 1.06))(GS (pm PlayOn))')
        self.assertEqual(self.world.side, "right")
        self.assertAlmostEqual(self.world.now - self.world.ball_time, .06)
        self.assertEqual(self.world.ball, (2., 10., -5.))

    def test_beam_only_once_before_kickoff_and_never_during_play(self):
        self.world.play_mode = "BeforeKickOff"
        self.assertIn("(beam", self.controller.act(self.world))
        self.assertNotIn("(beam", self.controller.act(self.world))
        self.world.play_mode = "PlayOn"
        self.assertNotIn("(beam", self.controller.act(self.world))
        self.world.play_mode = "BeforeKickOff"
        self.assertIn("(beam", self.controller.act(self.world))

    def test_stale_joints_and_invalid_sensor_values(self):
        self.world.now = 1
        self.world.play_mode = "PlayOn"
        self.assertEqual(self.controller.act(self.world), "(syn)")
        with self.assertRaises(ValueError):
            self.world.update('(pos (n torso_pos)(p nan 0 1))')


if __name__ == "__main__":
    unittest.main()
