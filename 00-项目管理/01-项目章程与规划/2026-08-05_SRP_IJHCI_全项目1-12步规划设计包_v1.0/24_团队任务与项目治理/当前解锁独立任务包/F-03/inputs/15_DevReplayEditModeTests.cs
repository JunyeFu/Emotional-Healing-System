using NUnit.Framework;
using SRP.F03.Editor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace SRP.F03.Tests
{
    public sealed class DevReplayEditModeTests
    {
        [Test]
        public void BannerExposesNonFormalIdentityAndBuildEvidence()
        {
            var gameObject = new GameObject("BannerUnderTest");
            try
            {
                var banner = gameObject.AddComponent<DevReplayBanner>();
                banner.ConfigureBuildEvidence("abcdef12", "2026-08-30T08:00:00Z", "6000.4.9f1 (f7258d6eebbe)");

                Assert.That(banner.ModeLabel, Is.EqualTo("DEV-REPLAY"));
                Assert.That(banner.FormalityLabel, Is.EqualTo("NOT FORMAL"));
                Assert.That(banner.BuildCommit, Is.EqualTo("abcdef12"));
                Assert.That(banner.BuildUtc, Is.EqualTo("2026-08-30T08:00:00Z"));
                Assert.That(banner.UnityRevision, Is.EqualTo("6000.4.9f1 (f7258d6eebbe)"));
            }
            finally
            {
                Object.DestroyImmediate(gameObject);
            }
        }

        [Test]
        public void DevelopmentBuildRequiresExplicitF03Authorization()
        {
            Assert.That(F03BuildAuthorization.IsAuthorized("1"), Is.True);
            Assert.That(F03BuildAuthorization.IsAuthorized(null), Is.False);
            Assert.That(F03BuildAuthorization.IsAuthorized("true"), Is.False);
        }

        [Test]
        public void DevelopmentSceneContainsOnlyTheF03MarkerRuntime()
        {
            var scene = EditorSceneManager.OpenScene(F03SceneContract.SourceScenePath, OpenSceneMode.Single);
            var result = F03SceneContract.Inspect(scene);

            Assert.That(result.IsValid, Is.True, result.Error);
            Assert.That(result.BannerCount, Is.EqualTo(1));
            Assert.That(result.ForbiddenComponentNames, Is.Empty);
        }
    }
}
