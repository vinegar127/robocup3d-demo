import json
import math
from pathlib import Path
import unittest

from team.team_press import TeamPressStrategy
from team.world import World


class TeamPressTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1]/'team/config.json').read_text())

    def world(self, number, sign=1):
        poses = {1: (-25, 0), 2: (-17, 8), 3: (-17, -8), 4: (-11, 6),
                 5: (-11, -6), 6: (-6.5, 5.5), 7: (-.75, 0)}
        heading = 0 if sign == 1 else math.pi
        p = poses[number]
        world = World('StudyBlue', now=2., play_mode='PlayOn', side='left' if sign == 1 else 'right',
                      position=(sign*p[0], sign*p[1], .66),
                      quaternion=(math.cos(heading/2), 0, 0, math.sin(heading/2)),
                      ball_position=(0, 0, .11), ball_estimate_time=2.)
        world.teammates = {n: {'position': (sign*x, sign*y, .66), 'time': 2., 'heard_at': 2.}
                           for n, (x, y) in poses.items() if n != number}
        world.opponents = {n: {'position': (sign*x, 0., .66), 'time': 2.}
                           for n, x in [(1, 25), (2, 15)]}
        return world

    def test_has_one_carrier_two_near_support_roles_and_two_defenders(self):
        plans = {n: TeamPressStrategy(self.config, n).plan(self.world(n)) for n in range(1, 8)}
        self.assertEqual(plans[6].state, 'PRESS_COVER')
        self.assertEqual(plans[5].state, 'ATTACK_RUN')
        self.assertEqual(plans[4].state, 'ATTACK_SUPPORT')
        self.assertEqual(plans[2].state, 'DEFEND')
        self.assertEqual(plans[3].state, 'DEFEND')
        self.assertEqual(plans[1].state, 'GOALKEEPER')
        self.assertNotEqual(plans[5].target, plans[6].target)

    def test_support_geometry_mirrors_with_attack_direction(self):
        for n in [4, 5, 6]:
            left = TeamPressStrategy(self.config, n).plan(self.world(n, 1))
            right = TeamPressStrategy(self.config, n).plan(self.world(n, -1))
            self.assertEqual(left.state, right.state)
            self.assertAlmostEqual(left.target[0], -right.target[0])
            self.assertAlmostEqual(left.target[1], -right.target[1])

    def test_forward_runner_stays_onside_with_partial_opponents(self):
        world = self.world(5)
        world.ball_position = (10., 0., .11)
        world.opponents = {}
        strategy = TeamPressStrategy(self.config, 5)
        plan = strategy.formation(world)
        self.assertEqual(plan.state, 'ATTACK_RUN')
        self.assertLess(plan.target[0], world.ball_position[0])

    def test_opponent_restart_does_not_use_the_attacking_shape(self):
        world = self.world(6)
        world.play_mode = 'KickOff_Right'
        strategy = TeamPressStrategy(self.config, 6)
        plan = strategy.formation(world)
        self.assertEqual(plan.state, 'SUPPORT')

    def test_stale_reports_cannot_assign_forward_roles(self):
        world = self.world(4)
        for player in world.teammates.values():
            player['heard_at'] = -10.
        plan = TeamPressStrategy(self.config, 4).formation(world)
        self.assertEqual(plan.state, 'PRESS_COVER')


if __name__ == '__main__':
    unittest.main()
