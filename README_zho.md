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
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Tkinter%20%7C%20Qt%20Quick-38d4e6.svg" alt="Tkinter and Qt Quick">
  <img src="https://img.shields.io/badge/Protocol-CAN-yellow.svg" alt="CAN">
</p>


**版本：** 0.1.1 · **作者：** JuanenRac（Electro Hobby 3D）&lt;electrohobby3d@gmail.com&gt;

许可证：源代码为 **GPL-3.0**，本文档为 **CC BY-SA 4.0**——见本仓库中的
`LICENSE`，或本文档末尾的“许可证与版权声明”一节。

一款面向 URTC 板卡的实时 CAN 总线测试器。它通过与刷写工具相同的 USB-CAN
适配器连接，询问板卡当前跳接为其 25 种工具配置文件中的哪一种，并仅显示
该工具自身的控件和遥测——而非试图用一个窗口同时表示全部 25 种。它所做的
一切都是针对当前正在运行的应用程序的运行时指令或遥测读取；它从不触碰
闪存，因此这里没有任何东西会让板卡的可用性比开始时更差。

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
和图标）打包进可执行文件中——完整的推理见刷写工具自身的 README，因为
它在这里同样适用。

**版本管理：** `TESTER_VERSION`（在 `tester_config.py` 中，显示在标题栏、
关于对话框、会话日志和调试包中）遵循 `MAJOR.MINOR.PATCH`。两个构建脚本
都会通过 `bump_version.py`，在每次真正的构建之前自动递增它，采用十进制
“里程表”方式：PATCH +1，一旦 PATCH 超过 9 就进位到 MINOR（例如
`0.1.9` → `0.2.0`）。从源码运行（`python urtc_tester.py`）绝不会触碰它——
只有一次真正的 `build_exe.bat`/`build_exe.sh` 运行才会。MAJOR 从不自动
递增，只能手动更改。版本历史见 `CHANGELOG.md`。

**启动时**，横幅会在屏幕中央显示 5 秒，然后主窗口才出现，而不是存在于
窗口内部——与刷写工具相同，原因也相同（保持窗口本身紧凑）。窗口/任务栏
图标同样是一个独立的小型设计，而非缩小的横幅。

连接面板也会显示官方的 HYDRA-UMC 动画标志。其维护的 SVG 源文件为
`assets/HYDRA_UMC_ICON.svg`；随附的十二个 PNG 帧让动画能够在 Tkinter 和
独立可执行文件中运行，而无需增加运行时图形依赖。原生 URTC 窗口/任务栏图标
按设计保持静态。

### 可视化控制台

共享的 **Qt Quick** 命令控制台可用于真实连接、只监听监控以及明确启用的身份探测：
~~~
python urtc_tester.py --qtquick
~~~
它使用生产级 SLCAN/SocketCAN 传输。它以只监听模式启动，因此在你明确启用主动检查前
不会发送任何内容；该探测仅发送已文档化的活动工具与版本查询。在其 25 个专用面板安全迁移
期间，Tkinter 仍是默认的完整工具。

成熟的实时 CAN 诊断流程现在使用深海军蓝/青色控制界面：产品标题、高对比度连接卡、
清晰的工具标签页、深色会话日志以及可见的进度通道。这项视觉与可访问性改进不会改变
被动监控、命令路由或任何安全边界。

### 菜单栏

- **文件** —— 保存日志（将屏幕上的日志保存为纯文本；如需一个包含系统
  诊断信息的更完整的打包，请改用下方的“日志与调试包”），以及退出。
- **语言** —— 在 5 种可用语言之间切换（翻译的工作方式见上方“语言”）。
- **帮助** —— Readme（在一个只读查看器窗口中打开本文件；一旦当前语言
  存在已翻译的版本，会自动使用该版本）、URTC GitHub（在浏览器中打开
  项目的仓库）、许可证（本工具的 GPL-3.0 许可证，读取自仓库自身的
  `LICENSE` 文件），以及关于（版本和作者）。

### 文件结构

本工具按职责被组织为多个模块，纯粹是为了可读性——将它们作为独立文件与
作为一个大文件，在功能上没有任何区别。完整的逐文件分解见本文档末尾附近
的“📂 仓库结构”一节。

**语言**：默认为英语。通过窗口顶部菜单栏中的**语言**菜单切换，而非主
窗口中的下拉框——将界面（标签、按钮、对话框和日志消息）切换为 5 种可用
语言中的任意一种，立即保存到本工具旁边的 `config.json`，在下次启动时
应用。翻译文件以纯文本形式存放在 `language/` 下（`english.lng`、
`spanish.lng`、`italian.lng`、`french.lng`、`german.lng`），采用简单的
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
2 个子列，原因相同。

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
`docs/CANBUS.md`）——颜色无论如何仍然适用。

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
显示一个小型的滚动折线图——一个普通的 Tkinter Canvas 控件，而非新的
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
| 激光雕刻机 | 功率 + 联锁启用/安全 | 限位开关 |
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

## 5. 📋 日志与调试包

与刷写工具相同：一个带时间戳的会话日志会自动写入 `logs/`（删除是安全
的），**导出调试包**会将当前屏幕上的日志加上基本的系统诊断信息
（操作系统、Python 版本、当前的传输方式/端口/比特率、检测到的工具）
保存为一个 `.zip` 文件，以便交给正在调试某个工具头问题的人。

## 6. ⚠️ 已知限制

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
  协议中没有流式推送模式可以让它更快。在读取热成像返回真实数据之前，
  必须已经触发了一次采集并报告就绪（检查状态）——过早读取只会绘制出
  传感器自身缓冲区当时碰巧持有的任何内容。
- **运行自检仅覆盖 25 种工具中的 7 种**（电烙铁、钻头、激光器、3D
  打印机、AOI、真空、扫描探针）——完整说明见上方“工作原理”。按下该
  按钮时，其他 18 种工具不会得到任何自动检查；验证它们仍然意味着要
  观察实际硬件对其自身面板控件的响应。

## 📂 仓库结构

`assets/` 目录还包含 `HYDRA_UMC_ICON.svg`（维护中的动画矢量源文件）
和 `hydra_umc_icon_frames/`（其随附的十二帧 Tkinter PNG 帧）。
`tools/render_hydra_umc_icon_frames.py` 在开发期间从 SVG 重新生成
这些帧；运行应用程序并不需要它。

```
/
├── urtc_tester.py             入口点——无 CLI 的启动流程和启动画面
├── qt_tester.py                Qt Quick 前端——受限、默认只读的
│                                `--qtquick` 指令面板
├── tester_config.py            配置/语言/协议常量（CAN ID、工具名称、
│                                MOTION_TOOL_IDS、AVAILABLE_LANGUAGES、
│                                EXPANSION_BOARD_TYPES）
├── tester_transports.py        SLCAN 和 SocketCAN 传输类
├── tester_bus_monitor.py       后台 CAN 读取线程（CANBusMonitor）
├── tester_gui_core.py          TesterGUI 核心——连接、检测、窗口生命
│                                周期，以及菜单栏；下方 3 个混入类
│                                组合而成的类
├── tester_common_panels.py     CommonPanelsMixin——全局/F-RAM/扩展/
│                                自检/总线监视器/自定义帧面板
│                                （始终可见的部分）
├── tester_panel_helpers.py     PanelHelpersMixin——每个工具面板构建
│                                器都使用的共享工具函数
├── tester_tool_panels.py       ToolPanelsMixin——19 个特定工具面板
│                                构建器，覆盖全部 25 种工具配置文件
│                                （多个工具共享一个构建器，例如
│                                `_build_motion_panel` 单独覆盖了
│                                其中 7 个）
├── advanced_protocol.py        为迁移到 Qt Quick 的控制系列提供的纯 CAN
│                                负载编码器——无需硬件的测试
├── hydra_umc_animation.py      用于 Tkinter 的动画 HYDRA-UMC 身份标识控件
├── hydra_umc_deck_widgets.py   实时诊断界面共享的圆角 HYDRA-UMC
│                                指令面板控件
├── tests/
│   └── test_advanced_protocol.py   针对 advanced_protocol.py 编码器的无硬件测试
├── requirements.txt            pyserial>=3.5（Tkinter 测试器）+ PySide6>=6.8,<7（`--qtquick` 面板）
├── build_exe.bat               独立 Windows 二进制文件构建脚本（PyInstaller）
├── build_exe.sh                同上，适用于 Linux
├── build-test.bat              不递增版本号的构建/编译检查
├── build-test.sh                同上，适用于 Linux
├── bump_version.py             里程表式版本递增，由构建脚本运行
├── bump_manifest_version.py    将 hydra-umc.project.json 的版本与原生版本同步（--sync）
├── URTC_Tester.spec            两个构建脚本共用的 PyInstaller 规范文件
├── assets/
│   ├── URTC_APP_ICON.svg       窗口/任务栏图标源文件（独立小型设计）
│   ├── URTC_LOGO_TESTER.svg    启动横幅源文件
│   ├── HYDRA_UMC_ICON.svg      维护中的动画 HYDRA-UMC 矢量源文件
│   ├── hydra_umc_icon_frames/  由上方 SVG 渲染出的十二帧 Tkinter PNG 帧
│   ├── qml/
│   │   └── TesterDeck.qml      受限 `--qtquick` 指令面板的 Qt Quick UI
│   ├── urtc_icon.ico           Windows 图标，由 URTC_APP_ICON.svg 构建
│   ├── urtc_icon.png           同上，PNG 形式（Linux）
│   └── urtc_tester_banner.png  启动横幅 PNG，由上方的 SVG 渲染而成
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
│   └── chinese.lng
├── logs/                       运行时会话日志写入此处（删除是安全的）
├── LICENSE                     完整许可证文本——见下方许可证与版权声明
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
│   └── CANBUS.md
├── tools/
│   ├── ci_validate.py                    CI 使用的 manifest/CHANGELOG/docs 校验
│   └── render_hydra_umc_icon_frames.py   从 SVG 重新生成 assets/hydra_umc_icon_frames/（仅限开发）
└── README_zho.md               本文件
```

## 📸 照片

<p align="center">
  <img src="images/URTC_TESTER_V1_1.png" alt="URTC Tester window" width="700">
</p>

## 🔗 相关项目

本项目是同一作者（JuanenRac / Electro Hobby 3D）打造的更大规模机器人生态系统的一部分，横跨固件、控制应用、AI 节点和工业集成的众多项目。值得了解，因为某个请求实际所指的可能正是这些项目之一，而非本仓库。

### 与本项目直接相关

- **[URTC](https://github.com/JuanenRac/URTC)** —— 本测试器连接并诊断的正是这个固件,其 25 个工具配置文件各对应一个面板。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 一次性对每一个工具头运行车队级审计（`audit` 指令），超出了本测试器所覆盖的单板范围。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — 用其自身对工具头的视觉质量保证（QA）检查，补充本项目的实时 CAN 总线诊断。

### 生态系统的其余部分

**💠 核心生态系统**
[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) · [HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) · [HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) · [HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE) · [HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI) · [HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL) · [HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL) · [HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF) · [URTC](https://github.com/JuanenRac/URTC) · [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) · [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)

**👁️ 视觉 AI 节点（Hailo-8）**
[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE) · [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER) · [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF) · [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES) · [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)

**🧠 认知 AI 节点（Hailo-10）**
[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) · [HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE) · [HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI) · [HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER) · [HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)

**🐝 编排与集群**
[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR) · [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC) · [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D) · [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER) · [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)

**🎮 数字孪生与仿真**
[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN) · [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA) · [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE) · [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)

**📊 数据与分析**
[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE) · [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR) · [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR) · [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)

**🏭 工业网关**
[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL) · [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER) · [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER) · [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)

**🛠️ 配套工具**
[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) · [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH) · [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

## 📜 许可证

URTC Tester 版权所有 (c) 2026 JuanenRac（Electro Hobby 3D）。分发本项目
或其衍生作品时必须包含此声明。

本项目由源代码及其自身的文档组成，两者依据不同的许可证提供——各自适合
其实际所涵盖的内容：

1. 源代码（`urtc_tester.py` 及每一个 `tester_*.py` 模块）以及通过
   `build_exe.bat`/`build_exe.sh` 从中构建的任何二进制文件，依据
   **GNU 通用公共许可证 v3.0（GPL-3.0）** 提供。完整文本见
   https://www.gnu.org/licenses/gpl-3.0.html。

2. 文档（本 README 及其自身的翻译版本——`README_spa.md`、`README_ita.md`、
   `README_fra.md`、`README_deu.md`）依据 **知识共享 署名-相同方式共享
   4.0 国际许可协议（CC BY-SA 4.0）** 提供。完整文本见
   https://creativecommons.org/licenses/by-sa/4.0/。

本工具是 [URTC（Universal Robot Tool Controller）](https://github.com/JuanenRac/URTC)
项目的实时 CAN 总线诊断配套工具——本工具所测试对接的板卡固件、硬件设计
和完整协议文档见该项目自身的仓库。URTC 自身的固件为 GPL-3.0，其硬件
设计为 CERN-OHL-S v2；本工具自身的许可证并不延伸至那个独立的项目，
反之亦然。一个覆盖类似功能范围的基于网页的替代方案也存在，位于
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)。

如果你基于本项目进行开发，请留意这种许可证划分：代码更改应保持
GPL-3.0，文档衍生品应保持 CC BY-SA——每一项都需附带指向本项目及其
作者的署名。

## 👤 作者

**JuanenRac**（Electro Hobby 3D）
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
