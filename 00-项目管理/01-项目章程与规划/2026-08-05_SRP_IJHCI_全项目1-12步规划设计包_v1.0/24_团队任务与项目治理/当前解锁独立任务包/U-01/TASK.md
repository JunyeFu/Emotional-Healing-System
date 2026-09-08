# U-01 【Unity】可靠控制技术探针与渲染回执

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：黄彬（Jesu）
- 分支：`codex/u-01-reliable-control`
- 第二复核人：傅钧烨
- 领取时间：2026-09-07

## 任务边界

- 领域：Unity
- 波次：W1
- 状态：`IN_REVIEW`
- 类型：FIXED
- 预计工作量：4人日
- 前置依赖：F-01、F-03、F-05、P-01
- 所需技能：Unity+C#+TCP/UDP+状态镜像+幂等
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-UNITY Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)
- [L-UNITYTEST Unity Test Framework中文手册](https://docs.unity3d.com/cn/2023.2/Manual/testing-editortestsrunner.html)

## 交付物

- SessionMirror
- 可靠控制客户端
- UDP5006接收门
- ACK
- 渲染回执
- 重连与故障注入

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [x] AC1丢包乱序重复fixture测试通过且控制重发保持同一事件ID
- [x] AC2旧帧不覆盖新帧且Unity本地时钟不推进模块
- [x] AC3握手错误断连重连和回执拒绝均按合同失败关闭

## 必需证据

- [x] Edit/Play测试
- [x] 网络故障日志
- [x] 状态镜像轨迹
- [x] ACK与渲染回执序列

## 完成条件

合同版本与F-01和F-05一致且消费已签收P-01传输输出并向U-03交付技术探针

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：`Assets/U01/Runtime/`（ReliableControlClient/SessionMirror/UDP5006Gate/AckManager/RenderReceiptManager/ReconnectHandler/ContractMessages）、`Assets/U01/Tests/EditMode/U01EditModeTests.cs`、`Assets/U01/Tests/PlayMode/U01PlayModeTests.cs`、`work/codex-blackboard.md`、`work/codex-verification-log.md`
- 验证命令与结果：Unity 6000.4.9f1 Test Runner（Unity Hub GUI）。EditMode Run All：85/85 passed。PlayMode Run All 三轮实测：5/9（16:04，195.66s）→ 8/9（16:20）→ 9/9（16.6s，最终全绿）。AC1/AC2/AC3 全部通过；结果文件 `C:\Users\15744\AppData\LocalLow\DefaultCompany\SRP-Weather-Visual\TestResults.xml`（2026-09-08T08:21Z，9 total/9 passed/0 failed）。
- 证据路径：TestResults.xml（上述路径）；review 记录 `D:\Coze\SRP\U01_review_round1.md` ~ `round7.md`；验证日志 `work/codex-verification-log.md` 2026-09-08 U-01 entry。
- commit：`9be3b0ce6496b4b832b0a1472064479b9127cf1c`（U01 R7: fix reconnect thread-safety + PlayMode test corrections; 9/9 green）；历史：`e55b810`、`42491a4`、`d1bf8b8`、`f681138`、`059b247`
- push目标：`origin/codex/u-01-reliable-control`（push 待用户确认后执行）
- 剩余风险：①`Assets/_Recovery/0 (4).unity`+`.meta` 为 Unity 崩溃恢复垃圾，未提交、待授权删除；②LoopbackTcpServer finally 竞态与 client L26-30 遗留段为静态遗留，不阻塞；③CLI 中文路径编码 bug 未修，测试需 Hub 手动触发；④DONE 需第二人（傅钧烨）复核签收。
