using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace SRP.Editor
{
    /// <summary>
    /// Prevents a legacy SampleScene/v1.2 prototype from being published as
    /// the formal v2.1 runtime. This gate remains red until the formal runtime
    /// controller and all four weather scenes are actually implemented.
    /// </summary>
    public sealed class FormalBuildGate : IPreprocessBuildWithReport
    {
        private static readonly string[] RequiredScenes =
        {
            "Assets/Scenes/StormScene.unity",
            "Assets/Scenes/HeatScene.unity",
            "Assets/Scenes/SnowScene.unity",
            "Assets/Scenes/FadeScene.unity",
        };

        public int callbackOrder => -1000;

        public void OnPreprocessBuild(BuildReport report) => ValidateOrThrow();

        [MenuItem("SRP/Validate Formal v2.1 Build")]
        public static void ValidateFromMenu()
        {
            ValidateOrThrow();
            Debug.Log("SRP_FORMAL_BUILD_GATE_PASS");
        }

        public static void ValidateFromCommandLine()
        {
            try
            {
                ValidateOrThrow();
                Debug.Log("SRP_FORMAL_BUILD_GATE_PASS");
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        private static void ValidateOrThrow()
        {
            var enabledScenes = EditorBuildSettings.scenes
                .Where(scene => scene.enabled)
                .Select(scene => scene.path)
                .ToHashSet(StringComparer.Ordinal);
            var missingScenes = RequiredScenes.Where(scene => !enabledScenes.Contains(scene)).ToArray();
            if (missingScenes.Length > 0)
            {
                throw new BuildFailedException(
                    "FORMAL_SCENES_MISSING: " + string.Join(",", missingScenes));
            }

            var failures = new List<string>();
            foreach (var scenePath in RequiredScenes)
            {
                var scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
                var behaviours = scene.GetRootGameObjects()
                    .SelectMany(root => root.GetComponentsInChildren<MonoBehaviour>(true))
                    .Where(item => item != null)
                    .ToArray();

                if (behaviours.Any(item => item is WeatherController || item is SpoutReceiver))
                {
                    failures.Add(scenePath + ":LEGACY_RUNTIME_COMPONENT_PRESENT");
                }
                if (!behaviours.Any(item => item.GetType().Name == "FormalRuntimeController"))
                {
                    failures.Add(scenePath + ":FORMAL_RUNTIME_CONTROLLER_MISSING");
                }
            }

            if (failures.Count > 0)
            {
                throw new BuildFailedException(
                    "SRP formal v2.1 build gate failed: " + string.Join(";", failures));
            }
        }
    }
}
