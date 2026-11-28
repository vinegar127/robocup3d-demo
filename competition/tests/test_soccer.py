import base64
import json
import math
import unittest

from team.agent import CONFIG
from team.communication import Communication, PACKET
from team.geometry import camera_to_world
from team.strategy import Strategy
from team.world import World


class SoccerTests(unittest.TestCase):
    def test_speech_fits_actual_server_limit_and_roundtrips(self):
        sender = Communication('StudyBlue', 1)
        source = World('StudyBlue', now=.85, position=(-4., 2., .66))
        source.ball = (2., 0., 0.)
        source.ball_position, source.ball_time, source.ball_source = (-2., 3., .11), .85, 'vision'
        command = sender.send(source)
        self.assertTrue(command)
        encoded = command.split()[-1][:-1]
        self.assertEqual(len(base64.b64decode(encoded)), 10)
        self.assertEqual(PACKET.size, 10)
        receiver = World('StudyBlue')
        receiver.update(f'(time (now .9))(MIC hear (0 {encoded}))')
        comm = Communication('StudyBlue', 2)
        comm.receive(receiver)
        self.assertEqual(comm.received, 1)
        self.assertEqual(receiver.teammates[1]['position'][:2], (-4., 2.))
        self.assertEqual(receiver.ball_position[:2], (-2., 3.))
        foreign = Communication('StudyOrange', 2)
        foreign.receive(World('StudyOrange', messages=[encoded]))
        self.assertEqual(foreign.received, 0)

    def test_camera_transform_and_right_side_rotation(self):
        point = camera_to_world((2., 0., 0.), (1., 2., .66), (1., 0., 0., 0.), 0., 0.)
        self.assertAlmostEqual(point[0], 3.1125)
        self.assertAlmostEqual(point[1], 2.)
        self.assertAlmostEqual(point[2], 1.08485)
        mirror = camera_to_world((2., 0., 0.), (-1., -2., .66), (0., 0., 0., 1.), 0., 0.)
        self.assertAlmostEqual(mirror[0], -point[0])
        self.assertAlmostEqual(mirror[1], -point[1])

    def test_vision_phantoms_do_not_steal_active_role(self):
        config = json.loads(CONFIG.read_text())
        world = World('StudyBlue', now=1., position=(0., 0., .66), ball_position=(1., 0., .11), ball_estimate_time=1.)
        world.teammates[2] = {'position': (.9, 0., .66), 'time': 1., 'source': 'vision'}
        self.assertEqual(Strategy(config, 7).select_active(world), 7)
        world.teammates[2]['heard_at'] = 1.
        self.assertEqual(Strategy(config, 7).select_active(world), 2)

    def test_shooting_geometry_on_both_sides(self):
        config = json.loads(CONFIG.read_text())
        for sign, side, quaternion in [(1, 'left', (1., 0., 0., 0.)), (-1, 'right', (0., 0., 0., 1.))]:
            world = World('StudyBlue', now=1., side=side, play_mode='PlayOn', position=(23.9 * sign, -.1 * sign, .66),
                          quaternion=quaternion, ball_position=(24.7 * sign, 0., .11), ball_estimate_time=1.)
            plan = Strategy(config, 7).plan(world)
            self.assertEqual(plan.state, 'SHOOT')
            self.assertGreater(plan.target[0] * sign, world.ball_position[0] * sign)
            self.assertAlmostEqual(abs(plan.face), 0 if sign == 1 else math.pi)

    def test_pass_release_is_a_plan_and_does_not_corrupt_role_assignment(self):
        config = json.loads(CONFIG.read_text())
        strategy = Strategy(config, 7)
        strategy.pass_receiver, strategy.pass_origin, strategy.pass_started = 6, (0., 0.), 1.
        world = World('StudyBlue', now=2., position=(0., 0., .66), play_mode='PlayOn',
                      ball_position=(1., 0., .11), ball_estimate_time=2.)
        self.assertIsInstance(strategy.select_active(world), int)
        plan = strategy.plan(world)
        self.assertEqual(plan.state, 'PASS_RELEASE')
        self.assertEqual(plan.receiver, 6)


if __name__ == '__main__':
    unittest.main()
