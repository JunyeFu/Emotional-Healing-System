using NUnit.Framework;
using UnityEngine;

namespace SRP.V03.Tests
{
    /// <summary>
    /// AC3 前半：DegradationPolicy cap 语义 + 标记作用域。
    /// VISIBLE_CERTAINTY = min(actual_confidence_envelope, fallback_state_cap)。
    /// </summary>
    public sealed class DegradationPolicyTests
    {
        private GameObject go;
        private FallbackLayerAdapter adapter;

        [SetUp]
        public void SetUp()
        {
            go = new GameObject("fallback-adapter");
            adapter = go.AddComponent<FallbackLayerAdapter>();
        }

        [TearDown]
        public void TearDown()
        {
            if (go != null) Object.DestroyImmediate(go);
        }

        private static FallbackLayerView View(string state, string reason = null) =>
            new FallbackLayerView(0.92f, 0.88f, state, reason);

        [Test]
        public void Good_NoMarker_VisibleCertaintyEqualsConfidence()
        {
            adapter.Apply(View("GOOD"), V03FallbackBehavior.NoExtraMarker, 0.85f);
            Assert.AreEqual(V03FallbackMarker.None, adapter.CurrentMarker);
            Assert.AreEqual(0.85f, adapter.CurrentVisibleCertainty, 1e-6f, "GOOD cap=1.0，不额外限制");
            Assert.IsTrue(adapter.HasCertaintyOutput);
        }

        [Test]
        public void Degraded_CapsVisibleCertaintyAt0_7()
        {
            adapter.Apply(View("DEGRADED", "signal noisy"), V03FallbackBehavior.LowCertaintyOnActualOnly, 0.9f);
            Assert.AreEqual(0.7f, adapter.CurrentVisibleCertainty, 1e-6f, "min(0.9, cap=0.7) = 0.7");
            Assert.AreEqual(V03FallbackMarker.LowCertainty, adapter.CurrentMarker);
        }

        [Test]
        public void Degraded_KeepsLowerConfidence_UnderCap()
        {
            adapter.Apply(View("DEGRADED"), V03FallbackBehavior.LowCertaintyOnActualOnly, 0.55f);
            Assert.AreEqual(0.55f, adapter.CurrentVisibleCertainty, 1e-6f, "min 语义：低于 cap 不抬高");
        }

        [Test]
        public void UnusableAndDisconnected_MarkTemporarilyUnavailable()
        {
            adapter.Apply(View("UNUSABLE", "resp lost"), V03FallbackBehavior.TemporarilyUnavailableOnActualOnly, 0.5f);
            Assert.AreEqual(V03FallbackMarker.TemporarilyUnavailable, adapter.CurrentMarker);
            Assert.AreEqual(0f, adapter.CurrentVisibleCertainty);
            Assert.IsFalse(adapter.HasCertaintyOutput);

            adapter.Apply(View("DISCONNECTED", "link down"), V03FallbackBehavior.TemporarilyUnavailableOnActualOnly, 0.5f);
            Assert.AreEqual(V03FallbackMarker.TemporarilyUnavailable, adapter.CurrentMarker);
        }

        [Test]
        public void CapCandidate_IsAnnotatedConstant_0_7()
        {
            Assert.AreEqual(0.7f, V03ParameterBounds.DegradedVisibilityCapCandidate, 1e-6f);
            Assert.AreEqual("U-03_DEGRADED_VISIBILITY_EVIDENCE", V03ParameterBounds.DegradedCapFreezeGate,
                "cap 冻结 gate 必须显式指向 U-03 证据任务");
        }

        [Test]
        public void Good_Cap_Is_One()
        {
            Assert.AreEqual(1.0f, V03ParameterBounds.GoodVisibilityCap, 1e-6f);
        }

        [Test]
        public void Marker_Scope_IsActualCarrierOnly()
        {
            Assert.AreEqual("ACTUAL_CARRIER_ONLY", FallbackLayerAdapter.MarkerScope,
                "fallback 标记作用域恒为 actual 载体（合同 fallback 行 ON_ACTUAL_ONLY）");
        }

        [Test]
        public void Reason_IsCarriedThrough()
        {
            adapter.Apply(View("DEGRADED", "resp quality low"), V03FallbackBehavior.LowCertaintyOnActualOnly, 0.9f);
            Assert.AreEqual("resp quality low", adapter.CurrentReason);
        }
    }
}
