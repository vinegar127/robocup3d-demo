import unittest
from tools.opening import inspect_opening


class OpeningTests(unittest.TestCase):
    def test_three_players_in_goalie_area_is_not_a_ready_team(self):
        players=[{'side':1,'number':n,'pos':pos} for n,pos in [(1,(26.6,0,.66)),(6,(23.5,-3,.66)),(7,(23.5,3,.66))]]
        report=inspect_opening(players)
        self.assertFalse(report['legal'])
        self.assertEqual(report['issues'][0]['kind'],'too_many_in_own_goalie_area')

    def test_connected_player_at_sideline_is_not_ready(self):
        report=inspect_opening([{'side':0,'number':4,'pos':(-8,21,.66)}])
        self.assertFalse(report['legal'])
        self.assertEqual(report['issues'][0]['kind'],'outside_field')

    def test_both_sides_can_be_ready_for_left_kickoff(self):
        players=[{'side':0,'number':7,'pos':(-.75,0,.66)}, {'side':1,'number':7,'pos':(6.5,0,.66)}]
        self.assertTrue(inspect_opening(players)['legal'])

    def test_two_cross_half_kickers_are_not_legal(self):
        players=[{'side':0,'number':6,'pos':(.5,0,.66)},{'side':0,'number':7,'pos':(.7,0,.66)}]
        self.assertEqual(inspect_opening(players)['issues'][0]['kind'],'multiple_cross_half_kickers')
