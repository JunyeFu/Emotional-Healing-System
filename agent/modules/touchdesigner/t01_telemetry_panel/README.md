# T-01 TouchDesigner 实时遥测面板

## BigRun Team 当前候选

单设备入口：[T01_BigRunWorkbench.toe](T01_BigRunWorkbench.toe)及[start-td-bigrun.cmd](../../../runtime/start-td-bigrun.cmd)。[逐项更新清单](../../../work/2026-10-19_bigrun-td-update.md)、[操作说明与未验证项](design/bigrun-workbench.md)。这是ECG/RR/HR/ACC与呼吸代理的只读候选；真实实验桥未接入，准备确认/开始保持禁用。下列旧mock入口保留，不与BigRun混用。

## 当前手动操作入口

双击 [T01_ManualWorkbench.toe](T01_ManualWorkbench.toe)，再双击 [start-td-mock.cmd](../../../runtime/start-td-mock.cmd)。也可先启动 mock；两者独立，接入后等待操作员，不自动建场、确认准备或开始。

点击顺序：准备下一位 → 确认准备 → 收到准备回执 → 开始实验 → 暂停/恢复或中止 → 自动封存 → 确认后测 → 返回主页/准备下一位。确认准备之前禁止开始；准备页和等待页不记录、不计时。中止需要二次确认，可取消；取消准备不建立运行记录。

实验记录可选中、导出和打开目录；明细可查看原始字段和复制场次编号。运行中 mock 断流进入记录失败，保留部分记录并返回，不冒充正常封存。mock 窗口 Ctrl+C 停止。

本入口仅为手动模拟测试：设备、Unity 和问卷回执为模拟，会话与存储使用实际 P-01/P-02。UDP5005 接入，UDP5007 传递操作请求；本地记录位于 `agent/local/artifacts/td-manual-workbench/`。不修改 F-04 签署制品，也不代表正式 T-02 或真实设备联合验收。

开发重建与自动验收入口：`py -3.14 agent/tasks/T-01/execution/capture_workbench.py --manual`，不是日常 mock 开关。当前实现为 `build_workbench_manual.py`、`workbench_redesign_runtime.py`、`manual_mock_service.py`；均在 [Agent 执行层](../../../tasks/T-01/execution/README.md)。

## 历史只读基线

以下说明仅对应旧 `T01_TelemetryPanel.toe/.tox`，不作为当前手动入口。旧制品只读监听`127.0.0.1:5005`，显示Python权威发布的v2.2遥测和TD本地链路统计。

当前使用和修复范围以[Agent交接说明](../../../../agent/tasks/T-01/outputs/current-td-contract.md)为入口；原签收与新候选分开。2026-09-28实际TD探针通过，独立可读性候选修复旧文字裁切；A主题原生控件仍待验证。

## 文件

A主题原生构建候选已开始实现，执行入口与验证边界见[实施记录](design/workbench-a-implementation.md)。目前仅通过主机测试，等待TD内执行。

当前候选界面设计见 [A 主题功能清单与预览](design/workbench-v3.md)；该主题尚未在运行制品中实现。

2026-09-08：磁盘 `.toe` 已移除六个根级默认演示节点及其内部节点，并修正 `/project1` 显示入口。T-01 内部49个展开文件字节不变，`.tox` 未改。此次工程壳清理为离线验证候选，旧运行证据只对应原哈希；见[清理与布局复核](design/layout-review-v1.md)。A主题仍未在运行制品实现。

- `t01_telemetry.py`：纯Python不可变快照适配器。
- `T01_TelemetryPanel.toe/.tox`：TouchDesigner 2025.32820制品。
- 构建、重开校验、回放和清单脚本已实际迁入[Agent执行层](../../../../agent/tasks/T-01/execution/README.md)，没有旧位置转发副本。
- `evidence/`：节点计划、状态、截图、回放视频和SHA-256清单。

## 主机专项测试

```powershell
py -3.14 -m pytest -q "agent/modules/touchdesigner/t01_telemetry_panel/tests"
```

运行制品没有UDP/TCP输出、Spout、文件输出或T-02请求回调。正式模式只接受v2.2；`dev_replay`兼容v2.1但步骤身份显示为不可用且不作推断。

人工标记、中止请求、告警与请求ACK的真实接口缺口见[T-02当前交接](../../../../agent/tasks/T-02/outputs/current-operator-contract.md)。旧TD引导工程和任意脚本遥控已迁入T-02历史归档；不作为本制品或操作员请求的执行入口。

## 完成边界

本目录只证明本机TD对Python权威v2.2遥测的只读网络消费、显示和异常恢复基线，不证明真实设备链、Unity联合运行、T-02请求通道、外部端到屏幕延迟、正式构建、科学有效性或`LIVE_E2E`。
