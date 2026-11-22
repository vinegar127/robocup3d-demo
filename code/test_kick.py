import unittest

from demo_sim import MiniSim, PlayerAgent
from core import BehaviorState, ObjectObs, Percept


def percept(cycle, ball_dist=None, *, x=0.0, play_mode="PlayOn"):
    return Percept(
        time=cycle * 0.02,
        cycle=cycle,
        accel=(0.0, 0.0, -9.81),
        observations=[] if ball_dist is None else [ObjectObs("ball", ball_dist, 0.0)],
        self_pos=(x, 0.0, 0.55),
        play_mode=play_mode,
    )


class KickTests(unittest.TestCase):
    def setUp(self):
        self.agent = PlayerAgent(0)
        self.agent._is_closest = True

    def test_single_low_distance_reading_does_not_start_kick(self):
        self.agent.act(percept(1, 0.79))
        self.agent.act(percept(2, 0.70, x=0.01))
        self.assertEqual(self.agent.state, BehaviorState.APPROACH)
        self.assertEqual(self.agent.stats.kicks, 0)

        self.agent.act(percept(3, 0.69, x=0.02))
        self.assertEqual(self.agent.state, BehaviorState.KICK)
        self.assertEqual(self.agent.stats.kicks, 1)

    def test_two_frames_use_current_robot_position(self):
        self.agent.act(percept(1, 0.78))
        self.agent.act(percept(2, 0.70, x=0.08))
        self.assertEqual(self.agent.state, BehaviorState.KICK)

    def test_missing_or_interrupted_observation_is_not_reused(self):
        for middle in (None, percept(2), percept(2, 1.0, play_mode="KickOff_Left")):
            with self.subTest(middle=middle):
                agent = PlayerAgent(0)
                agent._is_closest = True
                agent.act(percept(1, 1.0))
                if middle is not None:
                    agent.act(middle)
                agent.act(percept(3, 0.70))
                self.assertEqual(agent.state, BehaviorState.KICK)

    def test_multiple_shot_frames_count_as_one_successful_action(self):
        sim = MiniSim(players_per_team=1, seed=7, noise=0.0)
        sim.state.play_mode = "PlayOn"
        robot = sim.robots[0]
        robot.x = 0.0
        sim.ball.x = 0.35
        sim.run(3)
        self.assertGreater(robot.kicks, 1)
        self.assertEqual(robot.agent.stats.kicks, 1)
        self.assertEqual(robot.successful_kicks, 1)

        sim.ball.x = 2.0
        sim.step()
        sim.ball.x = 0.35
        sim.run(2)
        self.assertEqual(robot.agent.stats.kicks, 2)
        self.assertEqual(robot.successful_kicks, 2)


if __name__ == "__main__":
    unittest.main()
