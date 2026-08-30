using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SRP.F03.Editor
{
    public static class F03SceneContract
    {
        public const string SourceScenePath = "Assets/F03/Scenes/F03DevReplay.unity";

        private static readonly HashSet<string> ForbiddenComponentNames = new(StringComparer.Ordinal)
        {
            "FormalRuntimeController",
            "SpoutReceiver",
            "UDPReceiver",
            "WeatherController"
        };

        public static F03SceneInspection Inspect(Scene scene)
        {
            if (!scene.IsValid() || !scene.isLoaded)
            {
                return new F03SceneInspection(0, Array.Empty<string>(), "F03_SCENE_NOT_LOADED");
            }

            var behaviours = scene.GetRootGameObjects()
                .SelectMany(root => root.GetComponentsInChildren<MonoBehaviour>(true))
                .ToArray();
            if (behaviours.Any(item => item == null))
            {
                return new F03SceneInspection(0, Array.Empty<string>(), "F03_SCENE_MISSING_SCRIPT");
            }

            var bannerCount = behaviours.Count(item => item is DevReplayBanner);
            var forbidden = behaviours
                .Select(item => item.GetType().Name)
                .Where(ForbiddenComponentNames.Contains)
                .Distinct(StringComparer.Ordinal)
                .OrderBy(item => item, StringComparer.Ordinal)
                .ToArray();
            var error = bannerCount == 1 && forbidden.Length == 0
                ? null
                : $"F03_SCENE_CONTRACT_FAILED banner_count={bannerCount} forbidden={string.Join(",", forbidden)}";
            return new F03SceneInspection(bannerCount, forbidden, error);
        }
    }

    public sealed class F03SceneInspection
    {
        public F03SceneInspection(int bannerCount, IReadOnlyList<string> forbiddenComponentNames, string error)
        {
            BannerCount = bannerCount;
            ForbiddenComponentNames = forbiddenComponentNames;
            Error = error;
        }

        public int BannerCount { get; }
        public IReadOnlyList<string> ForbiddenComponentNames { get; }
        public string Error { get; }
        public bool IsValid => string.IsNullOrEmpty(Error);
    }
}
