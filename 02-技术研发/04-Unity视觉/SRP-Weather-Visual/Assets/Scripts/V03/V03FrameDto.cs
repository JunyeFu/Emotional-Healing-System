using System;
using System.Collections.Generic;

namespace SRP.V03
{
    /// <summary>
    /// F-05 v2.2 telemetry_frame 强类型 DTO。
    /// 字段与 02-技术研发/05-通信协议/contracts/runtime-contract-v2.2.schema.json 及
    /// consumer-fixtures/v2.2/unity/phase-instance-stream.jsonl 对齐。
    /// 可空整数（cycle_index）使用 int? 显式区分"缺失"与"0"（09 迁移指南规则2）。
    /// </summary>
    public sealed class V03FrameDto
    {
        public string SchemaVersion;
        public string MessageType;
        public string SessionId;
        public long FrameSeq;

        // ---- 时钟域（v2.2 自包含帧） ----
        public string ClockDomainId;
        public long SourceMonotonicNs;
        public long ReceivedMonotonicNs;
        public long SentMonotonicNs;
        public long ClockOffsetNs;
        public double ClockDriftPpm;
        public long SyncUncertaintyNs;

        // ---- 模块与会话 ----
        /// <summary>模块标识，取合同 technical_id：storm / heat / snow / fade。</summary>
        public string ModuleId;
        public int ModulePosition;
        /// <summary>会话段：closed_loop 等。</summary>
        public string Segment;
        public string CueMode;
        public string RuntimeMode;
        public string PolicyDecisionId;

        // ---- target ----
        public string TargetPhase;
        public float TargetProgress;
        public int? TargetCycleIndex;
        public string TargetStepId;

        // ---- actual ----
        public string ActualPhase;
        public float ActualProgress;
        public int? ActualCycleIndex;
        public string ActualStepId;
        public float ActualConfidence;

        // ---- recovery ----
        public float RecoveryValue;
        public bool RecoveryLocked;

        // ---- quality / fallback ----
        public float SignalQualityResp;
        public float SignalQualityEcg;
        public string FallbackState;
        public string FallbackReason;
        public string RespDeviceState;
        public string EcgDeviceState;

        /// <summary>解析质量态（fallback_state → V03QualityState）。</summary>
        public bool TryGetQualityState(out V03QualityState state) =>
            V03QualityBehaviorMatrix.TryParseQualityState(FallbackState, out state);
    }

    /// <summary>
    /// 模块映射与相位绑定矩阵（05 合同 r01_module_id_map + runtime_slot_binding）。
    /// </summary>
    public static class V03ModuleMap
    {
        /// <summary>帧 module_id（technical_id）→ 场景模块标识（r01_module_id_map）。</summary>
        public static bool TryMapSceneModule(string moduleId, out string sceneModule)
        {
            switch (moduleId)
            {
                case "storm": sceneModule = "storm"; return true;
                case "heat": sceneModule = "scorching"; return true;
                case "snow": sceneModule = "blizzard"; return true;
                case "fade": sceneModule = "fading"; return true;
                default: sceneModule = null; return false;
            }
        }

        public static bool IsKnownModule(string moduleId) =>
            moduleId == "storm" || moduleId == "heat" || moduleId == "snow" || moduleId == "fade";

        /// <summary>
        /// 该模块是否要求 F-05 v2.2 步骤实例绑定（runtime_slot_binding = F-05_V2_2_REQUIRED）。
        /// storm（INHALE/HOLD_1/EXHALE/HOLD_2）与 fade（INHALE_1/INHALE_2/EXHALE_1）为 REQUIRED；
        /// heat/snow 为 V2_1_COARSE_PHASE_DIRECT（粗相位直驱）。
        /// 依据 runtime_binding_boundary：缺失 v2.2 绑定不阻塞设计完成，但阻塞相关 runtime 实现。
        /// </summary>
        public static bool RequiresV22StepBinding(string moduleId) =>
            moduleId == "storm" || moduleId == "fade";
    }

    /// <summary>
    /// 帧语义校验器：落实 F-05 v2.2 消费者迁移指南规则 2/3/4/5。
    /// 返回错误码列表；空列表表示通过。
    /// </summary>
    public static class V03FrameValidator
    {
        public static IReadOnlyList<string> Validate(V03FrameDto f)
        {
            var errors = new List<string>();
            if (f == null)
            {
                errors.Add("E_NULL_FRAME");
                return errors;
            }

            if (!string.Equals(f.MessageType, "telemetry_frame", StringComparison.Ordinal))
                errors.Add("E_MESSAGE_TYPE");
            if (!string.Equals(f.SchemaVersion, "2.2", StringComparison.Ordinal))
                errors.Add("E_SCHEMA_VERSION");
            if (!V03ModuleMap.IsKnownModule(f.ModuleId))
                errors.Add("E_MODULE");

            // 规则2：*_cycle_index 与 *_step_id 同时有值或同时为 null
            bool hasTargetStep = !string.IsNullOrEmpty(f.TargetStepId);
            if (hasTargetStep != f.TargetCycleIndex.HasValue)
                errors.Add("E_TARGET_STEP_PAIRING");
            bool hasActualStep = !string.IsNullOrEmpty(f.ActualStepId);
            if (hasActualStep != f.ActualCycleIndex.HasValue)
                errors.Add("E_ACTUAL_STEP_PAIRING");

            // 规则3：非空步骤直接给出步骤身份；progress 仅在该步骤内部取值 [0,1]
            if (hasTargetStep)
            {
                if (TargetLayerView.IsNonePhase(f.TargetPhase))
                    errors.Add("E_TARGET_STEP_PHASE_NONE");
                if (f.TargetProgress < 0f || f.TargetProgress > 1f)
                    errors.Add("E_TARGET_PROGRESS_RANGE");
            }
            if (hasActualStep)
            {
                if (TargetLayerView.IsNonePhase(f.ActualPhase))
                    errors.Add("E_ACTUAL_STEP_PHASE_NONE");
                if (f.ActualProgress < 0f || f.ActualProgress > 1f)
                    errors.Add("E_ACTUAL_PROGRESS_RANGE");
            }

            // 规则4：空步骤时 phase 为 none 且 progress 为 0
            if (!hasTargetStep)
            {
                if (!TargetLayerView.IsNonePhase(f.TargetPhase))
                    errors.Add("E_TARGET_EMPTY_STEP_PHASE");
                if (f.TargetProgress != 0f)
                    errors.Add("E_TARGET_EMPTY_STEP_PROGRESS");
            }
            if (!hasActualStep)
            {
                if (!TargetLayerView.IsNonePhase(f.ActualPhase))
                    errors.Add("E_ACTUAL_EMPTY_STEP_PHASE");
                if (f.ActualProgress != 0f)
                    errors.Add("E_ACTUAL_EMPTY_STEP_PROGRESS");
            }

            // 规则5 的帧级前置：storm hold_*、fade inhale_* 必须有步骤实例字段可区分
            if (V03ModuleMap.RequiresV22StepBinding(f.ModuleId) && !hasTargetStep)
                errors.Add("E_V22_BINDING_MISSING");

            // fallback_state 必须落在质量四态枚举内
            if (!V03QualityBehaviorMatrix.TryParseQualityState(f.FallbackState, out _))
                errors.Add("E_FALLBACK_STATE");

            // confidence ∈ [0,1]
            if (f.ActualConfidence < 0f || f.ActualConfidence > 1f)
                errors.Add("E_ACTUAL_CONFIDENCE_RANGE");

            return errors;
        }
    }
}
