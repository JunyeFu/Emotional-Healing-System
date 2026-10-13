# 单窗口连续实验工作台：原生验证

日期：2026-10-08。候选：`T01_Workbench_A.flow-v5.candidate.toe`。

这是TouchDesigner实际面板截图，不是AI预览图。打开候选时保留同目录的`development-workflow/`，历史索引使用相对路径。目录内三场记录均为合成开发数据。

## 查看顺序

- [主页面](34-return-home.png)：新建准备、完成/中止计数、历史入口。
- [准备](02-1-ready.png)和[等待Unity](04-1-waiting.png)：曲线可查看，实验记录尚未开始。
- [监控](05-1-running.png)和[暂停](07-paused.png)：有效时间与总历时分开。
- [收尾](13-1-closeout-ready.png)：封存和后测回执齐备后，才能准备下一场。
- [历史列表](31-history.png)：同一窗口查看，不改变当前实验阶段。

## 验证结果

同一TD进程完成35次原生页面检查、3场连续模拟实验，其中2场正常完成、1场中止。三场文件独立，准备期实验记录为0；暂停期间有效时间冻结，但数据仍连续写入。下一场清空前场会话、曲线和计时，不重启接收器。主机相关测试92项通过。

截图实际尺寸为1280×720；另外检查了1600×900和1920×1080布局，不把截图称为这两种尺寸的原生输出。

复核命令：

```powershell
py -3.14 -X utf8 agent/tasks/T-01/execution/verify_flow_capture.py agent/tasks/T-01/evidence/flow-v5-20261008-162555
```

当前控制回执来自模拟桥。真实Unity、SessionCore、P-02、问卷与活动准入桥尚未接入此界面；本证据不代表正式实验或真实设备联调通过。任务状态及原签收不变。

设计和消息说明见[工作流设计](../../design/workbench-flow-v5.md)。
