# T-01 TouchDesigner 实时遥测面板

本目录是T-01独立运行制品，不修改F-04签署目录。`T01_TelemetryPanel.toe/.tox`只读监听`127.0.0.1:5005`，显示Python权威发布的v2.2遥测和TD本地链路统计。

## 文件

- `t01_telemetry.py`：纯Python不可变快照适配器。
- `T01_TelemetryPanel.toe/.tox`：TouchDesigner 2025.32820制品。
- `build_t01_touchdesigner.py`：幂等构建脚本。
- `verify_t01_touchdesigner_reopen.py`：重开、节点权限和错误门。
- `replay_t01_udp.py`：F-05 fixture、真实`SessionCore + TelemetryPublisher`及异常链路发送器。
- `evidence/`：节点计划、状态、截图、回放视频和SHA-256清单。

## 主机专项测试

```powershell
py -3.14 -m pytest -q "02-技术研发/03-TouchDesigner/t01_telemetry_panel/tests"
```

运行制品没有UDP/TCP输出、Spout、文件输出或T-02请求回调。正式模式只接受v2.2；`dev_replay`兼容v2.1但步骤身份显示为不可用且不作推断。

## 完成边界

本目录只证明本机TD对Python权威v2.2遥测的只读网络消费、显示和异常恢复基线，不证明真实设备链、Unity联合运行、T-02请求通道、外部端到屏幕延迟、正式构建、科学有效性或`LIVE_E2E`。
