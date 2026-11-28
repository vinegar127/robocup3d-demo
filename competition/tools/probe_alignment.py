"""Physical regression fixture for the stationary alignment seen in match-sg9jub99.

Only the trainer sets the initial ball/player poses. Both clients then receive
ordinary perceptions and generate all motor commands themselves. No player is
repositioned after the fixture starts. Run separately in each candidate checkout.
"""
import json
import math
from pathlib import Path
import sys

from tools import evaluate
from rcsssmj.games.soccer.sim.soccer_commands import PlaceBallCommand, PlacePlayerCommand


class AlignmentProbe(evaluate.Evaluator):
    def update(self, information, frame_id, recompilation):
        was_started = self.started
        super().update(information, frame_id, recompilation)
        if self.started and not was_started:
            heading = 3.1214250023290333
            self.command_queue.put(PlacePlayerCommand(7, 'StudyBlue',
                (-1.639, -.434, .673), (math.cos(heading/2), 0., 0., math.sin(heading/2))))
            self.command_queue.put(PlacePlayerCommand(1, 'StudyOrange',
                (-2.4998, -.0518, .673), (1., 0., 0., 0.)))
            self.command_queue.put(PlaceBallCommand((-2.652, -.486, .11), (0., 0., 0.)))
        if self.done and self.report is not None:
            self.report['scenario'] = 'alignment_probe'
            self.report['fixture'] = 'match-sg9jub99 relative geometry; standing opponent'
            (self.output/'report.json').write_text(json.dumps(self.report,indent=2),encoding='utf-8')


def main():
    evaluate.Evaluator = AlignmentProbe
    sys.argv = [sys.argv[0], '--scenario','kick','--mirror','--seconds','20','--wall-limit','300']
    evaluate.main()


if __name__ == '__main__':
    main()
