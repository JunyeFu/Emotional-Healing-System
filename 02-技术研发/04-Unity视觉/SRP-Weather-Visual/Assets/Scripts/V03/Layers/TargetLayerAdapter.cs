using UnityEngine;

namespace SRP.V03
{
    /// <summary>Target 层最小接口：编排器只经此接口驱动 target 层（AC1 层间隔离）。</summary>
    public interface IV03TargetLayer
    {
        void Apply(in TargetLayerView view, V03TargetBehavior behavior);

        /// <summary>链路级降级（无帧路径）：按 behavior 处理，不更新节律值。</summary>
        void ApplyDegraded(V03TargetBehavior behavior);
    }

    /// <summary>
    /// Target 层适配器：按 quality_behavior 驱动目标节律。
    /// 只接受 TargetLayerView —— actual/recovery/fallback 字段在类型上不可达（AC1）。
    /// </summary>
    public sealed class TargetLayerAdapter : MonoBehaviour, IV03TargetLayer
    {
        [SerializeField] private float phaseInterpolationMs = V03ParameterBounds.PhaseInterpolationMsCandidate;

        public string CurrentPhase { get; private set; } = "none";
        public float CurrentProgress { get; private set; }
        public string CurrentStepId { get; private set; }
        public int? CurrentCycleIndex { get; private set; }
        public V03TargetBehavior LastBehavior { get; private set; } = V03TargetBehavior.ContinueTarget;
        public bool IsAborted { get; private set; }
        public bool IsOpenLoopActive { get; private set; }
        public int AppliedFrameCount { get; private set; }

        /// <summary>相位插值参数（07 区间 [100,250]ms，越界 fail）。</summary>
        public float PhaseInterpolationMs
        {
            get => phaseInterpolationMs;
            set
            {
                V03ParameterBounds.AssertInRange(value,
                    V03ParameterBounds.PhaseInterpolationMsMin,
                    V03ParameterBounds.PhaseInterpolationMsMax,
                    nameof(phaseInterpolationMs));
                phaseInterpolationMs = value;
            }
        }

        public void Apply(in TargetLayerView view, V03TargetBehavior behavior)
        {
            AssertConfigured();
            LastBehavior = behavior;
            switch (behavior)
            {
                case V03TargetBehavior.ContinueTarget:
                    IsAborted = false;
                    IsOpenLoopActive = false;
                    // 空步骤帧 target_phase=none 直接呈现 none（09 规则4）
                    CurrentPhase = view.TargetPhase;
                    CurrentProgress = view.TargetProgress;
                    CurrentStepId = view.TargetStepId;
                    CurrentCycleIndex = view.TargetCycleIndex;
                    AppliedFrameCount++;
                    break;

                case V03TargetBehavior.OpenLoopTarget:
                    // 跳过本轮帧更新，按会话节律计划开环推进；
                    // 节律计划源 = 设计文档开放问题2，随 Python 侧 F-05 字段对齐后接入。
                    IsOpenLoopActive = true;
                    break;

                case V03TargetBehavior.FollowPythonSafeOpenLoopOrAbort:
                    // 帧内无安全开环标记字段 → 走 Abort 分支回 idle 安全态；
                    // 安全开环标记消费接口随开放问题2 一并预留。
                    IsAborted = true;
                    CurrentPhase = "none";
                    CurrentProgress = 0f;
                    CurrentStepId = null;
                    CurrentCycleIndex = null;
                    break;
            }
        }

        public void ApplyDegraded(V03TargetBehavior behavior)
        {
            AssertConfigured();
            LastBehavior = behavior;
            switch (behavior)
            {
                case V03TargetBehavior.OpenLoopTarget:
                    IsOpenLoopActive = true;
                    break;
                case V03TargetBehavior.FollowPythonSafeOpenLoopOrAbort:
                    IsAborted = true;
                    CurrentPhase = "none";
                    CurrentProgress = 0f;
                    CurrentStepId = null;
                    CurrentCycleIndex = null;
                    break;
                case V03TargetBehavior.ContinueTarget:
                default:
                    // 无帧不推进：保持当前节律状态
                    break;
            }
        }

        private void AssertConfigured()
        {
            V03ParameterBounds.AssertInRange(phaseInterpolationMs,
                V03ParameterBounds.PhaseInterpolationMsMin,
                V03ParameterBounds.PhaseInterpolationMsMax,
                nameof(phaseInterpolationMs));
        }
    }
}
