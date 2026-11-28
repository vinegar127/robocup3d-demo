# 原资料仓库中的可用代码与蓝色方方案（2026-11-16）

优先选 Apollo / My3D 路线。原资料仓库主要提供教学 Demo、论文和外部实现入口；沿这些入口核对后，My3D 最适合作为当前 T1 七人程序的稳定对手。这里的“更合适”有运行证据支持，但没有证据证明它比我们的默认球队竞技更强。

## 已做的工作

- 阅读原仓库 `vinegar127/robocup3d` 的代码库分析、README 和参考资料索引，并核对上游源码及当前分支。
- Apollo 当前 main 为 `71018c9`，My3D 当前 master 为 `e3e0a25`，与本地固定缓存相同；没有发现这两个公开分支里比现有缓存更新的运动权重。
- 校验本地 Apollo、My3D、Jenny 的固定来源清单，均通过，没有改动原始缓存。
- 新增 `run_public_match_linux.sh`：蓝色／左场为原版 My3D，红色／右场为我方 StudyBlue。保留原有自对赛入口。
- 用新入口完成实时图形短赛：7 对 7、两半场各 30 秒、0:0、合法开场、双方触球、14 个客户端及对手健康检查均通过；蓝方倒地为 **0 / 21,385 个观测帧**。
- 此前 My3D 的两场 600 秒 Linux 完整赛，对手倒地帧占比分别约 0.060% 与 0%。证据分别为 `match-mz7hlwb7`、`match-krca4wbe`。

## 哪些值得用

| 代码 | 适合当前项目的用途 | 关键限制 |
|---|---|---|
| [ApolloCodebase](https://github.com/XiangruiJiang/ApolloCodebase) | T1／RCSSServerMJ 七人底座，行走、起身、角色与队内通信；有公开 ONNX 资源 | 我方已复用其行走与起身模型；整队原版在当前规则下曾有被动开球阵型违规，不能无检查直接作为公平比赛结论 |
| [My3DProject](https://github.com/o-1717986918/My3DProject) | Apollo 派生的 C++ 完整队伍；当前最实用的稳定蓝方，亦可参考导航、角色、传球意图与恢复管理 | 在本机曾以 0:4、0:3 输给我方；稳定不等于比我方更强。默认原生路径只使用已具备的公开运动资源 |
| [FCPCodebase](https://github.com/m-abr/FCPCodebase) | 行为切换、共享运动原语、球后站位、起身看门狗等算法与工程参考 | 主要是 Python，辅以 C++；其 Robot 使用 Nao 与旧服务器关节定义，不能直接把模型或关节动作接入 T1 |
| [NUSim](https://github.com/NUbots/NUSim) | K1 的 MuJoCo／实机一致性工程参考 | 独立 K1 模拟器，使用 Booster SDK／FastDDS，不是当前 RCSSServerMJ 的 T1 普通客户端 |
| magmaRelease、UT Austin Villa | 状态机、定位与技能组织参考 | 本轮没有完成它们到当前服务器和 T1 的适配；不作为现成的蓝方替换包 |

源码依据：

- [Apollo README：T1、七人客户端、行走／起身 ONNX](https://github.com/XiangruiJiang/ApolloCodebase/blob/71018c968969d6e55130b0e1987cd5b4f5c3b4df/README.md)
- [My3D README：Apollo 派生与默认／实验能力边界](https://github.com/o-1717986918/My3DProject/blob/e3e0a255f983d009ac90eb8abe6cade8b3fbcb12/README.md)
- [FCP README：主要 Python 与部分 C++](https://github.com/m-abr/FCPCodebase/blob/22d9e2ff9f12a271ff882868c39cc672e56cc625/README.md)
- [FCP Robot：Nao 模型与关节定义](https://github.com/m-abr/FCPCodebase/blob/22d9e2ff9f12a271ff882868c39cc672e56cc625/world/Robot.py)
- [NUSim README：K1 与 FastDDS](https://github.com/NUbots/NUSim)

原资料中将 FCPCodebase 简单写成 C++ 不够准确；不能仅凭“冠军基础代码”或更新时间推断当前兼容性与实力。本轮选择依据是协议、机器人、实际资源和本地验收。

## 当前最值得借鉴的具体实现

1. **转向与平移解耦**：My3D `runtime/apollo/src/decision/role_behaviors.cc:300` 的 `walk_speed_command`，按目标距离制动；朝向偏差超过 18° 开始降速，达到 32° 时将平移降到零。源码明确说明默认行走在前进方向更可靠，大角度时先转再走，避免强行侧移／后退。
2. **有明确状态的恢复管理**：My3D `runtime/apollo/src/behavior/motion_manager.cc:275` 的 `step_get_up`，跟踪恢复状态、重置策略历史，并处理直立与超时；`getup_runner.cc` 用投影重力检查直立。我方运动层也有连续站立确认，可以作为移植后的补充检查。
3. **从共享、验证过的运动层开始**：Apollo 的 `walk_runner.cc`、`getup_runner.cc`、T1 模型定义与 ONNX 资源需要成套对应，不能只复制某段关节角。
4. **有看门狗和姿态条件的起身**：已只读保存 FCP `behaviors/custom/Get_Up/Get_Up.py`。它用连续陀螺仪观测、等待看门狗、前／后／侧翻状态和直立条件处理恢复。可以借鉴状态管理，Nao 的关键帧与传感器阈值仍须针对 T1 重新验证。

My3D 中快速行走、快速转身和学习踢球相关类并不说明对应研究权重已经公开或可运行。本机缓存里可确认的是 walk／getup 两份 ONNX；实验开关默认关闭，未擅自开启。其 README 也保留了快速行走倒地较多的限制，不能为了名称“强”就开启。

## 蓝色方与 Jenny 的边界

新的入口使用另一支完整对手 My3D；**Jenny 本身尚未修好**，它的原始代码和历史结果完整保留，没有把更换对手记成修复 Jenny 或重新解释此前的 4:0。

Jenny 的三项无对抗 30 秒诊断（零速度、前进、转向）在实际采样范围内均为 0 倒地。说明不能直接认定单独的行走权重完全失效。先前找到的历史动作未重置、部分比赛状态保持旧关节目标等问题仍需结合动态切换和恢复场景做因果验证；本轮没有把这些观察冒称为已修复根因。

录像清晰度优化按用户要求仍暂停，只有先前生成的构图预览，没有继续启动整场重渲染。

## 直接运行

```bash
# 蓝方 My3D，红方我方，完整时长的实时图形赛
bash run_public_match_linux.sh

# 两半场各 30 秒的短赛
bash run_public_match_linux.sh --half 30
```

此入口使用本机已原生构建的 `third_party/my3d/runtime/apollo/build/ApolloCodeBase` 及 My3D 自己的 assets，不修改我方 `team/` 或公开对手源码。许可证和固定来源仍见 `THIRD_PARTY_NOTICES.md` 与各对手 PROVENANCE。

## 证据

- `output/research/strong-code-20261116/findings.json`：当前头提交、本地完整赛与本次短赛证据、源码缓存摘要。
- `output/research/strong-code-20261116/my3d-blue-realtime-short.log`：本次实际命令输出。
- `output/evaluations/match-90j8y1kx/`：物理采样、报告、14 人日志与验证结果。
- 本次没有合并组员分支、改动默认球队策略或向 GitHub 写入内容。

## My3D 蓝方录像补录

已按同一 My3D／我方、场边、seed=62、每半场 30 秒和实时模式补录新的一场短赛。比分 0:0，蓝方倒地 0 帧，合法开场与原验收通过。

- [1080p / 25 fps / 60 秒近景回放](/media/vinegar/新加卷/3d仿真/output/research/strong-code-20261116/my3d-blue-1080p.mp4)
- 这是补录的新一场；未把先前未保存关节状态的那场比赛伪称为原场录像。
- `output/research/strong-code-20261116/my3d-blue-video-validation.json` 保存完整解码、尺寸、时长与文件哈希检查。

## My3D 蓝方完整赛录像

随后已补录两半场各 300 秒的完整比赛，红方 4:1 蓝方；蓝方倒地帧占比约 0.056%。

[10 分钟完整录像，1080p / 25 fps](/media/vinegar/新加卷/3d仿真/output/research/strong-code-20261116/my3d-blue-full-1080p.mp4)。完整解码与比赛验收通过，详见 `output/research/strong-code-20261116/my3d-blue-full.result.json`。
