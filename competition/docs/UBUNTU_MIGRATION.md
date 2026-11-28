# Ubuntu 原生迁移与验收顺序

本清单用于接力 agent。当前导出端是 Windows；以下 Linux 步骤尚未实机执行。建议 Ubuntu 24.04 x86-64、
Python 3.12，但以用户机器实际版本和赛事要求为准。先保存基线，再改算法。

## 1. 解压与核对

在用户目录新建工作目录，将 `RoboCupStudy-Ubuntu-handoff-20261104-v2.tar.gz` 放入其中，核对旁边回执中的
SHA-256，然后在空目录解压：

```bash
sha256sum RoboCupStudy-Ubuntu-handoff-20261104-v2.tar.gz
tar -xzf RoboCupStudy-Ubuntu-handoff-20261104-v2.tar.gz
cd RoboCupStudy
python3 -m tools.verify_handoff
uname -a
cat /etc/os-release
python3 --version
```

校验应显示 `verified: true`。`export_linux_verified: false` 表示导出时尚未验证 Linux，不是校验失败。
若系统 Python 早于 3.11，先安装兼容的 Python 后再运行校验工具；项目安装仍建议用 3.12。

## 2. 安装独立环境

确认 Python 为 3.12 或 3.13，并检查 `python3-venv` 和所需 OpenGL 库。需要时通过 Ubuntu 包管理器安装
`python3-venv`、`python3-pip`、`libgl1`、`libglfw3`；C++ 对手另需 `build-essential`、`cmake`、`libyaml-cpp-dev`。
将实际安装命令和版本输出记录到 `output/linux-validation/`。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip freeze > output-linux-freeze.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -c "from team.motion import Policy; Policy('walk'); Policy('getup'); print('models loaded')"
```

先不要运行会自动修补本地服务器的 `setup_ubuntu.sh`。若固定依赖版本无 Linux wheel、Python 不兼容或
系统库缺失，保存完整错误，明确选择兼容版本的理由和新锁文件；不能沿用旧 Windows 版本标签。

## 3. 测试官方服务器与技能

```bash
.venv/bin/python -m tools.evaluate --scenario walk --seconds 15
.venv/bin/python -m tools.evaluate --scenario recover --seconds 15
.venv/bin/python -m tools.evaluate --scenario shoot --seconds 20
.venv/bin/python -m tools.evaluate --scenario shoot --mirror --seconds 20
.venv/bin/python -m tools.evaluate --scenario kick --seconds 25
.venv/bin/python -m tools.evaluate --scenario kick --mirror --seconds 25
.venv/bin/python -m tools.evaluate --scenario pass --seconds 25
.venv/bin/python -m tools.check_team --two-teams
```

每条命令打印独立输出目录。对每场使用 `python -m tools.verify_report <目录>`，记录所有通过和失败。
默认版左侧远射在 Windows 也曾未满足球速阈值；不要通过放宽阈值或删掉失败把迁移标成通过。

如果官方 0.2.1 服务器复现空音频数组异常，可在保存未修补输出后执行 `tools.patch_rcssmj_021`。
若复现动态重编译控制量异常，另行评估 `tools.patch_recompile_controls`，保存备份及修补前后对照。
它们属于本地工程环境修复，不是已获 2027 主办方认可的服务器修改。

## 4. 运行 Python 对手

交接包已带固定缓存；可直接核对，缺文件时再使用来源下载器：

```bash
.venv/bin/python -m pip install -r requirements-opponents.txt
.venv/bin/python -m tools.verify_sources --kinds jenny freeloap
.venv/bin/python -m tools.benchmark --opponents jenny --half 300 --seeds 71 72 --jobs 1 --require-legal-opening
```

GRU 需要可选 PyTorch CPU 依赖。先安装基础对手依赖，再按官方 CPU 索引安装：

```bash
.venv/bin/python -m pip install -r requirements-gru-opponent.txt --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m tools.verify_sources --kinds retricato gru2
.venv/bin/python -m tools.benchmark --opponents gru2 --half 300 --seeds 73 74 --jobs 1 --startup-timeout 35 --require-legal-opening
```

优先单场并行。Windows 曾因同时启动多场 GRU 比赛出现内存分配失败；准备失败不是平局。
Jenny 与 freeloap 分别使用上游 `custom`、`7v7` 场地选项，保持 55×36 米。旧 Bahia 默认 `fifa` 的
105×68 米内部几何与本场不匹配，不能把它作为强队验收结论。

## 5. 原生编译 Apollo 与 My3D

`tools/build_apollo_opponent.py` 是 Windows 专用构建器，不能在 Ubuntu 执行。使用缓存内原始
`CMakeLists.txt` 和 POSIX TCP 源码，不复制 Windows Winsock 构建副本或 EXE。

从 ONNX Runtime 官方 v1.22.0 发布页获取 Linux x64 C++ 包，记录下载地址及 SHA-256，解压到单独依赖目录。
Python 的 `onnxruntime` wheel 不能直接代替这个 C++ SDK。将其绝对路径填入下面的占位路径后执行：

```bash
ROBOCUP_ORT_ROOT=/absolute/path/to/onnxruntime-linux-x64-1.22.0
cmake -S third_party/apollo -B third_party/apollo/build -DCMAKE_BUILD_TYPE=Release -DONNXRUNTIME_ROOT="$ROBOCUP_ORT_ROOT"
cmake --build third_party/apollo/build -j2
cmake -S third_party/my3d/runtime/apollo -B third_party/my3d/runtime/apollo/build -DCMAKE_BUILD_TYPE=Release -DONNXRUNTIME_ROOT="$ROBOCUP_ORT_ROOT"
cmake --build third_party/my3d/runtime/apollo/build -j2
.venv/bin/python -m tools.verify_sources --kinds apollo my3d
.venv/bin/python -m tools.benchmark --opponents my3d --half 300 --seeds 61 62 --jobs 1 --require-legal-opening
```

检查链接库能被运行时找到；若报 `libonnxruntime.so` 缺失，按上游 CMake 的 RPATH/依赖部署方式修复并记录，
不要替换模型。启动器优先使用运行目录的 `assets`，否则使用对应球队源码内的 `assets`。迁移准备已补正
My3D 的回退目录，并测试不会误载 Apollo 的资源；实际 Linux 动态链接和执行仍需本步骤验证。

Apollo 的旧被动开球阵型有球门区人数违规，严格开场可能拒绝开球；这不应算作我方胜局。

## 6. 恢复候选、对照和提交包

默认队伍保持在当前目录。为每个候选建立独立副本，将 `handoff/candidates/<候选名>/team` 和 `tests`
覆盖到该副本对应目录，保留原版模型和当前迁移工具。可以只复制 `team`、`tools`、`tests`、`third_party`
来建立副本，避免把整个历史证据再次复制进去。先核对 `docs/experiments/*-source.json` 中的改动文件哈希，
再运行单测、固定停滞复现、六项技能和 My3D 左右场完整赛。每次修改代码后使用新输出目录。

最后对齐赛事指定的实时/同步模式、CPU 预算和感知配置。记录客户端响应延迟、超时、倒地、双方触球和
比分；多次比赛按版本保留，不混合默认版与候选的胜率。现有计数和运动记录不能替代新增的实时延迟测量。

球队客户端 Linux 构建入口：

```bash
.venv/bin/python -m pip install pyinstaller
.venv/bin/python -m tools.build_release
```

在新的目录解压生成的 `output/releases/RoboCupStudy-linux.tar.gz`，连接本地服务器验证 `start.sh`、
`kill.sh`、点球入口、模型资源和运行库。核对赛方需要的主机、端口、队名、队员数量及提交格式；
当前 `start.sh` 接收主机参数，客户端默认端口为 60000，若赛方要求端口参数还需要适配。
在全新环境验证成功之前，不把产物标成正式可提交包。

迁移结束后将真实 Linux 结果写入新文档和版本锁文件，保留原有 Windows 记录。导出器支持从解压后的
`handoff/candidates` 恢复候选，也会把历史 Windows 路径映射到当前目录；不会修改原证据文件。
将新验收结果保存在 `output/linux-validation`，并使用新文件名重新导出：

```bash
.venv/bin/python -m tools.package_handoff --output output/releases/RoboCupStudy-Ubuntu-next-handoff.tar.gz
```

导出器不会自行认定 Linux 已验证；实际验收状态由新报告中的命令输出与结果支撑。
