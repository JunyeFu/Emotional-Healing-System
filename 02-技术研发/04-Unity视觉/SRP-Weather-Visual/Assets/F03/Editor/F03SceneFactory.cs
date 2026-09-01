using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace SRP.F03.Editor
{
    public static class F03SceneFactory
    {
        [MenuItem("SRP/F-03/Ensure DEV-REPLAY Scene")]
        public static void EnsureDevReplayScene()
        {
            Directory.CreateDirectory(Path.GetDirectoryName(F03SceneContract.SourceScenePath) ?? "Assets/F03/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var cameraObject = new GameObject("Main Camera");
            cameraObject.tag = "MainCamera";
            var camera = cameraObject.AddComponent<Camera>();
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0.035f, 0.055f, 0.09f, 1f);
            camera.orthographic = true;
            camera.transform.position = new Vector3(0f, 0f, -10f);

            var markerObject = new GameObject("F03 DEV-REPLAY Marker");
            markerObject.AddComponent<DevReplayBanner>();

            EditorSceneManager.SaveScene(scene, F03SceneContract.SourceScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log($"F03_DEV_REPLAY_SCENE_READY path={F03SceneContract.SourceScenePath}");
        }
    }
}
