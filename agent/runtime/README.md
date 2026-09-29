# SRP 当前运行入口

本页组织已有运行权威，不新增启动器或宣称正式系统已经就绪。当前工作目录为`D:\Agent\srp`；共享工程已迁入`agent/modules/`，其余根目录迁移进度以[root-layout.json](../root-layout.json)为准。

## Python

[P-01会话核心](../tasks/P-01/TASK.md)负责manifest、流程、时钟、可靠控制和遥测；[P-02记录存储](../tasks/P-02/outputs/current-store-contract.md)负责耐久追加、封存与只读重放。源码目前分别在`agent/modules/srp_session_core/`与`agent/modules/srp_session_store/`。

[U12-06研究接线](../tasks/U12-06/outputs/current-runtime.md)记录正式入口缺口；开发fixture不生成正式运行证据，正式环境仍须取得对应真实设备、权限、构建和研究批准。

## Unity与TD

[U-01可靠控制](../tasks/U-01/outputs/current-control-contract.md)和[U-02四层适配](../tasks/U-02/outputs/current-adapter-contract.md)提供各自已验收的软件能力。[V-05全旅程灰盒](../tasks/V-05/outputs/current-graybox.md)与后续天气实现负责完整参与者制品；当前不能将开发回放或合成帧当作正式体验。

[T-01只读监控](../tasks/T-01/outputs/current-td-contract.md)与[T-02请求交接](../tasks/T-02/outputs/current-operator-contract.md)区分已交付监控和待实现的实验员请求。Unity不以TD或Spout为启动依赖。

## 验证

在仓库根执行`py -3.14 -m pytest -q`复测当前Python模块；各包`execution/verify.ps1`给出对应软件与治理检查。该命令不替代Unity画面、TD运行、真实设备、机构批准或参与者实验。

历史Mock/Spout手册已移至[archive/runtime](../archive/runtime/README_run.md)，不再作为当前运行入口。
