using UnityEngine;

namespace SRP.V03
{
    /// <summary>
    /// Background 显式 no-op 封印（合同 background 行四态 UNCHANGED，AC3 后半句）。
    /// - 零节律接口：不暴露 SetPhase / SetProgress / 任何随呼吸推进的成员；
    ///   背景动画读取不到 quality / respiratory_period（period 泄露禁令）。
    /// - 仅保留会话级换场钩子，固定镜头环境不得跟随呼吸形成周期。
    /// U-03 另行实现模块有效时间驱动的整屏复色；此钩子不提供颜色动画。
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
