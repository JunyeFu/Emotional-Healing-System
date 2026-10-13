using NUnit.Framework;
using UnityEngine;

namespace SRP.V03.Tests
{
    /// <summary>
    /// 编排器投影拆分最小验证：合法帧 → 四层各收各的投影；非法帧拒收计数；
    /// 无帧保持现状；链路级降级分发；segment 边界重置锁定。
    /// 层间零串扰的完整负测试矩阵在 D3（设计文档 §7 阶段3）。
    /// </summary>
    public sealed class V03SceneAdapterTickTests
    {
        /// <summary>golden frame20（storm，GOOD）—— 与 V03FrameGoldenTests.Frame20 同源（inputs/10 jsonl）。</summary>
        private const string Frame20Json = @"{""schema_version"":""2.2"",""message_type"":""telemetry_frame"",""session_id"":""S-20260807-0001"",""frame_seq"":20,""clock_domain_id"":""python-session-1"",""source_monotonic_ns"":4000000,""received_monotonic_ns"":4050000,""sent_monotonic_ns"":4100000,""clock_offset_ns"":15000,""clock_drift_ppm"":0.4,""sync_uncertainty_ns"":8000,""module_id"":""storm"",""module_position"":0,""segment"":""closed_loop"",""target_phase"":""hold"",""target_progress"":0.4,""actual_phase"":""inhale"",""actual_progress"":0.35,""actual_confidence"":0.91,""recovery_value"":0.28,""recovery_locked"":false,""signal_quality"":{""resp"":0.92,""ecg"":0.88},""fallback_state"":""GOOD"",""fallback_reason"":null,""resp_device_state"":""CONNECTED"",""ecg_device_state"":""CONNECTED"",""cue_mode"":""scene_native"",""runtime_mode"":""formal_stage_1"",""policy_decision_id"":""PD-0001"",""target_cycle_index"":0,""target_step_id"":""hold_1"",""actual_cycle_index"":0,""actual_step_id"":""inhale_1""}";

        private sealed class FakeSource : IV03TelemetrySource
        {
            public V03FrameDto Next { get; set; }
            public bool HasFrame { get; set; }
            public V03LinkState LinkState { get; set; } = V03LinkState.Linked;

            public bool TryGetFrame(out V03FrameDto frame)
            {
                frame = HasFrame ? Next : null;
                return HasFrame && Next != null;
            }
        }

        private GameObject root;
        private FakeSource source;
        private V03SceneAdapter adapter;
        private TargetLayerAdapter target;
        private ActualLayerAdapter actual;
        private RecoveryLayerAdapter recovery;
        private FallbackLayerAdapter fallback;
        private BackgroundPass background;

        [SetUp]
        public void SetUp()
        {
            root = new GameObject("v03-scene");
            adapter = root.AddComponent<V03SceneAdapter>();
            target = root.AddComponent<TargetLayerAdapter>();
            actual = root.AddComponent<ActualLayerAdapter>();
            recovery = root.AddComponent<RecoveryLayerAdapter>();
            fallback = root.AddComponent<FallbackLayerAdapter>();
            background = root.AddComponent<BackgroundPass>();
            adapter.ConfigureLayers(target, actual, recovery, fallback, background);
            source = new FakeSource();
            adapter.Bind(source);
        }

        [TearDown]
        public void TearDown()
        {
            if (root != null) Object.DestroyImmediate(root);
        }

        [Test]
        public void Tick_ValidFrame_ProjectsEachLayerOwnView()
        {
            Assert.IsTrue(V03JsonFrameParser.TryParse(Frame20Json, out var frame, out var err), err);
            source.Next = frame;
            source.HasFrame = true;

            Assert.IsTrue(adapter.Tick());

            // target 只见 target 投影
            Assert.AreEqual("hold", target.CurrentPhase);
            Assert.AreEqual(0.4f, target.CurrentProgress, 1e-6f);
            Assert.AreEqual("hold_1", target.CurrentStepId);
            Assert.AreEqual(0, target.CurrentCycleIndex.Value);
            Assert.IsFalse(target.IsAborted);
            Assert.IsFalse(target.IsOpenLoopActive);

            // actual 只见 actual 投影（frame24 隐藏规则不适用于有相位的 frame20）
            Assert.IsFalse(actual.IsHidden);
            Assert.AreEqual("inhale", actual.CurrentPhase);
            Assert.AreEqual(0.91f, actual.CurrentConfidence, 1e-6f);
            Assert.AreEqual(V03ActualOpacityMode.Full, actual.CurrentOpacityMode);

            // recovery 跟随（首帧直通）
            Assert.AreEqual(0.28f, recovery.CurrentOutputValue, 1e-6f);
            Assert.IsFalse(recovery.IsLocked);

            // fallback GOOD 无标记
            Assert.AreEqual(V03FallbackMarker.None, fallback.CurrentMarker);
            Assert.AreEqual(V03QualityState.Good, adapter.LastQualityState);
            Assert.AreEqual(1, adapter.AppliedFrameCount);
            Assert.AreEqual(0, adapter.RejectedFrameCount);
        }

        [Test]
        public void Tick_InvalidFrame_RejectedAndCounted_LayersKeepState()
        {
            Assert.IsTrue(V03JsonFrameParser.TryParse(Frame20Json, out var good, out _));
            source.Next = good;
            source.HasFrame = true;
            Assert.IsTrue(adapter.Tick());

            // 构造非法帧：storm 有 target phase 但缺 step 实例（E_TARGET_EMPTY_STEP_PHASE + E_V22_BINDING_MISSING）
            var bad = new V03FrameDto
            {
                SchemaVersion = "2.2",
                MessageType = "telemetry_frame",
                ModuleId = "storm",
                Segment = "closed_loop",
                FallbackState = "GOOD",
                TargetPhase = "inhale",
                TargetProgress = 0.4f,
            };
            source.Next = bad;

            Assert.IsFalse(adapter.Tick());
            Assert.AreEqual(1, adapter.RejectedFrameCount, "非法帧拒收必须计数（不静默丢弃）");
            Assert.AreEqual(1, adapter.AppliedFrameCount);

            // 各层保持上一帧状态
            Assert.AreEqual("hold", target.CurrentPhase);
            Assert.AreEqual(0.28f, recovery.CurrentOutputValue, 1e-6f);
        }

        [Test]
        public void Tick_NoFrame_KeepsState_AndNotCountedAsRejected()
        {
            Assert.IsTrue(V03JsonFrameParser.TryParse(Frame20Json, out var frame, out _));
            source.Next = frame;
            source.HasFrame = true;
            Assert.IsTrue(adapter.Tick());

            source.HasFrame = false;
            Assert.IsFalse(adapter.Tick());
            Assert.AreEqual(1, adapter.AppliedFrameCount);
            Assert.AreEqual(0, adapter.RejectedFrameCount, "无新帧不算拒收");
        }

        [Test]
        public void NotifyLinkDown_Unusable_LocksRecovery_AndStillsActual()
        {
            Assert.IsTrue(V03JsonFrameParser.TryParse(Frame20Json, out var frame, out _));
            source.Next = frame;
            source.HasFrame = true;
            Assert.IsTrue(adapter.Tick());
            Assert.IsFalse(recovery.IsLocked);

            adapter.NotifyLinkDown(V03LinkState.Unusable);

            Assert.IsTrue(recovery.IsLocked, "链路级 UNUSABLE → PauseAndLock");
            Assert.IsTrue(actual.IsStaticFrame, "链路级 UNUSABLE → actual 静帧 broken outline");
            Assert.AreEqual(V03FallbackMarker.TemporarilyUnavailable, fallback.CurrentMarker);
            Assert.AreEqual(V03QualityState.Unusable, adapter.LastQualityState);
        }

        [Test]
        public void NotifyLinkDown_Disconnected_AbortsTargetToIdleSafety()
        {
            Assert.IsTrue(V03JsonFrameParser.TryParse(Frame20Json, out var frame, out _));
            source.Next = frame;
            source.HasFrame = true;
            adapter.Tick();

            adapter.NotifyLinkDown(V03LinkState.Disconnected);

            Assert.IsTrue(target.IsAborted, "链路级 DISCONNECTED 无安全开环标记 → Abort 回 idle 安全态");
            Assert.AreEqual("none", target.CurrentPhase);
            Assert.AreEqual(V03QualityState.Disconnected, adapter.LastQualityState);
        }

        [Test]
        public void Tick_SegmentChange_ResetsRecoveryLock_AndFiresBackgroundHook()
        {
            Assert.IsTrue(V03JsonFrameParser.TryParse(Frame20Json, out var f20, out _));
            source.Next = f20;
            source.HasFrame = true;
            adapter.Tick();

            // 同 segment 内锁定（UNUSABLE）
            f20.FallbackState = "UNUSABLE";
            f20.FallbackReason = "resp lost";
            f20.RecoveryValue = 0.9f;
            adapter.Tick();
            Assert.IsTrue(recovery.IsLocked);

            // segment 变化 + 恢复 GOOD → 边界重置解锁 → 新段首帧直通
            f20.Segment = "closed_loop_cooldown";
            f20.FallbackState = "GOOD";
            f20.FallbackReason = null;
            f20.RecoveryValue = 0.5f;
            adapter.Tick();

            Assert.IsFalse(recovery.IsLocked, "会话边界重置解锁");
            Assert.AreEqual(0.5f, recovery.CurrentOutputValue, 1e-6f, "重置后首帧直通新值");
            Assert.AreEqual("closed_loop_cooldown", background.LastSessionSegment);
            Assert.AreEqual(2, background.SegmentChangeCount);
        }

        [Test]
        public void Tick_WithoutBind_ReturnsFalse()
        {
            var bare = new GameObject("bare-adapter").AddComponent<V03SceneAdapter>();
            try
            {
                Assert.IsFalse(bare.Tick());
                Assert.IsFalse(bare.IsBound);
            }
            finally
            {
                Object.DestroyImmediate(bare.gameObject);
            }
        }
    }
}
