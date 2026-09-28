# U-02 层级隔离报告（证据③）

- 范围：四层 SceneAdapter 零串扰负测试，覆盖验收 AC1 / AC2 / AC3
- 代码：`Assets/Scripts/V03/V03SceneAdapter.cs` + `Layers/` 四个 Adapter + `BackgroundPass`
- 测试：`LayerIsolationTests.cs`（8）、`LayerZeroCrosstalkTests.cs`（12）、`BackgroundSealTests.cs`（4），共 24 用例，全部通过
- 结果来源：Unity EditMode 全量 98/98 Passed（`01_editmode_results.xml`），2026-09-20
- 架构前提：单向数据流 `帧DTO → V03SceneAdapter（唯一授权投影拆分点）→ 四个只读 View → 四层独立应用`；层间无共享可变状态；投影白名单在编译期隔离跨层字段。

## 一、AC1：每层单独变化不影响其他层，且符合 V-03 映射合同

### 投影白名单（静态隔离）

| 用例 | 断言要点 |
|---|---|
| TargetLayerView_FieldWhitelist_MatchesContract | Target View 仅含合同允许字段 |
| ActualLayerView_FieldWhitelist_MatchesContract | Actual View 仅含合同允许字段 |
| RecoveryLayerView_FieldWhitelist_MatchesContract | Recovery View 仅含合同允许字段 |
| FallbackLayerView_FieldWhitelist_MatchesContract | Fallback View 仅含合同允许字段 |
| TargetView_CarriesNoCrossLayerFields | Target View 不携带任何其他层字段 |
| ActualView_CarriesNoCrossLayerFields | Actual View 不携带任何其他层字段 |
| RecoveryView_CarriesNoQualityField | Recovery View 不携带 quality（不越权读降级态） |
| Views_CarryValuesCorrectly | 各 View 值与帧字段一致、无错位 |

### 单层变化隔离（运行时负向）

| 用例 | 变化源 | 断言要点 |
|---|---|---|
| TargetChange_Isolated_OtherLayersFrozen | 仅 target 字段变化 | actual / recovery / fallback 三层输出逐帧不变 |
| ActualPhaseProgressChange_Isolated_OtherLayersFrozen | 仅 actual phase 推进 | 其他三层冻结 |
| ActualConfidenceChange_FlowsOnlyThroughEnvelope | 仅 actual confidence 变化 | 只经 Actual 包络生效，不外溢 |
| RecoveryValueChange_Isolated_OtherLayersFrozen | 仅 recovery 值变化 | 其他三层冻结 |
| SignalQualityChange_Isolated_NoGlobalQualityShift | 仅 signal_quality 变化 | 不触发全局 quality 状态偏移 |

结论：白名单在投影阶段切断跨层字段，运行时五个单维变化用例验证"只动一层"，AC1 成立。

## 二、AC2：锁定后累计状态不再变化，且重置只在合法生命周期发生

| 用例 | 断言要点 |
|---|---|
| Lock_HoldsAcrossMixedQualityFrames_AndDoesNotLeak | 锁定双触发（UNUSABLE/DISCONNECTED 的 PauseAndLockLastValue，或帧内 recovery_locked=true）后，混合质量帧一律被忽略，锁定值不漂移、不向其他层泄露 |
| Unlock_OnlyAtSessionBoundary_ThenFollowsAgain | quality 回 GOOD **不**解锁；仅 segment 变化触发会话边界 ResetSession 后恢复跟随；重置后首值走低通而非直通；同 segment 帧不重复触发钩子 |

生命周期语义：segment 与上一应用帧不同 → `NotifySessionEnd()` + `ResetSession()` + `NotifySessionBegin()` + 背景层 `OnSessionSegmentChanged()`；会话进行中直接调 ResetSession 计入 RejectedResetCount（非法重置不静默放行）。

## 三、AC3：降级不伪造成功，也不从背景动画泄露目标节律

| 用例 | 断言要点 |
|---|---|
| LinkDown_NoFakeSuccess_CountersAndOutputsHonest | NotifyLinkDown 后不构造 View、不计 applied；无伪成功计数；各层输出保持诚实（保持/冻结而非新值） |
| LinkDown_Recovery_ResumesHonestOutputs | 链路恢复后从真实帧重新跟随，输出可追溯 |
| Background_ZeroRhythmLeakage_OverRhythmAndQualityNoise | 背景层在节律扰动与质量噪声全程下，零节律量泄露到任何功能层 |
| PublicMethods_HaveNoRhythmInterfaces | BackgroundPass 公共方法无任何节律接口（结构性封印） |
| PublicProperties_HaveNoRhythmOrQualityState | 公共属性不含节律值或 quality 状态 |
| OnSessionSegmentChanged_RecordsSegment | 背景层只记录 segment 计数，不读节律 |
| NoStaticRhythmMembers | 无静态节律成员（杜绝跨实例/跨帧残留通道） |

## 四、拒收帧（异常输入不产生半应用态）

| 用例 | 断言要点 |
|---|---|
| RejectedFrame_AllLayersFullyFrozen | 校验失败的帧：四层全部不应用，RejectedFrameCount +1 |
| RejectedThenValidFrame_ResumesCleanly_NoHalfAppliedState | 拒收后紧跟合法帧：无半应用残留，干净恢复 |

## 五、结论

- AC1：8 个白名单用例 + 5 个单层变化用例 → 层间字段与行为双隔离。
- AC2：2 个锁定/解锁用例 → 锁定期间累计状态冻结，解锁唯一合法入口为会话边界。
- AC3：2 个链路通断用例 + 4 个背景封印用例 → 不伪造成功、背景零节律泄露。
- 附带 2 个拒收帧用例关闭"异常输入半应用"缺口。
- 全部 24 用例在最终全量运行中通过（另有 Tick/Policy/Matrix/Validation/Golden 等共同构成 98/98）。
