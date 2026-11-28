# 公开基线对局与复现

同一份球队代码在新 MuJoCo 环境的四场完整公开基线复赛中取得 3 胜 1 平：对 Apollo 为
1:1、3:0，对 BahiaRT 上游默认配置为 4:0、6:0。全部完成 600 仿真秒，全部健康检查通过。
开发过程中另有胜局和败局，均按版本保留；不同开发版本的结果不合并成同一版本的胜率。

后续开场复核补充：运行健康不等于开场摆位合法，其中两场原版配置开局即触发罚出场。
具体范围见 `STARTUP_REVIEW.md`；本轮新对手与严格开场测试见 `PUBLIC_OPPONENTS.md`。

## 对手版本与比较范围

| 对手 | 固定提交 | 本地适配 |
|---|---|---|
| [ApolloCodebase](https://github.com/XiangruiJiang/ApolloCodebase) | `71018c968969d6e55130b0e1987cd5b4f5c3b4df` | 原始 C++；Windows 仅改两份 TCP 传输文件为 Winsock，未改战术、阵型或模型 |
| [BahiaRT-MujOCo-base](https://gitlab.com/bahiart/BahiaRT-MujOCo-base) | `a77702a97d22b7b66966dd0de2c369fd4d10dbed` | 原始 Python；包装器仅限制 ONNX Runtime 的 CPU 线程数量，负责启动和退出 |

服务器为 RCSSServerMJ 0.2.1、MuJoCo 3.5.0、T1、`ssim26`，场地为 55×36 米，球门宽 3.66 米，
每队 7 人。开发环境为 Windows、Python 3.12.6。正式时长为上下半场各 300 仿真秒。

BahiaRT 这份公开代码仅提供 105×68 米 FIFA 和 14×9 米 Adult 配置；本次使用其上游默认
`fifa`，未替换内部场地几何。它会运动、争球和起身，但其目标位置与当前小场不完全匹配。
因此“胜过 BahiaRT 默认基线”有这个明确范围，不代表胜过其专门适配 7 对 7 的比赛队。
Apollo 与球队使用同一公开行走、起身模型；比较包含战术和控制实现，不能据此声称运动模型优于 Apollo。

旧 SimSpark 环境中的 FCPortugal、magma 等代码不能直接作为本次 MuJoCo 对手。也没有据此比较其正式比赛实力。

## 已完成的开发对局

比分统一写作“我方 : 对手”。所有列出的完整比赛均保留结果，没有按胜负删除记录。

| 版本阶段 | 对手 | 我方初始场边 | 种子 | 比分 | 证据目录 |
|---|---|---|---|---|---|
| 行走推球版本 | Apollo | 左 | 21 | 1:0 | `output/evaluations/match-a8fb9tpa` |
| 增加球门空当选择 | BahiaRT 默认 fifa | 左 | 21 | 3:0 | `output/evaluations/match-fb9isl_9` |
| 精确对位中间版本，尚无死区补偿 | Apollo | 右 | 22 | 0:2 | `output/evaluations/match-2vihw3k1` |
| 隔离实验：快速推进与精确射门分开 | Apollo | 右 | 41 | 3:0 | `tmp/candidate-hybrid/output/evaluations/match-ds7khatd` |

两个更早的缩短赛制对照分别对 Apollo、BahiaRT 踢成 0:0，半场仅 45 秒；目录为
`match-nyjk5z17`、`match-md41nksa`。它们没有被算入完整比赛的胜负。

种子控制 Python 和 NumPy 随机源，但进程启动导致的初始仿真时间不同，结果不是逐位可重复。
报告保存 `initial_sim_time`，每场双方各开一个半场的球，另用左右初始场边复赛检查偏差。

## 固定版本复赛

`tools.benchmark` 先写 `spec.json`，固定球队源码 SHA-256、对手、场边、种子和时长，再开始比赛。
默认四场：Apollo 左/右、BahiaRT 左/右；左侧种子 31，右侧种子 32。报告保留全部胜、平、负和运行失败。
固定系列目录为 `output/benchmarks/public-03kx0rub`，最终以 `completed_result.json` 为准。
原始 `result.json` 保留一次场边分配错误造成的无效尝试，最终报告附上同一预设场边的有效重跑。

| 对手 | 我方左侧，种子 31 | 我方右侧，种子 32 | 合计 | 健康检查 |
|---|---|---|---|---|
| Apollo | 1:1 | 3:0 | 4:1，1 胜 1 平 | 两场通过 |
| BahiaRT 默认 fifa | 4:0 | 6:0 | 10:0，2 胜 | 两场通过 |

对应目录分别为 `match-htcpl_vc`、`match-4zuxeymk`、`match-3m_19fk2`、`match-1kgt53o7`，
均位于 `output/evaluations/`。交付包中的 `docs/public-validation.json` 保留完整服务器报告、
56 份客户端健康摘要、球队源码 SHA-256 和原始证据文件摘要。

该系列的 BahiaRT 右侧首轮启动出现注册竞态，实际上我方先注册成左侧。已终止该无效对局，
保留 `output/evaluations/match-0aysd6lb/INVALIDATED.json`，不把当时比分算入系列。
评测器改为等待服务器确认第一队注册完成，再启动第二队；验收器另核对客户端实际场边。
同一份球队代码按原定种子 32 重跑右侧，最终用 `completed_result.json` 保留原失败尝试和有效重跑结果。

隔离实验保留在 `tmp/candidate-hybrid`，没有替换固定系列的球队代码；尚未运行的
`tmp/candidate-intercept` 也是实验副本，不属于交付版本。

验收要求是每场完成、14 名球员无程序错误、对手持续输出电机命令、场上球员实际移动、双方真实触球。
按对手汇总时，还要求胜场多于负场且总进球多于失球。四场样本只说明这一配置下的结果，不是总体胜率估计。

## 复现命令

球队本身只需 `requirements.txt`。运行 BahiaRT 对照还需：

```bash
python -m pip install -r requirements-opponents.txt
python -m tools.fetch_bahia
```

下载器根据保留的上游清单校验每份文件的 SHA-256，遇到本地修改时停止。
BahiaRT 源码没有明确的再分发许可，因此只在本地作为对手，源码发布包仅附清单和下载器。

本机 Windows 的 Apollo 已编译到 `E:\RoboCup3D\opponents\apollo`。
重建入口为 `python -m tools.build_apollo_opponent`，依赖当前本机的 MinGW、yaml-cpp 0.8.0
和 ONNX Runtime C++ 1.22.0；构建脚本记录完整命令和仅有的两份源文件差异。

在 Ubuntu 上可按上游 CMake 构建 Apollo，需 C++17 编译器、CMake、yaml-cpp 开发包和
ONNX Runtime Linux x64 1.22.0 C++ 包。默认从 `third_party/apollo/build/ApolloCodeBase` 启动；
也可用 `APOLLO_HOME` 指向可执行文件所在目录。这个 Ubuntu 对照流程尚未实机验证。

```bash
python -m tools.verify_sources
python -m tools.evaluate --scenario match --opponent apollo --half 300 --seed 31
python -m tools.evaluate --scenario match --opponent apollo --half 300 --seed 32 --swap-teams
python -m tools.evaluate --scenario match --opponent bahia --half 300 --seed 31
python -m tools.benchmark --half 300 --jobs 2 --seeds 31 32
python -m tools.verify_report output/evaluations/<比赛目录> --require-win
python -m tools.analyze_game output/evaluations/<比赛目录>
```

本次因场边注册错误而补全系列的命令为：

```bash
python -m tools.complete_benchmark output/benchmarks/public-03kx0rub output/evaluations/match-1kgt53o7 --invalid-attempt output/evaluations/match-0aysd6lb
python -m tools.export_evidence output/benchmarks/public-03kx0rub/completed_result.json
```

补全工具拒绝替换已经有效的胜、平、负结果，只允许补全原先失败的案例，并核对原定场边、种子、
时长和球队源码。评测器中已修复注册竞态，后续新系列可直接使用 `tools.benchmark`。

`--require-win` 会在平局或失利时失败；默认验证检查比赛是否有效，不把有效平局当作胜利。

## 每场证据

- `report.json`：服务器记分、双方触球、半场完成情况和初始仿真时间。
- `telemetry.json`：训练端采样的真实球和机器人姿态，用于检查进球、方向、区域和倒地。
- `StudyBlue-*.json`：我方运行、队内通信、起身和摆腿次数。
- `StudyOrange-*.json`：公开客户端的帧数、电机输出、运动距离、倒地比例及异常。
- `*.upstream.log`：原始公开客户端输出。
- `source_manifest.json` 和 `source/team/`：近期测试启动时的代码摘要和源码副本。早期开发对局没有该快照。
- `validated.json`：通过健康及比分检查的报告；`analysis.json`：区域、进球时间及对位停滞统计。

球队仅连接普通 agent 端口。初态设置、开球、半场推进和状态采集由独立训练裁判负责，
这些接口不进入比赛客户端；对手转发器原样转发所有字节。
