using UnityEngine;

namespace SRP.V03
{
    /// <summary>Actual 层最小接口：编排器只经此接口驱动 actual 层（AC1 层间隔离）。</summary>
    public interface IV03ActualLayer
    {
        void Apply(in ActualLayerView view, V03ActualBehavior behavior);

        /// <summary>链路级降级（无帧路径）。</summary>
        void ApplyDegraded(V03ActualBehavior behavior);
    }

    /// <summary>actual 层视觉输出模式（写入场景的 opacity 经 07 区间断言）。</summary>
    public enum V03ActualOpacityMode
    {
        Full = 0,
        Degraded = 1,
        Unavailable = 2,
    }

    /// <summary>
    /// Actual 层适配器：交互状态估计的视觉载体。
    /// ACTIVE_LOW_CERTAINTY：opacity ∈ [0.45,0.7]、continuity ∈ [0.45,0.75]（07）。
    /// STATIC_BROKEN_OUTLINE：opacity ∈ [0.25,0.45]、edge_softening_px_1080p ∈ [1,3]、静帧呈现。
    /// actual_phase=none：整层隐藏（frame24 snow；09 规则4 —— 空步骤不得填入目标步骤值）。
    /// 安全区 x ∈ [0.2,0.45]、y ∈ [0.18,0.52] 由场景接线（载体挂点）保证，本层不持有位置。
    /// </summary>
    public sealed class ActualLayerAdapter : MonoBehaviour, IV03ActualLayer
    {
        [SerializeField] private float degradedOpacity = V03ParameterBounds.ActualDegradedOpacityCandidate;
        [SerializeField] private float unavailableOpacity = V03ParameterBounds.ActualUnavailableOpacityCandidate;
        [SerializeField] private float degradedContinuity = V03ParameterBounds.ActualDegradedContinuityCandidate;
        [SerializeField] private float edgeSofteningPx1080p = V03ParameterBounds.ActualEdgeSofteningPx1080pCandidate;

        public bool IsHidden { get; private set; }
        public V03ActualOpacityMode CurrentOpacityMode { get; private set; } = V03ActualOpacityMode.Full;
        public float CurrentOpacity { get; private set; } = 1f;
        public float CurrentContinuity { get; private set; } = 1f;
        public float CurrentEdgeSofteningPx { get; private set; }
        public bool IsStaticFrame { get; private set; }
        public string CurrentPhase { get; private set; } = "none";
        public float CurrentProgress { get; private set; }
        public string CurrentStepId { get; private set; }
        public int? CurrentCycleIndex { get; private set; }
        public float CurrentConfidence { get; private set; }
        public V03ActualBehavior LastBehavior { get; private set; } = V03ActualBehavior.Active;

        // ---- 配置 setter（全部经 07 区间断言，越界 fail 不钳制）----

        public float DegradedOpacity
        {
            get => degradedOpacity;
            set
            {
                V03ParameterBounds.AssertInRange(value, V03ParameterBounds.ActualDegradedOpacityMin, V03ParameterBounds.ActualDegradedOpacityMax, nameof(degradedOpacity));
                degradedOpacity = value;
            }
        }

        public float UnavailableOpacity
        {
            get => unavailableOpacity;
            set
            {
                V03ParameterBounds.AssertInRange(value, V03ParameterBounds.ActualUnavailableOpacityMin, V03ParameterBounds.ActualUnavailableOpacityMax, nameof(unavailableOpacity));
                unavailableOpacity = value;
            }
        }

        public float DegradedContinuity
        {
            get => degradedContinuity;
            set
            {
                V03ParameterBounds.AssertInRange(value, V03ParameterBounds.ActualDegradedContinuityMin, V03ParameterBounds.ActualDegradedContinuityMax, nameof(degradedContinuity));
                degradedContinuity = value;
            }
        }

        public float EdgeSofteningPx1080p
        {
            get => edgeSofteningPx1080p;
            set
            {
                V03ParameterBounds.AssertInRange(value, V03ParameterBounds.ActualEdgeSofteningPx1080pMin, V03ParameterBounds.ActualEdgeSofteningPx1080pMax, nameof(edgeSofteningPx1080p));
                edgeSofteningPx1080p = value;
            }
        }

        public void Apply(in ActualLayerView view, V03ActualBehavior behavior)
        {
            AssertConfigured();
            LastBehavior = behavior;

            CurrentPhase = view.ActualPhase;
            CurrentProgress = view.ActualProgress;
            CurrentStepId = view.ActualStepId;
            CurrentCycleIndex = view.ActualCycleIndex;
            CurrentConfidence = view.ActualConfidence;

            if (view.IsEmptyStep)
            {
                // 估计不可用 → 整层隐藏（frame24 snow 实证）
                Hide();
                return;
            }
            IsHidden = false;

            switch (behavior)
            {
                case V03ActualBehavior.Active:
                    CurrentOpacityMode = V03ActualOpacityMode.Full;
                    CurrentOpacity = 1f;
                    CurrentContinuity = 1f;
                    CurrentEdgeSofteningPx = 0f;
                    IsStaticFrame = false;
                    break;

                case V03ActualBehavior.ActiveLowCertainty:
                    CurrentOpacityMode = V03ActualOpacityMode.Degraded;
                    CurrentOpacity = degradedOpacity;
                    CurrentContinuity = degradedContinuity;
                    CurrentEdgeSofteningPx = 0f;
                    IsStaticFrame = false;
                    break;

                case V03ActualBehavior.StaticBrokenOutline:
                    CurrentOpacityMode = V03ActualOpacityMode.Unavailable;
                    CurrentOpacity = unavailableOpacity;
                    CurrentContinuity = 0f;
                    CurrentEdgeSofteningPx = edgeSofteningPx1080p;
                    IsStaticFrame = true; // 静帧：不驱动节律动画
                    break;
            }
        }

        public void ApplyDegraded(V03ActualBehavior behavior)
        {
            AssertConfigured();
            LastBehavior = behavior;
            if (behavior == V03ActualBehavior.StaticBrokenOutline)
            {
                // 链路级静帧：保持最后相位显示，冻结为 broken outline
                CurrentOpacityMode = V03ActualOpacityMode.Unavailable;
                CurrentOpacity = unavailableOpacity;
                CurrentContinuity = 0f;
                CurrentEdgeSofteningPx = edgeSofteningPx1080p;
                IsStaticFrame = true;
            }
        }

        private void Hide()
        {
            IsHidden = true;
            IsStaticFrame = false;
            CurrentOpacityMode = V03ActualOpacityMode.Full;
            CurrentOpacity = 0f;
            CurrentContinuity = 0f;
            CurrentEdgeSofteningPx = 0f;
        }

        private void AssertConfigured()
        {
            V03ParameterBounds.AssertInRange(degradedOpacity, V03ParameterBounds.ActualDegradedOpacityMin, V03ParameterBounds.ActualDegradedOpacityMax, nameof(degradedOpacity));
            V03ParameterBounds.AssertInRange(unavailableOpacity, V03ParameterBounds.ActualUnavailableOpacityMin, V03ParameterBounds.ActualUnavailableOpacityMax, nameof(unavailableOpacity));
            V03ParameterBounds.AssertInRange(degradedContinuity, V03ParameterBounds.ActualDegradedContinuityMin, V03ParameterBounds.ActualDegradedContinuityMax, nameof(degradedContinuity));
            V03ParameterBounds.AssertInRange(edgeSofteningPx1080p, V03ParameterBounds.ActualEdgeSofteningPx1080pMin, V03ParameterBounds.ActualEdgeSofteningPx1080pMax, nameof(edgeSofteningPx1080p));
        }
    }
}
