using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using Process = System.Diagnostics.Process;
using ProcessStartInfo = System.Diagnostics.ProcessStartInfo;

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
            ValidateAssetGovernance();

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

        private static void ValidateAssetGovernance()
        {
            var unityRoot = Directory.GetParent(Application.dataPath)?.FullName;
            var technicalRoot = unityRoot == null
                ? null
                : Directory.GetParent(Directory.GetParent(unityRoot)?.FullName ?? string.Empty)?.FullName;
            var repoRoot = technicalRoot == null
                ? null
                : Directory.GetParent(technicalRoot)?.FullName;
            if (unityRoot == null || repoRoot == null)
            {
                throw new BuildFailedException("ASSET_LICENSE_GATE_PATH_UNAVAILABLE");
            }

            var script = Path.Combine(repoRoot, "02-技术研发", "07-数据治理", "g02.py");
            var ledger = Path.Combine(unityRoot, "Governance", "asset_license_ledger.json");
            var baseline = Path.Combine(unityRoot, "Governance", "asset_inventory.json");
            var report = Path.Combine(Path.GetTempPath(), $"srp-g02-asset-{Guid.NewGuid():N}.json");
            var arguments = string.Join(" ", new[]
            {
                "-3.14", Quote(script), "scan-assets",
                "--repo-root", Quote(repoRoot),
                "--unity-root", Quote(unityRoot),
                "--ledger", Quote(ledger),
                "--baseline", Quote(baseline),
                "--output", Quote(report),
            });

            try
            {
                using var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "py",
                        Arguments = arguments,
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        CreateNoWindow = true,
                    }
                };
                if (!process.Start())
                {
                    throw new BuildFailedException("ASSET_LICENSE_GATE_START_FAILED");
                }
                var standardOutput = process.StandardOutput.ReadToEnd();
                var standardError = process.StandardError.ReadToEnd();
                if (!process.WaitForExit(120000))
                {
                    process.Kill();
                    throw new BuildFailedException("ASSET_LICENSE_GATE_TIMEOUT");
                }
                if (process.ExitCode != 0)
                {
                    throw new BuildFailedException(
                        $"ASSET_LICENSE_GATE_BLOCKED: exit={process.ExitCode}; " +
                        $"stdout={OneLine(standardOutput)}; stderr={OneLine(standardError)}");
                }
            }
            catch (BuildFailedException)
            {
                throw;
            }
            catch (Exception exception)
            {
                throw new BuildFailedException(
                    "ASSET_LICENSE_GATE_UNAVAILABLE: " + exception.GetType().Name);
            }
            finally
            {
                if (File.Exists(report))
                {
                    File.Delete(report);
                }
            }
        }

        private static string Quote(string value) => $"\"{value.Replace("\"", "\\\"")}\"";

        private static string OneLine(string value) =>
            value.Replace("\r", " ").Replace("\n", " ").Trim();
    }
}
