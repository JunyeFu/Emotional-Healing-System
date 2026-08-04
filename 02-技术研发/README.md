# SRP SE — 数据管道与实时桥接 (v1.2)

> 负责: 生理数据采集 → 信号处理 → 评分模型 → UDP通信 → 系统集成
> 技术栈: Python 3.14 + NeuroKit2 + BioSPPy + bleak + UDP JSON/OSC

## 快速启动

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
| M02 | 数据采集 | 设备或 Mock | 10 Hz `RawFrame`、数据源状态 | `01-数据采集/` |
| M03 | 交互状态估计 | `RawFrame` | 四维评分、`calm_index`、天气强度 | `02-信号处理/` |
| M04 | 通信与记录 | 评分帧 | UDP JSON v1.2、CSV | `05-通信协议/` |
| M05 | TD 引导与监控 | UDP `5005` | 监控画面、Spout 纹理 | `03-TouchDesigner/` |
| M06 | Unity 天气视觉 | UDP `5006`、Spout | 四天气体验画面 | `04-Unity视觉/` |
| M07 | 开发桥接 | 编辑器连接 | 构建与检查能力 | `06-MCP开发桥接/` |

跨项目模块关系见根目录 `PROJECT_MODULES.md`。`visualizer.py` 是 M04 输出的本地观察工具，不是同机演示闭环的必需模块。

## 测试

```bash
python -m pytest 01-数据采集/tests 02-信号处理/tests 05-通信协议/tests tests -q
```

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
