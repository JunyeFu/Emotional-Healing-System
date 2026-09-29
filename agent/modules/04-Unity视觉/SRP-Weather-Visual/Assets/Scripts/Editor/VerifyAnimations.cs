using UnityEngine;
using UnityEditor;

public class VerifyAnimations : EditorWindow
{
    [MenuItem("SRP/Verify All Animations")]
    public static void Run()
    {
        Debug.Log("=== Animation Clip Verification ===");

        VerifyClip("Walk", "Assets/Animations/Walk.anim");
        VerifyClip("Fall", "Assets/Animations/Fall.anim");
        VerifyClip("Stand2", "Assets/Animations/Stand2.anim");
        VerifyClip("Shield_Cracked", "Assets/Animations/Shield_Cracked.anim");

        var controller = AssetDatabase.LoadAssetAtPath<UnityEditor.Animations.AnimatorController>("Assets/Animations/Traveler.controller");
        Debug.Log($"=== AnimatorController: {controller.name} ===");
        Debug.Log($"Layers: {controller.layers.Length}, States in Base: {controller.layers[0].stateMachine.states.Length}");
        foreach (var s in controller.layers[0].stateMachine.states)
            Debug.Log($"  State: {s.state.name} (clip: {s.state.motion?.name})");
        Debug.Log($"Parameters: {controller.parameters.Length}");
        foreach (var p in controller.parameters)
            Debug.Log($"  Param: {p.name} ({p.type})");

        Debug.Log("[VERIFY] Done — read-only, no scene changes.");
    }

    static void VerifyClip(string label, string path)
    {
        var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
        if (clip == null) { Debug.LogError($"[VERIFY] {label}: NOT FOUND at {path}"); return; }

        var bindings = AnimationUtility.GetObjectReferenceCurveBindings(clip);
        if (bindings.Length == 0)
        {
            Debug.LogWarning($"[VERIFY] {label}: no ObjectReference curves");
            return;
        }

        var curve = AnimationUtility.GetObjectReferenceCurve(clip, bindings[0]);
        Debug.Log($"[VERIFY] {label}: {curve.Length} frames, length={clip.length}s, loop={clip.isLooping}, fps={clip.frameRate}");

        for (int i = 0; i < curve.Length; i++)
        {
            var sprite = curve[i].value as Sprite;
            Debug.Log($"[VERIFY]   frame[{i}] @ {curve[i].time:F3}s: {(sprite != null ? sprite.name : "NULL")}");
        }
    }
}
