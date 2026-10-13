namespace SRP.V03
{
    /// <summary>
    /// 遥测链路状态（U-01 适配器层上报）。
    /// 与 V03QualityState 互相独立：链路态描述"帧从哪来、通不通"，
    /// 质量态描述"帧内 fallback_state"。链路断开时无帧可用，由编排器走无帧降级路径。
    /// </summary>
    public enum V03LinkState
    {
        Linked = 0,
        Degraded = 1,
        Unusable = 2,
        Disconnected = 3,
    }

    /// <summary>
    /// 遥测源抽象：向编排器提供"最新一帧"。
    /// 不绑定任何一版 U-01 实现：main 版（TelemetryReceiver.TryDequeue(out json)）与
    /// ours 版（UDP5006Gate.ValidateFull 产出）各写一个薄适配器即可接入。
    /// 本任务交付接口 + 测试桩；生产适配器随 U-01 归属决策接入（U-02 设计文档 v1.0 §3）。
    /// </summary>
    public interface IV03TelemetrySource
    {
        /// <summary>取最新一帧；无新帧返回 false（不算错误，编排器保持现状）。</summary>
        bool TryGetFrame(out V03FrameDto frame);

        /// <summary>当前链路状态；链路级降级时由编排器经 NotifyLinkDown 消费。</summary>
        V03LinkState LinkState { get; }
    }
}
