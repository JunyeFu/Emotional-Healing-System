# UDP JSON 通信协议

> v1.2 — 匹配4维度评分模型与设备元数据。Python → TouchDesigner / Unity 实时数据传输。

> 状态说明：`LEGACY_DEV_ONLY`。本文件只解释v1.2开发原型；正式运行权威是[SRP运行合同v2.1](contracts/README.md)，不得从本文件生成正式消费者。

## 协议规范

- **传输层**：UDP
- **编码**：JSON (UTF-8)
- **频率**：10Hz（每100ms一帧）
- **端口**：TD:5005, Unity:5006
- **MTU**：单帧 < 1500 bytes（避免UDP分片）

## 消息格式

```json
{
  "version": "1.2",
  "timestamp": 1716300000.123,
  "scores": {
    "breath_sync": 72.5,
    "breath_depth": 58.1,
    "hrv_coherence": 68.3,
    "eda_calm": 70.8
  },
  "calm_index": 67.4,
  "weather": {
    "type": "storm",
    "intensity": 0.33,
    "trend": "weakening",
    "dominant": "breath_sync"
  },
  "breath": {
    "phase": "inhale",
    "rate": 6.2,
    "amplitude": 0.45,
    "regularity_raw": 0.6,
    "circle_radius": 0.1565,
    "source": "mock"
  },
  "cardiac": {
    "hr": 78,
    "rmssd": 40.2,
    "rr": 6.2,
    "ecg_raw": 0.15,
    "source": "mock"
  },
  "eda": {
    "tonic": 7.0,
    "raw": 7.2,
    "source": "mock"
  },
  "guidance": {
    "prompt": "慢慢吸气...4秒",
    "target_breath_rate": 5.0
  },
  "meta": {
    "frame_id": 1,
    "devices": {"ecg": "mock", "resp": "mock", "eda": "mock"},
    "signal_quality": {"ecg": "mock", "resp": "mock", "eda": "mock"},
    "pipeline_latency_ms": 3.2,
    "buffer_backlog_frames": 0
  }
}
```

## 字段说明

### scores — 4维度评分 (0–100)

| 字段 | 含义 | 生理通路 | 设备 |
|------|------|------|------|
| `breath_sync` | 呼吸率与目标频率的匹配度 | 呼吸→副交感 | PLUX呼吸带 |
| `breath_depth` | 呼吸振幅与目标深度的匹配度 | 呼吸→副交感 | PLUX呼吸带 |
| `hrv_coherence` | RMSSD向目标恢复程度 | 副交感(迷走) | Polar H10 |
| `eda_calm` | 皮肤电导相对基线下降幅度 | 交感(纯) | EDA腕带 |

### weather — 天气映射

| 字段 | 范围 | 说明 |
|------|:----:|------|
| `type` | storm/heat/snow/fade | 当前天气类型 |
| `intensity` | 0–1 | 天气强度（1=恶劣, 0=晴天），= 1 - calm_index/100 |
| `trend` | weakening/stable/intensifying | 天气变化趋势 |
| `dominant` | 任一score字段名 | 当前主导维度 |

### breath — 呼吸域

| 字段 | 范围 | 说明 |
|------|:----:|------|
| `phase` | inhale/hold/exhale | 当前呼吸相位 |
| `rate` | 0–30 bpm | 实时呼吸率 |
| `amplitude` | 0–1 | 归一化呼吸振幅 |
| `regularity_raw` | 0–1 | 呼吸模式规律性（自相关强度） |

### cardiac — 心脏域

| 字段 | 范围 | 说明 |
|------|:----:|------|
| `hr` | 40–200 BPM | 实时心率 |
| `rmssd` | 0–200 ms | HRV时域指标（副交感金标准） |
| `ecg_raw` | 0–3 | 归一化ECG原始值 |

### eda — 皮肤电域

| 字段 | 范围 | 说明 |
|------|:----:|------|
| `tonic` | 1–30 μS | 皮肤电导紧张性水平（SCL） |
| `raw` | — | 原始EDA值 |

### guidance — 引导信息

| 字段 | 范围 | 说明 |
|------|:----:|------|
| `prompt` | 字符串 | 当前呼吸引导提示词 |
| `target_breath_rate` | 3–15 bpm | 目标呼吸频率 |

### meta — 设备与管道状态（v1.2）

| 字段 | 说明 |
|------|------|
| `frame_id` | 管道帧序号 |
| `devices` | 各通道设备状态（mock/connected/no_signal） |
| `signal_quality` | 各通道信号质量摘要 |
| `pipeline_latency_ms` | 当前帧处理延迟 |
| `buffer_backlog_frames` | 设备缓冲积压帧数 |

## 版本兼容性

| 版本 | 变更 | 日期 |
|:--:|------|------|
| v1.0 | 8维评分 + aux域(ACC/TEMP) | 2026-05 |
| v1.1 | 精简为4维；aux域改为eda域；移除motion/acc/temp | 2026-06 |
| **v1.2** | **新增source、meta、circle_radius；对接真实设备骨架与Unity解析类** | 2026-06 |

### v1.0 → v1.1 迁移

- `scores` 对象：8字段 → 4字段（保留 `breath_sync`, `eda_calm`；`depth_quality`→`breath_depth`；`hrv_recovery`→`hrv_coherence`；移除 `hr_stability`, `rate_match`, `regularity`, `motion_stillness`）
- `aux` 域 → 改为 `eda` 域（仅保留 `eda_tonic`, `eda_raw`；移除 `acc_magnitude`, `motion_index`, `temp_skin`）
- 新增 `calm_index` 顶层字段（简化客户端访问）
- 接收端应对未知字段做 **ignore-unknown** 处理

## 与 MCP 开发桥接的关系

```
MCP（开发时）                    UDP JSON（运行时）
Claude Code → TD 建节点          Python → UDP:5005 → TD
Claude Code → Unity 搭场景        Python → UDP:5006 → Unity
```

MCP 负责搭建工程、写脚本；UDP JSON 负责运行时传输数据。
详见：`02-技术研发/06-MCP开发桥接/`

## Hermes Skill

| 任务 | Skill |
|------|-------|
| Python OSC/WebSocket | 40-srp-python-osc-websocket |
| TD 接收端 | 40-srp-touchdesigner-chop-network |
| Unity 接收端 | 40-srp-unity-osc-runtime |
