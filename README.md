# RoboCup 3D 教学 Demo

用于组员练习：**运行 Demo → 阅读代码 → 创建个人分支 → 修改 Demo → 验证 → commit 与 push**。

这是从 [vinegar127/robocup3d](https://github.com/vinegar127/robocup3d) 拆出的独立 Demo 仓库。论文、规则、学习路线和调研资料继续放在原仓库；首次协作任务见 **[TASK.md](TASK.md)**。

## 开始运行

安装 Git 和 Python，推荐 Python 3.12。Windows、Ubuntu、macOS 均可，不需要安装第三方 Python 包、MuJoCo 或显卡工具。

```text
git clone https://github.com/vinegar127/robocup3d-demo.git
cd robocup3d-demo
python code/demo_sim.py --cycles 1500
```

Ubuntu/macOS 如果没有 `python` 命令，使用 `python3`；Windows 也可以统一使用 `py -3.12`。所有命令从仓库根目录运行。

其他运行方式：

```text
python code/demo_sim.py --help
python code/demo_sim.py --cycles 400 --render
python code/demo_sim.py --bench 20 --cycles 600
```

`--render` 显示终端动画；`--bench` 运行多场教学基准。单场与基准使用不同的固定种子，同一类比较要保持命令一致。

也可以用 Chrome / Edge 打开 `tools/walkviz/index.html`，通过滑块观察简化步态。该页面是独立演示，页面参数不会自动写回 Python Demo。

## 代码从哪里读

| 文件 | 内容 |
| --- | --- |
| `code/demo_sim.py` | 教学世界、生成感知、执行动作、循环与统计 |
| `code/agent/agent.py` | `MotionConfig` 参数、球员状态机、找球、接近、对准和踢球 |
| `code/agent/core.py` | `Percept`、`Command`、球场和状态等内部数据结构 |
| `tools/walkviz/walk.py` | Python 步态生成器，Demo 运行时需要保留 |
| `tools/walkviz/index.html` | 独立的浏览器步态演示 |

先看 `MiniSim.step`：它把生成感知、`PlayerAgent.act` 决策和世界更新连接起来。再读 `PlayerAgent._decide_state`，最后选一个参数或行为做小改动。

## 教学范围

Demo 使用简化运动学与概率规则，不模拟完整的关节动力学、碰撞与接触力。对方球员是占位角色，并非公开比赛球队；Demo 比分不能说明正式比赛实力。

本仓库没有连接官方服务器的比赛客户端。迁移到正式 MuJoCo 比赛还需要协议、感知、机器人模型、运动控制和规则适配。

- [学习资料仓库](https://github.com/vinegar127/robocup3d)
- [官方 RCSSServerMJ 文档](https://robocup-sim.gitlab.io/rcssservermj/)

## 协作约定

每人从最新 `main` 创建 `feature/自己的ID-demo`，修改并推送自己的分支；不要直接推送 `main`。首次练习只要求改动能够解释、结果如实记录，不要求比分提高。完整步骤见 [任务书](TASK.md)。

仓库包含 GitHub Actions，在 Ubuntu 24.04 与 Windows 上检查 Python Demo 入口和教学基准。运行检查通过不等同于正式比赛验证。

## 来源和许可

来源为 `vinegar127/robocup3d` 的提交 `2fda39619c3640c5dd56e40284f37706129fe1c8`，保留原 [MIT LICENSE](LICENSE)。本次拆分保留 Demo 默认行为，修正导入路径、缺失文件引用和迁移说明；步态文件缺失时会明确报错。
