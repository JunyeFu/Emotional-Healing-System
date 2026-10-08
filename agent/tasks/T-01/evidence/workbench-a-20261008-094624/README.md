# A主题工作台实际截图

2026-10-08在TouchDesigner 2025.32820中运行现有A主题构建器，通过原生OP Viewer TOP保存画面，不是AI预览图。源工程为`agent/tasks/T-01/evidence/runtime/T01_ReadableBaseline.candidate.toe`，只操作隔离副本，原件未覆盖。

| 文件 | 实际内容与检查结果 |
| --- | --- |
| [总览](02-overview-replay.png) | 开发回放、目标与实际步骤、SQI、接收统计；可读，部分长标签省略 |
| [链路与时钟](03-link-and-clock.png) | 原单位字段、步骤与会话身份；长列表使用滚动容器 |
| [事件与审计](04-events-and-audit.png) | 如实显示“请求与审计通道未接入”，没有伪造事件或ACK |
| [1280布局](05-overview-1280.png) | 已实际渲染，但底部统计需滚动，未通过全页无遮挡验收 |
| [启动瞬间](01-overview-waiting.png) | 仅容器背景，文字尚未出现；保留原始捕获，不列为有效等待页 |

五张PNG实际均为1280×720。前四次请求的容器尺寸为1600×900，不代表已取得1600×900图像。每张旁边的JSON记录页面、实际尺寸和原生错误检查；[capture-report.json](capture-report.json)记录工程、构建器、输入来源和本机候选位置。最终隔离候选为`agent/local/artifacts/td-workbench-capture-20261008/20261008-094624/T01_Workbench_A.render-ready.toe`，保留在Git忽略的本机目录，工作台窗口已打开。

数据为F-01 v2.2合成开发fixture，通过UDP 127.0.0.1:5005发送；图中的设备连接和SQI来自fixture，不代表真实设备接入。TD缺席、真实设备链和正式准入不在本次验证范围。导出、截图、人工标记、中止请求按钮仍禁用；本次保存由取证脚本调用TOP.save完成，不是工具栏按钮功能。

实际运行发现并修正两处SDK调用错误：Button COMP没有font参数；Panel Execute DAT类型为panelexecuteDAT。隔离工程另加入源模块导入路径。最终四张可读画面均无原生界面脚本错误，T-01/F-04及验证器专项57项测试通过。页面由脚本切换；未验证鼠标点击标签，不作新签收或任务状态迁移。

## 复查入口

- 构建器：`agent/tasks/T-01/execution/build_workbench_a.py`
- 测试：`py -3.14 -X utf8 -m pytest agent/modules/03-TouchDesigner/t01_telemetry_panel/tests agent/modules/03-TouchDesigner/f04_readonly_console/tests agent/tasks/T-01/execution/test_verify.py -q`
- TD类型名官方参考：[OP Find DAT](https://derivative.ca/UserGuide/OP_Find_DAT)
- 本机取证脚本：`agent/local/artifacts/td-workbench-capture-20261008/launch_capture.py`与`capture_td.py`，只创建隔离工程和新证据目录。
