# U-01 第 6 轮指导单（R5 修复复核·差一处接线）

EditMode 亲跑 85 全绿已确认（黄彬截图）。R5-2 / R5-3 复核通过；R5-1 修了一半，差最后一处。

## R6-1（P0）：MarkDuplicate 写了但没人调用——OnDuplicateIgnored 仍是死事件

- `AckManager.MarkDuplicate`（AckManager.cs L92-95）已正确实现 `OnDuplicateIgnored?.Invoke(eventId)`；
- 但 `ReliableControlClient.ProcessControlEvent` 的重复分支（L859-867：`if (_ackManager.IsApplied(evt.event_id))` → CreateAck(duplicate_ignored) → SendAck → return）**全程没有调用 `MarkDuplicate`**。
- 结果：生产环境重复事件路径下 OnDuplicateIgnored 永不触发——和 R5-1 修掉的是同一类"声明了不触发"死事件问题。
- **修法（1 行）**：在 L860 重复分支内、SendAck(dupAck) 前后均可，加：
  ```csharp
  _ackManager.MarkDuplicate(evt.event_id);
  ```
- MarkRejected 保持现状（无 reject 发送路径，已注释保留，不编造调用点）。

## R6-2（P1）：补一个 EditMode 用例锁死这条接线

死事件已经栽过两次（OnEventApplied、OnDuplicateIgnored），加个回归测试防第三次：

- 在 R25 测试类（已有 InjectLine 反射 harness 和 _client）里加用例：
  1. 订阅 `_client.AckMgr.OnDuplicateIgnored`（client L154 暴露 `AckMgr`），记录回调 event_id；
  2. 用 TestHelpers 构造一条合法 control_event JSON（message_type=control_event、**schema_version="2.2"**、带 event_id/control_seq/event_type/issued_monotonic_ns 等必填字段），InjectLine 两次；
  3. 断言第二次注入后回调收到该 event_id（第一次不触发）；
  4. 注意：测试内 _stream 为 null 时 SendAck 空安全（L580 判 CanWrite），不用注入 stream。
- 加完后 EditMode 用例总数变为 **83**（U01 合计 91=EditMode 83 + PlayMode 8），verification-log 数字同步改。

## R6-3：verification-log 两处收尾

1. **PlayMode "8 全绿"目前无亲跑证据**——黄彬只跑过 EditMode。在黄彬亲跑 PlayMode 截图确认前，把 PlayMode 结果改为"待黄彬亲跑确认 ⏳"，不许写全绿；
2. R6-1/R6-2 提交后，L2/L9 的 HEAD 哈希更新为**最终 tip 的完整短哈希**（git log -1 --format=%h），别再抄错。

## 收尾

- 一个 commit 包 R6-1 + R6-2 + R6-3，报 commit hash；
- **不要 push**；
- 之后黄彬会亲跑：EditMode（应为 86：U01 83 + F03 3）和 PlayMode（8）两个 tab 各 Run All 截图，两边全绿才放行。
