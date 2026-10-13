using UnityEngine;

namespace SRP.V03
{
    /// <summary>
    /// Background 显式 no-op 封印（合同 background 行四态 UNCHANGED，AC3 后半句）。
    /// - 零节律接口：不暴露 SetPhase / SetProgress / 任何随呼吸推进的成员；
    ///   背景动画读取不到 quality / respiratory_period（period 泄露禁令）。
    /// - 仅保留会话级换场钩子（update_trigger = SESSION_SEGMENT_AND_SCROLL_TIMELINE）。
    /// evidence_hook: BACKGROUND_HASH_SCROLL_LOG_AND_PERIOD_LEAKAGE_REVIEW（U-03 承接）。
    /// </summary>
    public sealed class BackgroundPass : MonoBehaviour
    {
        public string LastSessionSegment { get; private set; }
        public int SegmentChangeCount { get; private set; }

        /// <summary>会话级换场钩子（由编排器在 segment 变化时调用）。</summary>
        public void OnSessionSegmentChanged(string segment)
        {
            LastSessionSegment = segment;
            SegmentChangeCount++;
        }
    }
}
