using NUnit.Framework;
using UnityEngine;

namespace SRP.V03.Tests
{
    /// <summary>
    /// AC2：RecoveryLock 帧免疫 + 重置生命周期。
    /// 覆盖：双触发锁定、100 随机帧免疫、quality 恢复不解锁、
    /// 运行中 ResetSession 拒绝、会话边界重置恢复跟随、低通收敛序列。
    /// </summary>
    public sealed class RecoveryLockTests
    {
        private GameObject go;
        private RecoveryLayerAdapter adapter;

        [SetUp]
        public void SetUp()
        {
            go = new GameObject("recovery-adapter");
            adapter = go.AddComponent<RecoveryLayerAdapter>();
            adapter.ConfigureLowPass(2f, 0.5f); // alpha = 0.5 / (2 + 0.5) = 0.2
            adapter.NotifySessionBegin();
        }

        [TearDown]
        public void TearDown()
        {
            if (go != null) Object.DestroyImmediate(go);
        }

        private static RecoveryLayerView View(float value, bool locked) => new RecoveryLayerView(value, locked);

        [Test]
        public void Lock_ImmuneTo100RandomFrames_AfterQualityLock()
        {
            // GOOD 跟随，建立输出
            adapter.Apply(View(0.28f, false), V03RecoveryBehavior.FollowPythonUpdate);
            Assert.IsTrue(adapter.HasOutputValue);

            // UNUSABLE → 锁定
            adapter.Apply(View(0.9f, false), V03RecoveryBehavior.PauseAndLockLastValue);
            Assert.IsTrue(adapter.IsLocked);
            float lockedValue = adapter.CurrentOutputValue;
            Assert.AreEqual(0.28f, lockedValue, 1e-6f, "锁定值 = 当前显示值（滤波后最后值）");

            // 100 帧随机值 + GOOD 行为 → 输出恒等于锁定值
            var rng = new System.Random(42);
            for (int i = 0; i < 100; i++)
            {
                float v = (float)rng.NextDouble();
                adapter.Apply(View(v, false), V03RecoveryBehavior.FollowPythonUpdate);
                Assert.AreEqual(lockedValue, adapter.CurrentOutputValue, 1e-6f,
                    $"frame {i} 打穿锁定（value={v}）");
            }
            Assert.AreEqual(100, adapter.LockedFrameIgnoreCount);
        }

        [Test]
        public void Lock_TriggeredByFrameFlag_EvenWhenBehaviorIsFollow()
        {
            adapter.Apply(View(0.5f, false), V03RecoveryBehavior.FollowPythonUpdate);
            float v0 = adapter.CurrentOutputValue;
            Assert.AreEqual(0.5f, v0, 1e-6f);

            // 帧内 recovery_locked = true（Python 侧标志）→ 锁定（behavior 仍为 Follow）
            adapter.Apply(View(0.8f, true), V03RecoveryBehavior.FollowPythonUpdate);
            Assert.IsTrue(adapter.IsLocked, "帧内 locked 标志必须触发锁定（双触发之一）");
            Assert.AreEqual(v0, adapter.CurrentOutputValue, 1e-6f);
        }

        [Test]
        public void QualityRecoveryToGood_DoesNotUnlock()
        {
            adapter.Apply(View(0.28f, false), V03RecoveryBehavior.FollowPythonUpdate);
            adapter.Apply(View(0.9f, false), V03RecoveryBehavior.PauseAndLockLastValue);
            Assert.IsTrue(adapter.IsLocked);
            float locked = adapter.CurrentOutputValue;

            for (int i = 0; i < 10; i++)
                adapter.Apply(View(0.1f, false), V03RecoveryBehavior.FollowPythonUpdate);

            Assert.IsTrue(adapter.IsLocked, "quality 回 GOOD 不解除锁定（实现决策：仅会话边界解锁）");
            Assert.AreEqual(locked, adapter.CurrentOutputValue, 1e-6f);
        }

        [Test]
        public void ResetSession_RejectedWhileSessionActive()
        {
            adapter.Apply(View(0.5f, false), V03RecoveryBehavior.PauseAndLockLastValue);
            Assert.IsTrue(adapter.IsLocked);

            Assert.IsFalse(adapter.ResetSession(), "运行中 ResetSession 必须拒绝");
            Assert.IsTrue(adapter.IsLocked, "拒绝后状态不变");
            Assert.AreEqual(1, adapter.RejectedResetCount);
        }

        [Test]
        public void ResetSession_AtSessionBoundary_UnlocksAndRestoresFollowing()
        {
            adapter.Apply(View(0.5f, false), V03RecoveryBehavior.PauseAndLockLastValue);
            Assert.IsTrue(adapter.IsLocked);

            adapter.NotifySessionEnd();
            Assert.IsTrue(adapter.ResetSession(), "会话边界（SessionEnd 后）重置成功");
            Assert.IsFalse(adapter.IsLocked);

            adapter.NotifySessionBegin();
            adapter.Apply(View(0.42f, false), V03RecoveryBehavior.FollowPythonUpdate);
            Assert.AreEqual(0.42f, adapter.CurrentOutputValue, 1e-6f, "重置后首帧直通");
        }

        [Test]
        public void LowPass_ConvergesTowardTarget_WhenFollowing()
        {
            adapter.Apply(View(0.0f, false), V03RecoveryBehavior.FollowPythonUpdate);
            Assert.AreEqual(0.0f, adapter.CurrentOutputValue, 1e-6f);

            adapter.Apply(View(1.0f, false), V03RecoveryBehavior.FollowPythonUpdate);
            Assert.AreEqual(0.2f, adapter.CurrentOutputValue, 1e-4f, "alpha = 0.2 一阶低通");

            adapter.Apply(View(1.0f, false), V03RecoveryBehavior.FollowPythonUpdate);
            Assert.AreEqual(0.36f, adapter.CurrentOutputValue, 1e-4f, "0.2 + 0.2*(1-0.2) = 0.36");
        }

        [Test]
        public void FrameLocked_ThenBoundaryReset_ThenFollowsAgain()
        {
            // 帧标志触发锁定
            adapter.Apply(View(0.6f, false), V03RecoveryBehavior.FollowPythonUpdate);
            adapter.Apply(View(0.99f, true), V03RecoveryBehavior.FollowPythonUpdate);
            Assert.IsTrue(adapter.IsLocked);

            // 会话边界重置
            adapter.NotifySessionEnd();
            Assert.IsTrue(adapter.ResetSession());
            adapter.NotifySessionBegin();

            // 恢复跟随
            adapter.Apply(View(0.33f, false), V03RecoveryBehavior.FollowPythonUpdate);
            Assert.AreEqual(0.33f, adapter.CurrentOutputValue, 1e-6f);
        }
    }
}
