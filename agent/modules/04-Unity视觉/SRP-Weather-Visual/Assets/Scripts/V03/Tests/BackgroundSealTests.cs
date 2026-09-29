using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;

namespace SRP.V03.Tests
{
    /// <summary>
    /// AC3 后半：Background 封印 —— 无节律接口，仅会话换场钩子。
    /// 反射断言 BackgroundPass 的 public API 集合，防止后续演进引入节律接口。
    /// evidence_hook: BACKGROUND_HASH_SCROLL_LOG_AND_PERIOD_LEAKAGE_REVIEW（U-03 承接）。
    /// </summary>
    public sealed class BackgroundSealTests
    {
        private GameObject go;
        private BackgroundPass pass;

        [SetUp]
        public void SetUp()
        {
            go = new GameObject("background-pass");
            pass = go.AddComponent<BackgroundPass>();
        }

        [TearDown]
        public void TearDown()
        {
            if (go != null) Object.DestroyImmediate(go);
        }

        [Test]
        public void PublicMethods_HaveNoRhythmInterfaces()
        {
            var methods = typeof(BackgroundPass)
                .GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                .Where(m => !m.IsSpecialName) // 排除属性访问器
                .Select(m => m.Name)
                .OrderBy(n => n)
                .ToArray();

            CollectionAssert.AreEqual(new[] { "OnSessionSegmentChanged" }, methods,
                "Background 不得暴露任何节律接口（SetPhase/SetProgress 等禁令，AC3）");
        }

        [Test]
        public void PublicProperties_HaveNoRhythmOrQualityState()
        {
            var props = typeof(BackgroundPass)
                .GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                .Select(p => p.Name)
                .OrderBy(n => n)
                .ToArray();

            CollectionAssert.AreEqual(new[] { "LastSessionSegment", "SegmentChangeCount" }, props,
                "仅暴露会话级换场记录；无节律/质量/period 状态可读");
        }

        [Test]
        public void OnSessionSegmentChanged_RecordsSegment()
        {
            pass.OnSessionSegmentChanged("closed_loop");
            pass.OnSessionSegmentChanged("open_loop");
            Assert.AreEqual("open_loop", pass.LastSessionSegment);
            Assert.AreEqual(2, pass.SegmentChangeCount);
        }

        [Test]
        public void NoStaticRhythmMembers()
        {
            var statics = typeof(BackgroundPass)
                .GetMembers(BindingFlags.Public | BindingFlags.Static | BindingFlags.DeclaredOnly)
                .Select(m => m.Name)
                .ToArray();
            CollectionAssert.IsEmpty(statics,
                "Background 不得有任何静态成员（封印：零节律、零质量、零 period）");
        }
    }
}
