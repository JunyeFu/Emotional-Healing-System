using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using System.IO;

public class SetupWeatherScenes : EditorWindow
{
    [MenuItem("SRP/Setup All Weather Scenes")]
    public static void SetupAll()
    {
        string[] scenes = {"StormScene","HeatScene","SnowScene","FadeScene"};
        int[] bgIndices = {1,2,3,4};
        string[] bgColors = {"#2D2D3A","#CC4400","#B0B8C0","#999999"};
        
        for (int i = 0; i < 4; i++)
        {
            var path = "Assets/Scenes/" + scenes[i] + ".unity";
            var scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
            SetupScene(scenes[i], bgIndices[i], bgColors[i]);
            EditorSceneManager.SaveScene(scene);
        }
        AssetDatabase.Refresh();
        Debug.Log("[SRP] All 4 weather scenes setup complete!");
    }
    
    static void SetupScene(string name, int bgIdx, string bgHex)
    {
        // Camera
        var camGO = new GameObject("MainCamera");
        var cam = camGO.AddComponent<Camera>();
        cam.orthographic = true;
        cam.orthographicSize = 6f;
        cam.transform.position = new Vector3(0,0,-10);
        ColorUtility.TryParseHtmlString(bgHex, out var bgColor);
        cam.backgroundColor = bgColor;
        camGO.tag = "MainCamera";
        
        // Background
        var bgGO = new GameObject("Background");
        bgGO.transform.position = new Vector3(0,0,10);
        var bgSR = bgGO.AddComponent<SpriteRenderer>();
        var bgSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/backgrounds/bg_0"+bgIdx+".png");
        bgSR.sprite = bgSprite;
        ScaleSpriteToScreen(bgGO, cam);
        
        // Traveler
        var travGO = new GameObject("Traveler");
        travGO.transform.position = new Vector3(0,-2,0);
        var travSR = travGO.AddComponent<SpriteRenderer>();
        var travSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_idle.png");
        travSR.sprite = travSprite;
        travSR.sortingOrder = 1;
        var anim = travGO.AddComponent<Animator>();
        anim.runtimeAnimatorController = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>("Assets/Animations/Traveler.controller");
        
        // Weather particles parent
        var particleGO = new GameObject("WeatherParticles");
        particleGO.transform.position = new Vector3(0,3,5);
        
        // Prompt display
        var promptGO = new GameObject("PromptDisplay");
        promptGO.transform.position = new Vector3(0,3,0);
        
        // Weather-specific setup
        switch(name)
        {
            case "StormScene":
                var rain = particleGO.AddComponent<ParticleSystem>();
                ConfigureRain(rain);
                var lightningGO = new GameObject("LightningOverlay");
                lightningGO.transform.position = new Vector3(0,0,8);
                var lr = lightningGO.AddComponent<SpriteRenderer>();
                lr.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/effects/lightning_full.png");
                lr.sortingOrder = 10;
                lightningGO.SetActive(false);
                break;
            case "HeatScene":
                var fire = particleGO.AddComponent<ParticleSystem>();
                ConfigureFire(fire);
                break;
            case "SnowScene":
                var snow = particleGO.AddComponent<ParticleSystem>();
                ConfigureSnow(snow);
                break;
            case "FadeScene":
                var sparkles = particleGO.AddComponent<ParticleSystem>();
                ConfigureSparkles(sparkles);
                break;
        }
    }
    
    static void ScaleSpriteToScreen(GameObject go, Camera cam)
    {
        var sr = go.GetComponent<SpriteRenderer>();
        if (sr == null || sr.sprite == null || cam == null) return;
        float spriteW = sr.sprite.bounds.size.x;
        float spriteH = sr.sprite.bounds.size.y;
        float screenH = cam.orthographicSize * 2f;
        float screenW = screenH * cam.aspect;
        go.transform.localScale = new Vector3(screenW/spriteW, screenH/spriteH, 1);
    }
    
    static void ConfigureRain(ParticleSystem ps)
    {
        var m = ps.main; m.startLifetime = 2f; m.startSpeed = new ParticleSystem.MinMaxCurve(5,15);
        m.startSize = 0.1f; m.startColor = new Color(0.5f,0.6f,1f,0.6f);
        m.maxParticles = 200;
        var e = ps.emission; e.rateOverTime = 100f;
        var s = ps.shape; s.shapeType = ParticleSystemShapeType.Box;
        s.scale = new Vector3(20,1,1); s.position = new Vector3(0,5,0);
        ps.Stop();
    }
    
    static void ConfigureFire(ParticleSystem ps)
    {
        var m = ps.main; m.startLifetime = 1.5f; m.startSpeed = new ParticleSystem.MinMaxCurve(1,4);
        m.startSize = 0.15f; m.startColor = new Color(1f,0.4f,0.1f,0.5f);
        m.maxParticles = 100; m.gravityModifier = -0.2f;
        var e = ps.emission; e.rateOverTime = 40f;
        var s = ps.shape; s.shapeType = ParticleSystemShapeType.Box;
        s.scale = new Vector3(15,0.5f,1); s.position = new Vector3(0,-2,0);
        ps.Stop();
    }
    
    static void ConfigureSnow(ParticleSystem ps)
    {
        var m = ps.main; m.startLifetime = 5f; m.startSpeed = new ParticleSystem.MinMaxCurve(0.5f,2f);
        m.startSize = 0.3f; m.startColor = new Color(1f,1f,1f,0.7f);
        m.maxParticles = 150; m.gravityModifier = 0.1f;
        var e = ps.emission; e.rateOverTime = 50f;
        var s = ps.shape; s.shapeType = ParticleSystemShapeType.Box;
        s.scale = new Vector3(20,1,1); s.position = new Vector3(0,8,0);
        ps.Stop();
    }
    
    static void ConfigureSparkles(ParticleSystem ps)
    {
        var m = ps.main; m.startLifetime = 3f; m.startSpeed = new ParticleSystem.MinMaxCurve(0.2f,1f);
        m.startSize = 0.08f; m.startColor = new Color(0.5f,0.8f,1f,0.6f);
        m.maxParticles = 80; m.gravityModifier = -0.05f;
        var e = ps.emission; e.rateOverTime = 20f;
        var s = ps.shape; s.shapeType = ParticleSystemShapeType.Sphere;
        s.radius = 5f;
        ps.Stop();
    }
}
