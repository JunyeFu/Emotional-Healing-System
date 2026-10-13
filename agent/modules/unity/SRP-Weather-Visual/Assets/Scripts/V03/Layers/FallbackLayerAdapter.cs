using UnityEngine;

namespace SRP.V03
{
    /// <summary>Fallback 层最小接口：编排器只经此接口驱动 fallback 层（AC1 层间隔离）。</summary>
    public interface IV03FallbackLayer
    {
        /// <summary>
        /// 应用 fallback 行为。actualConfidenceEnvelope 由编排器从同一帧投影传入
        /// （DegradationPolicy 需要 confidence，但 fallback Adapter 不反向依赖 Actual 层，
        /// forbidden_coupling 由类型 + 签名共同保证）。
        /// </summary>
        void Apply(in FallbackLayerView view, V03FallbackBehavior behavior, float actualConfidenceEnvelope);

        /// <summary>链路级降级（无帧路径）。</summary>
        void ApplyDegraded(V03FallbackBehavior behavior);
    }

    /// <summary>fallback 标记规格。作用域恒为 actual 载体（合同 fallback 行 ON_ACTUAL_ONLY）。</summary>
    public enum V03FallbackMarker
    {
        None = 0,
        LowCertainty = 1,
        TemporarilyUnavailable = 2,
    }

    /// <summary>
    /// Fallback 层适配器 + DegradationPolicy（AC3）。
    /// VISIBLE_CERTAINTY = min(actual_confidence_envelope, fallback_state_cap)：
    ///   GOOD cap = 1.0；DEGRADED cap = 0.7（候选，gate = U-03_DEGRADED_VISIBILITY_EVIDENCE）。
    /// 标记只能长在 actual 载体上：本 Adapter 不持有 target/recovery/background/audio 引用；
    /// 禁令：不得触碰 target / recovery / background_global_warning / audio_warning。
    /// </summary>
    public sealed class FallbackLayerAdapter : MonoBehaviour, IV03FallbackLayer
    {
        /// <summary>标记作用域（合同 fallback 行：ON_ACTUAL_ONLY —— 恒定，供测试与场景接线核对）。</summary>
        public const string MarkerScope = "ACTUAL_CARRIER_ONLY";

        public V03FallbackMarker CurrentMarker { get; private set; } = V03FallbackMarker.None;
        public float CurrentVisibleCertainty { get; private set; }
        public bool HasCertaintyOutput { get; private set; }
        public string CurrentReason { get; private set; }
        public V03FallbackBehavior LastBehavior { get; private set; } = V03FallbackBehavior.NoExtraMarker;

        public void Apply(in FallbackLayerView view, V03FallbackBehavior behavior, float actualConfidenceEnvelope)
        {
            LastBehavior = behavior;
            CurrentReason = view.FallbackReason;

            switch (behavior)
            {
                case V03FallbackBehavior.NoExtraMarker:
                    CurrentMarker = V03FallbackMarker.None;
                    CurrentVisibleCertainty = Mathf.Clamp01(actualConfidenceEnvelope) * V03ParameterBounds.GoodVisibilityCap;
                    HasCertaintyOutput = true;
                    break;

                case V03FallbackBehavior.LowCertaintyOnActualOnly:
                    // DegradationPolicy：min(envelope, cap)
                    CurrentMarker = V03FallbackMarker.LowCertainty;
                    CurrentVisibleCertainty = Mathf.Min(
                        Mathf.Clamp01(actualConfidenceEnvelope),
                        V03ParameterBounds.DegradedVisibilityCapCandidate);
                    HasCertaintyOutput = true;
                    break;

                case V03FallbackBehavior.TemporarilyUnavailableOnActualOnly:
                    CurrentMarker = V03FallbackMarker.TemporarilyUnavailable;
                    CurrentVisibleCertainty = 0f;
                    HasCertaintyOutput = false;
                    break;
            }
        }

        public void ApplyDegraded(V03FallbackBehavior behavior)
        {
            LastBehavior = behavior;
            if (behavior == V03FallbackBehavior.TemporarilyUnavailableOnActualOnly)
            {
                CurrentMarker = V03FallbackMarker.TemporarilyUnavailable;
                CurrentVisibleCertainty = 0f;
                HasCertaintyOutput = false;
            }
        }
    }
}
