"""Backport the upstream empty-audio-array fix to RCSSServerMJ 0.2.1.

Upstream reference:
https://gitlab.com/robocup-sim/rcssservermj/-/blob/master/src/rcsssmj/sim/audio_data.py
The released package initializes origins as (0, 3), but the engine uses (3, N).
"""

import importlib.metadata
from pathlib import Path

import rcsssmj.sim.audio_data


if importlib.metadata.version("rcsssmj") != "0.2.1":
    raise SystemExit("This backport applies only to rcsssmj 0.2.1")

target = Path(rcsssmj.sim.audio_data.__file__)
source = target.read_bytes()
old = b"np.zeros((0, 3), dtype=np.float64)"
new = b"np.zeros((3, 0), dtype=np.float64)"
if old in source and source.count(old) == 1:
    backup = target.with_suffix(".py.original")
    if not backup.exists():
        backup.write_bytes(source)
    target.write_bytes(source.replace(old, new))
    print("Applied upstream empty-audio-array fix:", target)
elif new in source and old not in source:
    print("Upstream fix is already present")
else:
    raise SystemExit("Unexpected source contents; no files changed")
