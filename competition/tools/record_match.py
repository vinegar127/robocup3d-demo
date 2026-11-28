"""Record actual MuJoCo joint states without changing agents or stepping physics.

Example: python -m tools.record_match --run-info output/run.json --scenario match
         --opponent jenny --swap-teams --seed 72 --half 300 --require-legal-opening
"""
import argparse
import ctypes
import faulthandler
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

import mujoco
import numpy as np

from tools import evaluate


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--run-info', type=Path, required=True)
    parser.add_argument('--record-fps', type=int, default=10)
    options, remaining = parser.parse_known_args()
    if not 1 <= options.record_fps <= 50:
        parser.error('record-fps must be between 1 and 50')
    if options.run_info.exists():
        parser.error('run-info already exists; use a new filename')
    # Avoid multi-gigabyte apport dumps; Python stack diagnostics remain enabled.
    ctypes.CDLL(None).prctl(4, 0)
    trace = options.run_info.with_suffix('.trace.log').open('w')
    faulthandler.enable(trace, all_threads=True)
    faulthandler.register(signal.SIGUSR1, file=trace, all_threads=True)

    class RecordedEvaluator(evaluate.Evaluator):
        def __init__(self, sim, args, output):
            super().__init__(sim, args, output)
            self.replay = output/'replay'
            self.replay.mkdir()
            self.buffer = []
            self.chunks = []
            self.next_capture = 0.
            self.model_saved = False
            self.record_finished = False
            self.record_nq = None
            self.record_count = 0
            self.record_metadata = {'fps': options.record_fps, 'source':'actual MuJoCo qpos captured after simulation steps',
                                    'model':'model.mjb', 'chunks':self.chunks, 'complete':False}
            options.run_info.parent.mkdir(parents=True, exist_ok=True)
            options.run_info.write_text(json.dumps({'directory':str(output), 'started':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                'recorder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2))

        def flush_replay(self):
            if self.buffer:
                name = f'chunk-{len(self.chunks):04d}.npz'
                np.savez_compressed(self.replay/name,
                    time=np.array([f[0] for f in self.buffer]),
                    qpos=np.stack([f[1] for f in self.buffer]),
                    score=np.array([f[2] for f in self.buffer]),
                    ball=np.stack([f[3] for f in self.buffer]),
                    mode=np.array([f[4] for f in self.buffer]))
                self.chunks.append(name)
                self.buffer.clear()
            self.record_metadata.update(frames=self.record_count, complete=self.done)
            (self.replay/'manifest.json').write_text(json.dumps(self.record_metadata,indent=2))
            (self.output/'telemetry.partial.json').write_text(json.dumps(self.samples))

        def update(self, information, frame_id, recompilation):
            super().update(information, frame_id, recompilation)
            if not self.started or self.record_finished:
                return
            elapsed = self.sim.sim_time-self.start
            if not self.model_saved:
                self.record_nq = self.sim.mj_model.nq
                mujoco.mj_saveModel(self.sim.mj_model, str(self.replay/'model.mjb'))
                self.record_metadata.update(nq=self.record_nq, our_side=self.sim.game_state.get_team_side('StudyBlue').value,
                    opponent=self.args.opponent, seed=self.args.seed, half_seconds=self.args.half)
                self.model_saved = True
            if self.sim.mj_model.nq != self.record_nq:
                raise RuntimeError('Model topology changed during recorded match; refusing an incorrect replay')
            if elapsed+1e-7 >= self.next_capture:
                self.buffer.append((elapsed,self.sim.mj_data.qpos.copy(),self.score,self.sim.ball.xpos.copy(),self.sim.game_state.play_mode.value))
                self.next_capture += 1/options.record_fps
                self.record_count += 1
            if len(self.buffer)>=100 or self.done:
                self.flush_replay()
            if self.done:
                self.record_finished = True

    evaluate.Evaluator = RecordedEvaluator
    sys.argv = [sys.argv[0], *remaining]
    try:
        evaluate.main()
    finally:
        faulthandler.unregister(signal.SIGUSR1)
        trace.close()


if __name__=='__main__':
    main()
