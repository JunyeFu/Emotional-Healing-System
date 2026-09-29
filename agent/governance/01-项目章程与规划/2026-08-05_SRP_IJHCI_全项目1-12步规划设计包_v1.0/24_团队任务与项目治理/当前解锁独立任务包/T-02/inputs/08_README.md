# T-01 TouchDesigner 实时遥测面板

本目录是T-01独立运行制品，不修改F-04签署目录。`T01_TelemetryPanel.toe/.tox`只读监听`127.0.0.1:5005`，显示Python权威发布的v2.2遥测和TD本地链路统计。

当前使用和修复范围以[Agent交接说明](../../../agent/tasks/T-01/outputs/current-td-contract.md)为入口；原签收与新候选分开。2026-09-28实际TD探针通过，独立可读性候选修复旧文字裁切；A主题原生控件仍待验证。

## 文件

A主题原生构建候选已开始实现，执行入口与验证边界见[实施记录](design/workbench-a-implementation.md)。目前仅通过主机测试，等待TD内执行。

当前候选界面设计见 [A 主题功能清单与预览](design/workbench-v3.md)；该主题尚未在运行制品中实现。

2026-09-08：磁盘 `.toe` 已移除六个根级默认演示节点及其内部节点，并修正 `/project1` 显示入口。T-01 内部49个展开文件字节不变，`.tox` 未改。此次工程壳清理为离线验证候选，旧运行证据只对应原哈希；见[清理与布局复核](design/layout-review-v1.md)。A主题仍未在运行制品实现。

- `t01_telemetry.py`：纯Python不可变快照适配器。
- `T01_TelemetryPanel.toe/.tox`：TouchDesigner 2025.32820制品。
- 构建、重开校验、回放和清单脚本已实际迁入[Agent执行层](../../../agent/tasks/T-01/execution/README.md)，没有旧位置转发副本。
- `evidence/`：节点计划、状态、截图、回放视频和SHA-256清单。

## 主机专项测试

```powershell
py -3.14 -m pytest -q "02-技术研发/03-TouchDesigner/t01_telemetry_panel/tests"
```

运行制品没有UDP/TCP输出、Spout、文件输出或T-02请求回调。正式模式只接受v2.2；`dev_replay`兼容v2.1但步骤身份显示为不可用且不作推断。

人工标记、中止请求、告警与请求ACK的真实接口缺口见[T-02当前交接](../../../agent/tasks/T-02/outputs/current-operator-contract.md)。旧TD引导工程和任意脚本遥控已迁入T-02历史归档；不作为本制品或操作员请求的执行入口。

## 完成边界

本目录只证明本机TD对Python权威v2.2遥测的只读网络消费、显示和异常恢复基线，不证明真实设备链、Unity联合运行、T-02请求通道、外部端到屏幕延迟、正式构建、科学有效性或`LIVE_E2E`。
