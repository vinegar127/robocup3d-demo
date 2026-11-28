# T1 多人进攻与转向候选

本目录是独立的 RCSSServerMJ 0.2.1 / MuJoCo / T1 七人球队，保存 2026-11-28
已验证的 `demo-team-press` 候选。它与仓库顶层的零依赖教学 Demo 使用不同
运动层和比赛环境，不能直接比较两者比分。

## 本版行为

- 保留一名主抢球者直接处理球，增加第二落点保护、前插接应及后续支援；两名后卫和门将保留。
- 前插目标受已知越位线约束；信息不足时在对方半场保持在球后。
- 独立转身的指令上限从 0.5 提至 0.75；近球 1.2 m 内、边走边转及带球使用原来较低的转向上限。
- 复用 Apollo 公开行走、起身模型和现有 T1 踢腿动作，没有重新训练权重，也不向球施加教学模型的合成冲量。
- 默认策略仍为 `baseline`，用 `--strategy demo-team-press` 明确选择本候选。

## Ubuntu 准备

推荐 Ubuntu 24.04、Python 3.12。以下命令均从本目录执行：

```sh
cd competition
bash setup_ubuntu.sh
.venv/bin/python -m unittest discover -s tests -v
```

如果已经在本目录，省略 `cd competition`。系统需要 `python3-venv`；图形和
C++ 对手所需系统包见 [Ubuntu 迁移说明](docs/UBUNTU_MIGRATION.md)。依赖
安装到独立 `.venv`，不替换系统 Python。

所需 Apollo 运动模型、对应参考源码、许可证与文件哈希已随代码保留在
`third_party/apollo/`。未包含 Python 环境、编译产物、视频或其他对手缓存。

## 接入已经运行的官方服务器

服务器的 agent 端口默认 60000。启动七个独立球员：

```sh
.venv/bin/python -m team.launch --host 127.0.0.1 --port 60000 \
  --team StudyBlue --strategy demo-team-press
```

`team.launch` 会透传策略选项；Ctrl+C 停止其子进程。球队不使用裁判权限自行开球。

## 本地对 My3D 训练赛

My3D 的固定来源为 `e3e0a255f983d009ac90eb8abe6cade8b3fbcb12`，需先下载并原生编译：

```sh
.venv/bin/python -m tools.fetch_public_opponent my3d
# 依照 docs/UBUNTU_MIGRATION.md 第 5 节安装 ONNX Runtime C++ SDK 并编译 My3D。
bash run_team_press_match_linux.sh --half 60
```

脚本默认蓝方为 My3D、红方为我方，完整时长为上下半场各 300 秒；上面的
`--half 60` 是两分钟短赛。原入口和其他策略继续保留。

## 实测范围

根项目的 41 项回归测试通过；另包含独立转身、转弯与追球物理检查。
单人标定中，0.75 指令上限的左右转身约 38°/秒，所测场景没有倒地。

同一种子、相同规则下，各运行了一场 120 秒的 My3D 短赛：

| 指标 | 旧追球候选 | 本版 |
| --- | ---: | ---: |
| 比分（我方 : My3D） | 0:0 | 0:0 |
| 我方倒地帧占比 | 0 | 0 |
| 球附近有效参与人数，平均 | 1.56 | 2.69 |
| 至少三人参与的采样占比 | 0 | 57.2% |
| 转身样本的角速度 90 分位 | 26.6°/秒 | 36.2°/秒 |

参与人数统计限定为 PlayOn、球位于我方 -8 m 以外、球员在球的 8 m 内且不
落后球超过 5 m。转身分位数是比赛中的描述性采样，不是固定输入标定。
战术和转向改动在这一对短赛中合并测试，不能据此证明抢球成功率或整体
比赛实力提升，也未完成本候选的多种子完整赛评估。

- [多人进攻、转向及短赛摘要](docs/evidence/team-press-20261128.json)
- [此前追球候选摘要](docs/evidence/navigation-20261128.json)
- [第三方来源和许可](THIRD_PARTY_NOTICES.md)

摘要保留原实测记录中的相对文件标识；原始录像、逐帧轨迹与本机输出目录
未提交 Git。需要重测时使用 `tools.record_match`、`tools.render_replay` 和
`tools.probe_navigation`，并为输出指定新文件名。

本子项目采用 GPL-3.0-or-later，见 [LICENSE](LICENSE)。顶层教学 Demo 的
MIT 许可不替代本目录及其公开运动资源的许可证。
