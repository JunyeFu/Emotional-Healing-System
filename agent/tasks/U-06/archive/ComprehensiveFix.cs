using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering.Universal;
using UnityEngine.Rendering;
using System.Linq;

public class ComprehensiveFix : EditorWindow
{
    [MenuItem("SRP/Comprehensive Fix & Rebuild")]
    public static void Fix()
    {
        // === STEP 0: Check URP setup ===
        var pipeline = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
        Debug.Log("[FIX] URP Asset: " + (pipeline != null ? pipeline.name : "NULL - NOT URP!"));
        if (pipeline != null)
        {
            Debug.Log("[FIX]   DefaultRendererIndex: " + (int)pipeline.GetType()
                .GetField("m_DefaultRendererIndex", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)
                ?.GetValue(pipeline));
        }

        // === STEP 1: Reimport all sprites with correct settings ===
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

        // === STEP 2: Clean scene ===
        var scene = EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);
        foreach (var r in scene.GetRootGameObjects()) DestroyImmediate(r);

        float bgW = 12f * 16f/9f;

        // === STEP 3: Camera with URP support ===
        var camGO = new GameObject("MainCamera");
        camGO.tag = "MainCamera";
        camGO.transform.position = new Vector3(0, 0, -10);
        var cam = camGO.AddComponent<Camera>();
        cam.orthographic = true;
        cam.orthographicSize = 6f;
        cam.nearClipPlane = 0.01f;
        cam.farClipPlane = 1000f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.1f, 0.1f, 0.3f); // dark blue
        cam.cullingMask = -1;

        // Ensure URP camera data exists and is configured
        var urpCamData = camGO.GetComponent<UniversalAdditionalCameraData>();
        if (urpCamData == null)
            urpCamData = camGO.AddComponent<UniversalAdditionalCameraData>();
        urpCamData.renderPostProcessing = false;
        urpCamData.antialiasing = AntialiasingMode.None;
        urpCamData.renderShadows = false;

        // === STEP 4: Create sprite material (URP-compatible) ===
        var spriteMat = new Material(Shader.Find("Sprites/Default"));
        Debug.Log("[FIX] Sprite shader found: " + (spriteMat.shader != null ? spriteMat.shader.name : "NULL"));

        // === STEP 5: Backgrounds ===
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
            sr.material = spriteMat;
            sr.sortingOrder = -10;
            if (sprite != null)
            {
                float sh = cam.orthographicSize * 2f;
                float sw = sh * 16f/9f;
                go.transform.localScale = new Vector3(
                    sw / sprite.bounds.size.x,
                    sh / sprite.bounds.size.y, 1);
            }
            Debug.Log("[FIX] bg_0"+(i+1)+" sprite="+(sprite!=null?sprite.name:"NULL")+" sr.sprite="+(sr.sprite!=null?sr.sprite.name:"NULL"));
        }

        // === STEP 6: Traveler ===
        var travGO = new GameObject("Traveler");
        travGO.transform.position = new Vector3(7, -2, 0);
        var tSR = travGO.AddComponent<SpriteRenderer>();
        tSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_idle.png");
        tSR.material = spriteMat;
        tSR.sortingOrder = 0;
        var travAnim = travGO.AddComponent<Animator>();
        travAnim.runtimeAnimatorController = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(
            "Assets/Animations/Traveler.controller");
        Debug.Log("[FIX] Traveler sprite="+(tSR.sprite!=null?tSR.sprite.name:"NULL"));

        // Shield child
        var shieldGO = new GameObject("Shield");
        shieldGO.transform.SetParent(travGO.transform);
        shieldGO.transform.localPosition = Vector3.zero;
        var shSR = shieldGO.AddComponent<SpriteRenderer>();
        shSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/shield/shield_00.png");
        shSR.material = spriteMat;
        shSR.sortingOrder = 5;
        shieldGO.SetActive(false);

        // === STEP 7: Rain Particles ===
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
        // Set particle material to default sprite
        var psr = rainGO.GetComponent<ParticleSystemRenderer>();
        psr.material = spriteMat;
        psr.sortingOrder = 10;

        // === STEP 8: Lightning ===
        var lightGO = new GameObject("LightningOverlay");
        lightGO.transform.position = Vector3.zero;
        var lSR = lightGO.AddComponent<SpriteRenderer>();
        lSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/effects/lightning_full.png");
        lSR.material = spriteMat;
        lSR.sortingOrder = 100;
        lSR.color = new Color(1, 1, 1, 0.5f);
        lightGO.SetActive(false);

        // === STEP 9: Prompt Display ===
        var promptGO = new GameObject("PromptDisplay");
        promptGO.transform.position = new Vector3(0, 3.5f, 0);

        // === STEP 10: Scene1Director ===
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
        var shieldSpritesProp = so.FindProperty("shieldSprites");
        shieldSpritesProp.arraySize = 9;
        for (int i = 0; i < 9; i++)
        {
            shieldSpritesProp.GetArrayElementAtIndex(i).objectReferenceValue =
                AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/shield/shield_0"+i+".png");
        }
        so.ApplyModifiedProperties();

        EditorSceneManager.SaveScene(scene);
        Debug.Log("[SRP] ===== Comprehensive Fix Complete! =====");
        Debug.Log("[SRP] GameObjects: " + scene.GetRootGameObjects().Length);
        Debug.Log("[SRP] Try entering Play mode and check Game View!");
    }
}
