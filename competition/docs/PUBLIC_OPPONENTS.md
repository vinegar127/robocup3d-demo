# 公开代码对手清单

2026-11-03 续测见 [公开对赛与优化检查](OPTIMIZATION_20261103.md)：新增 Jenny、另一 GRU 分支
与 freeloap 运行入口，保留完整赛、短场、候选算法和未通过的技能验收。下面保留上一轮结果。

本轮继续查找能连接 RCSSServerMJ 0.2.1、使用 T1 机器人参赛的公开实现。原始检索响应、README
和目录保存在 `output/research/public-search-20261102/`。找到仓库不等于找到可比赛的完整球队；
本轮同时核对动作模型、开场摆位、真实触球和运行健康。

## 新增并已接入

| 代码 | 固定提交 | 已核对的特点 | 当前验证 |
|---|---|---|---|
| [My3DProject](https://github.com/o-1717986918/My3DProject) | `e3e0a255f983d009ac90eb8abe6cade8b3fbcb12` | Apollo 派生的完整 C++ 队伍；新增踢球、传球生命周期、重启球与合法防守开球摆位 | 完整比赛左侧 2:1、右侧 0:0，均合法开场且健康通过 |
| [RCSS-Booster-Client，Retricato](https://github.com/Retricato/RCSS-Booster-Client) | `a11805749206b72ab9140ec08b158c1cd4e259cc` | 独立 GRU 行走模型，SEEK/ORBIT/PUSH 控球逻辑，角色判断与头部跟踪 | 完整比赛左侧 6:0、右侧 3:0，均合法开场且健康通过 |

筛选赛目录分别为 `match-vyifs7u8`、`match-g8l1l7l6`。45 秒半场只用于检查能否实际参赛，
没有当成正式时长的胜率。完整系列预先固定为上下半场各 300 秒，左右场边种子 61、62；
目录为 `output/benchmarks/public-svrac4w1`，所有胜、平、负及失败都保留。

My3DProject 两场完整比赛的目录为 `match-hda93g1u`、`match-sg9jub99`。两场均为 600 秒，
左右场边各开一个半场的球，固定版本的队伍代码保持不变。

GRU 客户端两场目录为 `match-zq635f0u`、`match-z71l8qa3`。本轮四场共 3 胜 1 平，
每场双方均真实触球，56 份客户端记录无程序错误。GRU 客户端本来有 11 个初始位置槽位；
本次按当前服务器的七人上限启动原版 1–7 号，角色参数保持上游默认。

| 对手 | 我方左侧，种子 61 | 我方右侧，种子 62 | 合计 | 合法开场与运行健康 |
|---|---|---|---|---|
| My3DProject | 2:1 | 0:0 | 2:1，1 胜 1 平 | 全部通过 |
| Retricato GRU 客户端 | 6:0 | 3:0 | 9:0，2 胜 | 全部通过 |

最终报告为 `output/benchmarks/public-svrac4w1/result.json`，机器可读证据汇总为
`docs/new-public-validation.json`。旧的默认配置对照与本轮严格开场结果分开记录。

My3DProject 的 Windows 构建只在构建副本改两份 TCP 文件以使用 Winsock，战术、模型和动作实现
保持原样。GRU 客户端仅增加单线程 CPU 设置、模型绝对路径、独立日志目录和完整 TCP 分帧；
没有替换感知、改变动作或修改其场地配置。源码及模型逐文件 SHA-256 保存在 `docs/opponents/`。

## 找到但暂不作为有效比赛对手

| 代码 | 核对结论 |
|---|---|
| [Aspen](https://github.com/Aspen071213/Aspen) | 已固定 `ade8367d8abe06974a53373e4c7260ace639658f` 并下载。默认 fifa 开场把非开球队 1 号放进中圈，严格检查拒绝开球；自定义阵型又沿 y 轴布置，与当前场地纵轴不同。目录 `match-2iz1otm8`，不计胜负 |
| [UBC](https://github.com/wywdylm/UBC) | 核心源码和运动模型与已测 Apollo 相同，逐个 Git 对象摘要核对；不重复计为新队伍 |
| [dayvidpham/ApolloCodebase](https://github.com/dayvidpham/ApolloCodebase)、[dtleem/ApolloCodebase](https://github.com/dtleem/ApolloCodebase) | 与已测 Apollo 的 62 份核心源码、头文件和运动模型相同；不重复计为两支新队 |
| [rob450-soccer/passing](https://github.com/rob450-soccer/passing) | Bahia 派生，增加路径规划、网格世界与传球相关修改；已记录源文件差异，尚未进行完整运行验证 |
| [soccer-3d-agent](https://github.com/caoyu777-hub/soccer-3d-agent)、[Jenny207/Robocup](https://github.com/Jenny207/Robocup)、[freeloap/BahiaRT-MujOCo-base](https://github.com/freeloap/BahiaRT-MujOCo-base) | Bahia 派生，决策和场地相关文件有改动；尚未逐个验证坐标和完整比赛，不宣称已击败 |
| [RCSS-Booster-Client，另一版本](https://github.com/prathameshshaileshshinde/RCSS-Booster-Client) | 同类 GRU 客户端，README 描述了入场、等待、追球流程；尚未完成与 Retricato 的核心差异核对，未重复计数 |
| [KingsRams](https://github.com/reyesrico/KingsRams) | README 明确默认站立，步行可用，但尚缺球处理和球队决策；不能把它当成能争球的完整对手 |
| [magmapy](https://github.com/magmaOffenburg/magmapy) | 是代理框架；当前公开版本缺完整运动和球赛行为，没有作为完整球队运行 |
| [NUbots/NUSim](https://github.com/NUbots/NUSim) | K1 独立模拟器，使用 Booster SDK/FastDDS，不是当前 RCSSServerMJ 的普通 agent 客户端，不能直接对赛 |
| [chape-mujoco](https://gitlab.com/itandroids/open-projects/chape-mujoco) | 公开目录主要是自有机器人模型和场景资源，没有据此确认存在可连接本服务器的 T1 球队 |
| [HTWK Gym](https://github.com/NaoHTWK/htwk-gym) | 有 T1/K1 行走、踢球训练和模型导出，适合后续运动研发；它本身没有构成当前服务器中的七人球队 |
| [Booster Soccer Showdown](https://github.com/ArenaX-Labs/booster_soccer_showdown) | 独立 Gym/SAI 足球任务与数据集，环境和接口不同，未作为本服务器对手 |

FCPortugal、magmaRelease 等旧 SimSpark 实现仍作为算法和架构参考；本次没有把协议不兼容的代码
换成静止机器人，再声称战胜原队。

## 复现新对手

普通球队运行不需要 PyTorch。仅测试新的 GRU 对手时安装额外 CPU 依赖：

```bash
python -m pip install -r requirements-opponents.txt
python -m pip install -r requirements-gru-opponent.txt --index-url https://download.pytorch.org/whl/cpu
python -m tools.fetch_public_opponent my3d
python -m tools.fetch_public_opponent retricato
python -m tools.build_apollo_opponent --kind my3d
python -m tools.verify_sources --kinds apollo bahia my3d retricato
python -m tools.benchmark --half 300 --jobs 2 --seeds 61 62 --opponents my3d retricato --require-legal-opening
```

本机 My3DProject 可执行文件位于 `E:\RoboCup3D\opponents\my3d`。Windows 构建依赖已存在的
MinGW、yaml-cpp 0.8.0 和 ONNX Runtime C++ 1.22.0。这套构建入口尚未用于 Ubuntu。
下载器只从固定提交获取清单内文件，并检查哈希，发现本地改动会停止。

My3DProject 保留 GPL 许可。其余新增仓库未见明确的再分发许可，因此源码包只附来源清单和下载器，
不捆绑这些对手源码或权重。已下载的原始文件留在本机 `third_party/`，没有重新许可。

## 开场合法性

用户观察到开场球员留在边线后，已补查出 Apollo 原版被动开球阵型的球门区人数违规。
旧对局的补充说明见 `STARTUP_REVIEW.md`。本轮新对手全部启用 `--require-legal-opening`，
准备失败不计为平局或胜局。展示脚本也默认使用能通过该检查的 My3DProject。
