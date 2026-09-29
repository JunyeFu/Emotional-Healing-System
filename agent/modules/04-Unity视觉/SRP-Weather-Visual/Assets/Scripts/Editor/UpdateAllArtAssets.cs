using UnityEngine;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering.Universal;
using System.Collections.Generic;
using System.Linq;

public class UpdateAllArtAssets : EditorWindow
{
    [MenuItem("SRP/Update ALL Art Assets (Full Rebuild)")]
    public static void Run()
    {
        Debug.Log("===== [ART] Starting full art asset update =====");

        // 1. Refresh asset database to pick up new files
        AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
        Debug.Log("[ART] Step 1: Asset refresh done");

        // 2. Configure all sprite imports
        ConfigureAllSprites();
        AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
        Debug.Log("[ART] Step 2: Sprite imports configured");

        // 3. Update Walk animation to 6 frames
        UpdateWalkAnimation();
        Debug.Log("[ART] Step 3: Walk animation updated");

        // 4. Create new animation clips for new poses
        CreatePoseAnimations();
        Debug.Log("[ART] Step 4: Pose animations created");

        // 5. Update Animator controller
        UpdateAnimatorController();
        Debug.Log("[ART] Step 5: Animator controller updated");

        // 6. Rebuild StormScene (scene is now open and modified)
        RebuildStormScene();
        Debug.Log("[ART] Step 6: StormScene rebuilt");

        // 7. Camera setup (inline, no scene reload)
        SetupCamera();
        Debug.Log("[ART] Step 7: Camera configured");

        // 8. Save scene
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[ART] Step 8: Scene saved");

        // 9. GameView 1080p
        try { ScaleTravelerAndScene.SetGameView1080p(); }
        catch (System.Exception e) { Debug.LogWarning($"[ART] GameView 1080p failed (non-critical): {e.Message}"); }

        Debug.Log("===== [ART] Full art asset update COMPLETE =====");
    }

    static void ConfigureAllSprites()
    {
        string[] spritePaths = {
            "Assets/Sprites/traveler/traveler_idle.png",
            "Assets/Sprites/traveler/traveler_lookdown.png",
            "Assets/Sprites/traveler/pose_kneel.png",
            "Assets/Sprites/traveler/pose_kneel2.png",
            "Assets/Sprites/traveler/pose_kneel3.png",
            "Assets/Sprites/traveler/pose_run.png",
            "Assets/Sprites/traveler/pose_sit.png",
            "Assets/Sprites/traveler/pose_stand2.png",
            "Assets/Sprites/traveler/walk/walk_01.png",
            "Assets/Sprites/traveler/walk/walk_02.png",
            "Assets/Sprites/traveler/walk/walk_03.png",
            "Assets/Sprites/traveler/walk/walk_04.png",
            "Assets/Sprites/traveler/walk/walk_05.png",
            "Assets/Sprites/traveler/walk/walk_06.png",
            "Assets/Sprites/traveler/shield/shield_clean.png",
            "Assets/Sprites/traveler/shield/shield_cracked.png",
            "Assets/Sprites/traveler/shield/shield_00.png",
            "Assets/Sprites/traveler/shield/shield_01.png",
            "Assets/Sprites/traveler/shield/shield_02.png",
            "Assets/Sprites/traveler/shield/shield_03.png",
            "Assets/Sprites/traveler/shield/shield_04.png",
            "Assets/Sprites/traveler/shield/shield_05.png",
            "Assets/Sprites/traveler/shield/shield_06.png",
            "Assets/Sprites/traveler/shield/shield_07.png",
            "Assets/Sprites/traveler/shield/shield_08.png",
            "Assets/Sprites/effects/lightning_full.png",
            "Assets/Sprites/effects/rain_drop.png",
            "Assets/Sprites/effects/speed_trail.png",
            "Assets/Sprites/backgrounds/bg_01.png",
            "Assets/Sprites/backgrounds/bg_02.png",
            "Assets/Sprites/backgrounds/bg_03.png",
            "Assets/Sprites/backgrounds/bg_04.png",
            "Assets/Sprites/backgrounds/bg_05.png",
        };

        foreach (string path in spritePaths)
        {
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null)
            {
                Debug.LogWarning($"[ART] No TextureImporter for: {path}");
                continue;
            }
            bool changed = false;

            if (importer.textureType != TextureImporterType.Sprite)
            {
                importer.textureType = TextureImporterType.Sprite;
                changed = true;
            }
            if (importer.spriteImportMode != SpriteImportMode.Single)
            {
                importer.spriteImportMode = SpriteImportMode.Single;
                changed = true;
            }
            if (importer.spritePixelsPerUnit != 32)
            {
                importer.spritePixelsPerUnit = 32;
                changed = true;
            }
            if (importer.filterMode != FilterMode.Point)
            {
                importer.filterMode = FilterMode.Point;
                changed = true;
            }
            if (importer.textureCompression != TextureImporterCompression.Uncompressed)
            {
                importer.textureCompression = TextureImporterCompression.Uncompressed;
                changed = true;
            }
            if (importer.mipmapEnabled)
            {
                importer.mipmapEnabled = false;
                changed = true;
            }
            if (!importer.alphaIsTransparency)
            {
                importer.alphaIsTransparency = true;
                changed = true;
            }
            if (importer.maxTextureSize < 2048)
            {
                importer.maxTextureSize = 2048;
                changed = true;
            }

            if (changed)
            {
                importer.SaveAndReimport();
                Debug.Log($"[ART] Configured: {path}");
            }
        }
    }

    static void UpdateWalkAnimation()
    {
        string clipPath = "Assets/Animations/Walk.anim";
        var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
        if (clip == null)
        {
            Debug.LogError("[ART] Walk.anim not found!");
            return;
        }

        // Frame rate: 8fps → 0.125s per frame. 6 frames = 0.75s total.
        float frameInterval = 1f / 8f;
        float totalTime = frameInterval * 6f;

        // Get sprite references for all 6 walk frames
        var spriteRefs = new List<Sprite>();
        for (int i = 1; i <= 6; i++)
        {
            string path = $"Assets/Sprites/traveler/walk/walk_{i:D2}.png";
            var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(path);
            if (sprite == null)
            {
                Debug.LogError($"[ART] Walk frame not found: {path}");
                return;
            }
            spriteRefs.Add(sprite);
        }

        // Build keyframes
        var keyframes = new ObjectReferenceKeyframe[6];
        for (int i = 0; i < 6; i++)
        {
            keyframes[i] = new ObjectReferenceKeyframe
            {
                time = i * frameInterval,
                value = spriteRefs[i]
            };
        }

        // Find the sprite binding
        var bindings = AnimationUtility.GetObjectReferenceCurveBindings(clip);
        EditorCurveBinding spriteBinding;
        if (bindings.Length > 0)
        {
            spriteBinding = bindings[0];
        }
        else
        {
            spriteBinding = new EditorCurveBinding
            {
                path = "",
                type = typeof(SpriteRenderer),
                propertyName = "m_Sprite"
            };
        }

        AnimationUtility.SetObjectReferenceCurve(clip, spriteBinding, keyframes);

        // Update clip settings
        var settings = AnimationUtility.GetAnimationClipSettings(clip);
        settings.startTime = 0f;
        settings.stopTime = totalTime;
        settings.loopTime = true;
        AnimationUtility.SetAnimationClipSettings(clip, settings);

        clip.frameRate = 8f;

        EditorUtility.SetDirty(clip);
        Debug.Log($"[ART] Walk.anim updated: 6 frames, {totalTime}s, 8fps");
    }

    static void CreatePoseAnimations()
    {
        // Kneel animation: 3-frame sequential
        CreateSingleSpriteAnim("Assets/Animations/Kneel.anim",
            "Assets/Sprites/traveler/pose_kneel.png", 1f, false);

        // Run animation: single frame
        CreateSingleSpriteAnim("Assets/Animations/Run.anim",
            "Assets/Sprites/traveler/pose_run.png", 0.5f, true);

        // Sit animation: single frame
        CreateSingleSpriteAnim("Assets/Animations/Sit.anim",
            "Assets/Sprites/traveler/pose_sit.png", 1f, false);

        // Stand2 animation: alternate idle variant
        CreateSingleSpriteAnim("Assets/Animations/Stand2.anim",
            "Assets/Sprites/traveler/pose_stand2.png", 1f, false);

        // Shield_Clean animation: single frame
        CreateSingleSpriteAnim("Assets/Animations/Shield_Clean.anim",
            "Assets/Sprites/traveler/shield/shield_clean.png", 1f, false);

        // Shield_Cracked animation: single frame
        CreateSingleSpriteAnim("Assets/Animations/Shield_Cracked.anim",
            "Assets/Sprites/traveler/shield/shield_cracked.png", 1f, false);
    }

    static void CreateSingleSpriteAnim(string clipPath, string spritePath, float duration, bool loop)
    {
        // Delete if exists
        var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
        if (existing != null)
        {
            AssetDatabase.DeleteAsset(clipPath);
        }

        var clip = new AnimationClip();
        clip.name = System.IO.Path.GetFileNameWithoutExtension(clipPath);
        clip.frameRate = 8f;

        var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(spritePath);
        if (sprite == null)
        {
            Debug.LogError($"[ART] Sprite not found: {spritePath}");
            return;
        }

        // Single frame
        var keyframes = new ObjectReferenceKeyframe[1];
        keyframes[0] = new ObjectReferenceKeyframe { time = 0, value = sprite };

        var binding = new EditorCurveBinding
        {
            path = "",
            type = typeof(SpriteRenderer),
            propertyName = "m_Sprite"
        };

        AnimationUtility.SetObjectReferenceCurve(clip, binding, keyframes);

        var settings = AnimationUtility.GetAnimationClipSettings(clip);
        settings.startTime = 0f;
        settings.stopTime = duration;
        settings.loopTime = loop;
        AnimationUtility.SetAnimationClipSettings(clip, settings);

        AssetDatabase.CreateAsset(clip, clipPath);
        Debug.Log($"[ART] Created: {clipPath}");
    }

    static void UpdateAnimatorController()
    {
        string ctrlPath = "Assets/Animations/Traveler.controller";
        var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ctrlPath);
        if (controller == null)
        {
            Debug.LogError("[ART] Traveler.controller not found!");
            return;
        }

        var sm = controller.layers[0].stateMachine;

        // Helper to add a state with a clip
        System.Func<string, string, Vector3, AnimatorState> addState = (stateName, animPath, pos) =>
        {
            // Remove existing state with same name
            var existingStates = sm.states;
            foreach (var s in existingStates)
            {
                if (s.state.name == stateName)
                {
                    sm.RemoveState(s.state);
                    break;
                }
            }

            var state = sm.AddState(stateName, pos);
            var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(animPath);
            if (clip != null) state.motion = clip;
            else Debug.LogWarning($"[ART] Animation clip not found: {animPath}");
            return state;
        };

        // Add new states
        addState("Kneel", "Assets/Animations/Kneel.anim", new Vector3(400, 0, 0));
        addState("Run", "Assets/Animations/Run.anim", new Vector3(400, 70, 0));
        addState("Sit", "Assets/Animations/Sit.anim", new Vector3(400, 140, 0));
        addState("Stand2", "Assets/Animations/Stand2.anim", new Vector3(300, -70, 0));

        // Shield variants
        var shieldCleanState = addState("Shield_Clean", "Assets/Animations/Shield_Clean.anim", new Vector3(350, 210, 0));
        var shieldCrackedState = addState("Shield_Cracked", "Assets/Animations/Shield_Cracked.anim", new Vector3(420, 210, 0));

        // Add trigger parameters for transitions
        var parameters = controller.parameters.ToList();

        void AddParam(string name, AnimatorControllerParameterType type)
        {
            if (!parameters.Any(p => p.name == name))
            {
                controller.AddParameter(name, type);
                parameters.Add(controller.parameters.Last());
            }
        }

        AddParam("Kneel", AnimatorControllerParameterType.Trigger);
        AddParam("Run", AnimatorControllerParameterType.Trigger);
        AddParam("Sit", AnimatorControllerParameterType.Trigger);
        AddParam("ShieldClean", AnimatorControllerParameterType.Trigger);
        AddParam("ShieldCrack", AnimatorControllerParameterType.Trigger);

        EditorUtility.SetDirty(controller);
        Debug.Log("[ART] Animator controller updated with new states");
    }

    static void SetupCamera()
    {
        var cam = Camera.main;
        if (cam == null)
        {
            var camGo = new GameObject("MainCamera");
            camGo.tag = "MainCamera";
            cam = camGo.AddComponent<Camera>();
        }

        cam.orthographic = true;
        cam.orthographicSize = 6f;
        cam.nearClipPlane = 0.01f;
        cam.farClipPlane = 1000f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.08f, 0.08f, 0.15f, 1f);
        cam.depth = 0;
        cam.enabled = true;
        cam.allowHDR = false;
        cam.allowMSAA = false;
        cam.cullingMask = -1;

        var urpData = cam.GetComponent<UniversalAdditionalCameraData>();
        if (urpData == null)
            urpData = cam.gameObject.AddComponent<UniversalAdditionalCameraData>();
        urpData.renderPostProcessing = false;
        urpData.antialiasing = AntialiasingMode.None;
        urpData.renderShadows = false;
        urpData.stopNaN = false;
        urpData.dithering = false;
        urpData.allowXRRendering = false;

        Debug.Log("[ART] Camera: ortho size=6, SolidColor bg, URP configured");
    }

    static void RebuildStormScene()
    {
        // Open scene
        var scene = EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        // Delete existing scene root content (but keep Camera)
        var cam = Camera.main;
        if (cam == null)
        {
            var camGo = new GameObject("MainCamera");
            camGo.tag = "MainCamera";
            cam = camGo.AddComponent<Camera>();
        }

        // Destroy all root objects except camera
        foreach (var go in scene.GetRootGameObjects())
        {
            if (go != cam.gameObject) Object.DestroyImmediate(go);
        }

        // ===== BUILD SCENE HIERARCHY =====

        // Background container
        var bgContainer = new GameObject("BackgroundContainer");
        float bgWorldW = 1672f / 32f; // 52.25 units
        float bgScale = 12f / (941f / 32f); // viewH / bgH = 12 / 29.406 = 0.408

        for (int i = 0; i < 5; i++)
        {
            var bgGo = new GameObject($"bg_0{i + 1}");
            bgGo.transform.SetParent(bgContainer.transform);
            var sr = bgGo.AddComponent<SpriteRenderer>();
            var sprite = AssetDatabase.LoadAssetAtPath<Sprite>($"Assets/Sprites/backgrounds/bg_0{i + 1}.png");
            sr.sprite = sprite;
            sr.sortingOrder = -10;

            // Left-to-right arrangement: bg_01 at x=0, bg_02 at x=+bgWorldW, etc.
            float centerX = i * bgWorldW;
            bgGo.transform.position = new Vector3(centerX, 0, 0);
            bgGo.transform.localScale = new Vector3(bgScale, bgScale, 1f);
        }
        Debug.Log("[ART] BackgroundContainer built: 5 segments, left-to-right");

        // Traveler
        var travelerGo = new GameObject("Traveler");
        var travSr = travelerGo.AddComponent<SpriteRenderer>();
        var travSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_idle.png");
        travSr.sprite = travSprite;
        travSr.sortingOrder = 0;
        travelerGo.AddComponent<Animator>().runtimeAnimatorController =
            AssetDatabase.LoadAssetAtPath<AnimatorController>("Assets/Animations/Traveler.controller");

        // Scale and position traveler
        float travWorldH = travSprite.rect.height / travSprite.pixelsPerUnit;
        float targetH = 1.875f;
        float scale = targetH / travWorldH;
        travelerGo.transform.localScale = new Vector3(scale, scale, 1f);
        travelerGo.transform.position = new Vector3(7.467f, -1.594f, 0f);  // feet on foreground wasteland, Y from EdgeDetectBridge

        // Shield child
        var shieldGo = new GameObject("Shield");
        shieldGo.transform.SetParent(travelerGo.transform);
        shieldGo.transform.localPosition = Vector3.zero;
        var shieldSr = shieldGo.AddComponent<SpriteRenderer>();
        var shieldSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/shield/shield_00.png");
        shieldSr.sprite = shieldSprite;
        shieldSr.sortingOrder = 5;
        shieldSr.enabled = false; // hidden by default
        float shieldH = shieldSprite.rect.height / shieldSprite.pixelsPerUnit;
        shieldGo.transform.localScale = new Vector3(targetH / shieldH, targetH / shieldH, 1f);

        Debug.Log($"[ART] Traveler: scale={scale:F4}, pos=(-6,-3,0), Shield child added");

        // Weather container (placeholder)
        var weatherGo = new GameObject("WeatherSystem");

        // Controllers
        var ctrlGo = new GameObject("Controllers");
        ctrlGo.AddComponent<Scene1Director>();
        ctrlGo.AddComponent<UDPReceiver>();
        ctrlGo.AddComponent<WeatherController>();

        Debug.Log("[ART] Scene rebuilt with full hierarchy");
    }
}
