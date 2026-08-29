# F-04 TouchDesigner模块化与图形化工作台升级控制 v1.0

> 状态：`ACTIVE_CONTROL / F-04_DONE / AC1-AC7_PASS / DIRECTOR_SIGNED`
> 生效日期：2026-08-29
> 状态权威：`05_可领取任务包.csv`
> 取代关系：本文件取代F-04原W0“只读页面骨架”任务定义、交付物和验收口径；不取代协议权威、TelemetryFrame v2.1或F-05、T-01、T-02任务定义。
> 升级前基线：`37f693e6c77905a95701bb5472c88112ea4317f3`，仅作为历史实现基线，不再作为最终验收候选。

## 1. 升级目标

F-04交付TouchDesigner原生的模块化、图形化、只读操作台。操作台必须使用本地静态fixture完整演示10类页面和5类场景，并以统一只读快照接口隔离页面、数据来源和后续运行接入。

本阶段不实现正式遥测消费者或人工请求通道。升级只建立可由T-01和T-02继续接入的清晰接缝，不提前实现其运行职责。

## 2. 权威顺序与职责

发生冲突时依次服从：

1. `00_总控/protocol_authority_v1.1.json`及其指向的协议权威；
2. `02-技术研发/05-通信协议/contracts/`中的TelemetryFrame v2.1合同；
3. 本文件规定的F-04内部结构、图形化要求和验收口径；
4. 任务注册表、生成手册和独立任务包；
5. 升级前F-04实现及截图。

| 任务 | 本阶段职责 | 不得由F-04提前实现 |
|---|---|---|
| F-04 | 本地静态fixture、模块化页面、图形化显示、只读权限与禁用占位 | 正式网络消费、运行控制、权威状态写回 |
| F-05 | 公共合同演进与消费者迁移 | F-04不得修改公共v2.1合同 |
| T-01 | UDP 5005、20Hz消费、序号、乱序、丢包、断流和重连运行逻辑 | F-04只保留停用且明确标记的输入占位 |
| T-02 | TCP 5010、人工标记、中止请求、ACK和审计 | F-04只显示禁用控件，不创建发送回调 |

## 3. 冻结模块结构

正式根模块固定为`F04_ReadonlyConsole`。构建器只能幂等替换该根模块，不得修改同一工程内其他根模块。

```text
F04_ReadonlyConsole
├── ConsoleShell
│   ├── PersistentHeader
│   ├── PageNavigation
│   └── ScenarioNavigation
├── Sources
│   ├── StaticFixtureAdapter       # F-04唯一启用数据适配器
│   └── UdpTelemetryPlaceholder    # disabled / T-01 NOT ACTIVE
├── SharedViews
│   └── WaveformPanel
├── Pages
│   ├── 01_SessionVersion
│   ├── 02_DeviceConnection
│   ├── 03_RespirationWaveform
│   ├── 04_EcgRrQuality
│   ├── 05_PhaseComparison
│   ├── 06_CycleResult
│   ├── 07_LatencyClock
│   ├── 08_Degradation
│   ├── 09_LogWrite
│   └── 10_ManualActions
└── Output
```

每个页面必须是独立模块，经统一页面出口进入`Output`。页面模块不得直接读取fixture文件、UDP节点、Unity连接或请求通道。

### 3.1 TelemetrySource接缝

`TelemetrySource`接口只提供：

```text
read_snapshot() -> ConsoleSnapshot
```

接口还包含一个只影响本地显示的`scenario_id`配置。`ConsoleShell`可以修改该配置以切换静态场景；该变化不得写入TelemetryFrame、日志权威或网络。

- `StaticFixtureAdapter`是F-04唯一启用的适配器，从`f04-static-display-fixture-v1`读取确定性数据。
- `UdpTelemetryAdapter`由T-01实现；F-04仅保留停用占位，不实现监听、节流、重连或序号处理。

### 3.2 ConsoleSnapshot内部接口

`ConsoleSnapshot`是所有页面唯一允许消费的显示接口：

```text
ConsoleSnapshot
├── meta
│   ├── fixture_id
│   ├── scenario_id
│   ├── page_id
│   └── replay_state = DEV-REPLAY
├── telemetry              # 完整TelemetryFrame v2.1字段
└── display_only
    ├── respiration_waveform_25hz
    ├── rr_quality
    ├── cycle_summary
    ├── log_status
    └── disabled_requests
```

`display_only`只服务本地静态演示，不得进入正式线格式。页面无权修改快照，页面渲染也不得产生网络、文件或运行控制副作用。

## 4. 图形化工作台最低标准

`ConsoleShell`顶部必须始终显示`READ ONLY / DEV-REPLAY / NOT LIVE`。左侧或顶部提供10页可见导航和5类场景可见导航；允许的场景固定为`GOOD`、`DEGRADED`、`UNUSABLE`、`DISCONNECTED`、`OUT_OF_ORDER`，禁止随机选择。

| 页面 | 必须呈现的核心图形机制 |
|---|---|
| 会话/版本 | 会话、合同版本、fixture和回放状态卡 |
| 设备连接 | 连接状态徽标、数据新鲜度和设备质量条 |
| 原始/滤波呼吸 | 双通道曲线；数据链为`DAT to CHOP -> Select/Math CHOP -> OP Viewer TOP` |
| ECG/RR质量 | 质量仪表和RR状态条 |
| 目标/实际相位 | 双相位轨迹或并列相位指示 |
| 周期结果 | 周期摘要卡和只读结果表 |
| 延迟/时钟 | 延迟与时钟偏移条形指示 |
| 降级 | 当前等级状态带和静态状态轨迹 |
| 日志写入 | 写入状态、计数和只读路径卡 |
| 人工标记/中止 | 显式禁用按钮及`T-02 NOT ACTIVE`说明 |

文字可用于标签和精确数值，但不得以纯文本转储替代上述核心图形机制。页面与场景导航只允许改变本地显示索引。

## 5. 禁止项

F-04实现和生成节点中禁止：

- Spout或其他网络输出；
- Unity连接或直接控制；
- 随机化、正式阈值编辑或真实设备驱动；
- UDP 5005有效监听及任何正式20Hz消费者逻辑；
- TCP 5010连接、人工请求发送回调、ACK或审计实现；
- 覆盖会话权威、日志权威或其他模块状态。

## 6. 验收标准

- **AC1**：10个页面均可通过可见导航访问，5个静态场景均可切换，只读标识始终存在。
- **AC2**：呼吸页具有CHOP支撑的真实曲线；其余状态页具有对应图形机制，不存在仅靠文本占位完成的页面。
- **AC3**：页面统一通过`ConsoleSnapshot`取数；替换静态数据适配器不需要修改页面模块。
- **AC4**：UDP 5005节点停用，人工操作控件禁用；关闭TouchDesigner后5005和9981均无监听。
- **AC5**：源码、节点清单和权限清单中不存在Spout、网络输出、随机化、阈值编辑、直接Unity输出或请求发送回调。
- **AC6**：TouchDesigner 2025.32820构建、保存、关闭、重开后无节点错误；提供10页`GOOD`基线截图和其余4个场景的状态差异截图。
- **AC7**：用户授权的独立团队总监打开`.toe`、切换全部页面和场景、检查节点权限并签署`PASS/FAIL`；自动检查不得替代该独立结论。

## 7. 必需证据与验证

升级候选必须提供：

- 可重建脚本、正式`.toe/.tox`及SHA-256；
- `ConsoleSnapshot`接口测试和静态适配器替换测试；
- 10页乘5场景映射检查；
- 页面清单、节点计划、节点清单、节点权限和节点错误报告；
- 10张`GOOD`页面截图及4张状态差异截图；
- 5005和9981端口检查；
- F-01合同回归、P-01/P-02相关回归；
- 任务注册表、独立任务包和`git diff --check`结果；
- 用户授权的独立团队总监签收记录。

静态fixture和截图只证明开发回放工作台可演示，不证明真实设备、正式运行链或联合运行成立。

## 8. 状态与独立任务包控制

1. 本文件生效时，F-04由`IN_REVIEW`退回`IN_PROGRESS`，总工期调整为3人日；领取人与第二复核人不变。
2. `IN_PROGRESS`期间从当前解锁独立任务包映射和生成目录移除旧F-04审阅包，避免新验收项被误标为已通过。
3. 升级实现完成并通过机器门后，F-04才可转回`IN_REVIEW`。
4. 转回`IN_REVIEW`时必须重新加入文件映射，并把本控制文件、实现、节点导出、截图、验证报告和哈希纳入新F-04独立任务包。
5. 只有AC1至AC7全部关闭并取得团队总监`PASS`后，F-04才可转为`DONE`；本控制文件本身不构成实现完成或签收。
6. 用户后续明确授权独立Agent承担本轮团队总监检验。独立任务`01a04c71-9894-73c3-aea1-30cb0d0280c0`已在候选`6a5d0c8dca0069bea228d9e7c7fdcb34049856bf`上完成二轮实机复审并签署`PASS`，可作为AC7签收依据。
