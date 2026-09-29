using System;
using NUnit.Framework;

namespace SRP.V03.Tests
{
    /// <summary>
    /// 07 参数边界快照对照（防漂移）：常量逐值断言。
    /// 快照源：07_parameters-bounds-locking v1.0（U-02 快照 inputs/07）。
    /// 若 07 升版，本测试先行报红，再按新版快照更新常量与断言。
    /// </summary>
    public sealed class ParameterBoundsSnapshotTests
    {
        [Test]
        public void PhaseInterpolation_Bounds_Snapshot()
        {
            Assert.AreEqual(100f, V03ParameterBounds.PhaseInterpolationMsMin, 1e-6f);
            Assert.AreEqual(250f, V03ParameterBounds.PhaseInterpolationMsMax, 1e-6f);
            Assert.AreEqual(175f, V03ParameterBounds.PhaseInterpolationMsCandidate, 1e-6f);
        }

        [Test]
        public void RecoveryLowPass_Bounds_Snapshot()
        {
            Assert.AreEqual(2f, V03ParameterBounds.RecoveryLowPassSecondsMin, 1e-6f);
            Assert.AreEqual(5f, V03ParameterBounds.RecoveryLowPassSecondsMax, 1e-6f);
            Assert.AreEqual(3.5f, V03ParameterBounds.RecoveryLowPassSecondsCandidate, 1e-6f);
        }

        [Test]
        public void ActualVisual_Bounds_Snapshot()
        {
            Assert.AreEqual(0.45f, V03ParameterBounds.ActualDegradedOpacityMin, 1e-6f);
            Assert.AreEqual(0.7f, V03ParameterBounds.ActualDegradedOpacityMax, 1e-6f);
            Assert.AreEqual(0.575f, V03ParameterBounds.ActualDegradedOpacityCandidate, 1e-6f);

            Assert.AreEqual(0.25f, V03ParameterBounds.ActualUnavailableOpacityMin, 1e-6f);
            Assert.AreEqual(0.45f, V03ParameterBounds.ActualUnavailableOpacityMax, 1e-6f);
            Assert.AreEqual(0.35f, V03ParameterBounds.ActualUnavailableOpacityCandidate, 1e-6f);

            Assert.AreEqual(0.45f, V03ParameterBounds.ActualDegradedContinuityMin, 1e-6f);
            Assert.AreEqual(0.75f, V03ParameterBounds.ActualDegradedContinuityMax, 1e-6f);
            Assert.AreEqual(0.6f, V03ParameterBounds.ActualDegradedContinuityCandidate, 1e-6f);

            Assert.AreEqual(1f, V03ParameterBounds.ActualEdgeSofteningPx1080pMin, 1e-6f);
            Assert.AreEqual(3f, V03ParameterBounds.ActualEdgeSofteningPx1080pMax, 1e-6f);
            Assert.AreEqual(2f, V03ParameterBounds.ActualEdgeSofteningPx1080pCandidate, 1e-6f);
        }

        [Test]
        public void RecoveryEndpoints_Storm_Snapshot()
        {
            Assert.AreEqual(1f, V03ParameterBounds.StormRainMultiplierNormalValue, 1e-6f);
            Assert.AreEqual(0.65f, V03ParameterBounds.StormRainMultiplierRecoveryMin, 1e-6f);
            Assert.AreEqual(0.8f, V03ParameterBounds.StormRainMultiplierRecoveryMax, 1e-6f);

            Assert.AreEqual(0.45f, V03ParameterBounds.StormVisibilityLockedMin, 1e-6f);
            Assert.AreEqual(0.6f, V03ParameterBounds.StormVisibilityLockedMax, 1e-6f);
            Assert.AreEqual(0.7f, V03ParameterBounds.StormVisibilityRecoveryMin, 1e-6f);
            Assert.AreEqual(0.85f, V03ParameterBounds.StormVisibilityRecoveryMax, 1e-6f);
        }

        [Test]
        public void RecoveryEndpoints_HeatSnowFade_Snapshot()
        {
            Assert.AreEqual(0.55f, V03ParameterBounds.HeatHazeMultiplierRecoveryMin, 1e-6f);
            Assert.AreEqual(0.75f, V03ParameterBounds.HeatHazeMultiplierRecoveryMax, 1e-6f);

            Assert.AreEqual(0.6f, V03ParameterBounds.SnowMistMultiplierRecoveryMin, 1e-6f);
            Assert.AreEqual(0.8f, V03ParameterBounds.SnowMistMultiplierRecoveryMax, 1e-6f);

            Assert.AreEqual(0.35f, V03ParameterBounds.FadeOutlineCompletenessLockedMin, 1e-6f);
            Assert.AreEqual(0.5f, V03ParameterBounds.FadeOutlineCompletenessLockedMax, 1e-6f);
            Assert.AreEqual(0.65f, V03ParameterBounds.FadeOutlineCompletenessRecoveryMin, 1e-6f);
            Assert.AreEqual(0.8f, V03ParameterBounds.FadeOutlineCompletenessRecoveryMax, 1e-6f);
        }

        [Test]
        public void SharedRules_Complete()
        {
            Assert.AreEqual("LINEAR_0_TO_1", V03ParameterBounds.RuleLinearZeroToOne);
            Assert.AreEqual("SAME_BETWEEN_CUE_MODES", V03ParameterBounds.RuleSameBetweenCueModes);
            Assert.AreEqual("NO_FORCED_FULL_ENDPOINT", V03ParameterBounds.RuleNoForcedFullEndpoint);
            Assert.AreEqual("WEATHER_IDENTITY_RETAINED_AT_HIGH_VALUE", V03ParameterBounds.RuleWeatherIdentityRetainedAtHighValue);
            Assert.AreEqual("EXACT_VALUES_REQUIRE_RUNTIME_EVIDENCE", V03ParameterBounds.RuleExactValuesRequireRuntimeEvidence);
        }

        [Test]
        public void AssertInRange_PassesInside_FailsOutside()
        {
            Assert.DoesNotThrow(() => V03ParameterBounds.AssertInRange(0.575f, 0.45f, 0.7f, "x"));
            Assert.DoesNotThrow(() => V03ParameterBounds.AssertInRange(0.45f, 0.45f, 0.7f, "x"), "边界值含");
            Assert.DoesNotThrow(() => V03ParameterBounds.AssertInRange(0.7f, 0.45f, 0.7f, "x"), "边界值含");

            Assert.Throws<ArgumentOutOfRangeException>(() =>
                V03ParameterBounds.AssertInRange(0.71f, 0.45f, 0.7f, "x"), "越上界 fail（不静默钳制）");
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                V03ParameterBounds.AssertInRange(0.44f, 0.45f, 0.7f, "x"), "越下界 fail（不静默钳制）");
        }

        [Test]
        public void Candidates_SitInsideTheirBounds()
        {
            Assert.GreaterOrEqual(V03ParameterBounds.PhaseInterpolationMsCandidate, V03ParameterBounds.PhaseInterpolationMsMin);
            Assert.LessOrEqual(V03ParameterBounds.PhaseInterpolationMsCandidate, V03ParameterBounds.PhaseInterpolationMsMax);

            Assert.GreaterOrEqual(V03ParameterBounds.RecoveryLowPassSecondsCandidate, V03ParameterBounds.RecoveryLowPassSecondsMin);
            Assert.LessOrEqual(V03ParameterBounds.RecoveryLowPassSecondsCandidate, V03ParameterBounds.RecoveryLowPassSecondsMax);

            Assert.GreaterOrEqual(V03ParameterBounds.ActualDegradedOpacityCandidate, V03ParameterBounds.ActualDegradedOpacityMin);
            Assert.LessOrEqual(V03ParameterBounds.ActualDegradedOpacityCandidate, V03ParameterBounds.ActualDegradedOpacityMax);

            Assert.GreaterOrEqual(V03ParameterBounds.ActualUnavailableOpacityCandidate, V03ParameterBounds.ActualUnavailableOpacityMin);
            Assert.LessOrEqual(V03ParameterBounds.ActualUnavailableOpacityCandidate, V03ParameterBounds.ActualUnavailableOpacityMax);

            Assert.GreaterOrEqual(V03ParameterBounds.ActualDegradedContinuityCandidate, V03ParameterBounds.ActualDegradedContinuityMin);
            Assert.LessOrEqual(V03ParameterBounds.ActualDegradedContinuityCandidate, V03ParameterBounds.ActualDegradedContinuityMax);

            Assert.GreaterOrEqual(V03ParameterBounds.ActualEdgeSofteningPx1080pCandidate, V03ParameterBounds.ActualEdgeSofteningPx1080pMin);
            Assert.LessOrEqual(V03ParameterBounds.ActualEdgeSofteningPx1080pCandidate, V03ParameterBounds.ActualEdgeSofteningPx1080pMax);
        }
    }
}
