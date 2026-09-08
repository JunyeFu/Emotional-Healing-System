# U-01 代码审查意见（第 1 轮）

> 审查人：Grip（后方技术审查）｜日期：2026-09-07
> 审查依据：`runtime-contract-v2.2.schema.json`、`06_目标运行接口_v2.md`、F-05 v2.2 迁移指南、`srp_session_core/transport.py`（P-01 服务器真实实现）、consumer-fixtures（hello-v2.2 / hello-v2.1-formal-rejected / phase-instance-stream.jsonl）、U-01 TASK.md 验收标准。
> 审查对象：`Assets/U01/` 全部 8 个 Runtime .cs + 1 个 EditMode 测试文件（截至 09-07 15:14）。

## 0. 总评

骨架完整、命名清晰、JSON 序列化器和线程模型可用，**工程底子是好的**。但有 3 个方向性硬伤：

1. **ACK 逻辑做反了**——Unity 是 ACK 的**发送方**，当前 AckManager 实现的是服务器侧"发事件等 ACK 超时重发"逻辑；
2. **测试测的是死代码**——UDP 完整校验方法 `Validate()` 在真实接收链路里从未被调用，运行时只走 `ValidateStatic()`（只查 message_type）；
3. **组件之间没有接线**——ReconnectHandler、RenderReceiptManager、AckManager 与 ReliableControlClient 互不调用，重连退避、渲染回执发送在真实运行中永远不会发生。

当前 EditMode 测试即使全绿，也**不能满足 AC1/AC2/AC3 的任何一条**（测试没有覆盖控制事件重发、旧帧覆盖、握手失败关闭、断连重连补发这些端到端行为）。

按下面 P0 → P1 → P2 顺序修。P0 不修完不要 commit。

---

## 1. P0 — 验收阻断项（必须修）

### P0-1 ACK 幂等逻辑方向错误（对应 AC1）

**现状**：`AckManager.TrackEventSent()` 跟踪"已发出的 control_event"、`ProcessIncomingAck()` 处理"收到的 ACK"、`CheckTimeouts()` 做超时重发升级。这是**服务器（Python ControlServer）的职责**，证据见 `transport.py`：`_pending_acks`、`publish_control()` 的 max_send_attempts 重试循环全在 Python 侧。

**Unity 侧真实职责**（见 `06_目标运行接口_v2.md` 与 `transport.py::_handle_unity_message`）：

| 场景 | Unity 正确行为 |
|---|---|
| 收到新 event_id 的 control_event | 应用到 SessionMirror → 回 `result="applied"` 的 ACK |
| 收到**重复** event_id（服务器超时重发/重连补发） | **不再重复应用**，回 `result="duplicate_ignored"` 的 ACK |
| 事件无法应用（会话不匹配/状态非法） | 回 `result="rejected"` + error_code |
| 渲染失败 | render_receipt `result="failed"`（不影响 ACK 本身） |

**改法**：
- 删除/反转 AckManager 语义：维护 `HashSet<string> _appliedEventIds`（已应用事件）即可；
- `ReliableControlClient.ProcessControlEvent()` 当前逻辑是"未 delivered 就 TrackEventSent 并回 applied"——`IsDelivered()` 永远为 false（Unity 永远收不到自己的 ACK），所以**重复事件每次都会回 applied 并再次触发 OnControlEvent**，幂等完全失效；
- 正确流程：`if (_applied.Contains(evt.event_id)) → 回 duplicate_ignored ACK，不再 ApplyControlEvent/OnControlEvent；else → 应用、加入集合、回 applied`；
- 注意：重连后（新世代）服务器补发的旧事件仍用同一 event_id，**仍要回 duplicate_ignored**（服务器 `_delivered_event_ids` 与 `_sent_event_ids` 逻辑要求如此，见 transport.py 183-200 行附近）。`_appliedEventIds` 不要在重连时清空。

### P0-2 UDP 校验是死代码（对应 AC2 + 合同门禁）

**现状**：`UDP5006Gate.ValidateStatic()`（真实链路 `ValidateWithTracking()` 调用）只检查 message_type；完整字段校验 + schema_version 门禁在 `Validate()` 里，**只有测试调用**。即：运行时任何畸形帧、v2.1 帧都能过门。

**改法**：
- `ValidateWithTracking()` 改为调用完整校验（把 `Validate()` 的必填字段/schema_version 检查合并进来），`ValidateStatic()` 删除或改为调用完整校验；
- 必填字段以 schema 为准（telemetry_frame 全部 required 字段，用 fixture `12_phase-instance-stream.jsonl` 逐字段对照，共 24+ 字段：schema_version/message_type/session_id/frame_seq/clock_domain_id/source_monotonic_ns/received_monotonic_ns/sent_monotonic_ns/clock_offset_ns/clock_drift_ppm/sync_uncertainty_ns/module_id/module_position/segment/target_phase/target_progress/actual_phase/actual_progress/actual_confidence/recovery_value/recovery_locked/signal_quality/fallback_state/resp_device_state/ecg_device_state/cue_mode/runtime_mode + 可空的 policy_decision_id/target_cycle_index/target_step_id/actual_cycle_index/actual_step_id）；
- **frame_seq 基线按 session_id 重置**：fixture 里 frame_seq 从 20 开始，且重连/新会话序号会重新从小号开始。当前 `_lastFrameSeq` 全局单调，新会话首帧会被误判 StaleSequence。维护 `(session_id → last_seq)`，session_id 变化时重置；
- v2.2 步骤实例规则：`target_cycle_index` 与 `target_step_id` 同时有值或同时 null（actual 同理），storm 的 hold_1/hold_2、fade 的 inhale_1/inhale_2 **禁止从 phase/progress 推断**——Gate 校验这两对字段的同存同null规则，违规帧 SchemaViolation 丢弃。

### P0-3 协议级失败必须 fail-closed，不得无限重连（对应 AC3）

**现状**：`ReceiveLoop()` 对任何异常（含握手被拒）都 `Thread.Sleep(1000)` 后无限重试。v2.1 正式握手被服务器拒绝（fixture `hello-v2.1-formal-rejected.json`，期望错误码 `SCHEMA_VERSION_MISMATCH`）后，Unity 会永远每秒重连握手——违反合同"按合同失败关闭"。

**服务器错误码语义**（从 `transport.py` 提取，握手阶段）：
`TRANSPORT_HANDSHAKE_INVALID`、`TRANSPORT_VERSION_MISMATCH`、`SCHEMA_VERSION_MISMATCH`、`TRANSPORT_ROLE_INVALID`、`CLIENT_INSTANCE_ID_INVALID`、`UNITY_CLIENT_ALREADY_CONNECTED`（welcome 带 `accepted:false`）。

**改法**：
- 握手阶段收到 welcome `accepted=false` 或 error 帧：判定为**永久协议错误**，停止重连，连接状态进入 UNUSABLE（见 P0-6 降级四态），打日志并对外暴露错误码；**不要**重试；
- 运行期收到 error 帧也要分类（当前 `OnTransportError` 只是打日志）：
  - `CONTROL_ACK_CONNECTION_MISMATCH`：自己是旧世代连接 → 主动断开走重连；
  - `CONTROL_ACK_NOT_PENDING`：ACK 对不上服务器待办（事件已过期）→ 记日志，不重连；
  - `TRANSPORT_FRAME_INVALID` 等：计数，连续异常达阈值 → 降级/断开；
- 只有**网络层异常**（连接被拒/EOF/超时）才走指数退避重连。

### P0-4 组件接线：重连与渲染回执当前是死代码

**现状**：
- `ReconnectHandler`（退避/jitter/世代/故障注入）从未被 `ReliableControlClient` 调用——ReliableControlClient 自己写了 `Thread.Sleep(1000)` 固定退避；两套 generation 互不相干。
- `RenderReceiptManager` 从未被调用——`ReliableControlClient` 有 `SendRenderReceipt()` 但没有任何地方 Register/Complete 回执。**渲染回执序列这条验收证据当前产出为零**。

**改法**：
- ReliableControlClient 接入 ReconnectHandler（或把退避逻辑收进 client，二选一，不要两套并存）：网络断开 → 退避重连 → 成功后世代+1；
- 渲染回执闭环：control_event 应用后（module/segment/start 等触发画面动作的事件）RegisterEvent → 主线程确认画面状态已应用（探针阶段可在事件应用后的下一帧 LateUpdate）→ CompleteRendered → SendRenderReceipt；abort/pause 类事件按合同回 skipped/rendered 要和 06 文档对齐；
- 故障注入（FaultMode.DropEveryNth/CorruptMessage）要真正挂到收发路径上，否则"网络故障日志"证据无法产出。

### P0-5 重连后状态同步（对应 AC3"断连重连"）

**现状**：重连成功只打了句日志，没有状态重置/重放逻辑。

**合同要求的重连语义**（transport.py 可证）：
- Unity 重连时 **client_instance_id 必须保持不变**（当前 Awake 里生成 GUID 且不随重连变，✅ 已满足，保持）；
- 重连 = 新世代，服务器会重新走 prepare/重放 manifest 与未确认 control_event；
- Unity 侧：重连成功后等新 session_manifest 到达再重建镜像；镜像里 `_appliedEventIds` 保留（见 P0-1）；UDP Gate 的 frame_seq 基线按新 session_id 重置（见 P0-2）；RenderReceiptManager 未完成的 pending 收据按 abort 处理（failed/skipped），不要把旧世代回执发出去。

### P0-6 补 PlayMode 测试 + 端到端 fixture 驱动测试（证据缺口）

**现状**：只有 EditMode 程序集，没有 PlayMode；且现有测试全是单元级（序列化/字段/管理器内部状态），没有一条测试驱动真实消息流。

**必须补的测试**（对照 TASK.md 验收）：

| AC | 必测场景 | 做法建议 |
|---|---|---|
| AC1 | 同一 event_id 控制事件"重发"两次 → 镜像只应用一次，第二次 ACK 为 duplicate_ignored | EditMode 可测：直接调消息处理入口，喂两次同一 control_event JSON |
| AC1 | 丢包/乱序/重复的 **telemetry fixture 流** → 旧帧/重复帧不覆盖新帧 | 用 `12_phase-instance-stream.jsonl` 打乱/重复后逐帧喂 Gate，断言接受序列的 frame_seq 单调、镜像不回退 |
| AC2 | 无 control_event 时本地时间流逝/收到旧帧 → 模块与 segment 不推进 | PlayMode：挂组件跑若干帧，不发控制事件，断言 SessionMirror 不变 |
| AC3 | hello v2.1 正式握手（`11_hello-v2.1-formal-rejected.json` 场景）→ 收到 SCHEMA_VERSION_MISMATCH 后**停止重连**、状态 UNUSABLE | 用 loopback 假服务器（EditMode 起 TcpListener 即可）回 welcome accepted:false / error 帧 |
| AC3 | 断连后重连 → 世代+1、同一 client_instance_id、补发事件回 duplicate_ignored | 假服务器断开再接受连接，断言行为 |
| AC3 | render_receipt 被拒/失败路径 | CompleteFailed 后消息能发出且字段正确 |

- 新建 `Assets/U01/Tests/PlayMode/`（asmdef 参照 `Assets/F03/Tests/PlayMode/SRP.F03.PlayModeTests.asmdef`：includePlatforms 空 + TestAssemblies）；
- 假服务器/假 UDP 发送端用 `System.Net.Sockets` 直接在测试里起 loopback，不需要真 Python。

---

## 2. P1 — 合同符合性与正确性（应修）

| # | 问题 | 依据 | 改法 |
|---|---|---|---|
| P1-1 | 时间戳用 `DateTime.UtcNow`（墙钟） | 合同字段名 `*_monotonic_ns`，P-01 用 `time.monotonic_ns`；墙钟会被 NTP 回拨 | 改用 `System.Diagnostics.Stopwatch.GetTimestamp()` 按 `Stopwatch.Frequency` 换算 ns（AckManager/RenderReceiptManager 的 `_nowNs` 默认值都要改） |
| P1-2 | ACK 的 `received_monotonic_ns` 与 `applied_monotonic_ns` 取同一时刻 | 06 文档：received=收到字节时刻（接收线程），applied=主线程应用时刻 | 接收线程记录 received 时间戳随消息入队，主线程处理时取 applied |
| P1-3 | TCP 入站消息无 schema_version 门禁 | schema base：`schema_version const "2.2"` | 收到 session_manifest/control_event 时校验 schema_version=="2.2"，不符 → 按协议错误失败关闭（P0-3 同一通道） |
| P1-4 | UDP 套接字绑定 `IPAddress.Any` | 06 文档安全要求：所有传输仅绑 127.0.0.1；P-01 只往 loopback 发 | `new UdpClient(new IPEndPoint(IPAddress.Loopback, _port))` |
| P1-5 | `ReadLine()` 逐字节 `(char)b` 拼接 | 中文/多字节 UTF-8 会乱码 | 按字节读到 \n 后整体 `Encoding.UTF8.GetString()` |
| P1-6 | SessionMirror 里 `mpos is int mp` 对真实 payload 失效 | JSON 反序列化数字为 long（见 ContractMessages.JsonReader：整数走 `long.TryParse`） | 改为 `is long mpLong ? (int)mpLong` 或经 GetInt 式转换；module_position 真实链路永远拿不到值 |
| P1-7 | control_event/telemetry 的 session_id 与当前会话不匹配时仍处理 | 06 文档会话隔离 | session_id 不符 → 拒绝并记日志（探针也要防串会话） |
| P1-8 | `DequeueNext()` 与 `DequeueAndDispatch()` 重复且计数逻辑不一致 | 代码可读性 | 删 DequeueNext（无调用方） |
| P1-9 | `clock_offset_ns` 等时钟同步字段接收后不使用 | 06 文档：时钟偏差 ≤50ms 为健康门槛 | 探针至少记录/暴露最近 clock_offset 与 sync_uncertainty，超阈值计入降级状态（供 U-03 用） |
| P1-10 | TcpClient.Connect 无超时 | 服务器不在线时接收线程卡 20s+ | 用 `BeginConnect`+WaitHandle 或带超时的 ConnectAsync |
| P1-11 | `ReliableControlClient` Inspector 里 `[SerializeField] AckManager/RenderReceiptManager` | 这两个是普通 C# 类（非 MonoBehaviour），不能序列化挂引用 | 改为代码 new（Awake 里构造）或改成 MonoBehaviour；当前接线方式在 Unity 里根本赋不上值 |

---

## 3. P2 — 流程与工程（提交前完成）

1. **立刻切任务分支**（当前还在 main 上写未跟踪文件！）：
   ```
   cd /d D:\Agent\03-SRP
   git -c filter.lfs.smudge=cat -c filter.lfs.process= -c filter.lfs.required=false checkout -b codex/u-01-reliable-control
   ```
2. 按 AGENTS.md Codex Workflow：进度写 `work/codex-blackboard.md`，验证记录写 `work/codex-verification-log.md`（测试跑了什么、结果如何、假服务器输出）。
3. **证据落盘**（TASK.md 必需证据）：探针运行时把 ACK 序列、render_receipt 序列、连接/世代事件、故障事件写成 JSONL 日志（建议 `Application.persistentDataPath/u01-probe/` 或仓库 work 目录），对应"网络故障日志 / 状态镜像轨迹 / ACK与渲染回执序列"三项证据。PlayMode 跑一轮完整假会话后把日志附进 verification-log。
4. 工程根目录 `SRP.U01.Tests.csproj`、`SRP-Weather-Visual.slnx` 等是 Unity 自动生成文件——确认 `.gitignore` 覆盖 `*.csproj`、`*.slnx`（git status 里 slnx 是 ?? 未忽略状态，要么加忽略规则要么不要 add）。**只 git add 任务相关文件**：`Assets/U01/`（含 .meta）+ `work/` 下记录。
5. `U01_TASK_PLAN.md` 放在 Assets/U01/ 下会被 Unity 当资源导入（不报错但不规范）——可移到 `work/` 或任务包目录，Assets 内只留代码与 asmdef。

---

## 4. 建议修复顺序

1. **先切分支**（P2-1），把现有代码 commit 一次存档（WIP）；
2. P0-1（ACK 幂等反转）→ P0-2（UDP 校验合并 + session 重置 + 步骤实例规则）→ P0-3（fail-closed 分类）→ P0-4（接线：重连/回执/故障注入）→ P0-5（重连状态）；
3. P1 全部（大多是小改）；
4. P0-6 补测试（EditMode 端到端 + PlayMode），用 fixture 文件做输入；
5. Unity Test Runner 全绿 + PlayMode 假会话跑出证据日志；
6. P2 记录补齐，commit/push 通知第二人复核。

改完通知 Grip 做第 2 轮审查。有对合同理解拿不准的地方，先查 `06_目标运行接口_v2.md` 和 `transport.py`，不要按猜测实现。
