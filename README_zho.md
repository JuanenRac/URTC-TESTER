<p align="center">
  <img src="/images/URTC_TESTER_BANNER.svg" alt="URTC Tester Logo" width="100%">
</p>

# URTC Tester（Windows / Linux）

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  🇨🇳 <b>简体中文</b> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>


<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Protocol-CAN-yellow.svg" alt="CAN">
</p>


**版本：** 0.4.1 · **作者：** JuanenRac（Electro Hobby 3D）&lt;electrohobby3d@gmail.com&gt;

许可证：源代码为 **GPL-3.0-or-later**，本文档为 **CC BY-SA 4.0**——见本仓库中的
`LICENSE`，或本文档末尾的“许可证与版权声明”一节。

一款面向 URTC 板卡的实时 CAN 总线测试器。它通过与刷写工具相同的 USB-CAN
适配器连接，询问板卡当前跳接为其 25 种工具配置文件中的哪一种，并仅显示
该工具自身的控件和遥测——而非试图用一个窗口同时表示全部 25 种。它所做的
一切都是针对当前正在运行的应用程序的运行时指令或遥测读取；它从不触碰
闪存，因此这里没有任何东西会让板卡的可用性比开始时更差。

**诚实核查 - 今天真正能运行的部分：** 为迁移到 Qt Quick 的控制系列所提供的 CAN 负载编码器（`advanced_protocol.py`）是真实的，并由 `tests/` 中的测试覆盖（`python -m pytest -q`）。这个仓库自己的 CI（`.github/workflows/ci.yml`）也会运行它们，同时运行 `ruff check`、`tools/ci_validate.py`、对每个 `.py` 文件的语法编译以及四个 `verify_qt_*.py` 脚本，所以那里的回归会导致构建失败。仓库根目录下的四个 `verify_qt_*.py` 脚本（`verify_qt_custom_frame.py`、`verify_qt_telemetry_watch.py`、`verify_qt_utility_panels.py`, `verify_qt_selftest.py`）是真实的、刻意放在 `tests/` 之外的端到端检查，针对一个带有真实跨线程信号传递的模拟传输层——运行 `QT_QPA_PLATFORM=offscreen python verify_qt_*.py` 时四者都能通过，CI 也会运行它们。这就是自动验证所能达到的诚实上限：传输层、CAN ID/字节布局处理，以及 Qt Quick 桥接逻辑都是真实的，并且针对模拟帧进行了验证，而不是真实硬件——正如下文"Known limitations"已经指出的，这套工具是在没有 USB 访问权限的环境下构建的，所以这里的任何东西都还没有针对真实板卡验证过。`qt_tester.py` 和 `assets/qml/TesterDeck.qml` 是真实而庞大的实现（合计数千行代码），由使用模拟板卡的测试和验证脚本检验，从未在真实板卡上运行过。

> **安全与安防现状:**本生态系统不是经认证的安全系统,目前也不存在已组装的 URTC 电路板。引导程序使用 CRC32 和共享密钥的 HMAC-SHA256 校验固件映像,而非非对称签名(计划中);已发布的应用映像使用公开的开发密钥签名(`signing_key_kind: dev`),因此任何人都可以生成引导程序接受的映像;尚未向任何真实电路板发送过任何内容。在依赖此处任何说法来保障人身安全之前,请先阅读[安全基线](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md)和[威胁模型](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md)。

## 📋 速览

| | |
|---|---|
| 版本 | `0.4.1` |
| 成熟度 | 可用 |
| 技术栈 | Python / PySide6 / Qt Quick / live CAN bus diagnostics |
| 目标 | 使用者的电脑 |
| 真实硬件 | 仅模拟：使用模拟器、替身或仿真测试；此版本没有在真实硬件上运行的记录 |

## 1. 🆚 与刷写工具的关系

本工具与 [URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER) 共享
同一个传输层（SLCAN 和 SocketCAN 类是完全相同的），因为两者最终都只需要
让 CAN 帧在同一类适配器上进出，但它们从事的是根本不同的工作：

| | 刷写工具 | 测试器 |
|---|---|---|
| 触碰闪存 | 是（这正是它的全部意义） | 从不 |
| 通信对象 | 主要是引导程序 | 正在运行的应用程序 |
| 目的 | 更新固件 | 测试/验证工具头的实际硬件 |

如果你不确定需要哪一个：如果板卡已经在运行固件，而你想检查某个工具是否
真的能用（加热器加热、电机转动、LED 点亮），你需要的就是这一个。

## 2. 📦 安装与运行

与刷写工具相同的模式：

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

或构建一个独立的二进制文件：Windows 上使用 `build_exe.bat`，Linux 上使用
`./build_exe.sh`。两者都会先清理 `build/`/`dist/`，并将 `assets/`（横幅
和图标）打包进可执行文件中——这些打包脚本所依赖的不递增版本号的验证路径
（`build-test.bat`/`build-test.sh`）见
[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)，打包脚本本身的完整推理
见刷写工具自身的 README，因为它在这里同样适用。

**版本管理：** `TESTER_VERSION`（在 `tester_config.py` 中，显示在标题栏、
关于对话框、会话日志和调试包中）遵循 `MAJOR.MINOR.PATCH`。两个构建脚本
都会通过 `bump_version.py`，在每次真正的构建之前自动递增它，采用十进制
“里程表”方式：PATCH +1，一旦 PATCH 超过 9 就进位到 MINOR（例如
`0.1.9` → `0.2.0`）。从源码运行（`python urtc_tester.py`）绝不会触碰它——
只有一次真正的 `build_exe.bat`/`build_exe.sh` 运行才会。MAJOR 从不自动
递增，只能手动更改。版本历史见 `CHANGELOG.md`。

### 可视化控制台

**Qt Quick** 命令控制台现在是真正的默认界面：
~~~
python urtc_tester.py
~~~
它使用 SLCAN/SocketCAN 传输，并以只监听模式启动，因此在你明确启用主动检查前
不会发送任何内容。25 种工具配置各自的命令在此都有经过确认的真实覆盖
（运动、钻头、AOI、电磁铁、点焊/超声波焊接脉冲、锡膏喷射、飞针、热成像检测、
5 个带看门狗保活的执行器、真空/扫描探头遥测），每一项都经过同样的关卡：
身份匹配、明确启用的主动模式，以及发送前在 QML 中的用户确认。
这些都尚未在真实板卡上检查过 —— 见下方“已知限制”。

该控制台还会显示检测到的工具的**实时读数**（带滚动曲线和 CSV 导出的温度、转速、限位开关；它们只监听，因此在仅监听模式下以及输出正在运行时也能使用），可运行**自检**，当**总线健康检查**（在没有其他操作占用总线时，每 3 秒查询一次当前工具）发现问题时会在标题栏警告，并提供带有 Readme、许可证和 GitHub 页面的 **关于 URTC Tester** 对话框，旁边是 **保存日志...**。

Qt Quick 窗口的标题栏有语言选择器；所选语言会被保存，并在下次启动时生效。它还可以查询并重置烙铁送丝器的位置（开环估计值；重置需要确认）。 身份探测在电路板发送补丁号时（URTC 固件 0.3.5 及更新版本）也会显示固件补丁号；更旧的固件只显示主版本.次版本。

现有的实时 CAN 诊断流程现在使用深海军蓝/青色控制界面：产品标题、高对比度连接卡、清晰的工具标签页、深色会话日志以及可见的进度通道。这只是视觉与可访问性改动，不会改变被动监控或命令路由，其中任何内容也从未在真实板卡上试过。

### 标题栏与工具

- **标题栏** - 连接状态、总线健康警告、语言选择器（选择会被保存，并在下次启动时生效）和版本号。
- **保存日志...** 和 **导出会话（带哈希的日志）** - 以纯文本保存屏幕日志，或保存包含日志、以 SHA-256 标识该日志的清单和系统诊断的 zip（见下文“日志与调试包”）。
- **关于 URTC Tester** - 版本和作者，带有 **自述文件**（有翻译时使用界面语言）、**许可证** 和项目 **URTC GitHub** 页面的按钮。

### 文件结构

本工具按职责被组织为多个模块，纯粹是为了可读性——将它们作为独立文件与
作为一个大文件，在功能上没有任何区别。完整的逐文件分解见本文档末尾附近
的“📂 仓库结构”一节。

**语言**：默认为英语。通过窗口顶部的语言选择器切换——将界面（标签、按钮、对话框和日志消息）切换为 8 种可用语言中的任意一种，立即保存到本工具旁边的 `config.json`，在下次启动时
应用。翻译文件以纯文本形式存放在 `language/` 下（`english.lng`、
`spanish.lng`、`italian.lng`、`french.lng`、`german.lng`、`chinese.lng`、
`japanese.lng`、`portuguese.lng`），采用简单的
`KEY=Value` 键值对，一行一个——以 `#` 开头的行和空行会被忽略，值内部的
字面 `\n` 会变成真正的换行符（用于少数几个多行对话框消息）。如果某个
翻译需要修正，可以直接编辑，也可以将其作为新增另一种语言的起点（添加
`language/<name>.lng`，在 `tester_config.py` 顶部附近的
`AVAILABLE_LANGUAGES` 中添加 `("<name>", "本地语言名称")`，并在
`config.json` 中设置 `"language": "<name>"`）。语言文件中缺失的键会
回退为显示该键自身的名称而不是崩溃，缺失或无法读取的语言文件（编辑
错误、文件名错误）会为整个界面回退到英语——无论哪种情况，工具在问题
被解决之前都能保持可用。

**Linux SLCAN/SocketCAN 设置**（适配器重新刷写、串口权限、`ip link`
启用）与刷写工具的第 1 节完全相同——请参见 [URTC Flasher 自身的
README](https://github.com/JuanenRac/URTC-FLASHER) 第 1 和第 2 节，
此处不再重复。

## 3. ⚙️ 工作原理

窗口布局为三列：左列和中列容纳下方始终可见的部分（第 1-4 节，然后是
第 6 节），右列容纳第 5 节的逐工具面板，这是窗口中唯一真正根据检测结果
而变化的部分。将始终可见的部分拆分到两列，而非全部堆叠在一列中，可以
防止窗口随着这些部分逐渐增多而变得高到无法适配普通屏幕。3D 打印机自身
的工具面板（25 个中最高的一个）更进一步，将其自身的控件内部拆分成
2 个子列，原因相同。本节所概述的模块级架构，详见
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

**连接**（第 1 节，与刷写工具完全相同）：选择串口/SLCAN 或 SocketCAN、
端口/接口，可选地自动检测比特率，然后连接。

**检测在连接时自动发生**（或点击**检测**重新执行）：本工具发送 `0x110`
（查询当前工具）和 `0x7F8`（查询版本），并使用响应来：
- 显示 25 种工具配置文件中哪一种处于活动状态，以及板卡的整体状态
  （任何已声明的错误、CAN 总线故障、仍处于开机画面）。
- 显示报告的 HardwareID 和固件版本，如果与本项目自身的
  `THIS_HARDWARE_ID` 不匹配则标记出来。
- 在右侧为该特定工具——且仅为该工具——构建**工具控制**面板。切换
  跳接的工具并重新检测会拆除旧面板并从零构建新面板。

**全局控制**（第 2 节，无论哪个工具处于活动状态都始终可见）：状态 LED
颜色覆盖、环形 LED 颜色和开/关，以及 OLED 显示模式（`0x100`）——这些
适用于每一个工具，因此它们不会移动到动态面板中。特别是在 AOI 检测
模式下，这里的环形灯开/关会被忽略，转而使用该工具自身的频闪控制（依据
[docs/CANBUS.md](docs/CANBUS.md)）——颜色无论如何仍然适用。

**扩展板**（第 3 节，始终可见）：`CONN_EXPANSION` 自身的通用 SPI 总线
和 DIAG0 线——每一个带驱动器的扩展板变体都共享的原始透传。ADS1115 和
MLX9064x 传感器，以及压接执行器自身的驱动器，并不在这里控制——它们改为
存在于各自工具自身的面板中（飞针探测、热成像检测、压接执行器——见下方
第 4 节），因为这些之中哪一个实际适用取决于跳接的是哪种工具配置文件。

**持久化 F-RAM**（第 4 节，同样始终可见，但刻意与上方的扩展板分开）：
FM24CL64B 共享 OLED 自身的硬件 I2C2 总线——这是一个核心板卡组件，而非
接在 `CONN_EXPANSION` 上的东西。将两者归为一组会暗示它们之间存在一种
并不真实的联系——扩展接口本身没有 F-RAM、没有 EEPROM，上面没有任何
非易失性存储。
- **SPI 透传**：输入以空格分隔的十六进制字节（1 到 7 个，例如
  `01 02 03`），点击发送，即可看到同一次传输期间 MISO 上返回的确切
  内容（`0x180`/`0x181`）——这是一种原始字节传输，不感知 TMC5160
  寄存器，与固件自身的处理方式一致。适用于在一个特定扩展板的寄存器
  协议值得专门构建面板之前，先测试总线本身。
- **DIAG0 电平**：**查询 DIAG0** 读取一个 TMC5160 失速/故障诊断线
  （`0x182`/`0x183`）的当前状态——高电平（未激活）或低电平（已置位）。
  这是一次简单的轮询读取，而非实时/推送的值——再次点击按钮以刷新它。
- **持久化 F-RAM**：**查询状态**读回板卡在断电前最后保存的内容
  （`0x190`/`0x191`）——它当时是什么工具、设定值、当时是否有严重
  错误处于激活状态。**擦除 F-RAM...** 会清除它（`0x192`，先弹出确认
  对话框——此操作无法撤销）。
- **扩展板类型**：**查询**显示 7 种可能的 `CONN_EXPANSION` 配置中当前
  设置的是哪一种（`0x1A1`——见 `EXPANSION.TXT`）。此处为只读——请改从
  `URTC Flasher` 自身的 CAN OTA 部分设置它，因为这是一项一次性的硬件
  配置步骤，而不是应该从一个实时诊断工具中随意更改的内容。
- **MLX9064x 传感器变体**：**查询**显示 3 种 MLX9064x 系列成员（或
  完全没有）中当前配置的是哪一种（`0x1A7`——见 `CANBUS.md`）——仅当
  上方的扩展板类型是 Advanced 变体或 Basic+MLX9064x 时才有意义。此处
  为只读，理由与上方的扩展板类型相同。
- **自由工具配置**：**查询**显示原始的 ID 跳线读数（0-31），以及
  F-RAM 的 `free_tool_selection` 寄存器当前所说的内容（`0x1A3`——见
  `EEPROM.TXT` 第 5 节）——只有当板卡的跳线读数为 0x1F/11111b 时才会
  被实际参考。此处为只读，理由与上方的扩展板类型相同——`URTC Flasher`
  是唯一写入它的工具。
- **外设类型与序列号**：**查询**显示固定的外设类型（始终为
  URTC/0x03），以及当前设置的设备序列号（`0x1A5`——见 `EEPROM.TXT`
  第 6 节），这是一个主机分配的标签，用于在同一 CAN 总线上区分多块
  原本相同的板卡。此处同样为只读——`URTC Flasher` 负责写入序列号，
  本工具只负责读回它。

**自定义 CAN 帧**（第 6 节，同样始终可见）：一个原始 ID + 十六进制字节
输入框，支持一次性和周期性发送——适用于目前尚无自身控件的指令，或用于
测试 `docs/CANBUS.md` 中未（或尚未）记录的内容。除了 ID 范围和 DLC≤8
之外没有其他验证；发送的内容就是原样发送到总线上的内容。同一节还会
打开**原始总线监视器**（见下文）。

**运行自检**（在检测旁边）：针对当前检测到的任意工具，运行一组小型的
安全、静止状态通信检查——确认当前工具查询和版本查询都能响应，然后
（对于有遥测的工具）发送一个安全的设定值/速度/功率 0，并检查预期的
遥测是否到达。刻意从不发送任何会真正加热、点火或以有意义功率旋转的
内容——这验证的是通信往返是否正常，而非某个执行器是否物理响应，因为
确认那一点终究需要一个人在旁观察。发送任何内容之前会要求确认。没有
遥测的工具（纯运动）或纯粹事件驱动的工具（扫描探针）会得到一条仅供
参考的信息，而非真正的通过/失败结果。**覆盖范围是部分的**：25 种工具
中只有 7 种定义了自检步骤（电烙铁、钻头、激光器、3D 打印机、AOI、真空、
扫描探针）——按下此按钮时，其他 18 种工具不会运行任何检查。

**实时温度图表**：电烙铁和 3D 打印机喷嘴面板都在其实时温度读数旁边
显示一个小型的滚动折线图——一个普通的 Qt Quick Canvas，而非新的
依赖（matplotlib/pyqtgraph 会打破本工具除 pyserial 之外的零依赖策略）。
固定的 Y 轴范围（0 到该工具自身的设定值上限），而非自动缩放，因此趋势
一眼就能看清，而不是坐标轴在其下方不断变化。

**原始总线监视器**（从自定义 CAN 帧一节打开）：一个独立的窗口，显示
看到的每一帧，任意 ID，独立于当前工具面板——一个实时滚动的表格
（时间/ID/DLC/数据/Δt）、暂停/清除，以及一个近似的总线负载/帧率读数
（每秒更新一次；该负载数值未对位填充开销建模，因此请将其视为一个粗略
的诊断数值，而非经过认证的测量值）。**导出 .trc...**/**导出 .asc...**
分别将当前显示的表格保存为一个简化的 PEAK PCAN-View / Vector CANalyzer
风格的追踪文件——足够接近，可以被大多数期望这些格式的工具读取，但不
保证与真实应用程序生成的内容逐字节相同。如果本脚本旁边存在
`urtc_custom_ids.json`（可选，默认不包含——`{"0x199": "My Sensor"}`），
ID 列会在原始十六进制 ID 旁边显示该友好名称——对于任何在不需要修改本
工具源码的情况下测试自定义扩展板自身流量的人来说都很有用。

## 4. 🧰 工具覆盖范围

25 种配置文件的每一种都有自己的面板，直接基于 `docs/CANBUS.md` 构建：

| 工具 | 控件 | 实时遥测 |
|---|---|---|
| 电烙铁 | 设定温度、开/关；送丝器方向 + 步数（一次性）；送丝器位置查询 + 重置为 0 | 实际温度；送丝器位置（开环估计值） |
| 膏体/液体点胶器、螺丝刀、两种夹爪、SMT 拾取放置、大幅面真空夹爪 | 方向 + 步数（一次性移动） | 无（共享 0x120，这 7 种均无遥测） |
| 真空拾取 | 无 | 模拟读数、零件检测 |
| 钻头 | 速度 + 方向 | 实际转速、限位开关 |
| AOI 检测 | 环形模式（关/频闪/常亮） + 频闪周期 | 限位开关 |
| 激光雕刻机 | 功率 + 激光锁定启用/安全（固件输出，并非硬件联锁） | 限位开关 |
| 3D 打印机 | 喷嘴设定值、挤出机方向/步数、层冷却风扇功率、热端风扇功率 | 热端温度、层冷却风扇转速、热端风扇转速 |
| 扫描探针 | 无 | 撞击事件计数 + 时间戳（最高优先级 `0x095`） |
| 电磁铁 | 激励/释放复选框 | 无 |
| 点焊头 | 脉冲持续时间 + 触发 | 无（只有当接触传感器先读取为高电平才会触发——见 `docs/CANBUS.md` 自身的 `0x1C0`） |
| 三防涂层、压装插入器 | 无——仅信息面板 | 无——这两个工具 ID 完全没有 CAN 处理程序，其自身的执行器和传感器位于机器人自身的主板上，见 `docs/TOOLS.TXT` |
| 飞针探测 | 基础读数是自动的；高级读数需要一个原始 ADS1115 配置字（十六进制）+ 触发转换 + 读取结果 | 基础板载 ADC 读数（自动，`0x243`） |
| UV 固化 | 功率滑块（0-255）+ 发送/关闭 | 无 |
| 热风返修 | 设定温度、鼓风机功率、开/关 | 实时温度（共享电烙铁自身的 `0x135` 遥测和实时图表——同一物理热控回路） |
| 压接执行器 | 方向 + 步数（一次性移动，与上方共享的运动类工具形状相同，但通过 `0x1F0` 到达扩展板自身的驱动器，而非板载的 `0x120`） | 无 |
| 热成像检测 | 触发采集、检查状态、读取热成像 | 32x24 像素热力图画布（蓝到红渐变），按需通过 CAN 逐块拉取——并非实时视频流，见下方第 6 节 |
| 焊膏喷射 | PWM 通道 + 频率（配置），然后是占空比 + 持续时间（触发脉冲） | 无 |
| 超声波焊接机 | 脉冲持续时间 + 触发 | 无（与点焊头形状相同，但没有接触传感器门控） |

**通信看门狗已为你处理妥当。** 电烙铁、热风返修（与电烙铁共享同一热控
回路和看门狗）、激光器和 3D 打印机喷嘴各自在固件中拥有一个 250ms 看
门狗；层冷却风扇则是 1000ms 的。勾选相应的“活动”复选框不只是发送一次
指令——只要该复选框保持勾选，它就会自动重发（250ms 看门狗工具为
150ms，层冷却风扇为 400ms），与真实主控制器必须做的方式相同。取消勾选
会发送一次零值/关闭帧然后停止。热端风扇没有看门狗（改为失速检测器——
见 `docs/CANBUS.md`），因此是一次纯粹的一次性发送。

**便利说明（软件层面的便利功能，并非安全功能）。**

- **停止所有输出**（两个窗口都有，在已连接且已启用主动检查时可用）无论装的是什么工具，都会发送所有已知的关闭命令——加热器、激光、钻头、UV 灯、层风扇、电磁铁释放、普通步进电机和压接机——并停止所有刷新。热端风扇会特意保持运转，因为喷嘴可能仍然很烫。 这是通过 CAN 总线发送的软件命令，并非紧急停止：如果总线、适配器、PC 或板卡出现故障，它将无法起作用。
- 单次焊接脉冲、锡膏脉冲和压接在经典窗口中也会要求确认，就像 Qt Quick 面板一直所做的那样。
- 钻头和 UV 灯与激光和加热器一样会被刷新。保持 3D 打印机加热器期间，其每 150 ms 的刷新带有 0 个挤出机步数，固件会将其视为停止命令：在该状态下启动的挤出机移动会在 150 ms 内被取消，因此在固件提供不干扰挤出机的模式之前，请在关闭加热器的情况下移动挤出机。
- 端口和波特率会为下次会话记住（`config.json`），Qt Quick 面板有自己的波特率选择器。**自动检测**首先只在每个波特率下监听（在运行中的总线上不发送任何内容），只有当总线完全静默时才在每个波特率下发起询问。
- 原始总线监视器可以限制为某些 CAN ID（**ID 过滤**）以及数据发生变化的帧（**仅显示变化**）。

### 🔥 热失控台架测试（URTC 固件 0.3.2+ / 0.3.3+）

Detect 现在会显示板卡锁定错误的*原因*：`0x111` 的第 4 字节（热失控保护：
MAXTEMP、HEATING_NO_RISE 或 DROPPED_AT_TARGET）显示在板卡状态中，由硬件看门狗
引起的复位（`0x111` 的第 5 字节）会记录到日志。**热计数**（两种界面的 F-RAM
面板）读取 `0x1AA`/`0x1AB`：累计热故障次数、加热器总开启小时数和最后一次故障。
旧固件的应答（4 字节的 `0x111`，没有 `0x1AB`）显示为“未报告”，绝不会显示为零。
在真实板卡上验证该保护的分步流程见
[`docs/THERMAL_RUNAWAY_BENCH_TEST.md`](docs/THERMAL_RUNAWAY_BENCH_TEST.md)。

## 5. 📋 日志与调试包

与刷写工具相同：一个带时间戳的会话日志会自动写入 `logs/`（删除是安全
的），**导出调试包**会将当前屏幕上的日志加上基本的系统诊断信息
（操作系统、Python 版本、当前的传输方式/端口/比特率、检测到的工具）
保存为一个 `.zip` 文件，以便交给正在调试某个工具头问题的人。

### 🤖 无窗口模式: 测试计划

`python urtc_tester.py --headless 命令` 以无窗口方式运行测试器，适用于生产线、台架脚本或 CI 任务: `info`（谁在应答: 工具、固件、快速状态）、`selftest`、`run-plan 文件` 和 `validate-plan 文件`。计划是放在 `plans/` 里的简短 JSON 步骤文件（确认工具、无故障、最低固件版本、自检、数值落在范围内的帧、等待、向台架旁的人提问）。命令会写出每一帧的日志，以及一份用 SHA-256 指明该日志的结果记录，与控制台使用的记录相同。计划只发送查询，除非它写明 `"actuation": true` 且操作员加上 `--allow-actuation`；引导程序、更新、配置和擦除帧永远不会发送，固件在不刷新时会丢弃的指令（加热器、钻头、激光）可在计划等待期间重复发送（`keepalive_ms`），凡是下达过指令的计划结束后会再次关闭所有输出。`--transport simulate` 播放模拟的工具头，`--transport replay --port 文件` 播放录制的 `.trc` 或 `.asc` 轨迹，因此无需电路板即可试跑计划。退出状态: 0 通过，1 有检查失败，2 计划或参数有误，3 测试无法进行。输出的文字为英文，与烧录器的命令行一致。详见 [`docs/HEADLESS.md`](docs/HEADLESS.md)。这些内容尚未在真实电路板上运行过。

## 6. ⚠️ 已知限制

本工具的证据契约——什么算作 pass/fail/unknown、为什么缺失证据永远是
unknown 而不是 pass、以及为什么本工具自身不授予任何固件刷写权限——记录
于 [docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md)。

- **尚未针对真实硬件测试。** 这里的每一部分——传输层、CAN ID/字节
  布局处理、看门狗保活时序——都经过了独立检查（模拟帧，在相关处使用
  真实子进程测试时序），但构建本工具的环境没有 USB 访问权限。请以
  刷写工具自身 README 所要求的同样谨慎态度对待首次真实会话。
- **按设计一次只有一个工具面板**，这不是一项待日后移除的当前限制——
  原因见上方的引言。
- **全局 LED 颜色是一种直接覆盖**，而非实时读回——没有遥测能显示
  状态/环形 LED 实际当前显示的是什么，只有最后一次下达的指令。
- **热成像检测自身的热成像是拉取式的，而非实时画面。** 读取一整帧
  意味着通过 CAN 依次请求全部 48 个数据块（最坏情况，即 MLX90640/
  MLX90642 自身的分辨率）——这可能需要几秒钟，而本工具自身的 CAN
  协议中没有流式推送模式可以让它更快。必须先触发一次采集；读取热成像随后最多等待两秒，等传感器报告就绪，如果没有就绪则不读取任何内容，因为固件在此之前不会响应数据块请求。会先询问所安装的传感器（MLX90640/MLX90642 为 48 个数据块，MLX90641 为 12 个），丢失的数据块会让其像素留空，而不会使图像其余部分错位。
- **运行自检仅覆盖 25 种工具中的 7 种**（电烙铁、钻头、激光器、3D
  打印机、AOI、真空、扫描探针）——完整说明见上方“工作原理”。按下该
  按钮时，其他 18 种工具不会得到任何自动检查；验证它们仍然意味着要
  观察实际硬件对其自身面板控件的响应。

## 📂 仓库结构

```
/
├── urtc_tester.py             入口点——启动 Qt Quick 控制台
├── qt_tester.py                Qt Quick 前端——默认的正式指令面板，默认只读
│
├── tester_config.py            配置/语言/协议常量（CAN ID、工具名称、
│                                MOTION_TOOL_IDS、AVAILABLE_LANGUAGES、
│                                EXPANSION_BOARD_TYPES）
├── tester_transports.py        SLCAN 和 SocketCAN 传输类
├── tester_bus_monitor.py       后台 CAN 读取线程（CANBusMonitor）
├── tester_autodetect.py        SLCAN 适配器的比特率搜索
├── tester_selftest.py          自检的步骤与执行（不含窗口代码）
├── tester_plan.py              测试计划: 校验、执行及其后的“全部关闭”
├── tester_cli.py               无窗口的测试器 (--headless): info、selftest、run-plan
├── tester_simulator.py         模拟工具头与已录制轨迹的播放器
├── plans/                      测试计划示例 (JSON)
├── tester_telemetry.py         各工具的实时读数与记录的数据序列
├── tester_trace_export.py      .trc / .asc 帧导出的写入代码
├── urtc_ui/                    共享界面辅助代码（URTC-COMMON 的副本）
├── advanced_protocol.py        为迁移到 Qt Quick 的控制系列提供的纯 CAN
│                                负载编码器——无需硬件的测试
├── verify_qt_custom_frame.py        真实的、放在 tests/ 之外的端到端检查，验证 Qt Quick Custom CAN Frame 面板（需要真实的 Qt 事件循环）
├── verify_qt_telemetry_watch.py     真实的、放在 tests/ 之外的端到端检查，验证 Qt Quick 遥测（Vacuum Pickup / Scan Probe）
├── verify_qt_utility_panels.py      真实的、放在 tests/ 之外的端到端检查，验证 Qt Quick 实用面板（Global Controls / Expansion Board / F-RAM）
├── verify_qt_selftest.py            位于 tests/ 之外的 Qt Quick 自检端到端检查
├── tests/
│   └── test_advanced_protocol.py   针对 advanced_protocol.py 编码器的无硬件测试——CI 会运行它，见上文诚实核查
├── requirements.txt            pyserial>=3.5 + PySide6>=6.8,<7
├── build_exe.bat               独立 Windows 二进制文件构建脚本（PyInstaller）
├── build_exe.sh                同上，适用于 Linux
├── build-test.bat              不递增版本号的构建/编译检查
├── build-test.sh                同上，适用于 Linux
├── bump.py                     显式的版本递增命令（编译从不递增）
├── bump_version.py             里程表式版本递增，由构建脚本运行
├── bump_manifest_version.py    将 urtc.project.json 的版本与原生版本同步（--sync）
├── URTC_Tester.spec            两个构建脚本共用的 PyInstaller 规范文件
├── assets/
│   ├── URTC_APP_ICON.svg       窗口/任务栏图标源文件（独立小型设计）
│   ├── URTC_LOGO_TESTER.svg    横幅源文件（矢量图）
│   ├── HYDRA_UMC_ICON.svg      维护中的动画 HYDRA-UMC 矢量源文件
│   ├── qml/
│   │   └── TesterDeck.qml      默认指令面板的 Qt Quick UI
│   ├── urtc_icon.ico           Windows 图标，由 URTC_APP_ICON.svg 构建
│   └── urtc_icon.png           同上，PNG 形式（Linux）
├── images/
│   ├── URTC_LOGO_TESTER.svg    显示在本 README 顶部的 Logo 横幅
│   └── URTC_TESTER_V1_1.png    本工具主窗口的截图（见下方照片）
├── language/
│   ├── english.lng             默认语言，纯文本 KEY=Value 字符串
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   ├── chinese.lng
│   └── portuguese.lng
├── logs/                       运行时会话日志写入此处（删除是安全的）
├── LICENSE                     完整许可证文本——见下方许可证与版权声明
├── NOTICE                      版权声明和文档许可证
├── README.md                   英文原版
├── README_spa.md               西班牙语翻译
├── README_ita.md               意大利语翻译
├── README_fra.md               法语翻译
├── README_deu.md               德语翻译
├── README_jpn.md               日语翻译
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   ├── INTEGRATION_CONTRACT.md
│   ├── CANBUS.md
│   └── THERMAL_RUNAWAY_BENCH_TEST.md
├── tools/
│   ├── build_test.py                     不递增版本号的编译检查 + Qt Quick 面板源码校验
│   └── ci_validate.py                    CI 使用的 manifest/CHANGELOG/docs 校验
└── README_zho.md               本文件
```

## 📸 照片

<p align="center">
  <img src="images/URTC_TESTER_V1_1.png" alt="URTC Tester window" width="700">
</p>

**故障记录器、可选功能、机架试验台和热像(新增,仅用模拟对象检查):** 面板读取板卡的黑匣子(`0x1A8` / `0x1A9`)并保存为 CSV 和 JSON,该选项开启时,板卡每报告一次错误就自动读取一次;可切换固件的可选功能(`0x1AE` / `0x1AF`,默认关闭,下次上电后生效);提供一个模拟的工具机架,使用 URTC-SMART-RACK 的串行协议、每个工具头的身份(类型和序列号)以及状态页导出;并以伪彩色显示热检测图像(模拟图像会明确标注)。工具名称和类别现在来自 URTC-COMMON 的共享工具配置。这些都没有在真实板卡上使用过。

**加热器 PID（新增，仅用模拟验证）:** 控制台读取固件加热器 PID 的状态（`0x1B9` / `0x1BA`: 当前生效的增益、状态和上一个控制周期的输出），保存增益（0 到 600），并启动或取消继电器式自整定；自整定会在烙铁当前设定温度（100 到 445 C）附近加热烙铁头，并保存找到的增益。保存增益和启动自整定需要通常的确认，取消则不需要。命令行的模拟工具头（`--transport simulate`）也会应答这些帧。须先在可选功能中打开该功能；以上内容都没有在真实电路板上使用过。

## 🔗 相关项目

本项目是同一作者(JuanenRac / Electro Hobby 3D)打造的 HYDRA-UMC 机器人生态系统的一部分。值得了解,因为某个请求实际上可能是关于这些项目之一,而非本仓库本身。

**父项目**
- **[URTC](https://github.com/JuanenRac/URTC)** — 面向实体 Universal Robot Tool Controller 板卡的固件,通过 CAN 总线支持 25 种以上工具配置;本仓库是其自身 CAN 总线工具家族中一个具体工具所属的父项目。

**兄弟项目** —— URTC 自身 CAN 总线工具家族中的其他工具
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — 面向 URTC 板卡的桌面图形烧录工具，支持 CAN-OTA 以及全芯片 SWD/JTAG。
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — 位于 CAN 总线前的网关，只放行列表中的标识符，限制其速率，并要求会话密钥。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — 通过 Web Serial API 实现的浏览器版 URTC-TESTER 替代方案，无需本地安装。

**直接相关**
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 具备真实、稳定退出码契约的车队 CLI，是 HYDRA-UMC-SERVER 自身 API 的真实在线客户端 —— 对所有工具头同时运行车队级审计(`audit` 命令),超越本测试工具所覆盖的单板范围。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — 面向热成像/RGB 检测工具头的固件及真实 Python 视觉伴侣程序 —— 以其自身对工具头的视觉质量保证检查,补充本项目的实时 CAN 总线诊断。
- **[URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)** — 桌面工具，用于检测、安装和更新 URTC 系列的仓库，每次只执行一项明确的操作。

**生态系统中的其他项目**

*核心硬件与平台*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 机器人手臂主板设计——CM5 主机 + 双核 STM32H745,目标是通过 CAN-OTA/SPI-OTA 协调最多 8 条工具臂(固件处于早期阶段,尚无已组装的电路板)。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — 面向 CM5 的可复现 Raspberry Pi OS 产品层——只读代理、经过验证的配置/配置文件、WiFi 首次配网。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — 每个桥接都据此校验自身指令的共享 JSON-Schema 契约与软件作业门限边界(并非经认证的安全功能)。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 面向外部机器连接器的声明式适配器清单注册与校验工具；把 SDK 自身的契约理念扩展到外部机器，而不取代工业网关类项目。

*核心后端与客户端*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — 每个控制客户端真正通信的真实无头后端(REST/WebSocket)。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — 具有实时多机器人 3D 可视化的网页控制面板。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 面向多台服务器的桌面(PySide6)集群指挥中心，打包为独立可执行文件。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 具有生物识别登录和配对 Wear OS 伴侣应用的原生 Android 控制应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — 具有实时 WebSocket 同步的 iOS/iPadOS 控制应用(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 面向机载 7 英寸 DSI 触摸屏的原生触控界面，直接嵌入 CM5 本体。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 将完成的模型推送到 STUDIO 自身目录的桌面版图形化 URDF 创建/编辑工具。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — 桌面 STL 模型编辑器，在 HYDRA-UMC-EDITOR-URDF 编辑的同一模型目录中变换/替换/移除/添加真实部件。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 通过 VDA 5050 MQTT 发布者为 AGV/AMR 车队提供的协调边界(仅针对仿真车队测试)。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 具备 GRBL 状态/控制字节访问能力的高层 CNC 单元协调器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 面向足式/人形机器人的协调边界,带有 Boston Dynamics Spot 指令发送器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 读取 3 路钥匙/外壳/联锁 GPIO 信号的激光单元协调器(仅针对模拟芯片测试;无法使激光器上膛或发射)。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — 面向 OpenPnP 贴片机板级流程的安全高层协调器。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 面向 Moonraker/Klipper 3D 打印机的安全协调边界，具备真实的受控作业指令。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 带有惰性导入 rclpy ROS 2 传输层的协调器(尚未在 ROS 2 环境中运行)。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 面向搭载摄像头的无人机的协调边界,带有 MAVLink 指令发送器(仅针对模拟器测试)。

*视觉 AI 节点(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — 面向 Hailo-8 视觉流水线的集成中枢，具备逐阶段的真实硬件就绪检测。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — 具备 Hailo 架构/校验和安全加载验证的真实编译模型注册表。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 具备真实 HailoRT 集成边界的真实 GStreamer 流水线 + MediaMTX 配置生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 以区域状态为授权条件的 Position-Based Visual Servoing 修正律;尚无摄像头位姿估计。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — 从文件读取物体位置的 v0 区域入侵、校准新鲜度与 E-STOP 请求逻辑;没有检测器为其供数,也尚未连接任何物理 E-STOP。

*认知 AI 节点(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — 面向 Hailo-10 认知流水线(LLM/VLA/语音编排)的集成中枢。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — 面向 Vision-Language-Action 模型的真实动作 token 编解码与轨迹生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 具备受限、需确认的 Watch 中继的真实语音前端(VAD + 意图解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — 基于真实规则的任务分解，以及针对 MCU 错误码的语义化错误恢复。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — 面向本生态系统自身 Markdown 文档的真实纯标准库 TF-IDF 文档检索。
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — 面向生态系统自身的本地、按策略门控的 AI 维护技师——观察、诊断并提出修复建议;两个最高风险等级目前特意尚未实现。

*编排与集群*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 具备真实 gRPC/Protobuf 健康报告契约与任务状态机的集成中枢。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 基于真实 HTTP API 的真实优先级任务队列，支持去重。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — 具备重试/退避与身份不匹配检测的真实基于 gRPC 的车队健康看门狗。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 具备真实障碍物/工作空间碰撞校验的真实基于 RRT 的三维路径规划器。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 经过多单元收敛属性测试的真实 CRDT LWW-Element-Map 状态同步。

*数字孪生与仿真*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 面向数字孪生引擎的集成中枢，具备真实的版本兼容性同步契约。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — 在仿真与真实硬件之间带有软件碰撞联锁的硬件在环路由器(未在真实硬件上测试)。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 面向真实 URDF 子集的真实正向运动学与关节限位校验。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — 具备 YOLO/COCO 标注导出功能的真实程序化 2D 场景生成器。

*数据与分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 具备真实数据摄入/查询 HTTP API 的真实 sqlite3 时序数据存储。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — 具备漂移监测能力的真实 FFT + 统计基线异常检测器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — 基于 DATALAKE 历史数据的真实 OEE/可用率计算，支持可复现的 CSV 导出。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — 面向 DATALAKE 的真实 CAN/WebSocket 数据摄入管道，支持序列去重。

*工业网关*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 中继至工业协议的集成中枢，具备真实的指令白名单/背压控制层。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 经真实二进制协议客户端会话验证的真实 OPC-UA 地址空间。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — 具备可选按客户端认证与主题 ACL 的真实 MQTT 代理。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 具备降级模式输出的真实 MTConnect `/probe` 与 `/current` XML 端点。

*辅助工具与生态系统运维*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 基于 DATALAKE/ANOMALY-DETECTOR 的智能摘要与异常高亮面板，具备诚实的统计回退机制。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 带有触觉提醒模式与配对手机语音中继的 WearOS 伴侣应用(尚未在实体手表上运行)。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 面向板卡安装机架的固件，具备真实的工具 ID 解码与 Smart Idle 预热逻辑。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — 发现、克隆并更新本生态系统中每个仓库的管理类桌面工具。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** —— 构建即刻可烧录、预装生态系统最新版本的 CM5 镜像的 Windows/Linux 桌面工具,具备类似 Raspberry Pi Imager 风格的首次启动 Wi-Fi/用户/SSH 配置。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 维护事件协调器：一个低权限的边缘角色采集经过脱敏的库存/健康快照，一个控制面角色以只读方式渲染它，并请求某个 AI 提供方给出诊断建议——从不应用补丁，也从不部署任何内容。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 可复现的开发主机（Raspberry Pi 5 / CM5），保存整个生态系统的源代码，并在持久队列下运行有界的构建/测试任务；这是专用的开发角色，明确区别于运行中的 CM5。

## 📜 许可证

URTC Tester 版权所有 (c) 2026 JuanenRac（Electro Hobby 3D）。分发本项目
或其衍生作品时必须包含此声明。

本项目由源代码及其自身的文档组成，两者依据不同的许可证提供——各自适合
其实际所涵盖的内容：

1. 源代码（`urtc_tester.py` 及每一个 `tester_*.py` 模块）以及通过
   `build_exe.bat`/`build_exe.sh` 从中构建的任何二进制文件，依据
   **GNU 通用公共许可证 v3.0（GPL-3.0-or-later）** 提供。完整文本见
   https://www.gnu.org/licenses/gpl-3.0.html。

2. 文档（本 README 及其自身的翻译版本——`README_spa.md`、`README_ita.md`、
   `README_fra.md`、`README_deu.md`、`README_jpn.md`、`README_por.md` 以及 `docs/` 中的指南）依据 **知识共享 署名-相同方式共享
   4.0 国际许可协议（CC BY-SA 4.0）** 提供。完整文本见
   https://creativecommons.org/licenses/by-sa/4.0/。

本工具是 [URTC（Universal Robot Tool Controller）](https://github.com/JuanenRac/URTC)
项目的实时 CAN 总线诊断配套工具——本工具所测试对接的板卡固件、硬件设计
和完整协议文档见该项目自身的仓库。URTC 自身的固件为 GPL-3.0-or-later，其硬件
设计为 CERN-OHL-S v2；本工具自身的许可证并不延伸至那个独立的项目，
反之亦然。一个覆盖类似功能范围的基于网页的替代方案也存在，位于
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)。

如果你基于本项目进行开发，请留意这种许可证划分：代码更改应保持
GPL-3.0-or-later，文档衍生品应保持 CC BY-SA——每一项都需附带指向本项目及其
作者的署名。

---

## 📚 文档与社区

- **[CONTRIBUTING.md](CONTRIBUTING.md)** —— 提交 Pull Request 所需的技术栈和编码规范。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** —— 本社区所期望的行为准则。
- **[SECURITY.md](SECURITY.md)** —— 如何报告漏洞，以及本项目真实的安全关注重点。
- **[SUPPORT.md](SUPPORT.md)** —— 在哪里提问和报告缺陷。
- **[LICENSE.md](LICENSE.md)** —— 本项目自身的许可证。

## 👤 作者

**JuanenRac**（Electro Hobby 3D）
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
