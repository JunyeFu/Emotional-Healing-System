using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace SRP.F03.Tests
{
    public sealed class DevReplayPlayModeTests
    {
        [UnityTest]
        public IEnumerator BannerRemainsVisibleAndNonFormalAcrossFrames()
        {
            var gameObject = new GameObject("BannerUnderTest");
            var banner = gameObject.AddComponent<DevReplayBanner>();

            yield return null;
            yield return null;

            Assert.That(banner.isActiveAndEnabled, Is.True);
            Assert.That(banner.ModeLabel, Is.EqualTo("DEV-REPLAY"));
            Assert.That(banner.FormalityLabel, Is.EqualTo("NOT FORMAL"));

            Object.Destroy(gameObject);
        }
    }
}
