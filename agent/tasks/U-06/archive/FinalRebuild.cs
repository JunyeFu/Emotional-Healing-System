using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering.Universal;

public class FinalRebuild : EditorWindow
{
    [MenuItem("SRP/Final Rebuild Scene 1")]
    public static void Build()
    {
        // Import sprites
        var guids = AssetDatabase.FindAssets("t:Texture2D", new[]{"Assets/Sprites"});
        foreach (var g in guids)
        {
            var p = AssetDatabase.GUIDToAssetPath(g);
            var imp = AssetImporter.GetAtPath(p) as TextureImporter;
            if (imp == null) continue;
            imp.textureType = TextureImporterType.Sprite;
            imp.filterMode = FilterMode.Point;
            imp.textureCompression = TextureImporterCompression.Uncompressed;
            imp.spritePixelsPerUnit = 32;
            imp.SaveAndReimport();
        }
        AssetDatabase.Refresh();

        var scene = EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);
        foreach (var r in scene.GetRootGameObjects()) DestroyImmediate(r);

        float bgW = 12f * 16f / 9f;

        // === CAMERA (explicit URP setup) ===
        var camGO = new GameObject("MainCamera");
        camGO.tag = "MainCamera";
        camGO.transform.position = new Vector3(0, 0, -10);
        var cam = camGO.AddComponent<Camera>();
        cam.orthographic = true;
        cam.orthographicSize = 6f;
        cam.nearClipPlane = 0.01f;
        cam.farClipPlane = 1000f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.078f, 0.078f, 0.149f); // #141426 very dark blue
        cam.depth = -1;
        cam.targetDisplay = 0;

        var urp = camGO.AddComponent<UniversalAdditionalCameraData>();
        urp.renderPostProcessing = false;
        urp.antialiasing = AntialiasingMode.None;
        urp.stopNaN = false;
        urp.dithering = false;
        // Force renderer index 0 (default)
        urp.SetRenderer(0);

        // === SPRITE MATERIAL ===
        var mat = new Material(Shader.Find("Sprites/Default"));

        // === BACKGROUNDS ===
        var bgContainer = new GameObject("BackgroundContainer");
        for (int i = 0; i < 5; i++)
        {
            var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(
                "Assets/Sprites/backgrounds/bg_0" + (i+1) + ".png");
            var go = new GameObject("bg_0" + (i+1));
            go.transform.SetParent(bgContainer.transform);
            go.transform.position = new Vector3(-i * bgW, 0, 0);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sprite;
            sr.sharedMaterial = mat;
            sr.sortingOrder = -10;
            if (sprite != null)
            {
                float sh = cam.orthographicSize * 2f;
                float sw = sh * 16f / 9f;
                go.transform.localScale = new Vector3(
                    sw / sprite.bounds.size.x, sh / sprite.bounds.size.y, 1);
            }
            Debug.Log("[BUILD] " + go.name + " sprite=" + (sr.sprite != null ? sr.sprite.name : "NULL"));
        }

        // === TRAVELER ===
        var travGO = new GameObject("Traveler");
        travGO.transform.position = new Vector3(7, -2, 0);
        var tSR = travGO.AddComponent<SpriteRenderer>();
        tSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_idle.png");
        tSR.sharedMaterial = mat;
        tSR.sortingOrder = 0;
        var anim = travGO.AddComponent<Animator>();
        anim.runtimeAnimatorController = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(
            "Assets/Animations/Traveler.controller");

        // Shield
        var shieldGO = new GameObject("Shield");
        shieldGO.transform.SetParent(travGO.transform);
        shieldGO.transform.localPosition = Vector3.zero;
        var shSR = shieldGO.AddComponent<SpriteRenderer>();
        shSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/shield/shield_00.png");
        shSR.sharedMaterial = mat;
        shSR.sortingOrder = 5;
        shieldGO.SetActive(false);

        // === RAIN ===
        var rainGO = new GameObject("RainParticles");
        rainGO.transform.position = new Vector3(0, 6, 0);
        var ps = rainGO.AddComponent<ParticleSystem>();
        var main = ps.main;
        main.startSize = 0.12f; main.maxParticles = 400;
        main.startSpeed = new ParticleSystem.MinMaxCurve(10, 20);
        main.startLifetime = 1.2f;
        main.startColor = new Color(0.55f, 0.65f, 1f, 0.65f);
        main.gravityModifier = 1.2f;
        main.duration = 999f; main.loop = true;
        var em = ps.emission; em.rateOverTime = 0f;
        var shape = ps.shape;
        shape.shapeType = ParticleSystemShapeType.Box;
        shape.scale = new Vector3(bgW * 3, 0.05f, 1);
        shape.position = new Vector3(0, 3, 0);
        ps.Stop();
        var psr = rainGO.GetComponent<ParticleSystemRenderer>();
        psr.material = mat;
        psr.sortingOrder = 10;

        // === LIGHTNING ===
        var lightGO = new GameObject("LightningOverlay");
        lightGO.transform.position = Vector3.zero;
        var lSR = lightGO.AddComponent<SpriteRenderer>();
        lSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/effects/lightning_full.png");
        lSR.sharedMaterial = mat;
        lSR.sortingOrder = 100;
        lSR.color = new Color(1, 1, 1, 0.5f);
        lightGO.SetActive(false);

        // === PROMPT DISPLAY ===
        var promptGO = new GameObject("PromptDisplay");
        promptGO.transform.position = new Vector3(0, 3.5f, 0);

        // === SCENE 1 DIRECTOR ===
        var dirGO = new GameObject("Scene1Director");
        var director = dirGO.AddComponent<Scene1Director>();
        var so = new SerializedObject(director);
        so.FindProperty("traveler").objectReferenceValue = travGO;
        so.FindProperty("shield").objectReferenceValue = shieldGO;
        so.FindProperty("rainPS").objectReferenceValue = ps;
        so.FindProperty("lightningOverlay").objectReferenceValue = lightGO;
        so.FindProperty("backgroundContainer").objectReferenceValue = bgContainer;
        so.FindProperty("mainCamera").objectReferenceValue = cam;
        so.FindProperty("idleDuration").floatValue = 3f;
        so.FindProperty("walkSpeed").floatValue = 2.2f;
        var spArr = so.FindProperty("shieldSprites");
        spArr.arraySize = 9;
        for (int i = 0; i < 9; i++)
            spArr.GetArrayElementAtIndex(i).objectReferenceValue =
                AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/shield/shield_0"+i+".png");
        so.ApplyModifiedProperties();

        EditorSceneManager.SaveScene(scene);
        Debug.Log("[SRP] ===== Scene 1 Final Build Complete =====");
        Debug.Log("[SRP] 5 backgrounds, Traveler+Shield+Animator, RainPS, Lightning, Scene1Director");
    }
}
