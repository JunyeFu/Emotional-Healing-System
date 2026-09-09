using System;
using System.Collections.Generic;
using UnityEngine;

namespace SRP.V03
{
    /// <summary>
    /// V-03 场景编排器：帧 DTO → 四层 View 投影拆分 → quality 行为分发。
    /// 与 FormalRuntimeController 同场景共存（FormalBuildGate FORMAL_RUNTIME_CONTROLLER_MISSING 检查不受影响）。
    /// 本类是唯一授权的投影拆分点；各层 Adapter 之间无共享可变状态（AC1）。
    /// 数据流单向：帧 DTO → 编排器拆投影 → 各层各自应用。
    /// </summary>
    public sealed class V03SceneAdapter : MonoBehaviour
    {
        [SerializeField] private TargetLayerAdapter targetLayer;
        [SerializeField] private ActualLayerAdapter actualLayer;
        [SerializeField] private RecoveryLayerAdapter recoveryLayer;
        [SerializeField] private FallbackLayerAdapter fallbackLayer;
        [SerializeField] private BackgroundPass backgroundPass;

        private IV03TelemetrySource source;
        private string lastAppliedSegment;

        public int RejectedFrameCount { get; private set; }
        public int AppliedFrameCount { get; private set; }
        public V03QualityState? LastQualityState { get; private set; }
        public bool IsBound => source != null;

        /// <summary>绑定遥测源（U-01 适配器或测试桩）。</summary>
        public void Bind(IV03TelemetrySource telemetrySource) => source = telemetrySource;

        /// <summary>测试/接线注入各层（场景接线也可用 SerializeField 拖引）。</summary>
        public void ConfigureLayers(
            TargetLayerAdapter target, ActualLayerAdapter actual,
            RecoveryLayerAdapter recovery, FallbackLayerAdapter fallback,
            BackgroundPass background)
        {
            targetLayer = target;
            actualLayer = actual;
            recoveryLayer = recovery;
            fallbackLayer = fallback;
            backgroundPass = background;
        }

        /// <summary>
        /// 单步推进：取帧 → 校验 → 投影 → 分发。返回是否应用了新帧。
        /// 无新帧：保持现状（不算拒收）；非法帧：拒收 + 计数，不静默丢弃（09 迁移指南）。
        /// </summary>
        public bool Tick()
        {
            if (source == null || targetLayer == null) return false;

            if (!source.TryGetFrame(out var frame)) return false;

            IReadOnlyList<string> errors = V03FrameValidator.Validate(frame);
            if (errors.Count > 0)
            {
                // 拒收不静默：计数可观测；链路质量由 source.LinkState 承载
                RejectedFrameCount++;
                return false;
            }

            // 会话边界：segment 变化 → 重置锁定/滤波 + 背景换场钩子
            if (!string.Equals(frame.Segment, lastAppliedSegment, StringComparison.Ordinal))
            {
                if (recoveryLayer != null)
                {
                    recoveryLayer.NotifySessionEnd();
                    recoveryLayer.ResetSession();
                    recoveryLayer.NotifySessionBegin();
                }
                if (backgroundPass != null)
                    backgroundPass.OnSessionSegmentChanged(frame.Segment);
                lastAppliedSegment = frame.Segment;
            }

            if (!frame.TryGetQualityState(out var quality))
                quality = V03QualityState.Disconnected; // 防御分支：validator 已拒非法 state
            LastQualityState = quality;

            // ---- 唯一投影拆分点 ----
            targetLayer.Apply(
                new TargetLayerView(frame.TargetPhase, frame.TargetProgress, frame.TargetCycleIndex, frame.TargetStepId),
                quality.TargetBehavior());

            if (actualLayer != null)
                actualLayer.Apply(
                    new ActualLayerView(frame.ActualPhase, frame.ActualProgress, frame.ActualCycleIndex, frame.ActualStepId, frame.ActualConfidence),
                    quality.ActualBehavior());

            if (recoveryLayer != null)
                recoveryLayer.Apply(
                    new RecoveryLayerView(frame.RecoveryValue, frame.RecoveryLocked),
                    quality.RecoveryBehavior());

            if (fallbackLayer != null)
                fallbackLayer.Apply(
                    new FallbackLayerView(frame.SignalQualityResp, frame.SignalQualityEcg, frame.FallbackState, frame.FallbackReason),
                    quality.FallbackBehavior(),
                    frame.ActualConfidence);

            AppliedFrameCount++;
            return true;
        }

        /// <summary>
        /// 链路级降级（无帧路径）：U-01 适配器在链路态恶化时显式调用。
        /// 按 LinkState 对应的 quality 行为分发，不构造 View（各层保持最后状态 + 降级动作）。
        /// </summary>
        public void NotifyLinkDown(V03LinkState linkState)
        {
            var quality = linkState == V03LinkState.Unusable
                ? V03QualityState.Unusable
                : V03QualityState.Disconnected;
            LastQualityState = quality;

            targetLayer?.ApplyDegraded(quality.TargetBehavior());
            actualLayer?.ApplyDegraded(quality.ActualBehavior());
            recoveryLayer?.ApplyDegraded(quality.RecoveryBehavior());
            fallbackLayer?.ApplyDegraded(quality.FallbackBehavior());
        }

        private void Update() => Tick();
    }
}
