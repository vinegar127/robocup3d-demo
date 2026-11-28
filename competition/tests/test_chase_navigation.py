import math
import unittest

from team.chase_navigation import ChaseNavigator
from team.demo_strategy import demo_navigate
from team.strategy import Plan
from team.world import World


class ChaseNavigationTests(unittest.TestCase):
    def world(self, heading=0.):
        return World('StudyBlue', position=(0., 0., .66),
                     quaternion=(math.cos(heading/2), 0., 0., math.sin(heading/2)))

    def test_distant_target_behind_turns_instead_of_backpedalling(self):
        plan = Plan('ALIGN_DRIBBLE', (-5., 0.), 0.)
        self.assertLess(demo_navigate(plan, self.world())[0], 0)
        vx, vy, omega = ChaseNavigator()(plan, self.world())
        self.assertEqual((vx, vy), (0., 0.))
        self.assertEqual(abs(omega), .5)

    def test_forward_travel_uses_full_existing_envelope(self):
        vx, vy, omega = ChaseNavigator()(Plan('ALIGN_DRIBBLE', (5., 0.), 0.), self.world())
        self.assertEqual((vx, vy, omega), (1., 0., 0.))

    def test_distant_side_target_turns_before_translation(self):
        vx, vy, omega = ChaseNavigator()(Plan('ALIGN_DRIBBLE', (0., 5.), 0.), self.world())
        self.assertEqual((vx, vy), (0., 0.))
        self.assertEqual(omega, .5)

    def test_near_ball_backoff_remains_available(self):
        vx, _, _ = ChaseNavigator()(Plan('ALIGN_DRIBBLE', (-.4, 0.), 0.), self.world())
        self.assertLess(vx, 0)

    def test_travel_hysteresis_and_return_to_fine_placement(self):
        nav = ChaseNavigator()
        world = self.world()
        nav(Plan('ALIGN_DRIBBLE', (2., 0.), 0.), world)
        self.assertTrue(nav.travelling)
        nav(Plan('ALIGN_DRIBBLE', (1.2, 0.), 0.), world)
        self.assertTrue(nav.travelling)
        nav(Plan('ALIGN_DRIBBLE', (.8, 0.), 0.), world)
        self.assertFalse(nav.travelling)

    def test_striking_and_goalkeeping_keep_the_measured_controller(self):
        for state in ['SHOOT', 'PASS', 'CLEAR', 'DRIBBLE', 'GOALKEEPER', 'SUPPORT', 'DEFEND']:
            with self.subTest(state=state):
                plan = Plan(state, (-2., .1), .2)
                world = self.world()
                self.assertEqual(ChaseNavigator()(plan, world), demo_navigate(plan, world))

    def test_faster_small_turn_stays_within_policy_limits(self):
        plan = Plan('ALIGN_DRIBBLE', (.4, 0.), math.radians(10))
        world = self.world()
        self.assertGreater(ChaseNavigator()(plan, world)[2], demo_navigate(plan, world)[2])
        self.assertLessEqual(abs(ChaseNavigator()(plan, world)[2]), .5)

    def test_search_uses_the_existing_full_turn_command(self):
        velocity = ChaseNavigator()(Plan('SEARCH_BALL', velocity=(0., 0., .35)), self.world())
        self.assertEqual(velocity, (0., 0., .5))

    def test_experimental_turn_cap_only_applies_away_from_ball(self):
        nav = ChaseNavigator(turn_limit=.75)
        world = self.world()
        world.ball_position = (5., 0., .11)
        plan = Plan('ALIGN_DRIBBLE', (-5., 0.), 0.)
        self.assertEqual(abs(nav(plan, world)[2]), .75)
        world.ball_position = (.5, 0., .11)
        self.assertEqual(abs(nav(plan, world)[2]), .5)

    def test_combined_forward_turn_retains_original_turn_cap(self):
        world = self.world()
        world.ball_position = (5., 0., .11)
        plan = Plan('ALIGN_DRIBBLE', (5., 1.5), 0.)
        vx, vy, omega = ChaseNavigator(turn_limit=.75)(plan, world)
        self.assertGreater(math.hypot(vx, vy), .15)
        self.assertLessEqual(abs(omega), .5)


if __name__ == '__main__':
    unittest.main()
