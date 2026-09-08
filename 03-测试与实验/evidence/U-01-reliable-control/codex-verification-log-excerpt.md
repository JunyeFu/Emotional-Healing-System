### 2026-09-08 U-01 Unity Reliable Control Probe And Render Receipt

| Field | Notes |
|---|---|
| Expected Observation | U-01 交付物（ReliableControlClient/SessionMirror/UDP5006Gate/AckManager/RenderReceiptManager/重连与故障注入）通过 EditMode 与 PlayMode 全部用例；AC1 重复/乱序/丢包 fixture、AC2 无控制事件不推进、AC3 握手拒绝/断连重连/回执拒绝全部按合同验证。 |
| Actual Result | HEAD `9be3b0c`：EditMode 85/85 passed；PlayMode 9/9 passed（16.6s）。PlayMode 三轮实测：第一轮 5/9（4 红三类根因：ReceiveLoop 后台线程调 UnityEngine.Random 致重连循环崩溃；AC1 断言期望值笔误；Formal 测试漏调 client.Connect() 且死等无超时）。修复后第二轮 8/9（AC3_Reconnect 断言时机早于重连握手完成，与 R2-3 语义不符）。测试语义修正后第三轮 9/9 全绿。生产代码仅 Random 线程安全一处修复，其余均为测试侧修正。 |
| Deviation / Surprise | CLI 无头测试两次静默失败（-projectPath 中文路径传参编码 bug，Hub 日志乱码实锤），最终经 Unity Hub GUI 手动执行；junction 绕行路径污染编译缓存触发 Safe Mode（106 个 ILPP pipe 错误），清除 Library\Bee+ScriptAssemblies 后恢复。AC3_Reconnect 首版测试假设 generation 在断连即递增，实际实现（R2-3 语义）为重连握手成功后递增，按实现语义修正测试断言时机。 |
| Verification Command | Unity 6000.4.9f1 Test Runner（Unity Hub GUI）：EditMode Run All（85/85）；PlayMode Run All 三轮（5/9→8/9→9/9，末轮 16.6s）。结果文件：`C:\Users\15744\AppData\LocalLow\DefaultCompany\SRP-Weather-Visual\TestResults.xml`（2026-09-08T08:21Z，9 total/9 passed/0 failed）。review 记录：`D:\Coze\SRP\U01_review_round1~7.md`。 |
| Residual Risk | `Assets/_Recovery/0 (4).unity` + `.meta` 为 Unity 强杀崩溃恢复垃圾，未提交、待授权删除；LoopbackTcpServer finally 竞态与 client L26-30 遗留段为静态遗留，不阻塞收尾；CLI 中文路径 bug 未修（测试需 Hub 手动触发）；DONE 需第二人（傅钧烨）复核签收。 |
