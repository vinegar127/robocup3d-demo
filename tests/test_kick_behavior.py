"""验证站位、踢腿时序和世界中的实际射门方向。"""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from demo_sim import MiniSim
from agent import PlayerAgent
from core import BehaviorState, Command, ObjectObs, Percept, Situation


def percept_at(x, y, yaw, *, side=1, cycle=100, visible=True, play_mode="PlayOn", fallen=False):
    azimuth = (math.degrees(math.atan2(-y, -x)) - yaw + 180) % 360 - 180
    return Percept(time=cycle * 0.02, cycle=cycle, self_pos=(x, y, 0.55),
                   self_yaw=yaw, team_side=side, play_mode=play_mode,
                   accel=(0, 0, 0 if fallen else -9.81),
                   observations=[ObjectObs("ball", math.hypot(x, y), azimuth)] if visible else [])


class KickDecisionTests(unittest.TestCase):
    def test_requires_position_and_heading_for_both_sides(self):
        cases = [(-0.45, 0, 0, 1, BehaviorState.KICK),
                 (0.45, 0, 180, -1, BehaviorState.KICK),
                 (0.45, 0, 180, 1, BehaviorState.ALIGN),  # 面向球，但位于球前方
                 (-0.70, 0, 0, 1, BehaviorState.ALIGN),  # 距离可踢，但站位未到
                 (-0.10, 0, 0, 1, BehaviorState.ALIGN),
                 (-0.45, 0, 45, 1, BehaviorState.ALIGN),
                 (-2.0, 0, 0, 1, BehaviorState.APPROACH)]
        for x, y, yaw, side, expected in cases:
            with self.subTest(position=(x, y), yaw=yaw, side=side):
                agent = PlayerAgent(0, team_side=side)
                agent.act(percept_at(x, y, yaw, side=side))
                self.assertEqual(agent.state, expected)

    def test_one_strike_per_animation_with_different_step_sizes(self):
        for dt in [0.01, 0.02, 0.10, 0.50]:
            with self.subTest(dt=dt):
                agent = PlayerAgent(0)
                agent.walk.plan(0.5, 0.1, 30)
                pulses = []
                for i in range(math.ceil(agent.kick.duration / dt)):
                    cmd = agent.act(percept_at(-0.45, 0, 0, cycle=100+i), dt=dt)
                    pulses.append(cmd.kick_power)
                    self.assertEqual((agent.walk.vx, agent.walk.vy, agent.walk.w), (0, 0, 0))
                self.assertEqual(sum(p > 0 for p in pulses), 1)
                self.assertFalse(agent.kick.active)
                self.assertGreater(agent.kick_cooldown, 0)
                self.assertEqual(agent.stats.kicks, 1)

    def test_animation_finishes_when_ball_leaves_view_or_closest_player_changes(self):
        agent = PlayerAgent(0)
        agent.act(percept_at(-0.45, 0, 0))
        agent._is_closest = False
        powers = [agent.act(percept_at(-0.45, 0, 0, visible=False, cycle=101+i)).kick_power
                  for i in range(22)]
        self.assertEqual(sum(p > 0 for p in powers), 1)
        self.assertFalse(agent.kick.active)

    def test_fall_or_kickoff_cancels_unfinished_kick(self):
        for kwargs in [{"fallen": True}, {"play_mode": "KickOff_Left"},
                       {"play_mode": "GameOver"}]:
            with self.subTest(event=kwargs):
                agent = PlayerAgent(0)
                agent.act(percept_at(-0.45, 0, 0))
                cmd = agent.act(percept_at(-0.45, 0, 0, cycle=101, **kwargs))
                self.assertFalse(agent.kick.active)
                self.assertEqual(cmd.kick_power, 0)


class KickWorldTests(unittest.TestCase):
    def world(self, x=-0.45, y=0, yaw=0):
        sim = MiniSim(players_per_team=1, noise=0, seed=7)
        sim.rng.gauss = lambda mu, sigma: mu
        sim.state.play_mode = "PlayOn"
        robot = sim.robots[0]
        robot.x, robot.y, robot.yaw = x, y, yaw
        robot.agent.walk.stop()
        return sim, robot

    def test_ball_follows_body_heading_instead_of_automatic_goal_aim(self):
        for x, y, yaw, expected in [(0, -0.45, 90, (0, 6.5)),
                                     (0.45, 0, 180, (-6.5, 0))]:
            with self.subTest(yaw=yaw):
                sim, robot = self.world(x, y, yaw)
                sim._apply_command(robot, Command(kick_power=1.0), 0.02)
                self.assertAlmostEqual(sim.ball.vx, expected[0])
                self.assertAlmostEqual(sim.ball.vy, expected[1])
                self.assertEqual(robot.kicks, 1)

    def test_kick_state_alone_does_not_shoot(self):
        sim, robot = self.world()
        robot.agent.state = BehaviorState.KICK
        for _ in range(30):
            sim._apply_command(robot, Command(), 0.02)
        self.assertEqual(robot.kicks, 0)
        self.assertEqual(sim.ball.speed, 0)

    def test_world_rejects_out_of_reach_behind_airborne_and_stopped_play(self):
        for event in ["far", "behind", "airborne", "kickoff", "fallen"]:
            with self.subTest(event=event):
                sim, robot = self.world()
                if event == "far":
                    robot.x = -1.0
                elif event == "behind":
                    robot.yaw = 180
                elif event == "airborne":
                    sim.ball.z = 0.5
                elif event == "kickoff":
                    sim.state.play_mode = "KickOff_Left"
                elif event == "fallen":
                    robot.fallen, robot.fallen_timer = True, 10
                sim._apply_command(robot, Command(kick_power=1.0), 0.02)
                self.assertEqual(robot.kicks, 0)

    def test_reaches_valid_shot_from_front_sides_and_mirrored_half(self):
        for side in [1, -1]:
            for x, y in [(-1.5, 0), (1.0, 0), (0, 1.0), (0, -1.0)]:
                with self.subTest(side=side, position=(x, y)):
                    yaw = math.degrees(math.atan2(-y, -x))
                    sim, robot = self.world(x, y, yaw)
                    robot.side = robot.agent.team_side = side
                    minimum_distance = math.inf
                    for _ in range(1000):
                        sim.step()
                        minimum_distance = min(minimum_distance,
                                               math.hypot(robot.x-sim.ball.x, robot.y-sim.ball.y))
                        if robot.kicks:
                            break
                    self.assertGreater(robot.kicks, 0, "20 秒内未完成有效射门")
                    self.assertGreater(minimum_distance, 0.28, "绕行时穿过了球")
                    self.assertLess(abs(sim._wrap(robot.yaw - (0 if side == 1 else 180))), 8.1)


if __name__ == "__main__":
    unittest.main()
