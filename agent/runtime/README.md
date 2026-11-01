# SRP 当前运行入口

## 离线数据分析

[srp-analysis.cmd](srp-analysis.cmd)提供`demo / prepare / analyze`，贯通六类输入、只读派生、参与者统计、PNG/PDF和报告。[格式与方法](../modules/srp_analysis/README.md)区分合成演练、真实数据初步分析与研究关闭。原A/B设定不变；不连接TD/Unity、不授予正式研究资格，原件与结果分开保存。

```powershell
agent/runtime/srp-analysis.cmd demo --out agent/local/artifacts/my-analysis-demo
```

新成员先完成[开发上手](../../human/developers/README.md)的无硬件验证。Unity工程在 `agent/modules/unity/SRP-Weather-Visual/`，TD工程在 `agent/modules/touchdesigner/`；原生版本和候选状态见开发指南，不以旧模拟链作为正式启动器。

> 当前任务范围已迁移至[固定A对受限适应B基线](../design/design-foundation-20261008/README.md)，原注册状态与签收仅覆盖原范围；运行代码/API及真实研究冻结尚未由本轮完成。

本页分开手动模拟操作入口和正式运行权威。当前工作目录为`D:\Agent\srp`；共享工程已迁入`agent/modules/`，其余根目录迁移进度以[root-layout.json](../root-layout.json)为准。

## TD 手动 Mock

BigRun单设备候选使用[T01_BigRunWorkbench.toe](../modules/touchdesigner/t01_telemetry_panel/T01_BigRunWorkbench.toe)和[start-td-bigrun.cmd](start-td-bigrun.cmd)，见[操作说明](../modules/touchdesigner/t01_telemetry_panel/design/bigrun-workbench.md)。只读接入不自动确认准备或开始；下列旧mock入口独立保留，不与BigRun同时运行。

1. 双击 [T01_ManualWorkbench.toe](../modules/touchdesigner/t01_telemetry_panel/T01_ManualWorkbench.toe)，工作台打开在首页。
2. 双击 [start-td-mock.cmd](start-td-mock.cmd)，持续接入模拟设备数据，不自动确认准备或开始。
3. 在 TD 点击准备下一位、确认准备；收到确认后点击开始实验。暂停、恢复、中止、后测和下一场均由你操作。

模拟输入包括设备、Unity 和问卷回执；会话核心和记录存储使用实际 P-01/P-02。数据在 `agent/local/artifacts/td-manual-workbench/`。停止脚本使用 Ctrl+C；运行中断流会保留部分记录，不自动续跑。
`capture_workbench.py --manual` 是自动验收工具，不是日常启动入口。

## Python

BigRun Team 单设备预备入口：[bigrun.cmd](bigrun.cmd)（`--help` 查看命令），[设备到手实测与双通道校准](../modules/acquisition/bigrun/README.md)。已接 DeviceDriver/RawFrame 和 P-02，仍为 DEVELOPMENT_UNVERIFIED；不是正式 TD/Unity 遥测，不启动或确认实验，也不会切换为 mock。

[P-01会话核心](../tasks/P-01/TASK.md)负责manifest、流程、时钟、可靠控制和遥测；[P-02记录存储](../tasks/P-02/outputs/current-store-contract.md)负责耐久追加、封存与只读重放。源码目前分别在`agent/modules/srp_session_core/`与`agent/modules/srp_session_store/`。

[U12-06研究接线](../tasks/U12-06/outputs/current-runtime.md)记录正式入口缺口；开发fixture不生成正式运行证据，正式环境仍须取得对应真实设备、权限、构建和研究批准。

## Unity与TD

[U-01可靠控制](../tasks/U-01/outputs/current-control-contract.md)和[U-02四层适配](../tasks/U-02/outputs/current-adapter-contract.md)提供各自已验收的软件能力。[V-05全旅程灰盒](../tasks/V-05/outputs/current-graybox.md)与后续天气实现负责完整参与者制品；当前不能将开发回放或合成帧当作正式体验。

[T-01只读监控](../tasks/T-01/outputs/current-td-contract.md)与[T-02请求交接](../tasks/T-02/outputs/current-operator-contract.md)区分已交付监控和待实现的实验员请求。Unity不以TD或Spout为启动依赖。

## 验证

在仓库根执行`py -3.14 -m pytest -q`复测当前Python模块；各包`execution/verify.ps1`给出对应软件与治理检查。该命令不替代Unity画面、TD运行、真实设备、机构批准或参与者实验。

历史Mock/Spout手册已移至[archive/runtime](../archive/runtime/README_run.md)，不再作为当前运行入口。
