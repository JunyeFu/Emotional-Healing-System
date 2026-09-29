using UnityEngine;
using UnityEditor.Animations;
using UnityEditor;
using System.IO;

public class CreateAnimations : EditorWindow
{
    [MenuItem("SRP/Create All Animations")]
    public static void CreateAllAnimations()
    {
        CreateWalkAnimation();
        CreateFallAnimation();
        CreateShieldAnimation();
        CreateLookdownAnimation();
        CreateIdleAnimation();
        CreateTravelerController();
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("[SRP] All animations and controller created!");
    }

    static AnimationClip CreateClip(string name, float fps, bool loop)
    {
        var path = "Assets/Animations/" + name + ".anim";
        var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
        if (existing != null) AssetDatabase.DeleteAsset(path);
        var clip = new AnimationClip { name = name, frameRate = fps };
        var settings = AnimationUtility.GetAnimationClipSettings(clip);
        settings.loopTime = loop;
        AnimationUtility.SetAnimationClipSettings(clip, settings);
        return clip;
    }

    static void AddSpriteFrames(AnimationClip clip, string[] spriteNames, string subfolder)
    {
        var bind = EditorCurveBinding.PPtrCurve("", typeof(SpriteRenderer), "m_Sprite");
        var frames = new ObjectReferenceKeyframe[spriteNames.Length];
        float interval = 1f / clip.frameRate;
        for (int i = 0; i < spriteNames.Length; i++)
        {
            var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(
                "Assets/Sprites/traveler/" + subfolder + "/" + spriteNames[i] + ".png");
            frames[i] = new ObjectReferenceKeyframe { time = i * interval, value = sprite };
        }
        AnimationUtility.SetObjectReferenceCurve(clip, bind, frames);
    }

    static void CreateWalkAnimation()
    {
        var clip = CreateClip("Walk", 8f, true);
        AddSpriteFrames(clip, new[]{"walk_01","walk_02","walk_03","walk_04"}, "walk");
        AssetDatabase.CreateAsset(clip, "Assets/Animations/Walk.anim");
        Debug.Log("Created Walk animation (4 frames, 8fps)");
    }

    static void CreateFallAnimation()
    {
        var clip = CreateClip("Fall", 6f, false);
        AddSpriteFrames(clip, new[]{"fall_1","fall_2","fall_3","fall_4","fall_5","fall_6","fall_7","fall_8"}, "fall");
        AssetDatabase.CreateAsset(clip, "Assets/Animations/Fall.anim");
        Debug.Log("Created Fall animation (8 frames, 6fps)");
    }

    static void CreateShieldAnimation()
    {
        var clip = CreateClip("Shield_Appear", 8f, false);
        AddSpriteFrames(clip, new[]{"shield_00","shield_01","shield_02","shield_03","shield_04","shield_05","shield_06","shield_07","shield_08"}, "shield");
        AssetDatabase.CreateAsset(clip, "Assets/Animations/Shield_Appear.anim");
        Debug.Log("Created Shield animation (9 frames, 8fps)");
    }

    static void CreateLookdownAnimation()
    {
        var clip = CreateClip("Lookdown", 1f, true);
        var bind = EditorCurveBinding.PPtrCurve("", typeof(SpriteRenderer), "m_Sprite");
        var sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_lookdown.png");
        var frames = new ObjectReferenceKeyframe[]{ new ObjectReferenceKeyframe{time=0,value=sprite} };
        AnimationUtility.SetObjectReferenceCurve(clip, bind, frames);
        AssetDatabase.CreateAsset(clip, "Assets/Animations/Lookdown.anim");
        Debug.Log("Created Lookdown animation (1 frame)");
    }

    static void CreateIdleAnimation()
    {
        var clip = CreateClip("Idle", 1f, true);
        var bind = EditorCurveBinding.PPtrCurve("", typeof(SpriteRenderer), "m_Sprite");
        var sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_idle.png");
        var frames = new ObjectReferenceKeyframe[]{ new ObjectReferenceKeyframe{time=0,value=sprite} };
        AnimationUtility.SetObjectReferenceCurve(clip, bind, frames);
        AssetDatabase.CreateAsset(clip, "Assets/Animations/Idle.anim");
        Debug.Log("Created Idle animation (1 frame)");
    }

    static void CreateTravelerController()
    {
        var path = "Assets/Animations/Traveler.controller";
        var existing = AssetDatabase.LoadAssetAtPath<AnimatorController>(path);
        if (existing != null) AssetDatabase.DeleteAsset(path);

        var controller = AnimatorController.CreateAnimatorControllerAtPath(path);
        var rootSM = controller.layers[0].stateMachine;

        // Get clips
        var idleClip = AssetDatabase.LoadAssetAtPath<AnimationClip>("Assets/Animations/Idle.anim");
        var walkClip = AssetDatabase.LoadAssetAtPath<AnimationClip>("Assets/Animations/Walk.anim");
        var fallClip = AssetDatabase.LoadAssetAtPath<AnimationClip>("Assets/Animations/Fall.anim");
        var shieldClip = AssetDatabase.LoadAssetAtPath<AnimationClip>("Assets/Animations/Shield_Appear.anim");
        var lookdownClip = AssetDatabase.LoadAssetAtPath<AnimationClip>("Assets/Animations/Lookdown.anim");

        // Add states
        rootSM.AddState("Idle").motion = idleClip;
        rootSM.AddState("Walk").motion = walkClip;
        rootSM.AddState("Fall").motion = fallClip;
        rootSM.AddState("Shield").motion = shieldClip;
        rootSM.AddState("Lookdown").motion = lookdownClip;

        rootSM.defaultState = rootSM.states[0].state;

        Debug.Log("Created Traveler.controller with 5 states: Idle(default), Walk, Fall, Shield, Lookdown");
    }
}
