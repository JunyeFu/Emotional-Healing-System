# U-01 双实现对照分析：reliable-control（本分支）vs unity-control（main 已合入）

> 目的：回应第二人复核要求——对比最新 main，说明本分支需保留哪些改动，形成可审阅结论。
> 数据来源：`git diff origin/main...HEAD`（38 files, +6534/-18）+ 双 worktree 文件级对比（2026-09-08）。
> main 侧实现（unity-control）由 commit 6c09f71d 等构成，Assets/U01/ 同路径，**同名 4 个 .cs 与本分支完全分叉（diffLines ≈ 两版行数之和，几乎零共同行）**。

## 1. 结论先行

1. **两版不是覆盖关系，是两套架构**。main 已签收 unity-control 版为权威实现；本分支（reliable-control）不应也无法直接合并（同名文件全分叉）。
2. 本分支定位建议：**高保障平行参考实现**——以本 evidence 目录 + 分支保留的形式存档，供第二人对照评审。
3. 若团队决定吸收本分支能力，建议**以 unity-control 的 DTO/Codec 体系为基座做模块移植**，不整体替换已签收代码。

## 2. 规模与文件地图

| 文件（Assets/U01/ 下） | reliable-control | unity-control (main) |
|---|---|---|
| Runtime/ReliableControlClient.cs | **1205 行（52592B）** | 298 行（12993B） |
| Runtime/SessionMirror.cs | 234 行 | 114 行 |
| Runtime/AckManager.cs | **6622B**（OURS-ONLY） | - |
| Runtime/ContractMessages.cs | **16055B**（OURS-ONLY，10 个契约类） | - |
| Runtime/ReconnectHandler.cs | **11532B**（OURS-ONLY，含故障注入） | - |
| Runtime/RenderReceiptManager.cs | **10969B**（OURS-ONLY） | - |
| Runtime/UDP5006Gate.cs | **19537B**（OURS-ONLY） | - |
| Runtime/ProtocolCodec.cs | - | 23908B（MAIN-ONLY） |
| Runtime/ProtocolDtos.cs | - | 4292B（MAIN-ONLY） |
| Runtime/DeliveryFactory.cs | - | 2214B（MAIN-ONLY） |
| Runtime/RenderReceiptGate.cs | - | 4848B（MAIN-ONLY） |
| Runtime/TelemetryReceiver.cs | - | 2022B（MAIN-ONLY） |
| Runtime/U01RuntimeBridge.cs | - | 4417B（MAIN-ONLY，统一运行入口） |
| Editor/U01EvidenceBuilder.cs | - | 6761B（MAIN-ONLY，证据一键生成） |
| README.md | - | 1340B（MAIN-ONLY） |
| Tests/EditMode/U01EditModeTests.cs | **1607 行**（85 项） | 523 行 |
| Tests/PlayMode/U01PlayModeTests.cs | **1248 行**（9 项） | 105 行 |

## 3. 能力覆盖矩阵

| 能力域 | reliable-control | unity-control (main) | 评注 |
|---|---|---|---|
| TCP 可靠控制客户端 | 1205 行：握手世代、ACK/回执闭环接线、错误帧分类 fail-closed | 298 行轻量实现 | 语义同源（同一 U-01 任务卡），实现深度差异大 |
| 协议消息定义 | ContractMessages 一体化（TransportHello/Welcome/Error、SessionManifest、ControlEvent、AckMessage、RenderReceipt 等 10 类） | ProtocolDtos + ProtocolCodec + DeliveryFactory 三层分离 | main 分层更利于扩展；ours 消息覆盖面更全（含 DeviceConfig、ModuleDurations） |
| ACK 幂等 | **AckManager**：HashSet 已应用事件、IsApplied/MarkApplied、duplicate_ignored、跨重连保留 | 内嵌于 client | ours 语义显式、可独立测试 |
| 重连与故障注入 | **ReconnectHandler**：ReconnectPolicy 策略类 + SetFaultMode(FaultMode, everyN, delay) 故障注入钩子 + Abort/ResetState | 无独立模块（README 称有 loopback 断线重连测试） | ours 的故障注入钩子是 main 版测试体系没有的能力 |
| 渲染回执 | **RenderReceiptManager**：TrackedReceipt 注册→CompleteRendered/Skipped/Failed→GetUnsentReceipts→MarkSent 全生命周期 | RenderReceiptGate：遥测帧确认门（minimumTelemetry 校验） | 两版取径不同：ours 管生命周期，main 管遥测确认 |
| UDP 5006 遥测 | **UDP5006Gate**：MonoBehaviour 门控 + ValidateFull 全量校验（必填字段、frame_seq 按 session 重置、v2.2 步骤实例规则） | TelemetryReceiver：2KB 轻量接收队列 | ours 校验强度显著更高 |
| 统一运行入口 | 无（组件手工接线） | **U01RuntimeBridge**：挂载即用，ConsumeControl/ConsumeTelemetry/ConfirmRendered | main 侧集成体验更好 |
| 证据生成 | 无（人工整理） | **U01EvidenceBuilder**（Editor） | main 侧证据链自动化 |
| 测试规模 | EditMode 85 项（1607 行）+ PlayMode 9 项（1248 行，三轮实测 9/9 XML 实证） | EditMode 523 行 + PlayMode 105 行 | ours 测试深度大（幂等/乱序/丢包 fixture、故障注入、握手拒绝负测试） |

## 4. 推荐保留/吸收清单（供第二人裁量）

| 优先级 | 模块 | 理由 |
|---|---|---|
| 高 | ReconnectHandler 故障注入框架（FaultMode/everyN/delaySeconds） | main 版测试缺乏系统性故障注入钩子，吸收后可低成本补网络负测试 |
| 高 | UDP5006Gate.ValidateFull 校验逻辑 | v2.2 步骤实例规则（target_cycle_index/target_step_id 同存同 null、frame_seq 按 session 重置）实现完整，可直接对照移植 |
| 中 | AckManager 显式幂等语义 | duplicate_ignored 语义清晰可测，可对照检查 main 版 client 内嵌实现是否有遗漏 |
| 中 | PlayMode 测试资产（1248 行） | 若吸收需按 main 版 API 适配，工作量大；建议作为设计参考而非直接移植 |

## 5. 本分支价值声明

即使不吸收代码，本分支提供了：①同一任务卡的**第二实现视角**（交叉验证协议语义理解）；②85+9 项测试的**完整实测证据链**（XML + 七轮评审 + 三轮 PlayMode 裁决记录）；③fail-closed / 幂等 / 门控校验的**参考实现**。分支按团队治理保留或归档均可，不影响 main 已签收实现。

## 6. 复现与证据入口

- 测试证据与复现命令：见同目录 `REVIEW_RECORD.md`
- 本分析数据快照：双 worktree 对比脚本输出（D:\Coze\tools\u01_compare.ps1，2026-09-08 22:3x 执行）
