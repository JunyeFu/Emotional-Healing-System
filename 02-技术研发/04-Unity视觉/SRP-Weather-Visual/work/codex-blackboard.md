# U-01 Blackboard — 代码审查修复记录

> 日期：2026-09-07 | 分支：codex/u-01-reliable-control
> 审查人：Grip 第1轮 | 修复人：Hermes Agent

## P0 修复完成

| 编号 | 问题 | 修复内容 | 状态 |
|------|------|----------|------|
| P0-1 | ACK逻辑方向错误 | AckManager反转为Unity侧：IsApplied/MarkApplied/CreateAck，_appliedEventIds跨重连保留 | ✅ |
| P0-2 | UDP校验死代码 | ValidateWithTracking调用完整校验ValidateFull，session_id→last_seq映射重置，步骤实例同存同null规则 | ✅ |
| P0-3 | fail-closed缺失 | UNUSABLE枚举+状态，握手被拒/协议错误→停止重连，_fatalError标记 | ✅ |
| P0-4 | 组件未接线 | ReliableControlClient集成AckManager+ReconnectHandler+RenderReceiptManager+SessionMirror | ✅ |
| P0-5 | 重连状态同步 | OnReconnected回调，_appliedEventIds跨重连保留，generation同步到Mirror | ✅ |
| P0-6 | PlayMode测试 | 6个端到端测试覆盖AC1/AC2/AC3，loopback假服务器 | ✅ |

## P1 修复

| 编号 | 问题 | 修复内容 | 状态 |
|------|------|----------|------|
| P1-1 | 时间戳用DateTime | 改为Stopwatch.GetTimestamp()（单调时钟） | ✅ |
| P1-2 | ACK时间戳相同 | received/applied分开赋值 | ✅ |
| P1-3 | TCP无schema校验 | ProcessLine增加schema_version检查 | ✅ |
| P1-4 | UDP绑Any | 改为IPAddress.Loopback | ✅ |
| P1-5 | ReadLine字节问题 | 用StreamReader.ReadLine()替代逐字节读取 | ✅ |
| P1-6 | int溢出 | Mirror用long存储序列号 | ✅ |
| P1-7 | session不匹配未拒 | ProcessControlEvent增加session_id校验 | ✅ |
| P1-8 | 重复Dequeue | ReliableControlClient移除重复方法 | ✅ |
| P1-9 | 时钟字段未用 | Mirror记录clock_offset_ns/clock_drift_ppm | ✅ |
| P1-10 | TcpClient无超时 | 增加ConnectTimeout参数 | ✅ |
| P1-11 | SerializeField误用 | 移除非MonoBehaviour上的SerializeField | ✅ |

## 编译状态

- SRP.U01.Runtime.dll ✅ 零错误
- SRP.U01.EditModeTests.dll ✅ 零错误
- SRP.U01.PlayModeTests.dll ✅ 零错误

## 待办

- [ ] Unity Test Runner 运行全部测试
- [ ] PlayMode假会话跑出证据日志
- [ ] 第二人复核
