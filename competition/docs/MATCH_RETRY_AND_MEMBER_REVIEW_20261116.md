# 第四场重跑、录像与组员评审（2026-11-16）

第四场 Jenny 右场重跑完成：我方 4:0，与 Windows 该场比分相同。7 对 7、两半场各 300 秒、seed=72、同步模式；合法开场、双方触球、14 个客户端、对手电机输出与无程序错误检查均通过，正常退出。
默认 `team/` 的全部源码哈希仍与 Windows 快照一致，没有应用算法候选，也没有合并组员分支。

## 录像

- [全场录像，约 10 分钟](/media/vinegar/新加卷/3d仿真/output/linux-validation/20261116-retry/jenny-right-full.mp4)
- [4 个进球近景精华，84 秒](/media/vinegar/新加卷/3d仿真/output/linux-validation/20261116-retry/jenny-right-highlights.mp4)
- [近景画面预览](/media/vinegar/新加卷/3d仿真/output/linux-validation/20261116-retry/jenny-right-highlights.preview.png)
录像使用本场实际 MuJoCo 模型与每 0.1 秒采集的全部 427 个 qpos 状态重放，没有重新推进或伪造物理动作。完整模型、状态分块和元数据保存在比赛目录 `replay/`。画面比分按我方:对手显示；本场我方是右场红色球衣，Jenny 是左场蓝色球衣。
前三场此前没有保存完整关节状态，不能补做与原比赛逐关节一致的 3D 录像；它们的日志、位置／姿态采样和分析仍完整保留。本次交付的 3D 录像对应重跑的第四场。

## 四场对照

| 场次 | Windows | Linux | 我方倒地帧 | 对手倒地帧 | 摆腿触发数 | 最长原地对位 |
|---|---:|---:|---:|---:|---:|---:|
| My3D 左场 | 2:1 | 4:0 | 0.18% | 0.06% | 27 | 7 秒 |
| My3D 右场 | 0:0 | 3:0 | 0.00% | 0.00% | 33 | 3 秒 |
| Jenny 左场 | 4:0 | 6:0 | 0.15% | 51.17% | 31 | 0 秒 |
| Jenny 右场 | 4:0 | 4:0 | 0.00% | 47.87% | 31 | 0 秒 |

表内四场 Linux 都是完成并通过验收的运行；失败退出和旧停滞不混入比分。前三场与 Windows 分数不同，第四场相同；不能只凭这几个种子判断 Linux 球队更强。摆腿触发数是客户端动作计数，不是服务器判定的射门次数。

![Windows 与 Linux 对比](/media/vinegar/新加卷/3d仿真/output/linux-validation/20261116-retry/windows-linux-comparison.png)

## 第四场观察

- 4 个进球的累计时间：141.78 秒、213.38 秒、367.58 秒、486.38 秒。来自 0.2 秒一次的物理采样，时间有采样量化误差。
- 我方倒地帧为 0.00%，对手为 47.87%。Jenny 经常倒地，因此 4:0 只能代表这个固定公开版本的工程对照。
- 球在我方进攻半场的 PlayOn 采样占比约 86.9%，最长约 32.2 秒没有超过 0.1 米的位移；球的位置分布不作为控球率。
- 本次未复现上次约 94 秒的停滞，未触发 60 秒全线程诊断或 120 秒停止条件。此次单独运行并增加只读记录，与此前并发运行条件不同；没有足够证据把原因确定为并发或认定问题已根治。

![第四场推进与球轨迹](/media/vinegar/新加卷/3d仿真/output/linux-validation/20261116-retry/jenny-right-analysis.png)

## 组员修改：采用建议

四个成员分支的固定提交、逐行差异、原始 CLI 输出、60 个训练种子与 60 个额外种子的指标，以及代码问题详见 [完整组员评审](/media/vinegar/新加卷/3d仿真/output/reviews/20261116-demo/REPORT.md)。

| 组员 | 实际修改 | 建议 |
|---|---|---|
| KuroiLei | walk_speed .55→.45 | 练习可验收；单场退化，额外种子均值差区间跨零，暂不修改默认参数 |
| WangShaoJie | 同样的 .55→.45 | 与 KuroiLei 改动完全重复，无需重复合并 |
| WCu0 | turn_speed 90→75 | 训练 60 场少 4 球，额外 60 场多 5 球，效果很小，暂维持默认 |
| YK521-LY | 球后站位、dt、耗时统计、walk=.90、range=.75 | 额外种子有明确提升，但新增球世界坐标变换缺少 yaw；先修该问题并重新验证，整包暂缓。统计与 dt 可拆开考虑 |

以上属于教学 Demo 分支，不会自动改变本项目的 MuJoCo 比赛球队。只做了本地评审与独立实验，没有 push、发 PR 评论或合并。

![组员复测](/media/vinegar/新加卷/3d仿真/output/reviews/20261116-demo/member-comparison.png)

## 数据与可复现入口

- [比赛对照结构化数据](/media/vinegar/新加卷/3d仿真/output/linux-validation/20261116-retry/match-analysis.json)
- [本次重跑结果、命令与验收](/media/vinegar/新加卷/3d仿真/output/linux-validation/20261116-retry/jenny-right-recorded.json)
- [本场原始物理数据](/media/vinegar/新加卷/3d仿真/output/evaluations/match-fuu5b_kp/telemetry.json)
- [本场完整源码哈希](/media/vinegar/新加卷/3d仿真/output/evaluations/match-fuu5b_kp/source_manifest.json)
- [录制环境依赖锁](/media/vinegar/新加卷/3d仿真/output/linux-validation/20261116-retry/requirements-recording-lock.txt)
- 新增 `tools.record_match`：继承原验收监视器，保存编译模型、关节状态、比分与部分遥测；不输出球队动作、不改规则、不重新步进。
- 新增 `tools.render_replay`：用真实状态作运动学重放与 MP4 编码；比分／时间为叠加显示。
- 全场与精华视频均已通过完整解码检查；分辨率 1280×720、10 fps，时长分别为 600.1 秒与 84.0 秒。文件 SHA-256 与编码元数据见 `video-validation.json`。
