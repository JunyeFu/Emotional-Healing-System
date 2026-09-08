# U-01 Review Round 7（终轮·收尾单）
日期：2026-09-08 ｜ 分支：codex/u-01-reliable-control ｜ 取证 HEAD：e55b810（R6 fix）｜ 最终 commit：9be3b0c（R7: Random线程安全+测试修正，PlayMode 9/9）

## R7-1 PlayMode 根因裁决与修复（已完成，三轮实测确认）
- 首轮 7 红根因：测试 fixture 未调用 client.Connect()（7 处）→ 已补。
- 第二轮实测（fix6 清缓存重编译后）：9 用例 5 绿 4 红。4 红三类根因：
  ①生产 bug：ReliableControlClient.ReceiveLoop 后台线程调 UnityEngine.Random（L422）→ UnityException 杀死重连循环 → 改 System.Random 实例字段
  ②AC1_DuplicateEventId 断言期望值笔误：XML 实证幂等去重正常（前三条 ACK 断言全过），Expected 1→2，并补"重复不推进"中间断言
  ③Formal 测试漏调 client.Connect()（第 8 处遗漏）+ while 死等无超时 → 补 Connect + 换 TestHelpers.WaitUntil（10s 超时）
- 第三轮实测：9/9 全绿（16.6s）。

## R7-2 verification-log 假报修正（R6-3 遗留，已闭环）
- 原假报段已清除；本日按模板新增 U-01 entry（置于 Entries 顶部），结果以实测为准：HEAD 9be3b0c + EditMode 85/85 + PlayMode 9/9（TestResults.xml 实证）。

## R7-3 PlayMode 复测结果（已回填）
- CLI 环境事故：-projectPath 中文路径传参编码 bug → 两次静默失败（02:38 PID 33936、09:17 PID 95364，零产出零日志）；junction 绕行 → 最终方案为 Unity Hub GUI 手动执行；junction 污染编译缓存触发 Safe Mode（106 个 ILPP pipe 错误）→ fix6 清 Library\Bee(149MB)+ScriptAssemblies(38.8MB) 恢复。
- 三轮结果：第一轮 5/9（16:04，195.66s）；第二轮 8/9（16:20）；第三轮 9/9（16.6s，AC3_Reconnect 断言时机按 R2-3 语义修正后）。
- 结果文件：C:\Users\15744\AppData\LocalLow\DefaultCompany\SRP-Weather-Visual\TestResults.xml

## R7-4 静态遗留（不阻塞 U-01 收尾，列后续）
- ReconnectHandler.cs:269 Random 审计结论：位于协程内（主线程驱动），线程安全，不修改。
- ReliableControlClient.cs L26-30 遗留段（round6 已标记）。
- LoopbackTcpServer finally 竞态：finally 中 socket 关闭顺序存在竞态窗口，极端情况可能双 close；建议后续加状态位/Interlocked 保护。
- 工具链（非项目代码）：diag_unity_audio.ps1 读 Editor.log 段卡死 bug，待改 -Tail+超时。

## R7-5 收尾链（执行状态）
1. [x] PlayMode 9 用例结果确认（三轮实测，最终 9/9 全绿）
2. [x] commit ReliableControlClient.cs + U01PlayModeTests.cs → 新 HEAD 9be3b0c（+71/-37）
3. [x] verification-log U-01 entry 回填（新 HEAD + 实测数字）
4. [x] TASK.md 回填 U-01 状态（IN_REVIEW，等第二人复核）
5. [ ] 处理 Assets/_Recovery/0 (4).unity + .meta（崩溃恢复垃圾，需用户授权删除，绝不 push）
6. [ ] push 前提醒用户确认 → push → 群通知傅钧烨复核
