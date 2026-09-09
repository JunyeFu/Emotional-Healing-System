using NUnit.Framework;

namespace SRP.V03.Tests
{
    /// <summary>
    /// golden 测试：F-05 v2.2 phase-instance-stream.jsonl 五帧（frame_seq 20~24）逐字段解析断言。
    /// fixture 原文：02-技术研发/05-通信协议/contracts/consumer-fixtures/v2.2/unity/phase-instance-stream.jsonl
    /// （U-02 快照 inputs/10_phase-instance-stream.jsonl，SHA-256 D2E166C3…）
    /// </summary>
    public sealed class V03FrameGoldenTests
    {
        private const string Frame20 = @"{""schema_version"":""2.2"",""message_type"":""telemetry_frame"",""session_id"":""S-20260807-0001"",""frame_seq"":20,""clock_domain_id"":""python-session-1"",""source_monotonic_ns"":4000000,""received_monotonic_ns"":4050000,""sent_monotonic_ns"":4100000,""clock_offset_ns"":15000,""clock_drift_ppm"":0.4,""sync_uncertainty_ns"":8000,""module_id"":""storm"",""module_position"":0,""segment"":""closed_loop"",""target_phase"":""hold"",""target_progress"":0.4,""actual_phase"":""inhale"",""actual_progress"":0.35,""actual_confidence"":0.91,""recovery_value"":0.28,""recovery_locked"":false,""signal_quality"":{""resp"":0.92,""ecg"":0.88},""fallback_state"":""GOOD"",""fallback_reason"":null,""resp_device_state"":""CONNECTED"",""ecg_device_state"":""CONNECTED"",""cue_mode"":""scene_native"",""runtime_mode"":""formal_stage_1"",""policy_decision_id"":""PD-0001"",""target_cycle_index"":0,""target_step_id"":""hold_1"",""actual_cycle_index"":0,""actual_step_id"":""inhale_1""}";

        private const string Frame21 = @"{""schema_version"":""2.2"",""message_type"":""telemetry_frame"",""session_id"":""S-20260807-0001"",""frame_seq"":21,""clock_domain_id"":""python-session-1"",""source_monotonic_ns"":4100000,""received_monotonic_ns"":4150000,""sent_monotonic_ns"":4200000,""clock_offset_ns"":15000,""clock_drift_ppm"":0.4,""sync_uncertainty_ns"":8000,""module_id"":""storm"",""module_position"":0,""segment"":""closed_loop"",""target_phase"":""hold"",""target_progress"":0.4,""actual_phase"":""exhale"",""actual_progress"":0.35,""actual_confidence"":0.91,""recovery_value"":0.28,""recovery_locked"":false,""signal_quality"":{""resp"":0.92,""ecg"":0.88},""fallback_state"":""GOOD"",""fallback_reason"":null,""resp_device_state"":""CONNECTED"",""ecg_device_state"":""CONNECTED"",""cue_mode"":""scene_native"",""runtime_mode"":""formal_stage_1"",""policy_decision_id"":""PD-0001"",""target_cycle_index"":0,""target_step_id"":""hold_2"",""actual_cycle_index"":0,""actual_step_id"":""exhale_1""}";

        private const string Frame22 = @"{""schema_version"":""2.2"",""message_type"":""telemetry_frame"",""session_id"":""S-20260807-0001"",""frame_seq"":22,""clock_domain_id"":""python-session-1"",""source_monotonic_ns"":4200000,""received_monotonic_ns"":4250000,""sent_monotonic_ns"":4300000,""clock_offset_ns"":15000,""clock_drift_ppm"":0.4,""sync_uncertainty_ns"":8000,""module_id"":""fade"",""module_position"":0,""segment"":""closed_loop"",""target_phase"":""inhale"",""target_progress"":0.4,""actual_phase"":""inhale"",""actual_progress"":0.35,""actual_confidence"":0.91,""recovery_value"":0.28,""recovery_locked"":false,""signal_quality"":{""resp"":0.92,""ecg"":0.88},""fallback_state"":""GOOD"",""fallback_reason"":null,""resp_device_state"":""CONNECTED"",""ecg_device_state"":""CONNECTED"",""cue_mode"":""scene_native"",""runtime_mode"":""formal_stage_1"",""policy_decision_id"":""PD-0001"",""target_cycle_index"":0,""target_step_id"":""inhale_1"",""actual_cycle_index"":0,""actual_step_id"":""inhale_1""}";

        private const string Frame23 = @"{""schema_version"":""2.2"",""message_type"":""telemetry_frame"",""session_id"":""S-20260807-0001"",""frame_seq"":23,""clock_domain_id"":""python-session-1"",""source_monotonic_ns"":4300000,""received_monotonic_ns"":4350000,""sent_monotonic_ns"":4400000,""clock_offset_ns"":15000,""clock_drift_ppm"":0.4,""sync_uncertainty_ns"":8000,""module_id"":""fade"",""module_position"":0,""segment"":""closed_loop"",""target_phase"":""inhale"",""target_progress"":0.4,""actual_phase"":""inhale"",""actual_progress"":0.35,""actual_confidence"":0.91,""recovery_value"":0.28,""recovery_locked"":false,""signal_quality"":{""resp"":0.92,""ecg"":0.88},""fallback_state"":""GOOD"",""fallback_reason"":null,""resp_device_state"":""CONNECTED"",""ecg_device_state"":""CONNECTED"",""cue_mode"":""scene_native"",""runtime_mode"":""formal_stage_1"",""policy_decision_id"":""PD-0001"",""target_cycle_index"":0,""target_step_id"":""inhale_2"",""actual_cycle_index"":0,""actual_step_id"":""inhale_1""}";

        private const string Frame24 = @"{""schema_version"":""2.2"",""message_type"":""telemetry_frame"",""session_id"":""S-20260807-0001"",""frame_seq"":24,""clock_domain_id"":""python-session-1"",""source_monotonic_ns"":4400000,""received_monotonic_ns"":4450000,""sent_monotonic_ns"":4500000,""clock_offset_ns"":15000,""clock_drift_ppm"":0.4,""sync_uncertainty_ns"":8000,""module_id"":""snow"",""module_position"":0,""segment"":""closed_loop"",""target_phase"":""exhale"",""target_progress"":0.4,""actual_phase"":""none"",""actual_progress"":0,""actual_confidence"":0.91,""recovery_value"":0.28,""recovery_locked"":false,""signal_quality"":{""resp"":0.92,""ecg"":0.88},""fallback_state"":""GOOD"",""fallback_reason"":null,""resp_device_state"":""CONNECTED"",""ecg_device_state"":""CONNECTED"",""cue_mode"":""scene_native"",""runtime_mode"":""formal_stage_1"",""policy_decision_id"":""PD-0001"",""target_cycle_index"":0,""target_step_id"":""exhale_1"",""actual_cycle_index"":null,""actual_step_id"":null}";

        private static V03FrameDto ParseOk(string json)
        {
            Assert.IsTrue(V03JsonFrameParser.TryParse(json, out var frame, out var error),
                "parse failed: " + error);
            return frame;
        }

        [Test]
        public void Golden_Frame20_Storm_Hold1_ParsesAllFields()
        {
            var f = ParseOk(Frame20);

            Assert.AreEqual("2.2", f.SchemaVersion);
            Assert.AreEqual("telemetry_frame", f.MessageType);
            Assert.AreEqual("S-20260807-0001", f.SessionId);
            Assert.AreEqual(20, f.FrameSeq);
            Assert.AreEqual("python-session-1", f.ClockDomainId);
            Assert.AreEqual(4000000, f.SourceMonotonicNs);
            Assert.AreEqual(4050000, f.ReceivedMonotonicNs);
            Assert.AreEqual(4100000, f.SentMonotonicNs);
            Assert.AreEqual(15000, f.ClockOffsetNs);
            Assert.AreEqual(0.4, f.ClockDriftPpm, 1e-9);
            Assert.AreEqual(8000, f.SyncUncertaintyNs);
            Assert.AreEqual("storm", f.ModuleId);
            Assert.AreEqual(0, f.ModulePosition);
            Assert.AreEqual("closed_loop", f.Segment);
            Assert.AreEqual("scene_native", f.CueMode);
            Assert.AreEqual("formal_stage_1", f.RuntimeMode);
            Assert.AreEqual("PD-0001", f.PolicyDecisionId);
            Assert.AreEqual("hold", f.TargetPhase);
            Assert.AreEqual(0.4f, f.TargetProgress, 1e-6f);
            Assert.IsTrue(f.TargetCycleIndex.HasValue, "cycle_index 0 不得与 null 混淆（09 规则2）");
            Assert.AreEqual(0, f.TargetCycleIndex.Value);
            Assert.AreEqual("hold_1", f.TargetStepId);
            Assert.AreEqual("inhale", f.ActualPhase);
            Assert.AreEqual(0.35f, f.ActualProgress, 1e-6f);
            Assert.AreEqual(0, f.ActualCycleIndex.Value);
            Assert.AreEqual("inhale_1", f.ActualStepId);
            Assert.AreEqual(0.91f, f.ActualConfidence, 1e-6f);
            Assert.AreEqual(0.28f, f.RecoveryValue, 1e-6f);
            Assert.IsFalse(f.RecoveryLocked);
            Assert.AreEqual(0.92f, f.SignalQualityResp, 1e-6f);
            Assert.AreEqual(0.88f, f.SignalQualityEcg, 1e-6f);
            Assert.AreEqual("GOOD", f.FallbackState);
            Assert.IsNull(f.FallbackReason);
            Assert.AreEqual("CONNECTED", f.RespDeviceState);
            Assert.AreEqual("CONNECTED", f.EcgDeviceState);
        }

        [Test]
        public void Golden_Frame21_Storm_Hold2_DistinguishesStepInstance()
        {
            var f = ParseOk(Frame21);

            Assert.AreEqual(21, f.FrameSeq);
            // 09 迁移指南规则5：storm hold_1 与 hold_2 必须按 step_id 区分，禁止从 phase/progress 推断
            Assert.AreEqual("hold", f.TargetPhase);
            Assert.AreEqual("hold_2", f.TargetStepId);
            Assert.AreEqual("exhale", f.ActualPhase);
            Assert.AreEqual("exhale_1", f.ActualStepId);
        }

        [Test]
        public void Golden_Frame22_Fade_Inhale1()
        {
            var f = ParseOk(Frame22);

            Assert.AreEqual("fade", f.ModuleId);
            Assert.AreEqual("inhale", f.TargetPhase);
            Assert.AreEqual("inhale_1", f.TargetStepId);
            Assert.AreEqual("inhale_1", f.ActualStepId);
        }

        [Test]
        public void Golden_Frame23_Fade_TargetActualDifferentSteps()
        {
            var f = ParseOk(Frame23);

            Assert.AreEqual(23, f.FrameSeq);
            // 同帧内 target 与 actual 属于不同步骤实例：target=inhale_2，actual=inhale_1
            Assert.AreEqual("inhale", f.TargetPhase);
            Assert.AreEqual("inhale_2", f.TargetStepId);
            Assert.AreEqual("inhale", f.ActualPhase);
            Assert.AreEqual("inhale_1", f.ActualStepId);
        }

        [Test]
        public void Golden_Frame24_Snow_ActualEmptyStep()
        {
            var f = ParseOk(Frame24);

            Assert.AreEqual("snow", f.ModuleId);
            Assert.AreEqual("exhale", f.TargetPhase);
            Assert.AreEqual("exhale_1", f.TargetStepId);
            // 09 规则4：空步骤 → phase=none、progress=0、cycle_index=null、step_id=null
            Assert.AreEqual("none", f.ActualPhase);
            Assert.AreEqual(0f, f.ActualProgress, 1e-6f);
            Assert.IsFalse(f.ActualCycleIndex.HasValue, "actual_cycle_index null 必须保真（09 规则2）");
            Assert.IsNull(f.ActualStepId);
        }

        [Test]
        public void Golden_AllFrames_PassValidator()
        {
            foreach (var json in new[] { Frame20, Frame21, Frame22, Frame23, Frame24 })
            {
                var f = ParseOk(json);
                var errors = V03FrameValidator.Validate(f);
                Assert.AreEqual(0, errors.Count,
                    "frame_seq=" + f.FrameSeq + " errors=" + string.Join(",", errors));
            }
        }
    }
}
