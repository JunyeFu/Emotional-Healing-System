using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;

namespace SRP.V03.Tests
{
    /// <summary>
    /// 帧校验负测试：F-05 v2.2 消费者迁移指南规则 2/3/4/5 的违例必须被拒收。
    /// </summary>
    public sealed class V03FrameValidationTests
    {
        private static V03FrameDto BuildValidFrame()
        {
            // 以 golden frame20（storm hold_1）为底本的合法帧
            return new V03FrameDto
            {
                SchemaVersion = "2.2",
                MessageType = "telemetry_frame",
                SessionId = "S-20260807-0001",
                FrameSeq = 20,
                ModuleId = "storm",
                ModulePosition = 0,
                Segment = "closed_loop",
                CueMode = "scene_native",
                RuntimeMode = "formal_stage_1",
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
                FallbackState = "GOOD",
            };
        }

        private static bool Contains(IReadOnlyList<string> errors, string code) => errors.Any(e => e == code);

        [Test]
        public void Rule2_TargetCycleIndexWithoutStepId_Rejected()
        {
            var f = BuildValidFrame();
            f.TargetStepId = null; // cycle_index 仍有值 → 配对破坏
            var errors = V03FrameValidator.Validate(f);
            Assert.IsTrue(Contains(errors, "E_TARGET_STEP_PAIRING"), string.Join(",", errors));
        }

        [Test]
        public void Rule2_ActualStepIdWithoutCycleIndex_Rejected()
        {
            var f = BuildValidFrame();
            f.ActualCycleIndex = null; // step_id 仍有值 → 配对破坏
            var errors = V03FrameValidator.Validate(f);
            Assert.IsTrue(Contains(errors, "E_ACTUAL_STEP_PAIRING"), string.Join(",", errors));
        }

        [Test]
        public void Rule4_EmptyStepWithNonZeroProgress_Rejected()
        {
            var f = BuildValidFrame();
            f.TargetStepId = null;
            f.TargetCycleIndex = null;
            f.TargetPhase = "none";
            f.TargetProgress = 0.5f; // 空步骤 progress 必须为 0
            var errors = V03FrameValidator.Validate(f);
            Assert.IsTrue(Contains(errors, "E_TARGET_EMPTY_STEP_PROGRESS"), string.Join(",", errors));
        }

        [Test]
        public void Rule4_EmptyStepWithPhaseNotNone_Rejected()
        {
            var f = BuildValidFrame();
            f.TargetStepId = null;
            f.TargetCycleIndex = null;
            f.TargetPhase = "inhale"; // 空步骤 phase 必须为 none
            f.TargetProgress = 0f;
            var errors = V03FrameValidator.Validate(f);
            Assert.IsTrue(Contains(errors, "E_TARGET_EMPTY_STEP_PHASE"), string.Join(",", errors));
        }

        [Test]
        public void Rule3_NonEmptyStepWithNonePhase_Rejected()
        {
            var f = BuildValidFrame();
            f.TargetPhase = "none"; // 非空步骤 phase 不得为 none
            var errors = V03FrameValidator.Validate(f);
            Assert.IsTrue(Contains(errors, "E_TARGET_STEP_PHASE_NONE"), string.Join(",", errors));
        }

        [Test]
        public void Rule3_ProgressOutOfRange_Rejected()
        {
            var f = BuildValidFrame();
            f.TargetProgress = 1.2f;
            var errors = V03FrameValidator.Validate(f);
            Assert.IsTrue(Contains(errors, "E_TARGET_PROGRESS_RANGE"), string.Join(",", errors));
        }

        [Test]
        public void Rule5_V22RequiredModuleWithoutStepBinding_Rejected()
        {
            var f = BuildValidFrame();
            f.ModuleId = "storm";
            f.TargetStepId = null;
            f.TargetCycleIndex = null;
            f.TargetPhase = "none";
            f.TargetProgress = 0f;
            var errors = V03FrameValidator.Validate(f);
            // storm 属 F-05_V2_2_REQUIRED：缺步骤实例绑定 → 阻塞相关 runtime 实现
            Assert.IsTrue(Contains(errors, "E_V22_BINDING_MISSING"), string.Join(",", errors));
        }

        [Test]
        public void Rule5_V21CoarseModuleWithoutStepBinding_Accepted()
        {
            var f = BuildValidFrame();
            f.ModuleId = "heat"; // V2_1_COARSE_PHASE_DIRECT：粗相位直驱，不要求步骤实例
            f.TargetStepId = null;
            f.TargetCycleIndex = null;
            f.TargetPhase = "none";
            f.TargetProgress = 0f;
            f.ActualStepId = null;
            f.ActualCycleIndex = null;
            f.ActualPhase = "none";
            f.ActualProgress = 0f;
            var errors = V03FrameValidator.Validate(f);
            Assert.AreEqual(0, errors.Count, string.Join(",", errors));
        }

        [Test]
        public void UnknownModule_Rejected()
        {
            var f = BuildValidFrame();
            f.ModuleId = "rain";
            var errors = V03FrameValidator.Validate(f);
            Assert.IsTrue(Contains(errors, "E_MODULE"), string.Join(",", errors));
        }

        [Test]
        public void BadFallbackState_Rejected()
        {
            var f = BuildValidFrame();
            f.FallbackState = "PERFECT";
            var errors = V03FrameValidator.Validate(f);
            Assert.IsTrue(Contains(errors, "E_FALLBACK_STATE"), string.Join(",", errors));
        }

        [Test]
        public void ConfidenceOutOfRange_Rejected()
        {
            var f = BuildValidFrame();
            f.ActualConfidence = 1.5f;
            var errors = V03FrameValidator.Validate(f);
            Assert.IsTrue(Contains(errors, "E_ACTUAL_CONFIDENCE_RANGE"), string.Join(",", errors));
        }

        [Test]
        public void NullFrame_Rejected()
        {
            var errors = V03FrameValidator.Validate(null);
            Assert.IsTrue(Contains(errors, "E_NULL_FRAME"));
        }
    }
}
