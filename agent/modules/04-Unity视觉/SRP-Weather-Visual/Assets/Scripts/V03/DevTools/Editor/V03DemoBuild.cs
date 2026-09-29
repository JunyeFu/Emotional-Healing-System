using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SRP.V03.DevTools
{
    /// <summary>
    /// U-02 降级演示一键构建（DEV ONLY）。
    /// 步骤 1：V03DemoBuild.CreateScene  —— 生成/刷新 DevTools/Scenes 下的演示场景
    /// 步骤 2：V03DemoBuild.BuildPlayer  —— 构建独立演示 exe（不含正式天气接线）
    /// </summary>
    public static class V03DemoBuild
    {
        private const string SceneDir = "Assets/Scripts/V03/DevTools/Scenes";
        private const string ScenePath = SceneDir + "/V03DegradationDemo.unity";

        public static void CreateScene()
        {
            if (!AssetDatabase.IsValidFolder(SceneDir))
                AssetDatabase.CreateFolder("Assets/Scripts/V03/DevTools", "Scenes");

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var go = new GameObject("V03DegradationDemo");
            go.AddComponent<V03DegradationDemoDriver>();
            var camera = new GameObject("DemoCamera").AddComponent<Camera>();
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0.08f, 0.09f, 0.10f, 1f);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log("V03_DEMO_SCENE_CREATED " + ScenePath);
        }

        public static void BuildPlayer()
        {
            string outDir = GetArg("--v03-out=");
            if (string.IsNullOrEmpty(outDir))
                throw new System.ArgumentException("--v03-out=<dir> required");

            Directory.CreateDirectory(outDir);

            var oldWidth = PlayerSettings.defaultScreenWidth;
            var oldHeight = PlayerSettings.defaultScreenHeight;
            var oldNative = PlayerSettings.defaultIsNativeResolution;
            var oldResizable = PlayerSettings.resizableWindow;
            PlayerSettings.defaultScreenWidth = 960;
            PlayerSettings.defaultScreenHeight = 600;
            PlayerSettings.defaultIsNativeResolution = false;
            PlayerSettings.resizableWindow = true;

            var options = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = Path.Combine(outDir, "V03DegradationDemo.exe"),
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.Development,
            };

            try
            {
                using var authorization = SRP.F03.Editor.F03BuildAuthorization.Begin();
                BuildReport report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                    throw new System.InvalidOperationException("V03 demo build failed: "
                        + report.summary.result + " errors=" + report.summary.totalErrors);
                Debug.Log("V03_DEMO_PLAYER_BUILT " + options.locationPathName);
            }
            finally
            {
                PlayerSettings.defaultScreenWidth = oldWidth;
                PlayerSettings.defaultScreenHeight = oldHeight;
                PlayerSettings.defaultIsNativeResolution = oldNative;
                PlayerSettings.resizableWindow = oldResizable;
                AssetDatabase.SaveAssets();
            }
        }

        private static string GetArg(string prefix)
        {
            foreach (string a in System.Environment.GetCommandLineArgs())
            {
                if (a.StartsWith(prefix)) return a.Substring(prefix.Length);
            }
            return null;
        }
    }
}
