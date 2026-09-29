using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class AssignLookdownSprite : EditorWindow
{
    [MenuItem("SRP/Assign Lookdown + Idle Sprites")]
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        var traveler = GameObject.Find("Traveler");
        var walk05 = traveler.GetComponent<WalkBG05>();

        var lookdown = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_lookdown.png");
        var idle = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_idle.png");

        var serialized = new SerializedObject(walk05);
        serialized.FindProperty("lookdownSprite").objectReferenceValue = lookdown;
        serialized.FindProperty("idleSprite").objectReferenceValue = idle;
        serialized.ApplyModifiedProperties();
        EditorUtility.SetDirty(walk05);

        Debug.Log($"[SPRITE] lookdown={lookdown?.name} idle={idle?.name}");

        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[SPRITE] Done + saved.");
    }
}
