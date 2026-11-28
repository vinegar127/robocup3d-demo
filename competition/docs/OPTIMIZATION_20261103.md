# 2026-11-03 公开对赛与优化检查

本轮新增公开对手运行入口、固定版本清单、物理复现和比赛诊断。默认 `team/` 暂时保留原版；
两个算法候选均保留在隔离目录并导出补丁，没有用局部进球或单场胜局代替技能验收。

## 新增对手与配置

| 对手 | 固定提交 | 配置与验证范围 |
|---|---|---|
| [Jenny207/Robocup](https://github.com/Jenny207/Robocup) | `33a59625df2eca33f26876055a7c514ab0d8a331` | Bahia 派生；上游 `--field custom`，55×36 米、原始 1–7 号阵型、运动模型及决策；两场完整比赛 |
| [RCSS-Booster-Client 的另一分支](https://github.com/prathameshshaileshshinde/RCSS-Booster-Client) | `14a423d96bebf1f6f2a0e7f3c21ef5ae43f53c6c` | 与 Retricato 使用相同行走权重，但客户端有约千行差异，增加边线入场与开球阶段；90 秒筛选与左右场完整系列均完成 |
| [freeloap/BahiaRT-MujOCo-base](https://github.com/freeloap/BahiaRT-MujOCo-base) | `ae7ad3d1aff545e7e85fbe15973cec7b8583e36c` | 上游 `--field 7v7`、55×36 米；90 秒筛选 0:0，合法开场、双方真实触球与客户端接口检查通过；未宣称完整赛胜利 |
| [rob450-soccer/passing](https://github.com/rob450-soccer/passing) | `95a8d7c0fbe43eebbe634733f2f38c916aaab201` | 已下载原始运行文件并核对 Git blob；路径规划和传接球状态机可参考，但默认仅定义 1–3 号入场位，不作为完整七人对手 |

这些是不同的公开实现或分支，不能当成互相独立的冠军队伍。Jenny 两场虽满足原有进程、电机、
触球与开场验收，但对手倒地帧占比分别约 62% 和 44%，其结果只代表这个固定公开版本的基础对照。
GRU 包装器只处理 CPU 线程、模型路径、日志目录和完整 TCP 分帧，没有修改模型、观测或动作策略。

## 已完成的完整赛

比分均按“我方:对手”记；每场上下半场各 300 秒，七对七，启用严格开场检查。

| 我方版本 | 对手 | 我方左侧 | 我方右侧 | 系列位置 |
|---|---|---|---|---|
| 默认球队 | Jenny | 4:0，种子 71 | 4:0，种子 72 | `output/benchmarks/public-0z4phmub` |
| 默认球队 | 新 GRU 分支 | 7:0，种子 73 | 4:0，种子 74 | `output/benchmarks/public-vc175ve3` |
| 原有默认球队 | My3D | 2:1，种子 61 | 0:0，种子 62 | 前轮 `output/benchmarks/public-svrac4w1` |
| 局部脱困候选 | My3D | 2:1，种子 61 | 3:0，种子 62 | `tmp/candidate-progress/output/benchmarks/public-i4howhk4` |
| 仅过滤自身观测候选 | My3D | 2:0，种子 61 | 2:1，种子 62 | `tmp/candidate-self-filter/output/benchmarks/public-qngno566` |

固定对手、场边与种子便于比较；网络客户端的调度和注册时刻仍会产生轨迹变化，不能据此声称
固定种子保证物理逐帧确定性，也不能把两场结果外推为稳定胜率。

本轮新完成八场完整赛：默认队四场、两个候选各两场；八场均通过严格合法开场、双方触球、
客户端与物理状态检查。机器可读汇总见 `docs/optimization-validation.json`，包含两次无效启动和所有技能检查失败，
没有将其计为胜场。旧 My3D 两场仅作为对照，不重复计入本轮场次。

## 优化一：原地对位停滞

前轮 My3D 右侧 0:0 中，7 号最长连续 283.02 秒处于原地对位，球最长近 285 秒没有明显移动。
检查当前服务器的 `simulation.py` 可见，视觉生成会遍历全部球员，并未排除自身可见身体标记；
当前球队也没有在避障前排除自身。因此机器人自己的脚等标记可能成为虚假的队友障碍。

固定几何复现中只有一个我方前锋和一个站立对手。训练器仅设置初始位姿，之后不再搬动机器人，
所有运动由普通客户端感知与电机指令产生：

| 版本 | 首次触球 | 20 秒内最大向前推进 | 我方倒地帧 |
|---|---|---|---|
| 默认版 | 未触球 | 0 米 | 0 |
| 局部脱困候选 | 5.06 秒 | 8.14 米 | 0 |
| 仅过滤自身视觉标记候选 | 1.82 秒 | 13.62 米 | 0 |

局部脱困候选在持续 2 秒无位置/球位进展时，只有球员位于球后、横向误差小于 0.20 米、朝向误差
小于 0.18 弧度，才放弃微调而开始推进。它没有更改裁判、体力、动作增益或运动模型。
两场完整赛最大原地对位等待分别为 1 秒、0 秒，球最长静止区间分别约 19.2 秒、17.8 秒。
固定复现证明该机制能脱困；完整赛结果只是额外证据，不单独用于归因。

复现入口为 `python -m tools.probe_alignment`。该场景单独标识为 `alignment_probe`，没有被记作
正式比赛或射门进球。对照数据在 `output/research/public-search-20261103/alignment-probe-comparison.json`。

## 优化二：射门稳定性

本轮分别对默认版和两个候选版运行六项原有物理技能验收；所有运行和失败均保留：

| 检查 | 默认版 | 局部脱困候选 | 仅过滤自身观测候选 |
|---|---|---|---|
| 行走到点 | 通过 | 通过 | 通过 |
| 左侧近门射门 | 通过 | 通过 | 未进球 |
| 右侧近门射门 | 通过 | 通过 | 通过 |
| 左侧摆腿远射 | 进球，但未满足摆腿/球速验收 | 射偏，未进球 | 通过 |
| 右侧摆腿远射 | 通过 | 通过 | 通过 |
| 传球、释放球权及随后接球 | 通过 | 通过 | 通过 |

两个候选均在 My3D 左右场取得胜局。原版本身也有远射验收失败，不能把全部波动归因于新改动；
新候选同样没有达到全部技能通过的标准。
因此当前优先处理踢球相位、横向出球误差和近门动作选择，暂不把候选切成默认球队。
各组原始结果在研究目录的 `baseline-skills`、`progress-skills`、`self-filter-skills`。

两个候选补丁分别在 `docs/experiments/progress.patch`、`self-filter.patch`；对应测试和运行目录仍在
`tmp/candidate-progress`、`tmp/candidate-self-filter`。局部脱困候选单元测试 20 项通过，过滤自身观测候选 19 项通过。
两个补丁分别应用到独立副本后，改动文件哈希与参赛候选完全一致。Windows 若全局启用 Git 换行转换，
应使用 `git -c core.autocrlf=false apply <补丁路径>` 保留相同字节；该选项仅对本次命令生效。

## 检索边界与运行记录

新增检索原始响应、README、固定提交与目录树存于 `output/research/public-search-20261103/`。
RCSSServerMJ 关键词检索仍返回 28 个仓库，其中许多是服务器或重复分支；另外扩展了 rcsssmj 和
MuJoCo 足球关键词。GitHub API 配额耗尽的请求保留错误，没有声称检查了未获取到的最新提交。

`Linhcry/robocup-t1-control-lab` 有 T1 运控、起身、控球和 PPO 实验，但 README 明确不发布权重；
`66Leslie/booster-mjlab` 同样明确没有发布模型权重。它们可作为训练参考，不能直接装成完整对手。
`CFn-ovo/3D` 是 RL-X 派生训练框架；`Robot-create-it/dancer_boosterdeploy` 主要是 K1 的部署与技能，
不是当前 T1 七人普通客户端。没有把这些仓库替换成静止球员再计胜场。

GRU 首次完整系列 `public-djsizty3` 两场均无效：一场 10 秒准备期内仍未入场，一场本机并发时
MuJoCo 分配内存失败。两场不计胜、平、负；后续系列降低为单场并行，并预先固定 35 秒入场等待，
不修改入场位置或规则。有效短场目录为 `match-9xj6swxd`。

新增完整对赛复现：

```bash
python -m tools.fetch_public_opponent jenny
python -m tools.fetch_public_opponent gru2
python -m tools.fetch_public_opponent freeloap
python -m tools.verify_sources --kinds jenny gru2 freeloap
python -m tools.benchmark --opponents jenny --half 300 --seeds 71 72 --jobs 1 --require-legal-opening
python -m tools.benchmark --opponents gru2 --half 300 --seeds 73 74 --jobs 1 --startup-timeout 35 --require-legal-opening
```

新增公开源码及权重没有加入项目再分发包；源码包只附固定来源清单和下载器。当前仍是 Windows
RCSSServerMJ 0.2.1 / T1 工程验证，没有据此声称赢过所有公开队或完成 2027 年赛规验收。
