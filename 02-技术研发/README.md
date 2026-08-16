# SRP SE — 数据管道与实时桥接 (v1.2)

> 负责: 生理数据采集 → 信号处理 → 评分模型 → UDP通信 → 系统集成
> 技术栈: Python 3.14 + NeuroKit2 + BioSPPy + bleak + UDP JSON/OSC

## 旧原型快速启动

以下命令只验证v1.2开发链，不产生正式运行证据。目标合同见[SRP运行合同v2.1](05-通信协议/contracts/README.md)。

```bash
# Windows PowerShell
cd 02-技术研发

# 安装依赖
pip install -r requirements.txt

# 运行模拟数据管道 (60秒, 终端1)
python main.py --weather storm --duration 60

# 实时可视化仪表盘 (终端2)
python visualizer.py

# 运行全部 Python 测试
python -m pytest 01-数据采集/tests 02-信号处理/tests 05-通信协议/tests tests -q
```

## 运行模块

| ID | 模块 | 输入 | 输出 | 主要实现 |
|---|---|---|---|---|
| M02 | Python会话核心 | v2.1 manifest、分配、单调时间、ACK与回执 | 权威状态、控制事件、会话事件和20Hz发布门 | `srp_session_core/` |
| M03 | 数据采集 | 真实设备或开发适配器 | 原始样本、设备状态、质量元数据 | `01-数据采集/` |
| M04 | 交互状态估计 | 原生采样与同步事件 | 目标/实际事件、质量、PF候选和累计状态 | `02-信号处理/` |
| M05 | 运行合同与记录 | Python权威状态、原始设备包 | v2.1合同、可靠控制、20Hz遥测、L0/L1追加与重放 | `05-通信协议/`、`srp_session_store/` |
| M06 | TD只读操作台 | UDP `5005` | 监控、人工标记和中止请求 | `03-TouchDesigner/` |
| M07 | Unity参与者制品 | TCP `5010`、UDP `5006` | 四天气完整体验、ACK和渲染回执 | `04-Unity视觉/` |
| M08 | 开发桥接 | 编辑器连接 | 构建与检查能力 | `06-MCP开发桥接/` |
| M00-G02 | 数据治理 | 联系方式预约、manifest和Unity资产 | 跨阶段去重、隐私门、备份恢复和许可门 | `07-数据治理/` |

跨项目模块关系见根目录 `PROJECT_MODULES.md`。`visualizer.py` 是 M05 输出的本地观察工具，不是正式运行闭环的必需模块。

## 测试

```bash
python -m pytest 01-数据采集/tests 02-信号处理/tests 05-通信协议/tests 07-数据治理/tests tests -q
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
