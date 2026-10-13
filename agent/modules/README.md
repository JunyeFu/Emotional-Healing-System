# SRP SE — 数据管道与实时桥接 (v1.2)

> 当前共享源码: 设备采集、会话编排、交互状态估计、通信与记录、Unity参与者工程、TD操作台。
> 技术栈: Python 3.14 + NeuroKit2 + BioSPPy + bleak + UDP JSON/OSC

目录归属与命名见[仓库规范](../../human/project/repository-layout.md)，模块编号以[模块地图](../../human/project/PROJECT_MODULES.md)为准。依赖见[版本基线](requirements-baseline-py3.14.txt)，启动与联调见[运行入口](../runtime/README.md)。

## 当前开发验证

从仓库根，使用已配置项目依赖的解释器：

```powershell
py -3.14 -m pytest agent/modules/tests/session_core agent/modules/tests/session_store -q
```

本机`python`与`py -3.14`可能指向不同环境；后续命令使用同一解释器。源码导航见下方运行模块。

## 旧原型快速启动

以下命令只验证v1.2开发链，不产生正式运行证据。目标合同见[SRP运行合同v2.1](communication/contracts/README.md)。

```bash
# Windows PowerShell
cd agent/modules

# 安装依赖
pip install -r requirements.txt

# 运行模拟数据管道 (60秒, 终端1)
python main.py --weather storm --duration 60

# 实时可视化仪表盘 (终端2)
python visualizer.py

# 运行全部 Python 测试
python -m pytest acquisition/tests signal-processing/tests communication/tests tests -q
```

## 运行模块

| ID | 模块 | 输入 | 输出 | 主要实现 |
|---|---|---|---|---|
| M02 | Python会话核心 | v2.1 manifest、分配、单调时间、ACK与回执 | 权威状态、控制事件、会话事件和20Hz发布门 | `srp_session_core/` |
| M03 | 数据采集 | 真实设备或开发适配器 | 原始样本、设备状态、质量元数据 | `acquisition/` |
| M04 | 交互状态估计 | 原生采样与同步事件 | 实际事件、质量、PF候选；目标由P-01提供 | `signal-processing/README.md`（S-02未完成，旧评分不替代） |
| M05 | 运行合同与记录 | Python权威状态、原始设备包 | v2.1合同、可靠控制、20Hz遥测、L0/L1追加与重放 | `communication/`、`srp_session_store/` |
| M07 | TD只读操作台 | UDP `5005` | 监控、人工标记和中止请求 | `touchdesigner/` |
| M06 | Unity参与者制品 | TCP `5010`、UDP `5006` | 四天气完整体验、ACK和渲染回执 | `unity/` |
| 辅助工具 | 开发桥接 | 编辑器连接 | 构建与检查能力 | `development-bridge/` |
| M00-G02 | 数据治理 | 联系方式预约、manifest和Unity资产 | 跨阶段去重、隐私门、备份恢复和许可门 | `data-governance/` |
| M00-U12-06 | 运行准入 | manifest、构建身份、依赖能力与外部回执 | 正式入口硬阻断与负测试 | `admission/U12-06_正式入口准入框架_v1.0.md` |

跨模块关系见[当前模块地图](../../human/project/PROJECT_MODULES.md)。`visualizer.py` 是 M05 输出的本地观察工具，不是正式运行闭环的必需模块。

Unity当前fade切片入口见[U-03交接](../../agent/tasks/U-03/outputs/current-slice.md)，仍等待V-05。旧TD/Spout场景设计已原文迁入[历史归档](../../agent/tasks/U-03/archive/场景设计.md)，不作为当前运行合同。

## 测试

```bash
python -m pytest acquisition/tests signal-processing/tests communication/tests data-governance/tests tests -q
```

P-01定向验证可运行`py -3.14 -m pytest tests/session_core -q`；P-02定向验证可运行`py -3.14 -m pytest tests/session_store -q`。这些结果只证明Python技术候选，不替代Unity、TouchDesigner或设备联调。

## 依赖关系

```
mock_data.py ──→ signal_pipeline.py ──→ scoring_model.py
                                          │
                              ┌───────────┼────────────┐
                              ▼           ▼            ▼
                       udp_sender.py  osc_sender.py  csv_logger.py
```

## 版本

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.2 | 2026-06-22 | UDP v1.2元数据、真实设备骨架、Unity/TD桥接状态同步 |
| v0.3 | 2026-05-28 | OSC远程遥控桥接 + 实时可视化仪表盘 |
| v0.2 | 2026-05-27 | Sprint 1: 4天气呼吸+评分, 全链路压测, BLE骨架 |
| v0.1 | 2026-05-26 | Sprint 0: 骨架初始化 |
