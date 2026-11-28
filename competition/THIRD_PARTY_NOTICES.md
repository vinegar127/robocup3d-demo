# Third-party software and models

The T1 walk and get-up ONNX models and their original reference source are from
[Apollo Codebase](https://github.com/XiangruiJiang/ApolloCodebase), pinned at
`71018c968969d6e55130b0e1987cd5b4f5c3b4df`.

Copyright (c) 2026 The Hong Kong University of Science and Technology (Guangzhou),
Humanoid Computing & Learning Lab. Licensed under GPL-3.0-or-later. The original
license, README, reference source and per-file SHA-256 hashes are retained in
`third_party/apollo`. The policy observation and decoding implementation in
`team/motion.py` is adapted from that source. This project is distributed under
GPL-3.0-or-later; see `LICENSE`.

The model weights were reused, not trained by this project. No claim is made to
reproduce Apollo's full competitive performance or its unpublished training work.

RCSSServerMJ, MuJoCo, ONNX Runtime, NumPy and their dependencies are installed as
separate packages with their own licenses. The source archive does not include a
Python environment. `tools/patch_rcssmj_021.py` backports the upstream empty-audio
array fix. `tools/patch_recompile_controls.py` applies a local workaround for invalid
controls after dynamic model recompilation; it preserves finite controls by
actuator name. Both retain original-file backups and neither changes game rules.

For local opponent benchmarks, the public BahiaRT MuJoCo base is pinned at
`a77702a97d22b7b66966dd0de2c369fd4d10dbed` from
https://gitlab.com/bahiart/BahiaRT-MujOCo-base. No explicit redistribution license
was found in that snapshot; its source and weights are excluded from the release
archive. `docs/opponents/bahia.json` records provenance and file hashes, and
`tools/fetch_bahia.py` fetches that original version for local use.

The native Apollo opponent uses pristine tactics and models. The Windows build
copy changes only `src/server/tcp_lpm_client.cc` and `.h` for Winsock transport;
`tools/build_apollo_opponent.py` records the difference and build command.
ONNX Runtime C++ 1.22.0 and yaml-cpp 0.8.0 build dependencies and their binaries
are not included in the source release. `tools/verify_sources.py` checks source
hashes and records the local opponent executable hash.

Additional local opponents are pinned in `docs/opponents/my3d.json`,
`aspen.json` and `retricato.json`. My3DProject's runtime retains its GPL notices;
the Windows build changes only the same two TCP transport files. Aspen and
Retricato's RCSS-Booster-Client have no explicit redistribution license in the
downloaded snapshots. Their source and weights are excluded from the source
archive; the manifests and hash-checking downloader are included for local use.
The GRU opponent wrapper only sets CPU thread limits, resolves asset/log paths
and performs complete TCP reads/writes. It leaves model weights, neural
observations, motor targets and decision logic unchanged.

The 2026-11-03 extension adds pinned local Jenny207/Robocup, freeloap's Bahia
variant, another RCSS-Booster-Client branch, and a source inspection of
rob450-soccer/passing. Their manifests are `docs/opponents/jenny.json`,
`freeloap.json`, `gru2.json` and `passing.json`. No explicit redistribution
license was identified in these downloaded snapshots. Their runtime source
and weights are excluded from release archives. Jenny's `custom` and
freeloap's `7v7` are upstream field options selected to match the 55 x 36 m
test field; no tactics, formations or model parameters were rewritten.
