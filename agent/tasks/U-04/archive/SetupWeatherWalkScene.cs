using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class SetupWeatherWalkScene : EditorWindow
{
    [MenuItem("SRP/Setup Weather Walk Scene")]
    public static void Run()
    {
        var scene = EditorSceneManager.GetActiveScene();

        // 1. Camera
        var cam = Camera.main;
        if (cam == null)
        {
            var camGO = new GameObject("MainCamera");
            camGO.tag = "MainCamera";
            camGO.transform.position = new Vector3(0, 0, -10);
            cam = camGO.AddComponent<Camera>();
            cam.orthographic = true;
            cam.orthographicSize = 6f;
            cam.backgroundColor = new Color(0.08f, 0.08f, 0.15f);
        }

        // 2. Traveler
        var traveler = GameObject.Find("Traveler");
        if (traveler == null)
        {
            traveler = new GameObject("Traveler");
            traveler.transform.position = new Vector3(-8.34f, -1.7f, 0);
            var tSR = traveler.AddComponent<SpriteRenderer>();
            tSR.sprite = LoadSprite("Assets/Sprites/traveler/traveler_idle.png");
            tSR.sortingOrder = 0;
            var anim = traveler.AddComponent<Animator>();
            anim.runtimeAnimatorController = LoadAsset<RuntimeAnimatorController>("Assets/Animations/Traveler.controller");
        }

        // Ensure walk components
        var w1 = traveler.GetComponent<WalkBG01_03>();
        if (w1 == null) traveler.AddComponent<WalkBG01_03>();
        var w4 = traveler.GetComponent<WalkBG04>();
        if (w4 == null) { w4 = traveler.AddComponent<WalkBG04>(); w4.enabled = false; }
        var w5 = traveler.GetComponent<WalkBG05>();
        if (w5 == null) { w5 = traveler.AddComponent<WalkBG05>(); w5.enabled = false; }

        // Ensure Scene1Director is disabled (conflicts with walk scripts)
        var s1d = Object.FindObjectOfType<Scene1Director>();
        if (s1d != null) s1d.enabled = false;

        // 3. Shield (child of Traveler) — destroy any existing, create fresh
        foreach (var t in traveler.GetComponentsInChildren<Transform>(true))
            if (t.name == "Shield" && t.parent == traveler.transform)
                Object.DestroyImmediate(t.gameObject);
        var shield = new GameObject("Shield");
        shield.transform.SetParent(traveler.transform);
        shield.transform.localPosition = Vector3.zero;
        var shSR = shield.AddComponent<SpriteRenderer>();
        shSR.sprite = LoadSprite("Assets/Sprites/traveler/shield/shield_clean.png");
        shSR.sortingOrder = 5;
        shield.SetActive(false);

        // 4. RainNear — foreground layer (larger, faster, more visible)
        var rainNearGO = GameObject.Find("RainNear");
        if (rainNearGO != null) Object.DestroyImmediate(rainNearGO);
        rainNearGO = CreateRainLayer("RainNear", cam, 0.15f, new Vector2(12f, 22f), 0.8f, 300, 25f, 0.55f, 15);
        rainNearGO.transform.position = cam.transform.position + new Vector3(0, 6f, 0);

        // 5. RainFar — background layer (smaller, slower, more transparent)
        var rainFarGO = GameObject.Find("RainFar");
        if (rainFarGO != null) Object.DestroyImmediate(rainFarGO);
        rainFarGO = CreateRainLayer("RainFar", cam, 0.06f, new Vector2(6f, 12f), 0.6f, 200, 20f, 0.4f, -5);
        rainFarGO.transform.position = cam.transform.position + new Vector3(0, 7f, 0);

        // Clean up old single RainParticles
        var oldRain = GameObject.Find("RainParticles");
        if (oldRain != null) Object.DestroyImmediate(oldRain);

        // 6. LightningOverlay (child of Camera) — destroy any existing, create fresh
        foreach (var t in cam.GetComponentsInChildren<Transform>(true))
            if (t.name == "LightningOverlay" && t.parent == cam.transform)
                Object.DestroyImmediate(t.gameObject);
        var lightGO = new GameObject("LightningOverlay");
        lightGO.transform.SetParent(cam.transform);
        lightGO.transform.localPosition = new Vector3(0, 0, 1);
        lightGO.transform.localScale = new Vector3(30f, 20f, 1f);
        var lSR = lightGO.AddComponent<SpriteRenderer>();
        lSR.sprite = LoadSprite("Assets/Sprites/effects/lightning_full.png");
        lSR.sortingOrder = 100;
        var c = lSR.color;
        c.a = 0.9f;
        lSR.color = c;
        lightGO.SetActive(false);

        // 7. WeatherDirector
        var wdGO = GameObject.Find("WeatherDirector");
        if (wdGO == null) wdGO = new GameObject("WeatherDirector");
        var wd = wdGO.GetComponent<WeatherDirector>();
        if (wd == null) wd = wdGO.AddComponent<WeatherDirector>();

        var wdSerialized = new SerializedObject(wd);
        wdSerialized.FindProperty("traveler").objectReferenceValue = traveler;
        wdSerialized.FindProperty("shield").objectReferenceValue = shield;
        wdSerialized.FindProperty("rainPSNear").objectReferenceValue = rainNearGO.GetComponent<ParticleSystem>();
        wdSerialized.FindProperty("rainPSFar").objectReferenceValue = rainFarGO.GetComponent<ParticleSystem>();
        wdSerialized.FindProperty("lightningOverlay").objectReferenceValue = lightGO;
        wdSerialized.FindProperty("mainCamera").objectReferenceValue = cam;
        wdSerialized.FindProperty("enableLightning").boolValue = false;
        wdSerialized.FindProperty("shieldClean").objectReferenceValue = LoadSprite("Assets/Sprites/traveler/shield/shield_clean.png");

        // shieldFrames[9]: shield_00 .. shield_08
        var framesProp = wdSerialized.FindProperty("shieldFrames");
        framesProp.arraySize = 9;
        for (int i = 0; i < 9; i++)
        {
            var path = $"Assets/Sprites/traveler/shield/shield_{i:D2}.png";
            framesProp.GetArrayElementAtIndex(i).objectReferenceValue = LoadSprite(path);
        }

        wdSerialized.ApplyModifiedProperties();
        EditorUtility.SetDirty(wd);

        EditorSceneManager.SaveScene(scene);
        Debug.Log("[SETUP] Weather Walk: RainNear+RainFar dual-layer, Lightning (off), Shield, WeatherDirector.");
    }

    static GameObject CreateRainLayer(string name, Camera cam, float startSize, Vector2 speedRange,
        float gravityMod, int maxParticles, float windAngleDeg, float alpha, int sortingOrder)
    {
        var go = new GameObject(name);
        var ps = go.AddComponent<ParticleSystem>();

        var main = ps.main;
        main.startLifetime = 1.5f;
        main.startSpeed = new ParticleSystem.MinMaxCurve(speedRange.x, speedRange.y);
        main.startSize = startSize;
        main.gravityModifier = gravityMod;
        main.maxParticles = maxParticles;
        main.startColor = new Color(0.55f, 0.65f, 1f, alpha);
        main.simulationSpace = ParticleSystemSimulationSpace.World;

        var emission = ps.emission;
        emission.rateOverTime = 0f;

        var shape = ps.shape;
        shape.shapeType = ParticleSystemShapeType.Box;
        shape.scale = new Vector3(25f, 0.1f, 1f);
        shape.rotation = new Vector3(0, 0, windAngleDeg);

        var psr = ps.GetComponent<ParticleSystemRenderer>();
        var mat = new Material(Shader.Find("Unlit/Transparent"));
        var rainSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/effects/rain_drop.png");
        if (rainSprite != null)
        {
            mat.mainTexture = rainSprite.texture;
            mat.mainTexture.filterMode = FilterMode.Point;
        }
        psr.material = mat;
        psr.sortingOrder = sortingOrder;
        psr.renderMode = ParticleSystemRenderMode.Stretch;
        psr.lengthScale = 2f;
        psr.velocityScale = 0.15f;

        return go;
    }

    static Sprite LoadSprite(string path)
    {
        return AssetDatabase.LoadAssetAtPath<Sprite>(path);
    }

    static T LoadAsset<T>(string path) where T : Object
    {
        return AssetDatabase.LoadAssetAtPath<T>(path);
    }
}
