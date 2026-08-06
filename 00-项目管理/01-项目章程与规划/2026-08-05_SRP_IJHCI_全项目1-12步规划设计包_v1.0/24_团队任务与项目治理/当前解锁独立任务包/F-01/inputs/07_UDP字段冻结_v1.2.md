# UDP 字段冻结表 v1.2

> 目的：作为 Python、TouchDesigner、Unity、CSV 的唯一字段契约。

## 原则

- 四天气先作为实验条件或用户选择入口。
- 生理输入只驱动恢复强度、视觉强度和呼吸引导同步性。
- 消费级设备数据只用于交互状态估计，不作为严肃判断依据。
- 新增字段必须先改本文件，再改发送端和接收端。

## 必需字段

| 路径 | 类型 | 来源 | 用途 |
|---|---|---|---|
| `version` | string | Python | 协议版本，固定 `1.2` |
| `timestamp` | number | Python | 秒级时间戳 |
| `scores.breath_sync` | number | Python | 呼吸节律匹配评分 |
| `scores.breath_depth` | number | Python | 呼吸深度评分 |
| `scores.hrv_coherence` | number | Python | HRV 协同性评分 |
| `scores.eda_calm` | number | Python | EDA 平稳评分 |
| `calm_index` | number | Python | 综合恢复强度，0-100 |
| `weather.type` | enum | Python/实验条件 | `storm` / `heat` / `snow` / `fade` |
| `weather.intensity` | number | Python | 0-1，1 为天气强，0 为恢复 |
| `weather.trend` | enum | Python | `weakening` / `stable` / `intensifying` |
| `weather.dominant` | string | Python | 当前主导评分维度 |
| `breath.phase` | enum | Python | `inhale` / `hold` / `exhale` |
| `breath.rate` | number | Python | 呼吸频率 |
| `breath.amplitude` | number | Python | 呼吸振幅 |
| `breath.regularity_raw` | number | Python | 呼吸规律性原始值 |
| `breath.circle_radius` | number | Python | 呼吸圈半径 |
| `breath.source` | string | Python | `mock` / `belt` / `none` |
| `cardiac.hr` | number | Python | 心率 |
| `cardiac.rmssd` | number | Python | RMSSD |
| `cardiac.rr` | number | Python | 当前呼吸率副本，供接收端简化显示 |
| `cardiac.ecg_raw` | number | Python | ECG 原始值 |
| `cardiac.source` | string | Python | `mock` / `polar_h10` / `none` |
| `eda.tonic` | number | Python | EDA tonic |
| `eda.raw` | number | Python | EDA raw |
| `eda.source` | string | Python | `mock` / `wristband` / `none` |
| `guidance.prompt` | string | Python | 环境化提示文本 |
| `guidance.target_breath_rate` | number | Python | 目标呼吸频率 |
| `meta.frame_id` | integer | Python | 帧序号 |
| `meta.devices` | object | Python | 设备状态 |
| `meta.signal_quality` | object | Python | 信号质量摘要 |
| `meta.pipeline_latency_ms` | number | Python | 管道延迟 |
| `meta.buffer_backlog_frames` | integer | Python | 缓冲积压 |

## 建议补充字段

现有协议可继续使用 `weather.type`。如果后续需要更明确地区分实验条件和画面状态，可在 v1.3 增加：

| 字段 | 类型 | 用途 |
|---|---|---|
| `seq` | integer | 等同或替代 `meta.frame_id`，用于丢包检查 |
| `timestamp_ms` | integer | 毫秒时间戳 |
| `weather_target` | enum | 实验条件选择的目标天气 |
| `guide_phase` | enum | 等同或替代 `breath.phase`，供 TD/Unity 简化解析 |
| `source_mode` | enum | `mock` / `real` / `replay` |
| `signal_ok` | boolean | 是否满足当前演示的最低输入质量 |

## CSV 固定列

CSV 至少包含：

```text
timestamp,frame_id,weather_type,weather_intensity,weather_trend,calm_index,
breath_sync,breath_depth,hrv_coherence,eda_calm,
breath_phase,breath_rate,breath_amplitude,hr,rmssd,eda_tonic,
source_breath,source_cardiac,source_eda,pipeline_latency_ms,operator_mark
```

## 接收端责任

| 接收端 | 必须处理 | 可忽略 |
|---|---|---|
| TouchDesigner | `meta.frame_id`、四维评分、`calm_index`、`weather.type`、`breath.phase`、Spout 状态 | 未知新增字段 |
| Unity | `weather.type`、`weather.intensity`、`calm_index`、`breath.phase`、`guidance.prompt` | 设备元数据 |
| CSV | 全量记录字段，未知字段不自动吞掉 | 无 |

## 成功标准

- 60 秒内 Python 发送约 600 帧。
- TD 和 Unity 均能解析同一份 JSON。
- CSV 字段顺序固定。
- 新增字段不会破坏旧接收端。
