using System;
using System.Linq;
using System.Reflection;
using NUnit.Framework;

namespace SRP.V03.Tests
{
    /// <summary>
    /// 层级隔离测试（AC1）：四个只读投影类型的字段白名单必须与 V-03 合同 source_fields 严格一致。
    /// 白名单取"精确集合相等"——多一个字段、少一个字段、字段改名都会失败，
    /// 从而在类型层封死 forbidden_coupling（违例信息物理上不可达）。
    /// </summary>
    public sealed class LayerIsolationTests
    {
        private static string[] PublicInstanceFields(Type type) =>
            type.GetFields(BindingFlags.Public | BindingFlags.Instance)
                .Select(f => f.Name)
                .OrderBy(n => n, StringComparer.Ordinal)
                .ToArray();

        [Test]
        public void TargetLayerView_FieldWhitelist_MatchesContract()
        {
            CollectionAssert.AreEqual(
                new[] { "TargetCycleIndex", "TargetPhase", "TargetProgress", "TargetStepId" },
                PublicInstanceFields(typeof(TargetLayerView)));
        }

        [Test]
        public void ActualLayerView_FieldWhitelist_MatchesContract()
        {
            CollectionAssert.AreEqual(
                new[] { "ActualConfidence", "ActualCycleIndex", "ActualPhase", "ActualProgress", "ActualStepId" },
                PublicInstanceFields(typeof(ActualLayerView)));
        }

        [Test]
        public void RecoveryLayerView_FieldWhitelist_MatchesContract()
        {
            CollectionAssert.AreEqual(
                new[] { "RecoveryLocked", "RecoveryValue" },
                PublicInstanceFields(typeof(RecoveryLayerView)));
        }

        [Test]
        public void FallbackLayerView_FieldWhitelist_MatchesContract()
        {
            CollectionAssert.AreEqual(
                new[] { "FallbackReason", "FallbackState", "SignalQualityEcg", "SignalQualityResp" },
                PublicInstanceFields(typeof(FallbackLayerView)));
        }

        [Test]
        public void TargetView_CarriesNoCrossLayerFields()
        {
            // forbidden_coupling(target 行)：actual、actual_confidence、error、recovery、fallback
            var names = PublicInstanceFields(typeof(TargetLayerView));
            Assert.IsFalse(names.Any(n =>
                    n.StartsWith("Actual", StringComparison.Ordinal) ||
                    n.StartsWith("Recovery", StringComparison.Ordinal) ||
                    n.StartsWith("Fallback", StringComparison.Ordinal)),
                "target 投影出现跨层字段: " + string.Join(",", names));
        }

        [Test]
        public void ActualView_CarriesNoCrossLayerFields()
        {
            // forbidden_coupling(actual 行)：target、error、recovery
            var names = PublicInstanceFields(typeof(ActualLayerView));
            Assert.IsFalse(names.Any(n =>
                    n.StartsWith("Target", StringComparison.Ordinal) ||
                    n.StartsWith("Recovery", StringComparison.Ordinal)),
                "actual 投影出现跨层字段: " + string.Join(",", names));
        }

        [Test]
        public void RecoveryView_CarriesNoQualityField()
        {
            // forbidden_coupling(recovery 行)：quality_as_local_override —— 质量态不得进入 recovery 投影
            var names = PublicInstanceFields(typeof(RecoveryLayerView));
            Assert.IsFalse(names.Any(n => n.Contains("Quality", StringComparison.Ordinal) || n.Contains("Fallback", StringComparison.Ordinal)),
                "recovery 投影出现质量态字段: " + string.Join(",", names));
        }

        [Test]
        public void Views_CarryValuesCorrectly()
        {
            var t = new TargetLayerView("hold", 0.4f, 0, "hold_1");
            Assert.AreEqual("hold_1", t.TargetStepId);
            Assert.IsFalse(t.IsEmptyStep);

            var a = new ActualLayerView("none", 0f, null, null, 0.91f);
            Assert.IsNull(a.ActualStepId);
            Assert.IsTrue(a.IsEmptyStep);

            var r = new RecoveryLayerView(0.28f, true);
            Assert.AreEqual(0.28f, r.RecoveryValue, 1e-6f);
            Assert.IsTrue(r.RecoveryLocked);

            var fb = new FallbackLayerView(0.92f, 0.88f, "GOOD", null);
            Assert.AreEqual(0.92f, fb.SignalQualityResp, 1e-6f);
            Assert.IsNull(fb.FallbackReason);
        }
    }
}
