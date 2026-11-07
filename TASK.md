# 任务 01：阅读、修改 Demo，推送自己的分支

仓库：<https://github.com/vinegar127/robocup3d-demo>

对象：全体组员；Windows、Ubuntu、macOS 均可

预计用时：首次操作约 1～2 小时

完成时间：以队长群通知为准

## 目标和交付

本次只做一件事：**运行并读懂 Demo 的基本流程，实际修改 Demo，在自己的分支 commit、push，再发 PR 给队长查看。**不需要另外编写环境信息小程序，不要求安装 Linux 或 MuJoCo。

交付：个人分支上的 Demo 代码修改，以及一个填写了修改前后结果的 PR 链接。允许使用 AI，但需要能解释代码，并说明自己怎样验证。

这是简化教学仿真，对方球员为占位角色。比分只用于比较教学 Demo，不代表正式比赛实力；本次也不要求比分提高。

## 1. 准备账号和工具

1. 安装 Git 和 Python，推荐 Python 3.12，准备一个代码编辑器。
2. 把自己的 GitHub 用户名发给队长，接受**新仓库**的协作者邀请。旧资料仓库的权限不会自动继承到新仓库。
3. Windows 打开 PowerShell，Ubuntu/macOS 打开终端，进入准备存放项目的目录。

检查工具：

```text
git --version
python --version
```

如果系统使用 `python3` 或 Windows 的 `py -3.12`，后文所有 `python` 都替换为同一个可用命令。本 Demo 只使用标准库，不用 `pip install`，也不用先配置虚拟环境。

## 2. 获取 Demo

第一次获取时运行：

```text
git clone https://github.com/vinegar127/robocup3d-demo.git
cd robocup3d-demo
git remote -v
git status
```

`origin` 应是 `vinegar127/robocup3d-demo.git`，当前分支应是 `main`，工作区干净。

注意：旧的 `robocup3d` 是资料仓库，这次必须克隆新的 `robocup3d-demo`。不需要先 `git init`，不要用下载 ZIP 代替 clone。

如果已经克隆了新 Demo 仓库，在该目录确认工作区干净，再运行：

```text
git switch main
git pull --ff-only origin main
```

如果已有未提交修改，先保存处理；`--ff-only` 失败时找队长，不要强制重置。

## 3. 配置作者，先创建分支

在仓库根目录执行；昵称和邮箱换成自己的：

```text
git config user.name "你的队内昵称"
git config user.email "你的GitHub邮箱或noreply邮箱"
git config core.quotepath false
git switch -c feature/member01-demo
git branch --show-current
git rev-parse HEAD
```

把 `member01` 换成自己的 GitHub 用户名。后文的分支名也必须一起替换。把最后一条输出的起始提交编号记下来，填写到 PR。

先创建分支，再修改代码。`user.name` 和 `user.email` 只设置提交作者，不等于已登录 GitHub。

## 4. 跑原版，阅读代码

以下命令始终在仓库根目录执行：

```text
python code/demo_sim.py --cycles 1500
python code/demo_sim.py --bench 20 --cycles 600
```

保存自己的关键输出：单场比分、射门、行走距离、摔倒次数，以及 20 场基准的汇总。不要复制他人的结果；比较前后时必须使用相同命令和周期数。

按下面顺序读代码，找到对应函数：

| 文件与入口 | 要理解的问题 |
| --- | --- |
| `code/demo_sim.py` → `MiniSim.step` | 一次循环的各个步骤如何连接？ |
| `MiniSim.build_percept` | 球员拿到哪些感知？ |
| `code/agent/agent.py` → `PlayerAgent.act`、`_decide_state` | 球员怎样决定找球、接近、对准和踢球？ |
| `MiniSim._apply_command` | 动作怎样影响这个教学世界？ |
| `code/agent/core.py` → `Percept`、`Command` | 感知和动作分别怎样表示？ |

可选：运行 `python code/demo_sim.py --cycles 400 --render` 看终端动画，或打开 `tools/walkviz/index.html` 看独立步态演示。浏览器滑块不会自动改变 Python 代码。

## 5. 实际修改 Demo

选一个小改动即可，推荐第一次只改一个参数。必须改到运行中实际使用的代码，不能只改注释、自己的名字或 README。

**最容易开始的例子：**打开 `code/agent/agent.py`，找到 `MotionConfig`，将 `walk_speed` 从 `0.55` 改为 `0.45`。解释这个数表示什么，并观察移动和比赛统计如何变化。每人也可以选择不同的值或下面的其他方向。

| 改动方向 | 可以观察什么 |
| --- | --- |
| `MotionConfig.walk_speed` | 移动速度、行走距离、接近球的表现 |
| `MotionConfig.turn_speed` | 转向、对准所需的时间和状态变化 |
| `MotionConfig.kick_range` | 进入踢球状态的时机、射门次数 |
| `MotionConfig.align_tolerance` | 对准要求、状态切换和射门表现 |
| 增加有意义的统计输出 | 例如汇总 `AgentStats.time_in_state`，查看各状态耗时 |

修改后，重新执行第 4 步的两条命令，记录真实结果。结果不变或变差都可以提交，但要解释观察和可能原因。不要改比分、进球判断或对手状态来制造“提升”。

阅读参数注释并找它在哪里被使用。如果由 AI 帮忙修改，至少能说明修改的文件、函数、参数含义和验证命令。

## 6. 检查并提交代码

```text
git branch --show-current
git status --short
git diff
```

当前分支必须是自己的 `feature/自己的ID-demo`。确认变化只涉及本次 Demo 修改，没有无关文件。

如果按示例修改了参数，运行：

```text
git add code/agent/agent.py
git diff --cached
git diff --cached --check
git commit -m "feat: 调整 Demo 行走速度并比较运行结果"
git push -u origin feature/member01-demo
```

如果改了其他文件，`git add` 后填写自己的实际文件路径，提交说明也改成实际内容；不要照抄一个没有发生的改动。`git diff --cached --check` 正常时没有输出。

首次 push 使用自己的 GitHub 账号认证。Windows 如弹出 Git Credential Manager 的浏览器登录，按提示登录；GitHub 不接受普通账户密码作为 Git HTTPS 密码。Ubuntu 如尚未配置认证，找队长协助使用自己的 GitHub CLI 或 SSH 授权。

不要直接 push `main`，不要使用 `--force`，不要上传虚拟环境、日志、密码或 Token。

## 7. 确认已上传并创建 PR

```text
git status --short --branch
git rev-parse HEAD
git ls-remote origin refs/heads/feature/member01-demo
```

本地工作区应干净，最后两条显示的提交哈希应相同；再到 GitHub 分支列表确认自己的代码可见。

打开 <https://github.com/vinegar127/robocup3d-demo/pulls> → **New pull request**：

- 目标仓库：`vinegar127/robocup3d-demo`。
- **base：main**；**compare：feature/自己的ID-demo**。
- 标题：`[任务01] 昵称：本次 Demo 修改`。
- 描述按自动出现的模板填写：改了什么、为什么改、完整运行命令、修改前后输出、自己的理解和 AI 使用情况。
- 在 Files changed 中核对变化，创建 PR，把链接发给队长。不要自己合并。

Push 是上传分支，PR 是把改动交给队长审查。收到修改意见后，继续在原分支修改、commit、push，原 PR 会自动更新。

首次练习中，多人可以独立研究同一参数。队长会分别查看和运行各人的分支，不必把所有互相冲突的参数实验合入 main。

## 验收标准

- [ ] 从新 Demo 仓库获取代码，使用自己的个人分支。
- [ ] 能指出感知、决策和世界更新分别在哪里。
- [ ] 至少一处实际 Demo 代码改动，能解释其作用。
- [ ] 同样的单场与基准命令，在修改前后各运行一次并记录结果。
- [ ] commit 和 push 成功，GitHub 能看到个人分支的修改。
- [ ] PR 目标正确、描述完整，链接已交给队长。

验收看是否完成真实修改、验证和协作，不以比分必须提高为条件。GitHub Actions 也会检查 Windows 与 Ubuntu 下的基本运行情况；通过它不代表完成正式 MuJoCo 比赛验证。

## 常见问题

| 现象 | 处理方法 |
| --- | --- |
| 能 clone，但 push 提示 403 | 确认接受的是新 Demo 仓库的邀请，且 Git 登录的是自己的已授权账号。公开可读不代表可以写入。 |
| `not a git repository` | 进入克隆得到的 `robocup3d-demo`；不要在资料目录或 ZIP 解压目录里执行 Git 命令。 |
| `src refspec ... does not match any` | 核对 `git branch --show-current` 和分支拼写，确认已 commit。 |
| 同名分支已存在 | 用 `git switch feature/自己的ID-demo` 回到原分支，不要反复新建。 |
| push 被拒绝或 pull 无法快进 | 先保存 `git status` 和报错发给队长，不用强制推送或覆盖式重置。 |
| PR 没有可比较内容 | 确认修改已 commit、push，base 为 main，compare 为自己的分支。 |
| 网络超时或域名无法解析 | 检查网络后重试，保留完整报错；不要关闭证书校验。 |

如果误在 main 上编辑但未提交，先创建个人分支，通常会将未提交改动一起带过去；已经在 main 提交过时先找队长。

以后开始新任务：在工作区干净时 `git switch main`、`git pull --ff-only origin main`，再创建一个新分支。不要直接在已合并的旧实验分支上继续堆改动。
