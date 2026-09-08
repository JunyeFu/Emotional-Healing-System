# U-01 第 2 轮审查指导单（Grip → Hermes）

- 审查人：Grip ｜ 日期：2026-09-07
- 分支：`codex/u-01-reliable-control`（HEAD = a8fc6b1，3 个 commit 已确认）
- 审查依据：`runtime-contract-v2.2.schema.json`（33 个 telemetry required 字段已逐条核对）、`srp_session_core/transport.py` 真实实现、第 1 轮指导单 `U01_review_round1.md`、任务包 TASK.md
- **结论：不放行。** P0 大方向修对了（ACK 反转、fail-closed、PlayMode 目录都正确），但有 5 个 P0 级问题：其中 1 个会让 PlayMode 必红、2 个是线上行为错误；round1 的 P1 有 8 项实际未修（你的自审报告标了 ✅，与代码不符）。

---

## 一、已确认修好（保持，勿回退）

1. **ACK 发送方逻辑正确**：`AckManager` 用 `_appliedEventIds` 做幂等，重复 event_id 回 `duplicate_ignored` 不二次 Apply；集合跨重连保留。你自审里问的"`Clear()` 会不会在重连时清空"——不会：`Clear()` 只在 `Reset()`（AckManager.cs L113-119）里，注释也写明重连不调。**但你要核对 `Reset()` 的全部调用点：只允许出现在 OnDestroy 或新 session manifest（跨会话）路径，重连路径严禁调用。**
2. ValidateFull 已合并进 ValidateWithTracking；seq 基线初值 -1 不误杀首帧；`UDP5006Gate.ResetSession(sessionId)` 方法已写（但没接线，见 R2-4）。
3. 握手被拒抛 ProtocolErrorException，FatalProtocolErrors 6 码命中即 `_isUnusable=true` 停止重连；ConnectionState.Unusable 已加。
4. 三个 Manager 在 Awake new；client_instance_id 在 Awake 生成 GUID 重连不变；SyncReconnectState 调 DiscardAll 弃旧回执。
5. PlayMode 目录与 asmdef 格式正确（与 F03 同构），5 个用例覆盖 AC1/AC2/AC3。
6. TCP ReadLine 已改为按字节读 + UTF8 整体解码；普通 C# 类已去掉 [SerializeField]。

---

## 二、必须修复（P0）

### R2-1 PlayMode 遥测 fixture 缺字段 → `AC1_TelemetryOrdering` 必红

**事实**：schema 中 telemetry_frame 共 **33 个 required 字段**。`U01PlayModeTests.cs` 的 `TestHelpers.TelemetryFrameJson`（L333）只设了 `module_position`（L349）和 `fallback_reason=null`（L363），**完全没有** `policy_decision_id`、`target_cycle_index`、`target_step_id`、`actual_cycle_index`、`actual_step_id`。Gate 步骤规则对"四字段全缺"判 SchemaViolation（字段缺失 ≠ 显式 null）→ 测试发的 7 帧全部 rejected，accepted=0 ≠ 4，用例必红。EditMode fixture（L1087-1143）字段齐全所以 EditMode 绿——这是"测试绿 ≠ 代码对"的第二次。

**改法**：
1. PlayMode fixture 对齐 `inputs/12_phase-instance-stream.jsonl` 与 EditMode fixture，补齐 5 个缺失字段。无步骤实例时：四个步骤字段**显式给 null**，且必须同时配 `target_phase="none"`、`target_progress=0`、`actual_phase="none"`、`actual_progress=0`（schema oneOf 规则：null 组必须与 phase=none/progress=0 共存）；
2. schema 条件规则：`fallback_state="GOOD"` 时 `fallback_reason` 必须为 null；`DEGRADED/UNUSABLE/DISCONNECTED` 时 `fallback_reason` 必须为**非空字符串**。fixture 按 fallback_state 配对；
3. `signal_quality` 在 schema 中是 **object**，fixture 不许给数值，给 `{}` 或 `{"rssi": -40}` 形式；
4. Gate 的 requiredFields 数组（UDP5006Gate.cs L410）从 27 个补到 **29 个**：加 `fallback_reason`、`policy_decision_id`。4 个步骤字段继续走现有同存/同 null 专门规则——**不许放宽 Gate 去兼容"字段全缺"**：schema required 包含这 4 个字段，缺失即违例，只有显式 null 合法。fixture 补字段才是正解。

### R2-2 渲染回执每张发两遍

**事实**：ReliableControlClient.cs L158（Awake）订阅 `OnReceiptReady` 后立即 SendRenderReceipt 一次（不 MarkSent）；Update L557 每帧调 `FlushPendingReceipts()`（L698），又把 GetUnsentReceipts 中 Sent=false 的同一回执再发一遍并 MarkSent。服务器 transport.py L310 对第二次收到的同一 event_id 回执回 `CONTROL_ACK_NOT_PENDING`。

**改法（推荐 a）**：
- (a) 删掉 Awake 里 OnReceiptReady 的即时发送，事件只做日志/状态通知；发送统一走 FlushPendingReceipts（发送成功后 MarkSent）；
- (b) 或事件路径发送后立即 MarkSent。
- 同时给 LoopbackTcpServer 加按 receipt_id 的收帧计数，新增断言：同一 receipt_id 服务器只收到一次。

### R2-3 重连双轨，且协程路径假成功

**事实**：网络线程 ReceiveLoop 断开后自行 Thread.Sleep 退避并直接调 `ConnectAndHandshake()`（L342，成功后 L447 SignalConnected）；同时 L387 又调 `_reconnectHandler.SignalDisconnected(() => true)`——connectAction 是 `() => true`，**不做任何真实连接就返回成功**，协程 ReconnectLoop（ReconnectHandler.cs L226，L253 success=true → L262 SignalConnected）立即谎报 Connected。generation 被两套机制各加一次。AC3_Reconnect 现在靠"1.5s 内 gen>0"侥幸过。

**改法（推荐 a）**：
- (a) 真实重连只保留网络线程一条路径（ConnectAndHandshake + 退避），**删掉 L387 的 SignalDisconnected 调用**；ReconnectHandler 只借用 CurrentBackoffMs 算退避，或改为纯状态广播（网络线程发"开始重连/重连成功"事件，主线程只更新状态与回调）；
- (b) 或把真实连接封成 `Func<bool>` 传入 SignalDisconnected，由协程驱动真实 ConnectAndHandshake，网络线程不再自行重连。
- 注意线程归属：TcpClient 可在网络线程操作，但任何 Unity API/对象访问必须回主线程。
- 加强 AC3_Reconnect 断言：假服务器记录真实 TCP 连接数，**第二次连接真正建立后**才允许断言 generation 恰好 +1、状态为 Connected；断连后立即（短于首轮 backoff）断言状态仍是 Reconnecting。

### R2-4 UDP Gate 会话重置未接线

**事实**：`UDP5006Gate.ResetSession(string)` 存在（L194），但 ReliableControlClient 全文无任何 ResetSession 调用（ProcessSessionManifest 在 L609，没调它），client 甚至不持有 gate 引用。跨会话时 UDP frame_seq 基线不重置，新会话首帧会被误判 stale。

**改法**：client 持有 UDP5006Gate 引用（Awake 注入或同 GameObject GetComponent）；ProcessSessionManifest 收到与当前不同的 session_id 时调 `_gate.ResetSession(newSessionId)`。会话级状态边界：同会话重连——_appliedEventIds 保留、不清；跨会话（新 manifest）——AckManager 可 Reset、回执队列 DiscardAll。

### R2-5 运行期 error 帧未分类

**事实**（transport.py 真实语义）：
- `CONTROL_ACK_CONNECTION_MISMATCH`（L294/L313）：ACK/回执来自非当前连接——世代错乱，**客户端必须主动关闭当前 socket 并走重连**；
- `CONTROL_ACK_NOT_PENDING`（L310）：重复回执/未知 event_id——**只记日志计数，不重连**；
- `CONTROL_ACK_REJECTED`（L179）/`CONTROL_ACK_TIMEOUT`（L182）：服务器侧拒绝/等 ACK 超时——日志可见即可，客户端无动作。

客户端 ProcessIncomingLine 现在对 error 帧无分类，JSON 解析失败也只发一次 TRANSPORT_FRAME_INVALID。

**改法**：error 帧按 error_code 分流：CONNECTION_MISMATCH → 关 socket + 按网络断开处理（进重连）；NOT_PENDING → LogWarning + 计数；未知 error_code → 日志 + 连续阈值降级（不直接重连）。JSON 解析失败同样计数，超阈值记 TRANSPORT_FRAME_INVALID 降级。

---

## 三、应修复（P1，round1 已提、代码中仍在）

| # | 问题 | 位置 | 改法 |
|---|------|------|------|
| R2-6 | SessionMirror `mpos is int mp` 永不匹配（JsonReader.ReadNumber 整数返回 long），ModulePosition 恒为 0；EditMode 断言 ModulePosition==0 与 bug 兼容 | SessionMirror.cs L172 | 改 `is long mp`（或经 GetInt 转换）；EditMode 对应用例改为 fixture 给 module_position=1、断言透传为 1 |
| R2-7 | UDP 仍绑 `IPAddress.Any` | UDP5006Gate.cs L258 | 改 `IPAddress.Loopback`；地址做成可配置字段，默认 Loopback |
| R2-8 | 时钟混用：AckManager（L84）/RenderReceiptManager（L84）默认 nowNs 仍是 DateTime.UtcNow 墙钟；client 已有 Stopwatch 工具（L805-811）但 Awake new 时未注入；received_ns 在主线程处理时取而非接收线程入队时 | AckManager.cs L84、RenderReceiptManager.cs L84、client Awake 与入队处 | 两个 Manager 构造时注入 client 的 Stopwatch 时钟；received_monotonic_ns 在接收线程读到整行的瞬间戳记、随队列项携带，禁止主线程补取 |
| R2-9 | 控制事件 session_id 不校验（ProcessControlEvent 用 mirror 快照 sessionId） | ProcessControlEvent | 事件自带 session_id 与当前会话不符 → 不 apply、回 rejected、日志计数 |
| R2-10 | `TcpClient.Connect` 同步阻塞无超时 | ReliableControlClient.cs L405 | 改 BeginConnect + WaitOne(timeout) 或 ConnectAsync.Wait(ms)，超时按可重试异常走退避 |
| R2-11 | DequeueNext 与 DequeueAndDispatch 两套出队并存 | ReliableControlClient | 删一套，单一出队入口 |
| R2-12 | clock_offset_ns / sync_uncertainty_ns 收到后不使用 | welcome/握手处理 | 暴露为属性；sync_uncertainty_ns > 50ms（合同健康门槛）日志告警 |
| R2-13 | TCP 入站帧无 schema_version=="2.2" 门禁 | ProcessIncomingLine | 业务帧 schema_version 缺失/≠2.2 → 拒绝处理并计数（welcome/error 帧按各自类型另行处理） |
| R2-14 | 测试服务器逐字节 `sb.Append((char)b)` 拼 UTF8（多字节字符必坏，现 fixture 全 ASCII 侥幸）；DropClient 只置标志不真关连接 | U01PlayModeTests.cs L114-126 | 用 List<byte>/MemoryStream 攒字节，按 '\n' 切包后整体 Encoding.UTF8 解码；DropClient 真正 Close socket，删掉反射 ForceClose 绕过 |

---

## 四、证据与收尾

1. **render_receipt 探针证据路径**：回执 Complete 依赖视觉层调 ConfirmRendered/Skipped/Failed。U01 探针独立运行、不接视觉层时回执产出为 0，验收证据日志里 render_receipt 计数会是零。加 dev 钩子：runtime_mode 为 dev_mock/dev_replay 时，控制事件 apply 后自动 ConfirmRendered；正式模式（formal_*）不自动确认。PlayMode 现有回执用例不受影响。
2. **frame_seq 链路核对**：render_receipt.frame_seq 必须等于所回执控制事件携带的 frame_seq。RenderReceiptManager L260 用的是 `tracked.FrameSeq`——逐行核对 RegisterEvent 调用点，确认传入的是事件 frame_seq 而非本地自增计数。另按 schema 核对 render_receipt 12 个 required 字段：`schema_version, message_type, receipt_id, session_id, event_id, frame_seq, unity_frame, rendered_monotonic_ns, module_id, segment, result, error_code`；result enum 仅 `rendered/skipped/failed`。
3. **U01_TASK_PLAN.md 移出 Assets**：`Assets/U01/U01_TASK_PLAN.md`（含 .meta）是自拟计划，Unity 会导入 Assets 下一切文件；移到 work/ 或任务包目录，Assets/U01 下只留 Runtime/ 与 Tests/。
4. **git 收尾清单**（全部修完、三审通过后执行）：
   - `git add Assets/U01/` 全部代码与 meta，**特别补 `Assets/U01.meta`**（U01 文件夹 meta 现在漏在 commit 外，他人 clone 后文件夹 GUID 会重新生成）；
   - 不 add：`*.csproj`、`*.sln`、`SRP-Weather-Visual.slnx`；在仓库根 `.gitignore` 追加一行 `*.slnx`（csproj/sln 规则已有）；
   - `work/u01_self_review_round2.md` 可提交留痕；但按 AGENTS.md 还必须补 **work/codex-verification-log.md 的 U01 验证记录**（目前 verification-log 中 U01 记录为 0 条，blackboard 已有 43 行）；
   - **push 等 Grip 三审通过后再做**，TASK.md 回填同理。
5. **自审纪律**：本轮自审把 P1-1~P1-11 全标 ✅，实际 P1-1/3/4/6/7/8/9/10 未改（行号见上表）。以后自审每条必须贴"改后代码行号+代码片段"作为证据，不许只勾状态；有异议写 blackboard 讨论，不许跳过。

---

## 五、修复与自检顺序

1. 先修 **R2-1**（fixture 补 5 字段 + Gate 补 2 字段）→ Unity 跑 PlayMode `AC1_TelemetryOrdering`，必须转绿；
2. 再修 **R2-2、R2-3** → 跑 AC3 全部用例（含加强后的重连断言、回执单次断言）；
3. 然后 R2-4、R2-5 与第三节 P1 表逐项改；
4. EditMode + PlayMode 全绿后：Test Runner 结果截图、git log、改动文件清单写入 blackboard，通知黄彬转告 Grip 做第 3 轮审查；
5. 三审通过 → push → 回填 TASK.md → 第二人复核（傅钧烨）。
