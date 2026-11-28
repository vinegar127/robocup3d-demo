import json
import math
from pathlib import Path
import unittest

from team.demo_strategy import DemoCorrectedStrategy, demo_navigate
from team.geometry import distance
from team.world import World


class DemoStrategyTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1]/'team/config.json').read_text())

    def world(self, position=(-.8, -.1, .66), heading=0., side='left', age=0.):
        return World('StudyBlue', now=2., side=side, play_mode='PlayOn',
                     position=position, quaternion=(math.cos(heading/2), 0., 0., math.sin(heading/2)),
                     ball_position=(0., 0., .11), ball_estimate_time=2.-age)

    def test_physical_foot_offset_and_radian_heading_on_both_sides(self):
        for sign, side, heading in [(1, 'left', 0.), (-1, 'right', math.pi)]:
            with self.subTest(side=side):
                world = self.world((-.8*sign, -.1*sign, .66), heading, side)
                plan = DemoCorrectedStrategy(self.config, 7).plan(world)
                self.assertEqual(plan.state, 'DRIBBLE')
                self.assertGreater(sign*plan.target[0], 0)

    def test_wrong_side_routes_around_ball_and_keeps_looking_at_it(self):
        world = self.world((1., 0., .66), math.pi)
        plan = DemoCorrectedStrategy(self.config, 7).plan(world)
        self.assertEqual(plan.state, 'ALIGN_DRIBBLE')
        self.assertGreater(abs(plan.target[1]), .5)
        self.assertAlmostEqual(abs(plan.face), math.pi)
        self.assertGreater(distance(plan.target, world.ball_position), .9)

    def test_large_turn_error_stops_translation(self):
        world = self.world(heading=math.pi/2)
        plan = DemoCorrectedStrategy(self.config, 7).plan(world)
        vx, vy, omega = demo_navigate(plan, world)
        self.assertEqual((vx, vy), (0., 0.))
        self.assertLess(omega, 0)

    def test_stale_ball_does_not_start_attack_even_at_setup(self):
        world = self.world(age=.8)
        strategy = DemoCorrectedStrategy(self.config, 7)
        plan = strategy.plan(world)
        self.assertTrue(plan.state.startswith('ALIGN_'))
        self.assertFalse(strategy.push_ready)

    def test_opponent_restart_clearance_is_preserved(self):
        world = self.world()
        world.play_mode = 'KickOff_Right'
        plan = DemoCorrectedStrategy(self.config, 7).plan(world)
        self.assertEqual(plan.state, 'RESTART_CLEARANCE')
        self.assertAlmostEqual(distance(plan.target, world.ball_position), 6.2)


if __name__ == '__main__':
    unittest.main()
