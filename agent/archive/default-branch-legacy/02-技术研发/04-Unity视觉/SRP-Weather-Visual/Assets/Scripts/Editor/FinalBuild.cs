using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class FinalBuild : EditorWindow
{
    [MenuItem("SRP/Final Build All")]
    public static void Build()
    {
        // Step 1: Configure ALL texture imports synchronously
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
        
        // Step 2: Build scenes
        string[] scenes = {"StormScene","HeatScene","SnowScene","FadeScene"};
        int[] bgIdx = {1,2,3,4};
        string[] colors = {"2D2D3A","CC4400","B0B8C0","999999"};
        
        for (int si = 0; si < 4; si++)
        {
            var scene = EditorSceneManager.OpenScene("Assets/Scenes/"+scenes[si]+".unity", OpenSceneMode.Single);
            foreach (var r in scene.GetRootGameObjects()) DestroyImmediate(r);
            
            // Camera
            var camGO = new GameObject("MainCamera");
            camGO.tag = "MainCamera";
            camGO.transform.position = new Vector3(0,0,-10);
            var cam = camGO.AddComponent<Camera>();
            cam.orthographic = true; cam.orthographicSize = 6f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            Color bgCol; ColorUtility.TryParseHtmlString("#"+colors[si], out bgCol);
            cam.backgroundColor = bgCol;
            
            // Background
            var bgPath = "Assets/Sprites/backgrounds/bg_0"+bgIdx[si]+".png";
            var bgSprite = AssetDatabase.LoadAssetAtPath<Sprite>(bgPath);
            
            var bgGO = new GameObject("Background");
            bgGO.transform.position = Vector3.zero;
            var bgSR = bgGO.AddComponent<SpriteRenderer>();
            bgSR.sprite = bgSprite;
            bgSR.sortingOrder = -10;
            if (bgSprite != null)
            {
                float sh = cam.orthographicSize * 2f;
                float sw = sh * 1.7778f;
                bgGO.transform.localScale = new Vector3(sw/bgSprite.bounds.size.x, sh/bgSprite.bounds.size.y, 1);
            }
            
            // Traveler
            var travGO = new GameObject("Traveler");
            travGO.transform.position = new Vector3(0,-2,0);
            var tSR = travGO.AddComponent<SpriteRenderer>();
            tSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_idle.png");
            tSR.sortingOrder = 0;
            var anim = travGO.AddComponent<Animator>();
            anim.runtimeAnimatorController = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>("Assets/Animations/Traveler.controller");
            
            // Particles
            var pGO = new GameObject("WeatherParticles");
            pGO.transform.position = new Vector3(0,2,0);
            var ps = pGO.AddComponent<ParticleSystem>();
            var m = ps.main; var e = ps.emission; var s = ps.shape;
            m.startSize=0.1f; m.maxParticles=100;
            e.rateOverTime = (si==0)?100f:(si==1)?40f:(si==2)?50f:20f;
            s.shapeType = (si==3)?ParticleSystemShapeType.Sphere:ParticleSystemShapeType.Box;
            if(si==3) s.radius=5f; else {s.scale=new Vector3(15,1,1); s.position=new Vector3(0,5,0);}
            if(si==0){m.startColor=new Color(0.5f,0.6f,1f,0.6f); m.startSpeed=new ParticleSystem.MinMaxCurve(5,15);}
            else if(si==1){m.startColor=new Color(1f,0.4f,0.1f,0.5f); m.startSpeed=new ParticleSystem.MinMaxCurve(1,4); m.gravityModifier=-0.2f;}
            else if(si==2){m.startColor=new Color(1f,1f,1f,0.7f); m.startSpeed=new ParticleSystem.MinMaxCurve(0.5f,2f); m.gravityModifier=0.1f;}
            else {m.startColor=new Color(0.5f,0.8f,1f,0.6f); m.startSpeed=new ParticleSystem.MinMaxCurve(0.2f,1f);}
            ps.Stop();
            
            // Lightning (Storm only)
            if (si == 0)
            {
                var lGO = new GameObject("LightningOverlay");
                lGO.transform.position = Vector3.zero;
                var lSR = lGO.AddComponent<SpriteRenderer>();
                lSR.sortingOrder = 100;
                lSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/effects/lightning_full.png");
                lGO.SetActive(false);
            }
            
            // Prompt placeholder
            var prGO = new GameObject("PromptDisplay");
            prGO.transform.position = new Vector3(0,3.5f,0);
            
            EditorSceneManager.SaveScene(scene);
        }
        Debug.Log("[SRP] Final build complete - all 4 scenes ready!");
    }
}
