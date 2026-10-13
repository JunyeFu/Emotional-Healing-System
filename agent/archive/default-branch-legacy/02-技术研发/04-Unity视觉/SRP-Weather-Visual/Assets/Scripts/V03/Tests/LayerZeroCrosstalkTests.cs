using System;
using NUnit.Framework;
using UnityEngine;

namespace SRP.V03.Tests
{
    /// <summary>
    /// D3（设计文档 §7 阶段3）：层间零串扰运行时负测试矩阵。
    /// 与 D1 类型级白名单（LayerIsolationTests）互补：
    ///   D1 证明投影类型上不可串扰；本文件在完整编排链
    ///   （V03SceneAdapter + 四层 Adapter + BackgroundPass + 桩遥测源）上证明——
    ///   AC1：单层字段变化注入后，其他层运行时状态逐字段冻结（负测试）；
    ///   AC2：Recovery 锁定跨质量波动稳定、解锁只发生在会话边界；
    ///   AC3：链路降级不伪造成功（无置信输出、不冒充应用帧），背景零节律泄露。
    /// 非法帧拒收路径的层冻结与恢复也在此收口（不静默、不留半应用状态）。
    /// </summary>
    public sealed class LayerZeroCrosstalkTests
    {
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
            root = new GameObject("v03-crosstalk");
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
            if (root != null) UnityEngine.Object.DestroyImmediate(root);
        }

        /// <summary>合法 storm 帧（v2.2 步骤绑定 REQUIRED → target/actual 均带步骤实例）。</summary>
        private static V03FrameDto Frame(int seq) => new V03FrameDto
        {
            SchemaVersion = "2.2",
            MessageType = "telemetry_frame",
            SessionId = "S-D3",
            FrameSeq = seq,
            ModuleId = "storm",
            ModulePosition = 0,
            Segment = "closed_loop",
            CueMode = "scene_native",
            RuntimeMode = "formal_stage_1",
            FallbackState = "GOOD",
            TargetPhase = "hold",
            TargetProgress = 0.4f,
            TargetCycleIndex = 0,
            TargetStepId = "hold_1",
            ActualPhase = "inhale",
            ActualProgress = 0.35f,
            ActualCycleIndex = 0,
            ActualStepId = "inhale_1",
            ActualConfidence = 0.91f,
            RecoveryValue = 0.28f,
            RecoveryLocked = false,
            SignalQualityResp = 0.92f,
            SignalQualityEcg = 0.88f,
        };

        private void Tick(V03FrameDto frame)
        {
            source.Next = frame;
            source.HasFrame = true;
            Assert.IsTrue(adapter.Tick(),
                $"frame {frame.FrameSeq} must pass validation; a failing precondition poisons later asserts");
        }

        // ------------------------------------------------------------------
        // AC1：单层变化 → 其他层运行时冻结（编排链端到端）
        // ------------------------------------------------------------------

        [Test]
        public void TargetChange_Isolated_OtherLayersFrozen()
        {
            Tick(Frame(1));

            bool aHidden = actual.IsHidden;
            var aMode = actual.CurrentOpacityMode;
            float aOp = actual.CurrentOpacity;
            float aCont = actual.CurrentContinuity;
            float aEdge = actual.CurrentEdgeSofteningPx;
            bool aStatic = actual.IsStaticFrame;
            string aPhase = actual.CurrentPhase;
            float aProg = actual.CurrentProgress;
            string aStep = actual.CurrentStepId;
            int? aCyc = actual.CurrentCycleIndex;
            float aConf = actual.CurrentConfidence;
            float rVal = recovery.CurrentOutputValue;
            bool rLocked = recovery.IsLocked;
            bool rHas = recovery.HasOutputValue;
            var fbMarker = fallback.CurrentMarker;
            float fbCert = fallback.CurrentVisibleCertainty;
            bool fbHas = fallback.HasCertaintyOutput;
            string fbReason = fallback.CurrentReason;

            var f2 = Frame(2);
            f2.TargetPhase = "inhale";
            f2.TargetProgress = 0.6f;
            f2.TargetStepId = "inhale_2";
            f2.TargetCycleIndex = 1;
            Tick(f2);

            // 对照：target 已更新
            Assert.AreEqual("inhale", target.CurrentPhase);
            Assert.AreEqual(0.6f, target.CurrentProgress, 1e-6f);
            Assert.AreEqual("inhale_2", target.CurrentStepId);
            Assert.AreEqual(1, target.CurrentCycleIndex.Value);

            // 负断言：actual 全字段冻结
            Assert.AreEqual(aHidden, actual.IsHidden, "actual.IsHidden leaked target change");
            Assert.AreEqual(aMode, actual.CurrentOpacityMode, "actual.OpacityMode leaked target change");
            Assert.AreEqual(aOp, actual.CurrentOpacity, 1e-6f, "actual.Opacity leaked target change");
            Assert.AreEqual(aCont, actual.CurrentContinuity, 1e-6f, "actual.Continuity leaked target change");
            Assert.AreEqual(aEdge, actual.CurrentEdgeSofteningPx, 1e-6f, "actual.EdgeSoftening leaked target change");
            Assert.AreEqual(aStatic, actual.IsStaticFrame, "actual.IsStaticFrame leaked target change");
            Assert.AreEqual(aPhase, actual.CurrentPhase, "actual.Phase leaked target change");
            Assert.AreEqual(aProg, actual.CurrentProgress, 1e-6f, "actual.Progress leaked target change");
            Assert.AreEqual(aStep, actual.CurrentStepId, "actual.StepId leaked target change");
            Assert.AreEqual(aCyc, actual.CurrentCycleIndex, "actual.CycleIndex leaked target change");
            Assert.AreEqual(aConf, actual.CurrentConfidence, 1e-6f, "actual.Confidence leaked target change");
            // 负断言：recovery 冻结
            Assert.AreEqual(rVal, recovery.CurrentOutputValue, 1e-6f, "recovery.OutputValue leaked target change");
            Assert.AreEqual(rLocked, recovery.IsLocked);
            Assert.AreEqual(rHas, recovery.HasOutputValue);
            // 负断言：fallback 冻结
            Assert.AreEqual(fbMarker, fallback.CurrentMarker, "fallback.Marker leaked target change");
            Assert.AreEqual(fbCert, fallback.CurrentVisibleCertainty, 1e-6f, "fallback.Certainty leaked target change");
            Assert.AreEqual(fbHas, fallback.HasCertaintyOutput);
            Assert.AreEqual(fbReason, fallback.CurrentReason);
        }

        [Test]
        public void ActualPhaseProgressChange_Isolated_OtherLayersFrozen()
        {
            Tick(Frame(1));

            string tPhase = target.CurrentPhase;
            float tProg = target.CurrentProgress;
            string tStep = target.CurrentStepId;
            int? tCyc = target.CurrentCycleIndex;
            bool tAbort = target.IsAborted;
            bool tOpenLoop = target.IsOpenLoopActive;
            float rVal = recovery.CurrentOutputValue;
            bool rLocked = recovery.IsLocked;
            var fbMarker = fallback.CurrentMarker;
            float fbCert = fallback.CurrentVisibleCertainty;
            string fbReason = fallback.CurrentReason;

            var f2 = Frame(2);
            f2.ActualPhase = "exhale";
            f2.ActualProgress = 0.7f;
            f2.ActualStepId = "exhale_1";
            f2.ActualCycleIndex = 1;
            Tick(f2);

            // 对照：actual 已更新（envelope = ActualConfidence 未变）
            Assert.AreEqual("exhale", actual.CurrentPhase);
            Assert.AreEqual(0.7f, actual.CurrentProgress, 1e-6f);

            // 负断言：target 全字段冻结
            Assert.AreEqual(tPhase, target.CurrentPhase, "target.Phase leaked actual change");
            Assert.AreEqual(tProg, target.CurrentProgress, 1e-6f, "target.Progress leaked actual change");
            Assert.AreEqual(tStep, target.CurrentStepId, "target.StepId leaked actual change");
            Assert.AreEqual(tCyc, target.CurrentCycleIndex, "target.CycleIndex leaked actual change");
            Assert.AreEqual(tAbort, target.IsAborted, "target.IsAborted leaked actual change");
            Assert.AreEqual(tOpenLoop, target.IsOpenLoopActive, "target.IsOpenLoop leaked actual change");
            // 负断言：recovery 冻结
            Assert.AreEqual(rVal, recovery.CurrentOutputValue, 1e-6f, "recovery.OutputValue leaked actual change");
            Assert.AreEqual(rLocked, recovery.IsLocked);
            // 负断言：fallback 冻结（envelope 未变 → 无任何通道流入）
            Assert.AreEqual(fbMarker, fallback.CurrentMarker);
            Assert.AreEqual(fbCert, fallback.CurrentVisibleCertainty, 1e-6f);
            Assert.AreEqual(fbReason, fallback.CurrentReason);
        }

        [Test]
        public void ActualConfidenceChange_FlowsOnlyThroughEnvelope()
        {
            Tick(Frame(1));
            Assert.AreEqual(0.91f, fallback.CurrentVisibleCertainty, 1e-6f);

            string tPhase = target.CurrentPhase;
            float rVal = recovery.CurrentOutputValue;
            var fbMarker = fallback.CurrentMarker;
            string fbReason = fallback.CurrentReason;

            var f2 = Frame(2);
            f2.ActualConfidence = 0.55f;
            Tick(f2);

            // 负断言：target / recovery 冻结
            Assert.AreEqual(tPhase, target.CurrentPhase, "target.Phase leaked confidence change");
            Assert.AreEqual(rVal, recovery.CurrentOutputValue, 1e-6f, "recovery.OutputValue leaked confidence change");
            // 合法唯一通道：GOOD cap=1.0 → VisibleCertainty = envelope 直通
            Assert.AreEqual(0.55f, fallback.CurrentVisibleCertainty, 1e-6f,
                "confidence must reach fallback only via the projected envelope (GOOD cap = 1.0)");
            // 标记与原因不随 confidence 变化
            Assert.AreEqual(fbMarker, fallback.CurrentMarker, "fallback.Marker leaked confidence change");
            Assert.AreEqual(fbReason, fallback.CurrentReason);
        }

        [Test]
        public void RecoveryValueChange_Isolated_OtherLayersFrozen()
        {
            Tick(Frame(1));

            string tPhase = target.CurrentPhase;
            float tProg = target.CurrentProgress;
            bool aHidden = actual.IsHidden;
            float aConf = actual.CurrentConfidence;
            var aMode = actual.CurrentOpacityMode;
            var fbMarker = fallback.CurrentMarker;
            float fbCert = fallback.CurrentVisibleCertainty;
            string fbReason = fallback.CurrentReason;

            var f2 = Frame(2);
            f2.RecoveryValue = 0.95f;
            Tick(f2);

            // 负断言：target / actual / fallback 全冻结
            Assert.AreEqual(tPhase, target.CurrentPhase, "target.Phase leaked recovery change");
            Assert.AreEqual(tProg, target.CurrentProgress, 1e-6f, "target.Progress leaked recovery change");
            Assert.AreEqual(aHidden, actual.IsHidden);
            Assert.AreEqual(aConf, actual.CurrentConfidence, 1e-6f);
            Assert.AreEqual(aMode, actual.CurrentOpacityMode);
            Assert.AreEqual(fbMarker, fallback.CurrentMarker, "fallback.Marker leaked recovery change");
            Assert.AreEqual(fbCert, fallback.CurrentVisibleCertainty, 1e-6f, "fallback.Certainty leaked recovery change");
            Assert.AreEqual(fbReason, fallback.CurrentReason);

            // 对照：recovery 按低通朝新值推进（0.28, 0.95 开区间；不依赖具体 tau）
            Assert.Greater(recovery.CurrentOutputValue, 0.28f + 1e-5f, "recovery must follow new value");
            Assert.Less(recovery.CurrentOutputValue, 0.95f - 1e-5f, "low-pass must not jump to target value");
            Assert.IsFalse(recovery.IsLocked);
        }

        [Test]
        public void SignalQualityChange_Isolated_NoGlobalQualityShift()
        {
            Tick(Frame(1));

            string tPhase = target.CurrentPhase;
            float aConf = actual.CurrentConfidence;
            var aMode = actual.CurrentOpacityMode;
            float rVal = recovery.CurrentOutputValue;
            bool rLocked = recovery.IsLocked;
            var fbMarker = fallback.CurrentMarker;
            float fbCert = fallback.CurrentVisibleCertainty;

            // 只动 signal_quality 与 fallback_reason —— fallback_state 不变 → 全局质量态不变
            var f2 = Frame(2);
            f2.SignalQualityResp = 0.55f;
            f2.SignalQualityEcg = 0.6f;
            f2.FallbackReason = "resp drifting";
            Tick(f2);

            Assert.AreEqual(tPhase, target.CurrentPhase, "target leaked signal-quality change");
            Assert.AreEqual(aConf, actual.CurrentConfidence, 1e-6f);
            Assert.AreEqual(aMode, actual.CurrentOpacityMode);
            Assert.AreEqual(rVal, recovery.CurrentOutputValue, 1e-6f, "recovery leaked signal-quality change");
            Assert.AreEqual(rLocked, recovery.IsLocked);
            Assert.AreEqual(fbMarker, fallback.CurrentMarker);
            Assert.AreEqual(fbCert, fallback.CurrentVisibleCertainty, 1e-6f);
            // fallback 自身仅 Reason 更新（本层输入）
            Assert.AreEqual("resp drifting", fallback.CurrentReason);
        }

        // ------------------------------------------------------------------
        // AC2：锁定跨质量波动稳定；解锁只在会话边界
        // ------------------------------------------------------------------

        [Test]
        public void Lock_HoldsAcrossMixedQualityFrames_AndDoesNotLeak()
        {
            Tick(Frame(1)); // recovery 首帧直通 0.28

            var f2 = Frame(2);
            f2.FallbackState = "UNUSABLE";
            f2.FallbackReason = "resp lost";
            f2.RecoveryValue = 0.9f;
            Tick(f2);
            Assert.IsTrue(recovery.IsLocked);
            Assert.AreEqual(0.28f, recovery.CurrentOutputValue, 1e-6f, "locked value = last filtered output");

            var rng = new System.Random(7);
            for (int i = 0; i < 20; i++)
            {
                var f = Frame(3 + i);
                f.FallbackState = (i % 2 == 0) ? "GOOD" : "DEGRADED";
                f.RecoveryValue = (float)rng.NextDouble();
                Tick(f);
                Assert.AreEqual(0.28f, recovery.CurrentOutputValue, 1e-6f,
                    $"frame {3 + i} broke the lock (value={f.RecoveryValue})");
                Assert.IsTrue(recovery.IsLocked, $"frame {3 + i} unlocked mid-session");
            }
            Assert.AreEqual(20, recovery.LockedFrameIgnoreCount);

            // 锁定不外溢：target/actual 在混合质量下持续正常应用
            Assert.AreEqual(22, adapter.AppliedFrameCount, "every valid frame must still be applied");
            Assert.IsFalse(target.IsAborted, "GOOD/DEGRADED must not abort target");
            Assert.IsFalse(target.IsOpenLoopActive, "last frame GOOD → open-loop off");
            Assert.IsFalse(actual.IsHidden, "actual must keep rendering under mixed quality");
            Assert.IsFalse(actual.IsStaticFrame, "last frame GOOD → not static");
        }

        [Test]
        public void Unlock_OnlyAtSessionBoundary_ThenFollowsAgain()
        {
            Tick(Frame(1));

            var f2 = Frame(2);
            f2.FallbackState = "UNUSABLE";
            f2.RecoveryValue = 0.9f;
            Tick(f2);
            Assert.IsTrue(recovery.IsLocked);

            // 同段 10 帧 GOOD：quality 恢复不解锁
            for (int i = 0; i < 10; i++)
            {
                Tick(Frame(3 + i));
                Assert.IsTrue(recovery.IsLocked, $"frame {3 + i}: quality recovery must not unlock");
            }
            Assert.AreEqual(10, recovery.LockedFrameIgnoreCount);

            // segment 边界：解锁 + 首帧直通 + 背景钩子记录一次
            var fb = Frame(13);
            fb.Segment = "closed_loop_cooldown";
            fb.RecoveryValue = 0.5f;
            Tick(fb);
            Assert.IsFalse(recovery.IsLocked, "session boundary must unlock");
            Assert.AreEqual(0.5f, recovery.CurrentOutputValue, 1e-6f, "first frame after reset passes through");
            Assert.AreEqual("closed_loop_cooldown", background.LastSessionSegment);
            Assert.AreEqual(2, background.SegmentChangeCount, "segment change fires hook exactly once");

            // 边界后恢复低通跟随（第二帧不直通）
            var fc = Frame(14);
            fc.Segment = "closed_loop_cooldown";
            fc.RecoveryValue = 0.8f;
            Tick(fc);
            Assert.Greater(recovery.CurrentOutputValue, 0.5f + 1e-5f, "following resumes after reset");
            Assert.Less(recovery.CurrentOutputValue, 0.8f - 1e-5f, "post-reset frames go through low-pass, not passthrough");
            Assert.AreEqual(2, background.SegmentChangeCount, "same-segment frames must not re-fire the hook");
        }

        // ------------------------------------------------------------------
        // AC3：降级不伪造成功；背景零节律泄露
        // ------------------------------------------------------------------

        [Test]
        public void LinkDown_NoFakeSuccess_CountersAndOutputsHonest()
        {
            Tick(Frame(1));
            Assert.AreEqual(1, adapter.AppliedFrameCount);
            Assert.AreEqual(0, adapter.RejectedFrameCount);

            adapter.NotifyLinkDown(V03LinkState.Unusable);

            Assert.AreEqual(V03QualityState.Unusable, adapter.LastQualityState);
            Assert.AreEqual(1, adapter.AppliedFrameCount, "link-down must not be counted as an applied frame");
            Assert.AreEqual(0, adapter.RejectedFrameCount, "link-down is not a rejected frame either");
            // 不伪造置信输出
            Assert.IsFalse(fallback.HasCertaintyOutput, "degraded state must not fake certainty output");
            Assert.AreEqual(0f, fallback.CurrentVisibleCertainty);
            Assert.AreEqual(V03FallbackMarker.TemporarilyUnavailable, fallback.CurrentMarker);
            // 各层诚实降级
            Assert.IsTrue(actual.IsStaticFrame);
            Assert.AreEqual(V03ActualOpacityMode.Unavailable, actual.CurrentOpacityMode);
            Assert.IsTrue(recovery.IsLocked, "UNUSABLE → pause and lock");
            Assert.IsFalse(target.IsAborted, "UNUSABLE → open-loop, not abort");
            Assert.IsTrue(target.IsOpenLoopActive);
        }

        [Test]
        public void LinkDown_Recovery_ResumesHonestOutputs()
        {
            Tick(Frame(1));
            adapter.NotifyLinkDown(V03LinkState.Disconnected);
            Assert.IsTrue(target.IsAborted, "DISCONNECTED without safe open-loop flag → abort to idle");

            source.LinkState = V03LinkState.Linked;
            var f2 = Frame(2);
            f2.TargetPhase = "inhale";
            f2.TargetStepId = "inhale_2";
            f2.TargetCycleIndex = 1;
            Tick(f2);

            Assert.AreEqual(V03QualityState.Good, adapter.LastQualityState);
            Assert.AreEqual(2, adapter.AppliedFrameCount, "recovered frame must be applied exactly once more");
            Assert.AreEqual(0, adapter.RejectedFrameCount);
            Assert.IsTrue(fallback.HasCertaintyOutput, "resume must honestly rebuild certainty output");
            Assert.AreEqual(V03FallbackMarker.None, fallback.CurrentMarker);
            Assert.IsFalse(target.IsAborted, "GOOD frame must leave abort state");
            Assert.AreEqual("inhale", target.CurrentPhase);
        }

        [Test]
        public void Background_ZeroRhythmLeakage_OverRhythmAndQualityNoise()
        {
            var rng = new System.Random(11);
            string[] phases = { "inhale", "hold", "exhale", "hold" };
            for (int i = 0; i < 50; i++)
            {
                var f = Frame(1 + i);
                f.TargetPhase = phases[i % 4];
                f.TargetProgress = (float)rng.NextDouble();
                f.ActualConfidence = 0.3f + 0.6f * (float)rng.NextDouble();
                f.RecoveryValue = (float)rng.NextDouble();
                if (i % 5 == 4) f.FallbackState = "DEGRADED";
                Tick(f);
                Assert.AreEqual(1, background.SegmentChangeCount,
                    $"frame {1 + i}: rhythm/quality noise leaked into background");
                Assert.AreEqual("closed_loop", background.LastSessionSegment);
            }
            Assert.AreEqual(50, adapter.AppliedFrameCount);
        }

        // ------------------------------------------------------------------
        // 非法帧拒收：全层冻结 + 恢复不留半应用状态
        // ------------------------------------------------------------------

        [Test]
        public void RejectedFrame_AllLayersFullyFrozen()
        {
            Tick(Frame(1));

            string tPhase = target.CurrentPhase;
            float tProg = target.CurrentProgress;
            string tStep = target.CurrentStepId;
            int? tCyc = target.CurrentCycleIndex;
            bool tAbort = target.IsAborted;
            bool tOpenLoop = target.IsOpenLoopActive;
            bool aHidden = actual.IsHidden;
            var aMode = actual.CurrentOpacityMode;
            float aOp = actual.CurrentOpacity;
            bool aStatic = actual.IsStaticFrame;
            string aPhase = actual.CurrentPhase;
            float aConf = actual.CurrentConfidence;
            float rVal = recovery.CurrentOutputValue;
            bool rLocked = recovery.IsLocked;
            int rIgnore = recovery.LockedFrameIgnoreCount;
            var fbMarker = fallback.CurrentMarker;
            float fbCert = fallback.CurrentVisibleCertainty;
            string fbReason = fallback.CurrentReason;
            int bgCount = background.SegmentChangeCount;

            var bad = Frame(2);
            bad.FallbackState = "BAD_STATE"; // E_FALLBACK_STATE
            source.Next = bad;
            source.HasFrame = true;

            Assert.IsFalse(adapter.Tick(), "invalid frame must be rejected");
            Assert.AreEqual(1, adapter.RejectedFrameCount, "rejection must be counted (never silent)");
            Assert.AreEqual(1, adapter.AppliedFrameCount);

            Assert.AreEqual(tPhase, target.CurrentPhase, "target.Phase mutated on rejected frame");
            Assert.AreEqual(tProg, target.CurrentProgress, 1e-6f);
            Assert.AreEqual(tStep, target.CurrentStepId);
            Assert.AreEqual(tCyc, target.CurrentCycleIndex);
            Assert.AreEqual(tAbort, target.IsAborted);
            Assert.AreEqual(tOpenLoop, target.IsOpenLoopActive);
            Assert.AreEqual(aHidden, actual.IsHidden, "actual mutated on rejected frame");
            Assert.AreEqual(aMode, actual.CurrentOpacityMode);
            Assert.AreEqual(aOp, actual.CurrentOpacity, 1e-6f);
            Assert.AreEqual(aStatic, actual.IsStaticFrame);
            Assert.AreEqual(aPhase, actual.CurrentPhase);
            Assert.AreEqual(aConf, actual.CurrentConfidence, 1e-6f);
            Assert.AreEqual(rVal, recovery.CurrentOutputValue, 1e-6f, "recovery mutated on rejected frame");
            Assert.AreEqual(rLocked, recovery.IsLocked);
            Assert.AreEqual(rIgnore, recovery.LockedFrameIgnoreCount);
            Assert.AreEqual(fbMarker, fallback.CurrentMarker, "fallback mutated on rejected frame");
            Assert.AreEqual(fbCert, fallback.CurrentVisibleCertainty, 1e-6f);
            Assert.AreEqual(fbReason, fallback.CurrentReason);
            Assert.AreEqual(bgCount, background.SegmentChangeCount, "background mutated on rejected frame");
        }

        [Test]
        public void RejectedThenValidFrame_ResumesCleanly_NoHalfAppliedState()
        {
            Tick(Frame(1));

            var bad = Frame(2);
            bad.TargetProgress = 1.5f; // E_TARGET_PROGRESS_RANGE（有步骤时 progress ∈ [0,1]）
            source.Next = bad;
            source.HasFrame = true;
            Assert.IsFalse(adapter.Tick());
            Assert.AreEqual(1, adapter.RejectedFrameCount);

            var f3 = Frame(3);
            f3.TargetPhase = "exhale";
            f3.TargetProgress = 0.7f;
            f3.TargetStepId = "exhale_1";
            f3.TargetCycleIndex = 1;
            f3.RecoveryValue = 0.6f;
            Tick(f3);

            // 各层严格等于帧3 值：坏帧的 1.5 既未半应用、帧1 的 0.4 也被覆盖
            Assert.AreEqual("exhale", target.CurrentPhase);
            Assert.AreEqual(0.7f, target.CurrentProgress, 1e-6f, "target must show frame-3 value exactly");
            Assert.AreEqual("exhale_1", target.CurrentStepId);
            Assert.AreEqual(1, target.CurrentCycleIndex.Value);
            // recovery：帧1 → 帧3 连续低通（坏帧未进入滤波管线），开区间 (0.28, 0.6)
            Assert.Greater(recovery.CurrentOutputValue, 0.28f + 1e-5f);
            Assert.Less(recovery.CurrentOutputValue, 0.6f - 1e-5f,
                "rejected frame must not enter the filter pipeline");
            Assert.AreEqual(2, adapter.AppliedFrameCount, "frames 1 and 3 applied, frame 2 rejected");
            Assert.AreEqual(1, adapter.RejectedFrameCount);
        }
    }
}
