"""球的相对观测必须先按机器人朝向旋转，再用于场上规划。"""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code" / "agent"))
from agent import PlayerAgent
from core import Percept, Situation


class AgentGeometryTests(unittest.TestCase):
    def assertPointAlmostEqual(self, actual, expected):
        self.assertAlmostEqual(actual[0], expected[0])
        self.assertAlmostEqual(actual[1], expected[1])

    def test_forward_ball_at_cardinal_headings(self):
        agent = PlayerAgent(0)
        agent.est_pos = (2.0, -3.0)
        sit = Situation(ball_visible=True, ball_dist=1.0, ball_azimuth=0.0)
        for yaw, expected in [(0, (3, -3)), (90, (2, -2)),
                              (180, (1, -3)), (-90, (2, -4))]:
            with self.subTest(yaw=yaw):
                agent.est_yaw = yaw
                self.assertPointAlmostEqual(agent._ball_world(sit), expected)

    def test_observation_azimuth_is_relative_to_body(self):
        agent = PlayerAgent(0)
        agent.est_pos = (2.0, -3.0)
        agent.est_yaw = 90.0
        sit = Situation(ball_visible=True, ball_dist=2.0, ball_azimuth=-90.0)
        self.assertPointAlmostEqual(agent._ball_world(sit), (4, -3))

    def test_kick_spot_behind_center_ball_for_both_attack_directions(self):
        # 位于球南侧、朝北看：球实际在场地中心。
        sit = Situation(ball_visible=True, ball_dist=1.0, ball_azimuth=0.0)
        for side, expected_x in [(1, -0.45), (-1, 0.45)]:
            with self.subTest(team_side=side):
                agent = PlayerAgent(0, team_side=side)
                agent.est_pos = (0.0, -1.0)
                agent.est_yaw = 90.0
                self.assertPointAlmostEqual(agent._kick_spot(sit), (expected_x, 0))

    def test_shot_direction_uses_same_world_ball_as_kick_spot(self):
        agent = PlayerAgent(0)
        agent.est_yaw = 90.0
        sit = Situation(ball_visible=True, ball_dist=1.0, ball_azimuth=0.0)
        percept = Percept(time=0, cycle=0)
        # 球在 (0, 1)，进攻球门中心 (9, 0)，射门方向应略偏南。
        self.assertAlmostEqual(agent._kick_direction(percept, sit),
                               math.degrees(math.atan2(-1, 9)))

    def test_lost_ball_time_uses_actual_step_duration(self):
        agent = PlayerAgent(0)
        percept = Percept(time=0, cycle=0, play_mode="PlayOn")
        sit = Situation(ball_visible=False)
        agent._decide_state(percept, sit, dt=0.1)
        agent._decide_state(percept, sit, dt=0.05)
        self.assertAlmostEqual(agent.lost_ball_time, 0.15)


if __name__ == "__main__":
    unittest.main()
