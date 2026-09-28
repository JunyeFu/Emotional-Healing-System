# U-02 参数快照对照（证据②）

- 快照权威源：V-03《参数边界与锁定规则 v1.0》（任务包 `inputs/07_V-03_参数边界与锁定规则_v1.0.json`，SHA-256 `8B7D2335…E4E90D937`）
- 代码落点：`Assets/Scripts/V03/V03ParameterBounds.cs`
- 防漂移测试：`Assets/Scripts/V03/Tests/ParameterBoundsSnapshotTests.cs`（8 个用例，全部通过）
- 机制：07 权威文件一旦升版，快照测试先行报红，再按新版逐值更新常量与断言；禁止在未对照权威源时私自调参。
- 采集时间：2026-09-20；Unity 6000.4.9f1；EditMode 全量 98/98 Passed。

## 1. 相位插值时长

| 字段 | 下界 | 上界 | 候选 | 单位 |
|---|---|---|---|---|
| phase_interpolation_ms | 100 | 250 | 175 | ms |

## 2. 恢复层一阶低通

| 字段 | 下界 | 上界 | 候选 | 单位 |
|---|---|---|---|---|
| recovery_low_pass | 2 | 5 | 3.5 | s |

实现公式：`alpha = sampleInterval / (tau + sampleInterval)`；首帧直通，后续 `out = lerp(prev, in, alpha)`；采样间隔 1/20 s。

## 3. 实际层（Actual）视觉降级

| 字段 | 下界 | 上界 | 候选 |
|---|---|---|---|
| DEGRADED 不透明度 | 0.45 | 0.70 | 0.575 |
| UNUSABLE 不透明度 | 0.25 | 0.45 | 0.350 |
| DEGRADED 连续性 | 0.45 | 0.75 | 0.600 |
| 边缘柔化（1080p） | 1 px | 3 px | 2 px |

## 4. 恢复端点（分模块）

### storm

| 字段 | 值 |
|---|---|
| 正常雨强倍率 | 1.00 |
| 恢复雨强倍率区间 | 0.65 ~ 0.80 |
| 锁定可见度区间 | 0.45 ~ 0.60 |
| 恢复可见度区间 | 0.70 ~ 0.85 |

### heat / snow / fade

| 模块·字段 | 区间 |
|---|---|
| heat 热浪倍率（恢复） | 0.55 ~ 0.75 |
| snow 雪雾倍率（恢复） | 0.60 ~ 0.80 |
| fade 轮廓完整度（锁定） | 0.35 ~ 0.50 |
| fade 轮廓完整度（恢复） | 0.65 ~ 0.80 |

## 5. 共享规则（字符串常量逐值快照）

| 规则标识 | 代码常量值 |
|---|---|
| 统一插值口径 | `LINEAR_0_TO_1` |
| cue 模式一致 | `SAME_BETWEEN_CUE_MODES` |
| 禁止强制打满端点 | `NO_FORCED_FULL_ENDPOINT` |
| 高值区保留天气身份 | `WEATHER_IDENTITY_RETAINED_AT_HIGH_VALUE` |
| 精确值需运行时证据 | `EXACT_VALUES_REQUIRE_RUNTIME_EVIDENCE` |

## 6. 边界行为（不静默钳制）

`AssertInRange(value, min, max)` 命中边界（含）放行；越界直接抛 `ArgumentOutOfRangeException`，不做 clamp——防止参数漂移被吞掉。已由 `AssertInRange_PassesInside_FailsOutside` 覆盖。

## 7. 候选合规性自检

全部候选值均落在自身下界/上界闭区间内（含端点），由 `Candidates_SitInsideTheirBounds` 逐对断言。
