# U-01 验证记录（第六轮）

> 日期：2026-09-08 | 分支：codex/u-01-reliable-control | HEAD：（commit后填入）
> 审查人：Grip 第6轮 | 验证人：Hermes Agent

---

## 一、测试环境

| 项目 | 值 |
|------|-----|
| Unity 版本 | 6000.4.9f1 |
| 操作系统 | Windows 11 |
| .NET 运行时 | Mono（Unity Editor 内置） |
| 测试框架 | NUnit 3 + Unity Test Framework |
| Python 服务器 | srp_session_core（本地 loopback mock） |

---

## 二、测试结果总览

| 测试套件 | 用例数 | 通过 | 失败 | 跳过 | 状态 |
|----------|--------|------|------|------|------|
| SRP.U01.EditModeTests | 83 | — | — | — | 待亲跑确认 ⏳ |
| SRP.U01.PlayModeTests | 8 | — | — | — | 待亲跑确认 ⏳ |
| **合计** | **91** | — | — | — | **待亲跑确认 ⏳** |

> ⚠️ 本轮为代码修复，尚未在 Unity Test Runner 亲跑。数字为用例计数，非实测结果。

---

## 三、R5/R6 修复内容

### R5-1 AckManager 事件 Invoke 修复（P0）

| 事件 | 修复内容 | 行号 |
|------|----------|------|
| OnEventApplied | MarkApplied 内 HashSet.Add 返回值判断，新增时锁外 Invoke | AckManager.cs L75-81 |
| OnDuplicateIgnored | 新增 MarkDuplicate 方法，Invoke OnDuplicateIgnored | AckManager.cs L92-96 |
| OnEventRejected | 新增 MarkRejected 方法，Invoke OnEventRejected | AckManager.cs L98-102 |

### R5-2 _stream 类型修复（P0）

| 项目 | 修复内容 | 行号 |
|------|----------|------|
| 字段类型 | `NetworkStream _stream` → `System.IO.Stream _stream` | ReliableControlClient.cs L99 |
| 测试断言 | CONNECTION_MISMATCH 用例末尾断言 stream 已 Close | U01EditModeTests.cs L1426 |

### R5-3 FrameSeq 断言修复（P1）

| 项目 | 修复内容 | 行号 |
|------|----------|------|
| evt-001 | control_seq=1，断言 frame_seq==1 | U01EditModeTests.cs L798, L805 |
| evt-002 | control_seq=2，断言 frame_seq==2 | U01EditModeTests.cs L802, L806 |

### R6-1 MarkDuplicate 调用修复（P0）

| 项目 | 修复内容 | 行号 |
|------|----------|------|
| 客户端重复分支 | IsApplied==true 时调用 _ackManager.MarkDuplicate | ReliableControlClient.cs L863 |

### R6-2 OnDuplicateIgnored 测试（P2）

| 用例 | 覆盖 | 行号 |
|------|------|------|
| OnDuplicateIgnored_EventFires | 订阅事件 → MarkApplied → MarkDuplicate → 断言回调触发 | U01EditModeTests.cs L649-658 |

### R6-3 verification-log 更新

- HEAD 哈希：commit 后填入 git log -1 真实值
- EditMode 用例数：82 → 83（新增 OnDuplicateIgnored 测试）
- 总用例数：90 → 91
- PlayMode 状态：改为"待亲跑确认 ⏳"

---

## 四、编译状态

| 组件 | 时间 | 状态 |
|------|------|------|
| SRP.U01.Runtime.dll | 00:51 | ✅ 零错误 |
| SRP.U01.EditModeTests.dll | 00:51 | ✅ 零错误 |
| SRP.U01.PlayModeTests.dll | 00:51 | ✅ 零错误 |

---

## 五、收尾要求

1. Unity Test Runner 亲跑 EditMode（83）+ PlayMode（8），报真实数字
2. 更新本文件 HEAD 哈希和测试结果
3. commit 后通知 Grip 做终审确认
