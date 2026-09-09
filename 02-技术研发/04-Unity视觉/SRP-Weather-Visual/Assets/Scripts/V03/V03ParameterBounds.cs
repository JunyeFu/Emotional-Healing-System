using System;

namespace SRP.V03
{
    /// <summary>
    /// 07 参数边界与锁定规则 常量表。
    /// 源：07_parameters-bounds-locking v1.0（U-02 快照 inputs/07，SHA-256 对照见 FILES.md）。
    /// 规则落地：
    /// - 写入场景的参数经区间断言，越界 fail（ArgumentOutOfRangeException），不静默钳制；
    /// - shared_rules 全集以常量承载：LINEAR_0_TO_1 / SAME_BETWEEN_CUE_MODES /
    ///   NO_FORCED_FULL_ENDPOINT / WEATHER_IDENTITY_RETAINED_AT_HIGH_VALUE /
    ///   EXACT_VALUES_REQUIRE_RUNTIME_EVIDENCE；
    /// - 所有 *Candidate 均为区间中点候选值，冻结需 runtime 证据（exact_values_require_runtime_evidence）。
    /// </summary>
    public static class V03ParameterBounds
    {
        // ---- target 相位插值 ----
        public const float PhaseInterpolationMsMin = 100f;
        public const float PhaseInterpolationMsMax = 250f;
        /// <summary>候选值 = 区间中点。</summary>
        public const float PhaseInterpolationMsCandidate = 175f;

        // ---- recovery 低通 ----
        public const float RecoveryLowPassSecondsMin = 2f;
        public const float RecoveryLowPassSecondsMax = 5f;
        /// <summary>候选值 = 区间中点。</summary>
        public const float RecoveryLowPassSecondsCandidate = 3.5f;

        // ---- actual 层视觉参数（DEGRADED = 低确定性；UNUSABLE/DISCONNECTED = 暂不可用）----
        public const float ActualDegradedOpacityMin = 0.45f;
        public const float ActualDegradedOpacityMax = 0.7f;
        public const float ActualDegradedOpacityCandidate = 0.575f;

        public const float ActualUnavailableOpacityMin = 0.25f;
        public const float ActualUnavailableOpacityMax = 0.45f;
        public const float ActualUnavailableOpacityCandidate = 0.35f;

        public const float ActualDegradedContinuityMin = 0.45f;
        public const float ActualDegradedContinuityMax = 0.75f;
        public const float ActualDegradedContinuityCandidate = 0.6f;

        public const float ActualEdgeSofteningPx1080pMin = 1f;
        public const float ActualEdgeSofteningPx1080pMax = 3f;
        public const float ActualEdgeSofteningPx1080pCandidate = 2f;

        // ---- recovery 恢复端点（07：正常值 1 / 锁定端点 → 恢复目标区间）----
        // storm：rain_multiplier 正常态 1 → 恢复目标 [0.65,0.8]；visibility 锁定 [0.45,0.6] → 恢复目标 [0.7,0.85]
        public const float StormRainMultiplierNormalValue = 1f;
        public const float StormRainMultiplierRecoveryMin = 0.65f;
        public const float StormRainMultiplierRecoveryMax = 0.8f;
        public const float StormVisibilityLockedMin = 0.45f;
        public const float StormVisibilityLockedMax = 0.6f;
        public const float StormVisibilityRecoveryMin = 0.7f;
        public const float StormVisibilityRecoveryMax = 0.85f;

        // heat：haze_multiplier → 恢复目标 [0.55,0.75]
        public const float HeatHazeMultiplierRecoveryMin = 0.55f;
        public const float HeatHazeMultiplierRecoveryMax = 0.75f;

        // snow：mist_multiplier → 恢复目标 [0.6,0.8]
        public const float SnowMistMultiplierRecoveryMin = 0.6f;
        public const float SnowMistMultiplierRecoveryMax = 0.8f;

        // fade：outline_texture_base_color_completeness 锁定 [0.35,0.5] → 恢复目标 [0.65,0.8]
        public const float FadeOutlineCompletenessLockedMin = 0.35f;
        public const float FadeOutlineCompletenessLockedMax = 0.5f;
        public const float FadeOutlineCompletenessRecoveryMin = 0.65f;
        public const float FadeOutlineCompletenessRecoveryMax = 0.8f;

        // ---- shared_rules（07 全集，供断言与文档对照）----
        public const string RuleLinearZeroToOne = "LINEAR_0_TO_1";
        public const string RuleSameBetweenCueModes = "SAME_BETWEEN_CUE_MODES";
        public const string RuleNoForcedFullEndpoint = "NO_FORCED_FULL_ENDPOINT";
        public const string RuleWeatherIdentityRetainedAtHighValue = "WEATHER_IDENTITY_RETAINED_AT_HIGH_VALUE";
        public const string RuleExactValuesRequireRuntimeEvidence = "EXACT_VALUES_REQUIRE_RUNTIME_EVIDENCE";

        /// <summary>
        /// DEGRADED 态 fallback 可见确定性上限（候选值 0.7）。
        /// exact_cap_freeze_gate = U-03_DEGRADED_VISIBILITY_EVIDENCE：
        /// U-03 证据到位后冻结为精确值；在此之前仅作实现候选（设计文档 v1.0 §4.4）。
        /// </summary>
        public const float DegradedVisibilityCapCandidate = 0.7f;
        public const string DegradedCapFreezeGate = "U-03_DEGRADED_VISIBILITY_EVIDENCE";

        /// <summary>GOOD 态 cap = 1.0（不额外限制）。</summary>
        public const float GoodVisibilityCap = 1.0f;

        /// <summary>区间断言：越界 fail（不静默钳制）。依据 07 区间断言要求。</summary>
        public static void AssertInRange(float value, float min, float max, string paramName)
        {
            if (value < min || value > max)
                throw new ArgumentOutOfRangeException(paramName,
                    $"{paramName}={value} out of [{min},{max}] (07 parameters-bounds-locking)");
        }
    }
}
