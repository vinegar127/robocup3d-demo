# RoboCupStudy 接力说明（2026-11-04）

先在 Ubuntu 建立可信的原生基线，再继续优化球队。当前默认程序、两个候选、源码来源、Windows 比赛证据
和失败记录均已保存。Linux 安装、物理技能验收、原生对手比赛和提交包验收尚未完成。

## 用户目标与协作约束

- 参加 2027 年 5 月的新 MuJoCo 环境 RoboCup 3D 仿真赛事；具体赛名与最终赛规尚未确认。
- 用户希望持续实现、寻找公开对手和实际对赛，默认用中文交流，尽量直接完成已授权的本地工作。
- Windows 工作区原址为 `E:\3d仿真`，Python 原址为 `E:\RoboCup3D\.venv\Scripts\python.exe`。
  Ubuntu 是同一台电脑的双系统，需要重启进入；原 Windows 路径不是 Linux 配置值。
- 不主动新建聊天或启动子 agent。用户可把本包交给 Ubuntu 上另一个 agent 接力。
- 本文件记录技术状态与建议执行顺序；主机权限、安全要求和用户的新指令仍以当前接力会话为准。

## 从哪里开始

1. 在 Ubuntu 的用户目录解压交接包，例如 `~/robocup-work/`。不要在已存在的同名项目上覆盖解压。
2. 进入解压后的 `RoboCupStudy`，运行 `python3 -m tools.verify_handoff` 核对全部文件哈希。
3. 阅读本文件、`UBUNTU_MIGRATION.md`、`OPTIMIZATION_20261103.md`，再阅读 `README.md`。
4. 按迁移清单检查系统、依赖、服务器、运动技能和原生对手。每一步保存实际输出，不把脚本存在当成已验证。
5. 完成 Linux 基线后，分别恢复两个实验候选并复测。默认队伍保持独立，避免混用比赛证据。

交接提示词见 `HANDOFF_PROMPT.txt`，可直接粘贴给接手 agent。新 agent 不会自动获得完整聊天记忆；
关键状态以本包的源码、哈希、报告和日志为准。

## 当前代码及能力

默认队伍在 `team/`，由七个独立 Python 客户端组成，使用 T1 23 关节机器人。TCP 长度分帧、感知解析、
世界模型、角色分配、阵型、绕球、推进、传接球、球门空当选择、摆腿残差动作、起身和合法队内语音均有实现。
模型复用 Apollo 的 GPL 行走与起身 ONNX 权重，没有训练新权重。

主要数据流为 `team/agent.py → world.py / behavior.py → strategy.py → motion.py / strike.py → protocol.py`。
测试裁判在 `tools/evaluate.py`；比赛客户端不导入裁判 API。球场定位依赖服务器 `torso_pos` 和 `torso_quat`，
尚无白线视觉 6D 定位、训练好的扑救模型或完整 RL 训练流程。未来赛规若关闭绝对位姿，需要补定位。

迁移准备时只改了公开 C++ 对手的资源路径选择：`tools/opponents.py:native_assets` 让 Linux
out-of-tree 构建选用对应球队的资源。`team/` 仍与既有默认版的比赛哈希一致。相关回归检查在
`tests/test_portable_paths.py`，这些检查不代表已经执行 Linux 二进制。

## 版本与验证范围

Windows 已使用的工程版本：Python 3.12.6、RCSSServerMJ (`rcsssmj`) 0.2.1、MuJoCo 3.5.0、
NumPy 2.5.4、ONNX Runtime 1.22.0。可选对手使用 SciPy 1.18.1、PyYAML 6.0.3、PyTorch 2.15.0+cpu。
Linux 上这些固定版本的可安装性仍须实测；安装失败时保留错误并建立版本对照，不静默升级后继续沿用旧结果。

当前基线是 `ssim26`、T1、55×36 米、球门宽 3.66 米、七对七、上下半场各 300 秒。2027 最终赛规待核实。
批量 Windows 对赛使用同步模式；图形实时展示是另一种运行方式。正式比赛的同步/实时模式、截止时间和
CPU 配额需要重新对齐，不能以同步模式掩盖的响应超时证明实时部署合格。

Windows 本地服务器有两项修补：空音频数组形状修复、动态重编译时按执行器名保留有限控制量。
脚本为 `tools/patch_rcssmj_021.py` 和 `tools/patch_recompile_controls.py`。不要无记录地把它们自动
套进 Linux 正式基线；先测试官方版本，必要时分别记录未修补与修补结果。已有 `setup_ubuntu.sh` 会自动
运行两项修补，因此首次建立原生对照应按迁移文档手动安装。

## 已完成的 Windows 完整赛

比分统一写作“我方:对手”。以下每场均为 600 秒并通过严格合法开场与客户端检查。

| 我方代码 | 对手 | 我方左侧 | 我方右侧 |
|---|---|---|---|
| 默认版 | My3D，前轮 | 2:1 | 0:0 |
| 默认版 | Retricato GRU，前轮 | 6:0 | 3:0 |
| 默认版 | Jenny | 4:0 | 4:0 |
| 默认版 | 另一 GRU 分支 (`gru2`) | 7:0 | 4:0 |
| 局部脱困候选 | My3D | 2:1 | 3:0 |
| 仅过滤自身观测候选 | My3D | 2:0 | 2:1 |

Jenny 两场对手倒地帧占比分别约 62% 和 44%，不能视作强队实力标尺。另一 GRU 分支第一场倒地占比约 1.4%。
freeloap 只完成 90 秒筛选，0:0，未做完整时长验收。固定提交、全部限制见 `PUBLIC_OPPONENTS.md` 和
`OPTIMIZATION_20261103.md`。这些是公开代码版本的工程对照，不代表击败正式冠军队或全部公开球队。

旧 Apollo/Bahia 结果见 `PUBLIC_BENCHMARK.md`。用户曾指出开场球员在边线；复核发现 Apollo 被动开球
阵型的球门区人数违规，裁判将球员罚出。旧健康检查未覆盖开场合法性，已在 `STARTUP_REVIEW.md` 更正。
两场旧对局存在开场问题，不能继续称它们全部合法。新对局使用 `--require-legal-opening`，准备失败不计胜负。

## 两个候选与失败检查

| 候选 | 完整源码快照 | 补丁 | 状态 |
|---|---|---|---|
| 局部脱困 | `handoff/candidates/progress/team` 与 `tests` | `docs/experiments/progress.patch` | 未合并 |
| 过滤自身视觉标记 | `handoff/candidates/self-filter/team` 与 `tests` | `docs/experiments/self-filter.patch` | 未合并 |

候选完整文件在交接包中，不依赖 Windows 的 `tmp` 目录。补丁分别应用到独立副本后，改动文件哈希与参赛
版本一致。若使用 Git 应用补丁，使用 `git -c core.autocrlf=false apply <补丁路径>` 防止 Windows 全局换行转换。
不要连续把两个补丁套到同一个默认副本上，再把混合代码当成原候选。

`handoff/candidates/legacy-hybrid` 保留更早的快速推进实验，只有历史对照，不是当前默认版；
`unrun-intercept` 是尚未运行的抢球预测草稿。它们用于保留研究进度，不计入本轮八场完整赛。
`tmp/` 内少量研究/汇总脚本也按历史路径保留，其中有 Windows 绝对路径；优先使用当前 `tools/`，
需要重放旧脚本时先核对路径和输出范围。

原地对位问题已有物理复现：服务器视觉可能包含自身身体标记，当前默认避障没有排除自身。旧 My3D 右侧
0:0 中最长原地对位 283.02 秒。固定场景内，默认版 20 秒未触球；局部脱困版 5.06 秒触球、推进 8.14 米；
仅过滤自身观测版 1.82 秒触球、推进 13.62 米，均未摔倒。复现入口 `python -m tools.probe_alignment`。

六项物理技能验收中，每组均有一项失败，不能说已全部通过：

- 默认版：左侧远射进球，但球速未达到验收阈值；其余五项通过。
- 局部脱困候选：左侧远射未进球；其余五项通过。
- 过滤自身观测候选：左侧近门射门未进球；其余五项通过。

失败射门的球在门线附近横向位置约 1.95 米、2.10 米，超出球门半宽 1.83 米。踢球相位、横向出球误差和
近门动作选择是下一轮优化重点；目前没有足够证据把全部波动归因于新改动或 Windows。

## 证据如何读取

`docs/optimization-validation.json` 保存本轮八场完整赛、两个无效启动、短场、技能检查、候选源码哈希和
证据摘要。`docs/new-public-validation.json`、`public-validation.json`、`validation.json` 保留更早记录。
`output/research/public-search-20261103/` 保存原始检索、差异、诊断、射门失败和三组技能检查。

交接包按原工作区相对位置保存报告引用的比赛目录，例如 `output/evaluations/match-*`、
`tmp/candidate-progress/output/evaluations/match-*`。JSON 内原有 `E:\3d仿真\...` 是历史出处，保留原字节以维持
证据哈希；在 Linux 下用解压根目录替换这个前缀，不要要求该盘符真实存在。单场验证直接传本地目录：

```bash
.venv/bin/python -m tools.verify_report output/evaluations/match-nax9j85q --require-legal-opening
```

`HANDOFF_MANIFEST.json` 列出交接包全部文件哈希。本包还包括按固定来源清单核对的本地对手缓存，方便个人
跨系统接力。它与不捆绑未知许可对手源码/权重的公共源码包用途不同；Windows 虚拟环境、MinGW、DLL、
C++ 已编译 EXE、临时训练环境和其余无引用的历史草稿不在本包内，Linux 需原生安装与构建。

## 接手后的完成标准

按 `UBUNTU_MIGRATION.md` 建立 Ubuntu 原生基线，保存系统和依赖清单、服务器修补状态、单测、模型加载、
七人入场、物理技能、原生公开对手比赛、实时响应和 Linux 打包结果。先检查对手资源和运行健康，再解释比分。
若 Ubuntu 结果不同，先核对版本、场地、模式、资源、左右场、超时和倒地情况，再判断算法强弱。

项目仍有明确未完成项：Linux 原生验收、可靠射门、候选合并、2027 规则对齐、独立视觉定位、训练新网络和
扑救。用户没有要求每次为这些常规本地实现再次确认；遇到需要用户进入 Ubuntu 或提供赛事规则的步骤时，
说明缺少什么，继续完成不依赖它的工作。
