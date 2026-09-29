using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class ApplyBridgeParams : EditorWindow
{
    [MenuItem("SRP/Apply Bridge Params — bg04/bg05 Y + Speed")]
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        // bg04
        var walk04 = Object.FindObjectOfType<WalkBG04>();
        if (walk04 != null)
        {
            var serialized = new SerializedObject(walk04);
            serialized.FindProperty("bridgeWorldY").floatValue = -2.63f;
            serialized.FindProperty("walkSpeed").floatValue = 1.76f;
            serialized.ApplyModifiedProperties();
            EditorUtility.SetDirty(walk04);
            Debug.Log($"[APPLY] WalkBG04: bridgeWorldY={walk04.bridgeWorldY}, walkSpeed={walk04.walkSpeed}");
        }
        else Debug.LogError("[APPLY] WalkBG04 not found!");

        // bg05
        var walk05 = Object.FindObjectOfType<WalkBG05>();
        if (walk05 != null)
        {
            var serialized = new SerializedObject(walk05);
            serialized.FindProperty("bridgeWorldY").floatValue = -0.4f;
            serialized.FindProperty("walkSpeed").floatValue = 1.98f;
            serialized.ApplyModifiedProperties();
            EditorUtility.SetDirty(walk05);
            Debug.Log($"[APPLY] WalkBG05: bridgeWorldY={walk05.bridgeWorldY}, walkSpeed={walk05.walkSpeed}");
        }
        else Debug.LogError("[APPLY] WalkBG05 not found!");

        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[APPLY] Scene saved.");
    }
}
