# SE 软件工程 — 角色交接文档

> SRP v2.1 | 2026/5/20—6/30 | 本文档面向 SE 角色
> 核心职责：数据采集 → 信号处理 → 评分模型 → UDP通信 → 系统集成 → Git管理

---

## 1. 角色定位

你是团队唯一的软件工程角色，负责整个系统的"血脉"——从设备读取生理数据，经过处理变成评分，通过 UDP 发给 TD 和 Unity，同时记录 CSV 日志。你是系统集成者，确保数据流不断、协议不破、代码可运行。

| 子系统 | 你的职责 | RACI |
|--------|----------|:--:|
| 生理数据采集 | 连接 Polar H10 + 呼吸胸带，BLE 读取原始信号 | R/A |
| 数据处理与建模 | NeuroKit2 清洗→特征提取→4维独立评分 (breath_sync/depth/hrv_coherence/eda_calm) + calm_index | R/A |
| UDP 通信 | Python socket UDP JSON @ 10Hz → TD:5005 + Unity:5006 | R/A |
| 系统集成 | 确保 Python→TD→Unity 端到端数据流可运行 | R/A |
| Git 版本控制 | 分支管理、PR 流程、代码审查 | R |

---

## 2. 技术栈

| 层级 | 技术 | 版本 | 为什么 |
|------|------|------|--------|
| BLE 连接 | `bleak` | ≥0.21 | 跨平台 BLE 库，Windows/Linux 均可用，不依赖 BlueZ |
| Polar H10 SDK | Polar BLE SDK | 最新 | 官方 SDK，提供 ECG/HR/RR 解码，避免自己解析 GATT |
| 信号处理 | `NeuroKit2` | ≥0.2 | 一行代码完成 ECG 滤波+R峰检测+HRV计算，生物信号处理首选 |
| 辅助处理 | `BioSPPy` | ≥2.1 | 补充 NeuroKit2 未覆盖的呼吸信号处理 |
| 数值计算 | `NumPy`, `SciPy` | ≥1.26, ≥1.11 | 评分模型计算、信号滤波 |
| UDP 通信 | Python `socket` | stdlib | 零依赖、10Hz 延迟可忽略、JSON 编码 |
| 数据分析 | `Pandas`, `Matplotlib` | ≥2.0, ≥3.8 | CSV 日志离线分析、实验数据可视化 |
| 版本控制 | `Git` + GitHub | 2.x | WSL 环境，分支 `srp/<模块>/<描述>` |
| 虚拟环境 | `venv` | Python 3.14+ | ~/.hermes-venv，经代理 172.24.48.1:7897 安装依赖 |

### 环境搭建

```bash
# 激活虚拟环境
source ~/.hermes-venv/bin/activate

# 安装依赖（通过代理）
pip install --proxy http://172.24.48.1:7897 \
  bleak neurokit2 biosppy numpy scipy pandas matplotlib
```

---

## 3. 七阶段任务分解

| 阶段 | 日期 | 你的任务 | 产出物 | 验收标准 | Hermes Skill |
|------|------|----------|--------|----------|-------------|
| 1 需求 | 5/20-5/25 | 技术可行性评估、设备选型调研、评分模型初稿 | 技术评估报告 | 设备方案通过审批 | 40-srp-technical-feasibility, 40-srp-device-selection |
| 2 原型 | 5/26-6/1 | BLE 连接脚本、模拟数据生成器、UDP JSON 协议实现、CSV 日志模块 | `ble_connect.py`, `mock_data.py`, `udp_sender.py`, `csv_logger.py` | 模拟数据能驱动 TD 和 Unity | 40-srp-polar-h10-ble-bridge, 40-srp-python-osc-websocket |
| 3 闭环 | 6/2-6/9 | 真实设备接入、信号处理管道、评分模型调参、端到端数据流跑通 | `signal_pipeline.py`, `scoring_model.py`, 闭环 Demo v0.5 | 真实设备→TD→Unity 数据流可运行 | 40-srp-biosignal-processing, 40-srp-signal-quality-gate |
| 4 完善 | 6/10-6/17 | 评分模型优化、异常处理、日志完善、CSV 导出格式标准化 | `scoring_model_v2.py`, `error_handler.py`, CSV 样本 | 4 场景全链路稳定运行 ≥10min | 40-srp-respiration-belt-rip |
| 5 测试 | 6/18-6/23 | 配合可用性测试，修复数据处理 Bug，信号质量门禁 | Bug 修复清单、信号质量报告 | 关键 Bug 清零 | 40-srp-signal-quality-gate |
| 6 实验 | 6/24-6/28 | 实验期间技术值守、数据采集监控、CSV 数据完整性校验 | 实验数据集 (.csv) | 全部被试数据采集完成且无丢帧 | 40-srp-reporting-standard |
| 7 交付 | 6/29-6/30 | 代码整理、接口文档、系统集成报告、Git 仓库清理 | `README.md`, `API.md`, 系统集成报告, Git repo | 代码可复现 | 40-srp-git-and-review, deliverable-quality-gate |

---

## 4. 接口契约

### UDP JSON 格式（10Hz，每 100ms 一帧）

```json
{
  "ts": 1716300000.123,
  "breath": {
    "score": 72.5,
    "rate": 14.2,
    "depth": 0.65,
    "phase": "inhale"
  },
  "calm": {
    "index": 68.3,
    "trend": "improving"
  },
  "hrv": {
    "hr": 72,
    "rmssd": 45.2
  },
  "weather": {
    "type": "storm",
    "intensity": 0.32
  }
}
```

| 字段 | 范围 | 含义 |
|------|:----:|------|
| breath.score | 0-100 | 呼吸与引导圈同步度 |
| breath.phase | inhale/hold/exhale | 当前呼吸阶段 |
| calm.index | 0-100 | 综合平静指数 |
| weather.intensity | 0-1 | 1=恶劣天气, 0=晴天 |

### 端口分配

| 端口 | 目标 | 用途 |
|:----:|------|------|
| 5005 | TouchDesigner | 监控台 + 呼吸引导圈 |
| 5006 | Unity 2D | 天气场景 + 旅人 |

---

## 5. 模拟数据策略

阶段 2 使用模拟数据跑通全链路：

```python
import numpy as np
import time, json, socket

def mock_breath(t):
    """模拟呼吸波形：正弦波 + 轻微噪声"""
    return np.sin(2 * np.pi * 0.2 * t) * 0.5 + 0.5 + np.random.normal(0, 0.02)

def mock_ecg(t):
    """模拟 ECG：周期性 QRS 波"""
    phase = (t * 1.2) % 1.0  # 72 BPM
    return np.exp(-((phase - 0.3) / 0.05)**2) * 0.8 + np.random.normal(0, 0.01)
```

---

## 6. 对接点

| 对接方 | 你提供 | 他们需要 |
|--------|--------|----------|
| 交互设计A (TD) | UDP JSON @ :5005 | breath.phase 驱动呼吸圈, calm.index 驱动天气强度 |
| 数字媒体 (Unity) | UDP JSON @ :5006 | weather.intensity 驱动粒子/颜色, calm.index 驱动旅人动画 |
| 交互设计B (实验) | CSV 日志文件 | 被试生理数据供统计分析 |

---

## 7. 文件命名规范

```
02-技术研发/01-数据采集/
├── ble_connect.py           Polar H10 BLE 连接
├── mock_data.py             模拟数据生成器
├── udp_sender.py            UDP JSON 发送器
└── csv_logger.py            CSV 日志记录器

02-技术研发/02-信号处理/
├── signal_pipeline.py       NeuroKit2 处理管道
├── scoring_model.py         评分模型
└── error_handler.py         异常处理

03-测试与实验/实验数据/
└── P{ID}_{天气}_{日期}.csv  被试数据 (如 P01_storm_20260624.csv)
```

---

## 8. 质量门禁

使用 `deliverable-quality-gate` 检查：
- [ ] `ble_connect.py` 能扫描并连接 Polar H10
- [ ] `signal_pipeline.py` 能输出 4 维评分 (breath_sync, breath_depth, hrv_coherence, eda_calm) 和 calm_index
- [ ] `udp_sender.py` 发送的 JSON 格式通过 TD 和 Unity 验证
- [ ] CSV 日志包含完整的 ts/4_scores/calm_index/hr/rr 列
- [ ] 代码通过 pylint 无 critical error
- [ ] Git 分支命名符合 `srp/<模块>/<描述>` 规范
