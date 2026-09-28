# U-01【Unity】可靠控制技术探针与渲染回执

## 责任与状态

- 注册表状态：DONE；原执行人Codex，分支codex/u-01-unity-control。
- 原第二人傅钧烨，2026-09-07 +08:00签收；候选6c09f71d14bcb0288a4b83f87b177975c49bfe3d，签收提交aab416cbbcea542f6d43a3c6e0e03e48fb258445。
- 本轮由Codex规范化执行入口和复测，不重新签收，不改变原验收范围。

## 完成标准

原包约4人日。AC1：丢包、乱序、重复fixture及重连通过，同一控制重发保持事件ID。AC2：旧帧不覆盖，Unity本地时钟不推进模块。AC3：错误握手、断连、重连和回执拒绝按合同失败关闭。

本轮要求统一执行入口，生成新证据不覆盖历史原件，当前使用说明与P-01/P-02/F-05边界一致，并生成逐包与串联Word。

## 固定过程

1. 读取inputs/sources.json列出的注册、签署、合同、实现和历史证据。
2. 执行execution/verify.ps1，分别跑Unity EditMode、PlayMode和证据生成；新结果进入evidence/runtime。
3. 使用已迁移verify_u01.py校验新旧证据；核对控制、ACK、回执和镜像轨迹的实际内容。
4. 核对P-01时钟权威、P-02回执记录与U-02渲染确认，先修正outputs/current-control-contract.md，再更新outputs/summary.json。
5. 使用agent/tools/build_task_reviews.py生成human/tasks/U-01/summary.docx及项目串联Word，逐页检查后明确路径提交推送。

## 文件归属与接口

inputs只放来源；execution放主机验证入口；evidence放本轮结果；outputs放当前合同说明和结构化总结；archive记录历史原件及保留理由。

Unity Runtime、Editor和Tests属于共享Unity工程，按程序集目录保留，最终工程迁移时整体移动，不能把Editor脚本拆离Assets导致程序集失效。旧evidence目录中的验证脚本已迁入execution，无转发副本；五份已签收证据原件保留。

运行组件为SRP.U01.U01RuntimeBridge；Python发TCP 5010控制，Unity回ACK/渲染回执并接收UDP 5006。消费v2.2显式步骤身份，禁止从进度推断步骤。渲染完成由适配器显式ConfirmRendered，不以ACK或golden回执证明实际画面。

## 技能与学习材料

C#、Unity生命周期、程序集、Edit/Play测试和TCP/UDP。中文资料统一消费项目08_任务技能与国内学习资料_v1.0.md中的L-UNITY、L-UNITYTEST；[Unity中文学习入口](https://learn.u3d.cn/)与[微软中文TcpClient文档](https://learn.microsoft.com/zh-cn/dotnet/api/system.net.sockets.tcpclient)用于实现查阅。

## 交接

上游F-01/F-05、F-03、P-01；P-02记录真实收到的消息。下游U-02/U-03实现实际呈现与确认，U12-11/P-01冻结并接入核心前教学，I-01验证真实设备全链。既有技术探针通过不关闭这些下游事项。
