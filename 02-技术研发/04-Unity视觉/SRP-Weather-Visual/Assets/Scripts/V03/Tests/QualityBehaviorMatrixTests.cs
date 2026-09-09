using NUnit.Framework;

namespace SRP.V03.Tests
{
    /// <summary>
    /// quality_behavior 全矩阵表驱动测试（05 合同 40 rows 归一）。
    /// 各层行为与 technical_id/cue_mode 无关；矩阵变化必须显式改这里（合同变更哨兵）。
    /// </summary>
    public sealed class QualityBehaviorMatrixTests
    {
        [Test]
        public void TargetBehavior_MatchesContract()
        {
            Assert.AreEqual(V03TargetBehavior.ContinueTarget, V03QualityState.Good.TargetBehavior());
            Assert.AreEqual(V03TargetBehavior.ContinueTarget, V03QualityState.Degraded.TargetBehavior());
            Assert.AreEqual(V03TargetBehavior.OpenLoopTarget, V03QualityState.Unusable.TargetBehavior());
            Assert.AreEqual(V03TargetBehavior.FollowPythonSafeOpenLoopOrAbort, V03QualityState.Disconnected.TargetBehavior());
        }

        [Test]
        public void ActualBehavior_MatchesContract()
        {
            Assert.AreEqual(V03ActualBehavior.Active, V03QualityState.Good.ActualBehavior());
            Assert.AreEqual(V03ActualBehavior.ActiveLowCertainty, V03QualityState.Degraded.ActualBehavior());
            Assert.AreEqual(V03ActualBehavior.StaticBrokenOutline, V03QualityState.Unusable.ActualBehavior());
            Assert.AreEqual(V03ActualBehavior.StaticBrokenOutline, V03QualityState.Disconnected.ActualBehavior());
        }

        [Test]
        public void RecoveryBehavior_MatchesContract()
        {
            Assert.AreEqual(V03RecoveryBehavior.FollowPythonUpdate, V03QualityState.Good.RecoveryBehavior());
            Assert.AreEqual(V03RecoveryBehavior.FollowPythonCautionOrPause, V03QualityState.Degraded.RecoveryBehavior());
            Assert.AreEqual(V03RecoveryBehavior.PauseAndLockLastValue, V03QualityState.Unusable.RecoveryBehavior());
            Assert.AreEqual(V03RecoveryBehavior.PauseAndLockLastValue, V03QualityState.Disconnected.RecoveryBehavior());
        }

        [Test]
        public void FallbackBehavior_MatchesContract()
        {
            Assert.AreEqual(V03FallbackBehavior.NoExtraMarker, V03QualityState.Good.FallbackBehavior());
            Assert.AreEqual(V03FallbackBehavior.LowCertaintyOnActualOnly, V03QualityState.Degraded.FallbackBehavior());
            Assert.AreEqual(V03FallbackBehavior.TemporarilyUnavailableOnActualOnly, V03QualityState.Unusable.FallbackBehavior());
            Assert.AreEqual(V03FallbackBehavior.TemporarilyUnavailableOnActualOnly, V03QualityState.Disconnected.FallbackBehavior());
        }

        [Test]
        public void BackgroundBehavior_AlwaysUnchanged()
        {
            Assert.AreEqual(V03BackgroundBehavior.Unchanged, V03QualityState.Good.BackgroundBehavior());
            Assert.AreEqual(V03BackgroundBehavior.Unchanged, V03QualityState.Degraded.BackgroundBehavior());
            Assert.AreEqual(V03BackgroundBehavior.Unchanged, V03QualityState.Unusable.BackgroundBehavior());
            Assert.AreEqual(V03BackgroundBehavior.Unchanged, V03QualityState.Disconnected.BackgroundBehavior());
        }

        [Test]
        public void TryParseQualityState_AcceptsAllFourStates_CaseInsensitive()
        {
            Assert.IsTrue(V03QualityBehaviorMatrix.TryParseQualityState("GOOD", out var s1));
            Assert.AreEqual(V03QualityState.Good, s1);
            Assert.IsTrue(V03QualityBehaviorMatrix.TryParseQualityState("degraded", out var s2));
            Assert.AreEqual(V03QualityState.Degraded, s2);
            Assert.IsTrue(V03QualityBehaviorMatrix.TryParseQualityState(" UNUSABLE ", out var s3));
            Assert.AreEqual(V03QualityState.Unusable, s3);
            Assert.IsTrue(V03QualityBehaviorMatrix.TryParseQualityState("DISCONNECTED", out var s4));
            Assert.AreEqual(V03QualityState.Disconnected, s4);
        }

        [Test]
        public void TryParseQualityState_RejectsUnknownValue()
        {
            Assert.IsFalse(V03QualityBehaviorMatrix.TryParseQualityState("PERFECT", out _));
            Assert.IsFalse(V03QualityBehaviorMatrix.TryParseQualityState(null, out _));
        }

        [Test]
        public void ModuleMap_MapsSceneModulesPerR01()
        {
            Assert.IsTrue(V03ModuleMap.TryMapSceneModule("storm", out var m1));
            Assert.AreEqual("storm", m1);
            Assert.IsTrue(V03ModuleMap.TryMapSceneModule("heat", out var m2));
            Assert.AreEqual("scorching", m2);
            Assert.IsTrue(V03ModuleMap.TryMapSceneModule("snow", out var m3));
            Assert.AreEqual("blizzard", m3);
            Assert.IsTrue(V03ModuleMap.TryMapSceneModule("fade", out var m4));
            Assert.AreEqual("fading", m4);
            Assert.IsFalse(V03ModuleMap.TryMapSceneModule("rain", out _));
        }

        [Test]
        public void ModuleMap_V22RequiredModules_AreStormAndFade()
        {
            Assert.IsTrue(V03ModuleMap.RequiresV22StepBinding("storm"));
            Assert.IsTrue(V03ModuleMap.RequiresV22StepBinding("fade"));
            Assert.IsFalse(V03ModuleMap.RequiresV22StepBinding("heat"));
            Assert.IsFalse(V03ModuleMap.RequiresV22StepBinding("snow"));
        }
    }
}
