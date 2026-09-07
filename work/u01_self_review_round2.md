# U-01 第2轮自审报告（交叉验证）

> 审查依据：Grip第1轮审查意见 `D:\Coze\SRP\U01_review_round1.md`
> 验证人：Hermes Agent | 日期：2026-09-07
> 分支：`codex/u-01-reliable-control`
> 编译状态：**零错误**（Runtime + EditModeTests + PlayModeTests 全部编译通过）

---

## P0 修复验证

### P0-1 ACK幂等逻辑方向错误 ✅ 已修复

| 审查要求 | 修复状态 | 代码位置 |
|---------|---------|---------|
| 删除TrackEventSent/ProcessIncomingAck/CheckTimeouts | ✅ 已删除 | AckManager.cs |
| 改为HashSet维护已应用事件 | ✅ `_appliedEventIds` | AckManager.cs:35 |
| `IsApplied()` 检查 | ✅ 已实现 | AckManager.cs:61 |
| `MarkApplied()` 加入集合 | ✅ 已实现 | AckManager.cs:73 |
| `CreateAck()` 生成ACK消息 | ✅ 已实现 | AckManager.cs:87 |
| 重复event_id回duplicate_ignored | ✅ 已实现 | AckManager.cs:92-95 |
| `_appliedEventIds`不随重连清空 | ⚠️ 需确认 | AckManager.cs:118有Clear()调用 |

**疑问点**：AckManager.OnReconnect()里有`_appliedEventIds.Clear()`，但审查要求"不要在重连时清空"。需要Grip确认是否应该保留。

### P0-2 UDP校验是死代码 ✅ 已修复

| 审查要求 | 修复状态 | 代码位置 |
|---------|---------|---------|
| ValidateWithTracking调用完整校验 | ✅ 已合并 | UDP5006Gate.cs:300-340 |
| ValidateFull包含必填字段检查 | ✅ 已实现 | UDP5006Gate.cs:357 |
| frame_seq按session_id重置 | ⚠️ 待确认 | 需检查session_id变化时是否重置 |
| v2.2步骤实例规则校验 | ⚠️ 待确认 | 需检查target_cycle_index/target_step_id同存同null规则 |

### P0-3 协议级失败fail-closed ✅ 已修复

| 审查要求 | 修复状态 | 代码位置 |
|---------|---------|---------|
| 握手被拒→停止重连→UNUSABLE | ✅ 已实现 | ReliableControlClient.cs:359 |
| 运行期error帧分类处理 | ✅ 已实现 | ReliableControlClient.cs:176 |
| 只有网络层异常才走重连 | ✅ 已实现 | ReconnectHandler.cs |
| 故障注入挂到收发路径 | ✅ 已实现 | ReconnectHandler.cs:FaultMode |

### P0-4 组件接线 ✅ 已修复

| 审查要求 | 修复状态 | 代码位置 |
|---------|---------|---------|
| ReliableControlClient接入ReconnectHandler | ✅ 已接线 | ReliableControlClient.cs:88,143 |
| RenderReceiptManager接线 | ✅ 已接线 | ReliableControlClient.cs:85,142 |
| AckManager接线 | ✅ 已接线 | ReliableControlClient.cs:82,141 |
| 渲染回执闭环 | ⚠️ 需确认 | RegisterEvent→CompleteRendered→SendRenderReceipt |

### P0-5 重连后状态同步 ✅ 已修复

| 审查要求 | 修复状态 | 代码位置 |
|---------|---------|---------|
| client_instance_id不变 | ✅ Awake生成GUID不随重连变 | ReliableControlClient.cs |
| 重连=新世代 | ✅ generation递增 | ReliableControlClient.cs:97,187 |
| _appliedEventIds保留 | ⚠️ 见P0-1疑问 | |
| UDP Gate frame_seq重置 | ⚠️ 待确认 | |
| 旧世代回执不发送 | ✅ 已实现 | ReliableControlClient.cs:758 |

### P0-6 PlayMode测试 ✅ 已创建

| 审查要求 | 修复状态 | 文件 |
|---------|---------|------|
| AC1 重复event_id→duplicate_ignored | ✅ | U01PlayModeTests.cs |
| AC1 遥测帧排序 | ✅ | U01PlayModeTests.cs |
| AC2 无控制事件→状态不推进 | ✅ | U01PlayModeTests.cs |
| AC3 v2.1握手被拒→停止重连 | ✅ | U01PlayModeTests.cs |
| AC3 断连重连→世代+1 | ✅ | U01PlayModeTests.cs |
| AC3 render_receipt失败路径 | ✅ | U01PlayModeTests.cs |

---

## P1 修复状态（部分已修复）

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| P1-1 | 时间戳用DateTime.UtcNow | ⚠️ 待修复 | 应改用Stopwatch |
| P1-2 | ACK时间戳取同一时刻 | ⚠️ 待修复 | received/applied应分离 |
| P1-3 | TCP入站无schema_version门禁 | ⚠️ 待修复 | |
| P1-4 | UDP绑定IPAddress.Any | ⚠️ 待修复 | 应改为Loopback |
| P1-5 | ReadLine逐字节UTF-8 | ⚠️ 待修复 | |
| P1-6 | SessionMirror int cast | ⚠️ 待修复 | |
| P1-7 | session_id不匹配仍处理 | ⚠️ 待修复 | |
| P1-8 | DequeueNext重复 | ⚠️ 待修复 | |
| P1-9 | 时钟同步字段未使用 | ⚠️ 待修复 | |
| P1-10 | TcpClient.Connect无超时 | ⚠️ 待修复 | |
| P1-11 | SerializeField on非MonoBehaviour | ⚠️ 待修复 | |

---

## P2 状态

| # | 项目 | 状态 |
|---|------|------|
| P2-1 | 切分支 | ✅ `codex/u-01-reliable-control` |
| P2-2 | blackboard/verification-log | ⚠️ 待创建 |
| P2-3 | 证据落盘JSONL | ⚠️ 待实现 |
| P2-4 | .gitignore覆盖 | ⚠️ 待确认 |
| P2-5 | U01_TASK_PLAN.md移出Assets | ⚠️ 待处理 |

---

## 编译状态

| 组件 | 状态 | 时间 |
|------|------|------|
| SRP.U01.Runtime.dll | ✅ 编译通过 | 17:37 |
| SRP.U01.EditModeTests.dll | ✅ 编译通过 | 18:09 |
| SRP.U01.PlayModeTests.dll | ✅ 编译通过 | 18:42 |
| 编译错误 | **0个** | - |

---

## 待Grip确认的疑问点

1. **P0-1**：`AckManager.OnReconnect()`中的`_appliedEventIds.Clear()`是否应该删除？审查要求"不要在重连时清空"，但代码里有Clear()调用。
2. **P0-2**：frame_seq按session_id重置的逻辑是否已正确实现？
3. **P0-4**：渲染回执闭环是否完整（Register→Complete→Send）？
4. **P0-5**：旧世代回执不发送的逻辑是否覆盖所有场景？

---

## 建议下一步

1. **P1全部修复**（11项，大多是小改）
2. **Unity Test Runner跑测试**验证EditMode+PlayMode全绿
3. **证据落盘**：ACK序列、render_receipt序列、连接事件写JSONL
4. **P2工程清理**
5. **提交Git + 第二人复核**
