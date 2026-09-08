# U-01 第三轮审查指导单（三审）

审查基准：runtime-contract-v2.2.schema.json + 服务器真实实现（srp_session_core/transport.py、core.py、generate_golden_trace.py）。
当前 HEAD：cd3b7cc（分支 codex/u-01-reliable-control）。

---

## 一、三审结论

R2-1 ~ R2-14 经逐行复核，**13 项确认修复为真**（R2-1/2/3/4/5/6/8/9/10/11/12/13/14），git 收尾（U01.meta、*.slnx、TASK_PLAN 移出 Assets、status 干净）也都到位。

**一处澄清（不用改）**：R2-7（UDP 绑定地址）**实际已修好**——UDP5006Gate.cs L68 `_bindAddress = "127.0.0.1"`、L142 绑定用的就是它；L231 的 `IPAddress.Any` 是 `UdpClient.Receive(ref remoteEp)` 的**对端地址出参**，UDP 接收 API 本就该这么写，不是绑定点。服务器侧 transport.py 也强制 `NON_LOOPBACK_TARGET_FORBIDDEN`。此条关闭，是审查方误判。

但三审发现 **3 个真问题**（2 个 P0、1 个 P1）和 3 个观察项。其中两个 P0 是前两轮没覆盖到的链路缺口：**回执端到端在测试里零覆盖、fixture 遥测帧违反 schema oneOf**。

---

## 二、必须修复（P0/P1）

### R3-1（P0）dev 模式自动确认钩子缺失 → 回执链路零证据

**事实**：
- 全 client 代码无 dev_mock / dev_replay 自动确认逻辑（grep 零命中）。
- PlayMode 测试中 `ConfirmRendered` / `ConfirmRenderSkipped` **一次都没有被调用**；mock 服务器的 `_receiptIdCounts`（TrackReceiptId）在端到端流程里永远是空的——AC3 用例只是直接 new RenderReceiptManager 做单元级 CompleteFailed，没有"控制事件 → 回执产出 → 服务器收到"的完整链路验证。
- 后果：dev_mock/dev_replay 探针会话里，视觉层（U-02 尚未实现）不调 ConfirmRendered，**渲染回执永远不产出**，U-01 的核心验收对象（回执可靠回传）没有任何运行证据；正式 manifest 又禁用 Mock，探针阶段根本跑不通。

**改法**（ReliableControlClient.cs ProcessControlEvent，约 L870-896，applied ACK 发送、RegisterEvent 之后）：

```csharp
// DEV-only auto-confirm: in dev_mock/dev_replay there is no real visual
// layer (U-02) to call ConfirmRendered. Simulate successful render so
// render receipts flow end-to-end. Formal modes MUST NOT auto-confirm.
if (evt.event_type == "segment")
{
    var snap = _sessionMirror?.Snapshot;
    string mode = snap?.RuntimeMode ?? "";
    if (mode == "dev_mock" || mode == "dev_replay")
    {
        ConfirmRendered(evt.event_id);
    }
}
```

- SessionMirror.Snapshot 若未暴露 RuntimeMode，补上（manifest 与 telemetry 帧里都有 runtime_mode，snapshot 本就该带）。
- **formal_level_c / formal_stage_1 / formal_stage_3 绝对不许触发自动确认**，加注释写明正式模式由视觉层真实渲染回调驱动。
- 钩子只对 `segment` 事件（原因见 R3-3）。

**测试要求**（U01PlayModeTests.cs，新增端到端用例）：
- 用 dev_replay 模式 manifest 走完整握手 → mock 服务器下发一个 `segment` 控制事件 → 等待若干帧 → 断言 mock 服务器 `ReceiptIdCount >= 1`、`DuplicateReceiptCount == 0`、收到的 render_receipt 中 `result == "rendered"` 且 `event_id` 与所发事件一致。
- 复用现有 TrackReceiptId 统计，不要新造计数。

### R3-2（P0）PlayMode fixture 遥测帧违反 schema oneOf

**事实**：U01PlayModeTests.cs 的 TelemetryFrameJson（约 L418-439）里：
- `target_cycle_index = null, target_step_id = null`，但 `target_phase = "hold", target_progress = 0.4`；
- `actual_cycle_index = null, actual_step_id = null`，但 `actual_phase = "inhale", actual_progress = 0.35`。

schema telemetry_frame 的 allOf oneOf（约 L855-912）规定步骤字段二选一：
- null 组：cycle_index=null + step_id=null + **phase="none" + progress=0**；
- 活动组：cycle_index 为 integer≥0 + step_id 为 string（且 storm 模块 step_id 只能是 inhale_1/hold_1/exhale_1/hold_2，step→phase 有一致性 if/then：hold_1→hold、inhale_1→inhale）。

Unity 侧 Gate 只查 required 字段、不做 oneOf 校验，所以这个帧在 Unity 测试里能过 Gate；但**真实服务器 transport.py L450 `validate_message("telemetry_frame", frame)` 会直接 schema 拒绝**，golden trace 对接必炸。测试证据帧不合规 = 证据无效。

**改法**（呼吸闭环帧本就该带步骤，填活动组）：

```csharp
["target_cycle_index"] = 0,
["target_step_id"]    = "hold_1",     // 与 target_phase="hold" 一致
["actual_cycle_index"] = 0,
["actual_step_id"]    = "inhale_1",   // 与 actual_phase="inhale" 一致
```

phase/progress 保持现值。改完对照 schema L855-1000 自查 oneOf 与 step↔phase 一致性。

### R3-3（P1）回执注册范围过宽，与服务器验收规则不对齐

**事实**：client L884-886 对 `module / segment / start / prepare` 四类事件都 RegisterEvent。但服务器 core.py `_confirm_receipt`（L638-643）明确：

```python
if control["event_type"] != "segment":
    audit = ... "rejected", "RENDER_RECEIPT_CONTROL_TYPE_INVALID"
```

即**只有 segment 事件的回执会被服务器接受**；prepare/start/module 的回执一律 rejected（仅审计记录，不致命但属垃圾流量）。另外 core.py L660-663：segment 回执 `result != "rendered"` 会直接 `transport_failure`（会话判失败）——skipped/failed 对 segment 是致命语义。

**改法**：
1. L884 注册条件收窄为仅 `evt.event_type == "segment"`。
2. ConfirmRenderSkipped / ConfirmRenderFailed 的注释写清合同语义：仅适用于 segment 事件；skipped/failed 回执会被服务器判为会话失败；pause/abort/prepare/start/module/end 事件**不发任何回执**（pending 到会话结束由 DiscardAll 清理即可）。
3. R3-1 的 dev 钩子同样只碰 segment（已写明）。

---

## 三、观察项（不阻塞本轮收尾，记入 blackboard，下轮处理）

- **R3-4（P2）回执 frame_seq 本地自增**：RenderReceiptManager L100/L228 用 `Interlocked.Increment(_nextFrameSeq)`。经核实服务器 core **不校验** frame_seq（schema 只要求 integer≥0），故不违规；但黄金轨迹 generate_golden_trace.py L112 的惯例是 `frame_seq = control_seq`。建议 L100 RegisterEvent 直接用 `evt.control_seq`（ControlEvent 已解析该字段，client L1099），ad-hoc 路径保留本地计数器。一行改动，顺手就改。
- **R3-5（P2）received_monotonic_ns 在主线程取**：client L850  ProcessControlEvent 里取时间戳，注释自认 ideally from receive thread。应在 L547 接收线程入队时戳记（入队结构带时间戳）。当前同属 Stopwatch 单调时钟域，偏差仅排队延迟，不阻塞。
- **R3-6（P2）反射 helper 残留**：U01PlayModeTests.cs L485-490 ForceCloseTcpClient 反射、L900 调用点仍在。R2-14 已让 DropClient 真正 Close 连接，反射绕过应删除，测试直接用 DropClient。

---

## 四、收尾要求（本轮必须全部完成）

1. 修复 R3-1 ~ R3-3，R3-4 顺手改；R3-5/R3-6 可记 blackboard 下轮，但 R3-6 删反射 helper 只是顺手，建议一起删。
2. 三个 DLL 编译零错误；**EditMode + PlayMode 全部跑绿**，新端到端回执用例必须是真断言（不是只跑不 assert）。
3. **补 work/codex-verification-log.md 的 U-01 验证记录**（第二轮就要求了，至今缺失）：测试环境、Unity 版本、EditMode/PlayMode pass/fail 数、用例清单、手动验证项。
4. 更新 work/codex-blackboard.md：三审结论、R3-1~R3-6 处置。
5. commit 到当前分支（**先不要 push**，等复核）；git status 只允许任务相关文件。
6. 自审报告纪律：每条修复贴**文件+行号+改动摘要**，不许只写"已修复"；上轮自审文件标⚠️、对我报✅的事不许再发生。

修完后把 commit hash、测试 pass/fail 数字发出来，我做终审，全绿后再安排 push 和第二人复核。
