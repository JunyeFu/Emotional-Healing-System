using UnityEngine;

namespace SRP.V03
{
    /// <summary>Recovery 层最小接口：编排器只经此接口驱动 recovery 层（AC1 层间隔离）。</summary>
    public interface IV03RecoveryLayer
    {
        void Apply(in RecoveryLayerView view, V03RecoveryBehavior behavior);

        /// <summary>链路级降级（无帧路径）。</summary>
        void ApplyDegraded(V03RecoveryBehavior behavior);
    }

    /// <summary>
    /// Recovery 层适配器 + RecoveryLock（AC2）。
    /// 锁定触发（双路，设计文档 v1.0 §4.3）：
    ///   a) quality 行为 = PAUSE_AND_LOCK_LAST_VALUE（UNUSABLE / DISCONNECTED）；
    ///   b) 帧内 recovery_locked = true（Python 侧标志）。
    /// 锁定语义：冻结累计环境值，后续帧 recovery_value 一律忽略；恢复端点参数保持锁定值
    /// （storm rain_multiplier 1→[0.65,0.8] / visibility [0.45,0.6]→[0.7,0.85] 等，07）。
    /// 解锁：仅 ResetSession()（会话边界）。quality 回 GOOD / 帧内 locked 回 false 均不解锁 ——
    /// 避免锁定期间环境值跳变（实现决策，TASK.md 回填时注明，供傅钧烨复核）。
    /// </summary>
    public sealed class RecoveryLayerAdapter : MonoBehaviour, IV03RecoveryLayer
    {
        [SerializeField] private float recoveryLowPassSeconds = V03ParameterBounds.RecoveryLowPassSecondsCandidate;

        /// <summary>
        /// 采样间隔（秒）。UDP 遥测 ≤20Hz → 默认 0.05s；
        /// 测试注入更大间隔以便精确断言滤波序列（alpha = dt/(tau+dt)）。
        /// </summary>
        [SerializeField] private float sampleIntervalSeconds = 1f / 20f;

        public bool IsLocked { get; private set; }
        public float CurrentOutputValue { get; private set; }
        public bool HasOutputValue { get; private set; }
        public bool SessionActive { get; private set; }
        public int LockedFrameIgnoreCount { get; private set; }
        public int RejectedResetCount { get; private set; }
        public V03RecoveryBehavior LastBehavior { get; private set; } = V03RecoveryBehavior.FollowPythonUpdate;

        /// <summary>低通时间常数（07 区间 [2,5]s，越界 fail）。</summary>
        public float RecoveryLowPassSeconds
        {
            get => recoveryLowPassSeconds;
            set
            {
                V03ParameterBounds.AssertInRange(value,
                    V03ParameterBounds.RecoveryLowPassSecondsMin,
                    V03ParameterBounds.RecoveryLowPassSecondsMax,
                    nameof(recoveryLowPassSeconds));
                recoveryLowPassSeconds = value;
            }
        }

        /// <summary>测试注入：配置低通时间常数与采样间隔（tau ∈ [2,5]）。</summary>
        public void ConfigureLowPass(float lowPassSeconds, float sampleInterval)
        {
            V03ParameterBounds.AssertInRange(lowPassSeconds,
                V03ParameterBounds.RecoveryLowPassSecondsMin,
                V03ParameterBounds.RecoveryLowPassSecondsMax,
                nameof(lowPassSeconds));
            if (sampleInterval <= 0f)
                throw new System.ArgumentOutOfRangeException(nameof(sampleInterval),
                    "sample interval must be positive");
            recoveryLowPassSeconds = lowPassSeconds;
            sampleIntervalSeconds = sampleInterval;
        }

        // ---- 会话生命周期（编排器在 segment 边界驱动）----

        public void NotifySessionBegin() => SessionActive = true;

        public void NotifySessionEnd() => SessionActive = false;

        /// <summary>
        /// 会话边界重置：清锁定与滤波状态。
        /// 运行中（SessionActive=true）调用 → 拒绝（返回 false）+ 计数，状态不变（设计文档 §4.3）。
        /// </summary>
        public bool ResetSession()
        {
            if (SessionActive)
            {
                RejectedResetCount++;
                return false;
            }
            IsLocked = false;
            HasOutputValue = false;
            CurrentOutputValue = 0f;
            LockedFrameIgnoreCount = 0;
            return true;
        }

        public void Apply(in RecoveryLayerView view, V03RecoveryBehavior behavior)
        {
            AssertConfigured();
            LastBehavior = behavior;

            // 双触发锁定
            if (behavior == V03RecoveryBehavior.PauseAndLockLastValue || view.RecoveryLocked)
            {
                if (!IsLocked)
                {
                    IsLocked = true;
                    if (!HasOutputValue)
                    {
                        // 无历史输出时锁定触发帧的值
                        CurrentOutputValue = view.RecoveryValue;
                        HasOutputValue = true;
                    }
                }
                return;
            }

            if (IsLocked)
            {
                // 锁定免疫：帧值一律忽略（AC2：锁定后喂 100 帧随机值输出恒等）
                LockedFrameIgnoreCount++;
                return;
            }

            // 跟随路径：一阶低通离散化 alpha = dt / (tau + dt)
            // DEGRADED（FollowPythonCautionOrPause）与 GOOD（FollowPythonUpdate）同走低通：
            // Caution 变体的变化率钳制与 Pause 分支在 07 中无参数权威来源，
            // 当前保守实现 = 继续低通；锁定仅在 UNUSABLE/DISCONNECTED/帧标志触发。
            float alpha = sampleIntervalSeconds / (recoveryLowPassSeconds + sampleIntervalSeconds);
            if (!HasOutputValue)
            {
                CurrentOutputValue = view.RecoveryValue;
                HasOutputValue = true;
                return;
            }
            CurrentOutputValue = Mathf.Lerp(CurrentOutputValue, view.RecoveryValue, alpha);
        }

        public void ApplyDegraded(V03RecoveryBehavior behavior)
        {
            AssertConfigured();
            LastBehavior = behavior;
            if (behavior == V03RecoveryBehavior.PauseAndLockLastValue)
            {
                if (!IsLocked)
                {
                    // 链路级锁定：无帧可用，锁定当前显示值（从未有过输出则保持无输出状态）
                    IsLocked = true;
                }
            }
            // 链路级 FollowPythonCautionOrPause：无帧，保持现状
        }

        private void AssertConfigured()
        {
            V03ParameterBounds.AssertInRange(recoveryLowPassSeconds,
                V03ParameterBounds.RecoveryLowPassSecondsMin,
                V03ParameterBounds.RecoveryLowPassSecondsMax,
                nameof(recoveryLowPassSeconds));
        }
    }
}
