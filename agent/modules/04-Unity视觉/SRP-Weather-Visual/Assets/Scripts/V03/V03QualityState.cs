using System;

namespace SRP.V03
{
    /// <summary>
    /// V-03 合同质量四态（对应 F-05 v2.2 帧的 fallback_state 字段取值）。
    /// 依据：05_V-03 四层视听映射合同 v1.0 quality_behavior 全矩阵。
    /// </summary>
    public enum V03QualityState
    {
        Good = 0,
        Degraded = 1,
        Unusable = 2,
        Disconnected = 3,
    }

    /// <summary>target 层行为（合同 target 行 quality_behavior）。</summary>
    public enum V03TargetBehavior
    {
        ContinueTarget,
        OpenLoopTarget,
        FollowPythonSafeOpenLoopOrAbort,
    }

    /// <summary>actual 层行为（合同 actual 行 quality_behavior）。</summary>
    public enum V03ActualBehavior
    {
        Active,
        ActiveLowCertainty,
        StaticBrokenOutline,
    }

    /// <summary>recovery 层行为（合同 recovery 行 quality_behavior）。</summary>
    public enum V03RecoveryBehavior
    {
        FollowPythonUpdate,
        FollowPythonCautionOrPause,
        PauseAndLockLastValue,
    }

    /// <summary>fallback 层行为（合同 fallback 行 quality_behavior）。</summary>
    public enum V03FallbackBehavior
    {
        NoExtraMarker,
        LowCertaintyOnActualOnly,
        TemporarilyUnavailableOnActualOnly,
    }

    /// <summary>background 层行为（合同 background 行 quality_behavior：四态恒为 UNCHANGED）。</summary>
    public enum V03BackgroundBehavior
    {
        Unchanged,
    }

    /// <summary>
    /// 质量态到各层行为的映射矩阵。
    /// 依据：05 合同 40 rows 归一 —— 各 technical_id / cue_mode 下同层行为一致，
    /// 差异仅在相位槽（design_phase_slots）与视觉载体（visual_carrier），不在 quality_behavior。
    /// </summary>
    public static class V03QualityBehaviorMatrix
    {
        public static V03TargetBehavior TargetBehavior(this V03QualityState state) => state switch
        {
            V03QualityState.Good => V03TargetBehavior.ContinueTarget,
            V03QualityState.Degraded => V03TargetBehavior.ContinueTarget,
            V03QualityState.Unusable => V03TargetBehavior.OpenLoopTarget,
            V03QualityState.Disconnected => V03TargetBehavior.FollowPythonSafeOpenLoopOrAbort,
            _ => throw new ArgumentOutOfRangeException(nameof(state)),
        };

        public static V03ActualBehavior ActualBehavior(this V03QualityState state) => state switch
        {
            V03QualityState.Good => V03ActualBehavior.Active,
            V03QualityState.Degraded => V03ActualBehavior.ActiveLowCertainty,
            V03QualityState.Unusable => V03ActualBehavior.StaticBrokenOutline,
            V03QualityState.Disconnected => V03ActualBehavior.StaticBrokenOutline,
            _ => throw new ArgumentOutOfRangeException(nameof(state)),
        };

        public static V03RecoveryBehavior RecoveryBehavior(this V03QualityState state) => state switch
        {
            V03QualityState.Good => V03RecoveryBehavior.FollowPythonUpdate,
            V03QualityState.Degraded => V03RecoveryBehavior.FollowPythonCautionOrPause,
            V03QualityState.Unusable => V03RecoveryBehavior.PauseAndLockLastValue,
            V03QualityState.Disconnected => V03RecoveryBehavior.PauseAndLockLastValue,
            _ => throw new ArgumentOutOfRangeException(nameof(state)),
        };

        public static V03FallbackBehavior FallbackBehavior(this V03QualityState state) => state switch
        {
            V03QualityState.Good => V03FallbackBehavior.NoExtraMarker,
            V03QualityState.Degraded => V03FallbackBehavior.LowCertaintyOnActualOnly,
            V03QualityState.Unusable => V03FallbackBehavior.TemporarilyUnavailableOnActualOnly,
            V03QualityState.Disconnected => V03FallbackBehavior.TemporarilyUnavailableOnActualOnly,
            _ => throw new ArgumentOutOfRangeException(nameof(state)),
        };

        public static V03BackgroundBehavior BackgroundBehavior(this V03QualityState state) => state switch
        {
            V03QualityState.Good => V03BackgroundBehavior.Unchanged,
            V03QualityState.Degraded => V03BackgroundBehavior.Unchanged,
            V03QualityState.Unusable => V03BackgroundBehavior.Unchanged,
            V03QualityState.Disconnected => V03BackgroundBehavior.Unchanged,
            _ => throw new ArgumentOutOfRangeException(nameof(state)),
        };

        /// <summary>解析帧内 fallback_state 字符串（GOOD/DEGRADED/UNUSABLE/DISCONNECTED，大小写不敏感）。</summary>
        public static bool TryParseQualityState(string raw, out V03QualityState state)
        {
            switch (raw == null ? string.Empty : raw.Trim().ToUpperInvariant())
            {
                case "GOOD": state = V03QualityState.Good; return true;
                case "DEGRADED": state = V03QualityState.Degraded; return true;
                case "UNUSABLE": state = V03QualityState.Unusable; return true;
                case "DISCONNECTED": state = V03QualityState.Disconnected; return true;
                default: state = V03QualityState.Good; return false;
            }
        }
    }
}
