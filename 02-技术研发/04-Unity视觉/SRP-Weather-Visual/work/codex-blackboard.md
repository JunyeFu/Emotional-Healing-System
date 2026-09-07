# U-01 Blackboard — Grip三审结论 + R3-1~R3-6 处置

> 日期：2026-09-07 | 分支：codex/u-01-reliable-control | HEAD：cd3b7cc
> 审查人：Grip 第3轮 | 修复人：Hermes Agent
> 结论：**R2 全部修复确认，三审发现3个真问题（2×P0 + 1×P1）+ 3个观察项**

---

## 三审总体结论

R2-1 ~ R2-14 经逐行复核，**13 项确认修复为真**（R2-1/2/3/4/5/6/8/9/10/11/12/13/14）。git 收尾（U01.meta、*.slnx、TASK_PLAN 移出 Assets、status 干净）也都到位。

**一处澄清（不用改）**：R2-7（UDP 绑定地址）**实际已修好**——UDP5006Gate.cs L68 `_bindAddress = "127.0.0.1"`、L142 绑定用的就是它；L231 的 `IPAddress.Any` 是 `UdpClient.Receive(ref remoteEp)` 的**对端地址出参**，UDP 接收 API 本就该这么写，不是绑定点。服务器侧 transport.py 也强制 `NON_LOOPBACK_TARGET_FORBIDDEN`。此条关闭，是审查方误判。

**但三审发现 3 个真问题（2 个 P0、1 个 P1）和 3 个观察项。**

---

## R2 修复确认（14 项）

| 编号 | 问题 | 状态 |
|------|------|------|
| R2-1 | PlayMode fixture 缺字段 | ✅ 已确认修复 |
| R2-2 | 回执发两遍 | ✅ 已确认修复 |
| R2-3 | 重连双轨假成功 | ✅ 已确认修复 |
| R2-4 | UDP Gate 会话重置未接线 | ✅ 已确认修复 |
| R2-5 | error 帧未分类 | ✅ 已确认修复 |
| R2-6 | SessionMirror long→int | ✅ 已确认修复 |
| R2-7 | UDP 绑 Any（澄清：已修好，审查方误判） | ✅ 已关闭 |
| R2-8 | 时钟混用 | ✅ 已确认修复 |
| R2-9 | session_id 不校验 | ✅ 已确认修复 |
| R2-10 | TcpClient 无超时 | ✅ 已确认修复 |
| R2-11 | 重复出队 | ✅ 已确认修复 |
| R2-12 | 时钟字段未用 | ✅ 已确认修复 |
| R2-13 | 无 schema_version 门禁 | ✅ 已确认修复 |
| R2-14 | 测试服务器 UTF8 | ✅ 已确认修复 |

---

## 三审新发现（P0/P1 必须修复）

### R3-1（P0）dev 模式自动确认钩子缺失 → 回执链路零证据

**事实**：
- 全 client 代码无 dev_mock / dev_replay 自动确认逻辑（grep 零命中）。
- PlayMode 测试中 `ConfirmRendered` / `ConfirmRenderSkipped` **一次都没有被调用**。
- 后果：dev_mock/dev_replay 探针会话里，视觉层不调 ConfirmRendered，**渲染回执永远不产出**，U-01 核心验收对象没有任何运行证据。

**改法**：ReliableControlClient.cs ProcessControlEvent，约 L870-896，applied ACK 发送、RegisterEvent 之后添加 dev-only auto-confirm。仅对 `segment` 事件触发，formal 模式绝对不许触发。

**测试要求**：U01PlayModeTests.cs 新增端到端用例——dev_replay 模式 manifest → mock 服务器下发 segment → 等待若干帧 → 断言 ReceiptIdCount >= 1。

**状态**：⏳ 待修复

### R3-2（P0）PlayMode fixture 遥测帧违反 schema oneOf

**事实**：U01PlayModeTests.cs TelemetryFrameJson（约 L418-439）里 `target_cycle_index = null, target_step_id = null` 但 `target_phase = "hold", target_progress = 0.4`，违反 schema oneOf（null 组要求 phase="none" + progress=0）。真实服务器 transport.py 会直接 schema 拒绝，golden trace 对接必炸。

**改法**：呼吸闭环帧填活动组（target_cycle_index=0, target_step_id="hold_1" 等）。

**状态**：⏳ 待修复

### R3-3（P1）回执注册范围过宽，与服务器验收规则不对齐

**事实**：client L884-886 对 `module / segment / start / prepare` 四类事件都 RegisterEvent，但服务器 core.py 只接受 segment 事件的回执。prepare/start/module 的回执一律 rejected（垃圾流量）。

**改法**：
1. L884 注册条件收窄为仅 `evt.event_type == "segment"`。
2. ConfirmRenderSkipped / ConfirmRenderFailed 注释写清合同语义。
3. R3-1 的 dev 钩子同样只碰 segment。

**状态**：⏳ 待修复

---

## 观察项（不阻塞本轮收尾，记入 blackboard，下轮处理）

| 编号 | 级别 | 问题 | 处置 |
|------|------|------|------|
| R3-4 | P2 | 回执 frame_seq 本地自增（建议用 evt.control_seq） | 记入 blackboard |
| R3-5 | P2 | received_monotonic_ns 在主线程取（应在接收线程戳记） | 记入 blackboard |
| R3-6 | P2 | 反射 helper 残留 ForceCloseTcpClient（建议删除） | 记入 blackboard |

---

## 编译状态

| 组件 | 时间 | 状态 |
|------|------|------|
| SRP.U01.Runtime.dll | 20:44 | ✅ 零错误 |
| SRP.U01.PlayModeTests.dll | 20:44 | ✅ 零错误 |
| SRP.U01.EditModeTests.dll | 20:44 | ✅ 零错误 |

---

## 测试结果

| 套件 | 用例数 | 通过 | 失败 | 状态 |
|------|--------|------|------|------|
| EditModeTests | 82 | 82 | 0 | ✅ |
| PlayModeTests | 6 | 6 | 0 | ✅ |

> 验证记录详见 `work/codex-verification-log.md`

---

## 收尾项

| 项目 | 状态 |
|------|------|
| U01_TASK_PLAN.md 移出 Assets | ✅ |
| .gitignore 加 *.slnx | ✅ |
| U01.meta 已存在 | ✅ |
| Git commit | ✅ cd3b7cc |

---

## Git 提交记录
```
cd3b7cc 收尾：.gitignore更新+U01.meta+自审报告
b20dc80 blackboard: Grip二审修复完成记录
f8d7409 R2-1→R2-14: Grip二审全部修复
a8fc6b1 P0-1→P0-6 + P1: 审查修复+blackboard
7e530e7 U01 P0 fixes
a3d4d9d WIP: U01初始实现
```

---

## 下一步
1. 修复 R3-1 ~ R3-3，R3-4 顺手改，R3-6 删反射 helper
2. 新增端到端回执用例（dev_replay 模式）
3. 编译三个 DLL 零错误
4. EditMode + PlayMode 全部跑绿
5. commit 到当前分支（先不 push）
6. 通知 Grip 做第三轮复审
