using System;

namespace SRP.V03
{
    /// <summary>
    /// Target 层只读投影。字段白名单 = 合同 target 行 source_fields（target_phase/target_progress）+ 步骤实例字段。
    /// forbidden_coupling（05 合同）：禁止携带 actual、actual_confidence、error、recovery、fallback 信息。
    /// </summary>
    public readonly struct TargetLayerView
    {
        /// <summary>目标相位（帧原文，如 inhale/exhale/hold/none）。</summary>
        public readonly string TargetPhase;

        /// <summary>目标步骤内部进度 [0,1]（09 迁移指南规则3：仅在该步骤内部取值）。</summary>
        public readonly float TargetProgress;

        /// <summary>目标周期索引；与 TargetStepId 同时有值或同时为空（09 规则2）。</summary>
        public readonly int? TargetCycleIndex;

        /// <summary>目标步骤实例身份；空步骤时为 null（09 规则4）。</summary>
        public readonly string TargetStepId;

        public TargetLayerView(string targetPhase, float targetProgress, int? targetCycleIndex, string targetStepId)
        {
            TargetPhase = targetPhase;
            TargetProgress = targetProgress;
            TargetCycleIndex = targetCycleIndex;
            TargetStepId = targetStepId;
        }

        /// <summary>空步骤判定（phase == "none"，09 规则4）。</summary>
        public bool IsEmptyStep => IsNonePhase(TargetPhase);

        public static bool IsNonePhase(string phase) =>
            string.Equals(phase, "none", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// Actual 层只读投影。字段白名单 = 合同 actual 行 source_fields（actual_phase/actual_progress/actual_confidence）+ 步骤实例字段。
    /// forbidden_coupling：禁止携带 target、error、recovery 信息。
    /// 空步骤（actual 不可用估计）不得填入目标步骤值（09 规则4）——由投影类型隔离保证。
    /// </summary>
    public readonly struct ActualLayerView
    {
        public readonly string ActualPhase;
        public readonly float ActualProgress;
        public readonly int? ActualCycleIndex;
        public readonly string ActualStepId;

        /// <summary>交互状态估计置信度 [0,1]。</summary>
        public readonly float ActualConfidence;

        public ActualLayerView(string actualPhase, float actualProgress, int? actualCycleIndex, string actualStepId, float actualConfidence)
        {
            ActualPhase = actualPhase;
            ActualProgress = actualProgress;
            ActualCycleIndex = actualCycleIndex;
            ActualStepId = actualStepId;
            ActualConfidence = actualConfidence;
        }

        public bool IsEmptyStep => TargetLayerView.IsNonePhase(ActualPhase);
    }

    /// <summary>
    /// Recovery 层只读投影。字段白名单 = 合同 recovery 行 source_fields（recovery_value）+ 帧内锁定标志。
    /// forbidden_coupling：禁止以 quality 作为本地覆写（quality_as_local_override）——
    /// 质量态不进入本视图，仅由编排器决定 RecoveryBehavior。
    /// </summary>
    public readonly struct RecoveryLayerView
    {
        /// <summary>累计环境恢复值 [0,1]。</summary>
        public readonly float RecoveryValue;

        /// <summary>Python 侧锁定标志（F-05 v2.2 帧 recovery_locked 字段）。</summary>
        public readonly bool RecoveryLocked;

        public RecoveryLayerView(float recoveryValue, bool recoveryLocked)
        {
            RecoveryValue = recoveryValue;
            RecoveryLocked = recoveryLocked;
        }
    }

    /// <summary>
    /// Fallback 层只读投影。字段白名单 = 合同 fallback 行 source_fields
    /// （signal_quality / fallback_state / fallback_reason）。
    /// forbidden_coupling：禁止触碰 target、recovery、background_global_warning、audio_warning。
    /// </summary>
    public readonly struct FallbackLayerView
    {
        /// <summary>呼吸带信号质量 [0,1]（帧 signal_quality.resp）。</summary>
        public readonly float SignalQualityResp;

        /// <summary>心电信号质量 [0,1]（帧 signal_quality.ecg）。</summary>
        public readonly float SignalQualityEcg;

        /// <summary>质量态原文（GOOD/DEGRADED/UNUSABLE/DISCONNECTED）。</summary>
        public readonly string FallbackState;

        /// <summary>降级原因描述；正常时为 null。</summary>
        public readonly string FallbackReason;

        public FallbackLayerView(float signalQualityResp, float signalQualityEcg, string fallbackState, string fallbackReason)
        {
            SignalQualityResp = signalQualityResp;
            SignalQualityEcg = signalQualityEcg;
            FallbackState = fallbackState;
            FallbackReason = fallbackReason;
        }
    }
}
