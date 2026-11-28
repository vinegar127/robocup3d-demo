"""Evidence must reject a disabled opponent, a false win and a swapped side."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.verify_report import verify


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(__file__).resolve().parents[1]/'tmp/evidence-tests'
        self.parent.mkdir(parents=True,exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=self.parent)
        self.directory = Path(self.temp.name)
        self.report = {'scenario':'match','completed_two_halves':True,'contacts':[[0,7],[1,7]],
                       'opponent':'bahia','our_side':1,'requested_our_side':1,'score':[0,2]}
        self.summaries = []
        for team in ['StudyBlue','StudyOrange']:
            for n in range(1,8):
                row = {'team':team,'number':n,'error':None,'frames':1000,'distance_walked':10,
                       'messages_received':10 if team=='StudyBlue' else 0,'recoveries':0,'side':'right'}
                if team=='StudyOrange':
                    row.update(public_opponent='bahia',public_commit='pinned-test-commit',motor_frames=990,
                               parse_errors=0,fallen_frames=10)
                self.summaries.append(row)
        (self.directory/'telemetry.json').write_text(json.dumps([{'players':[{'pos':[0,0,.66],'quat':[1,0,0,0]}]}]))

    def tearDown(self):
        assert self.directory.resolve().is_relative_to(self.parent.resolve())
        self.temp.cleanup()

    def save(self):
        (self.directory/'report.json').write_text(json.dumps(self.report))
        for row in self.summaries:
            (self.directory/f"{row['team']}-{row['number']}.json").write_text(json.dumps(row))

    def test_side_assignment_race_cannot_invert_a_loss_into_a_win(self):
        for row in self.summaries:
            if row['team']=='StudyBlue':
                row['side']='left'
        self.save()
        with self.assertRaisesRegex(AssertionError,'SIDE_ASSIGNMENT'):
            verify(self.directory,require_win=True)

    def test_healthy_draw_is_valid_but_not_a_win(self):
        self.report['score']=[1,1]
        self.save()
        self.assertFalse(verify(self.directory)['won'])
        with self.assertRaisesRegex(AssertionError,'No score advantage'):
            verify(self.directory,require_win=True)

    def test_opponent_without_motor_output_cannot_be_counted(self):
        next(s for s in self.summaries if s['team']=='StudyOrange')['motor_frames']=0
        self.save()
        with self.assertRaisesRegex(AssertionError,'failed to act'):
            verify(self.directory,require_win=True)


if __name__=='__main__':
    unittest.main()
