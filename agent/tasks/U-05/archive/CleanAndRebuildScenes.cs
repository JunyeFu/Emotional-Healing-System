using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class CleanAndRebuildScenes : EditorWindow
{
    [MenuItem("SRP/Clean and Rebuild All Scenes")]
    public static void Rebuild()
    {
        string[] scenes = {"StormScene","HeatScene","SnowScene","FadeScene"};
        int[] bgIndices = {1,2,3,4};
        string[] bgColors = {"2D2D3A","CC4400","B0B8C0","999999"};
        
        for (int si = 0; si < 4; si++)
        {
            var scene = EditorSceneManager.OpenScene("Assets/Scenes/"+scenes[si]+".unity", OpenSceneMode.Single);
            
            // Destroy all root objects
            var roots = scene.GetRootGameObjects();
            foreach (var r in roots) Object.DestroyImmediate(r);
            
            // Camera
            var camGO = new GameObject("MainCamera");
            camGO.tag = "MainCamera";
            camGO.transform.position = new Vector3(0,0,-10);
            var cam = camGO.AddComponent<Camera>();
            cam.orthographic = true;
            cam.orthographicSize = 6f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            Color c; ColorUtility.TryParseHtmlString("#"+bgColors[si], out c);
            cam.backgroundColor = c;
            
            // Background — full screen
            var bg = new GameObject("Background");
            bg.transform.position = new Vector3(0,0,0);
            var bgSR = bg.AddComponent<SpriteRenderer>();
            bgSR.sortingOrder = -10;
            var bgSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/backgrounds/bg_0"+bgIndices[si]+".png");
            bgSR.sprite = bgSprite;
            if (bgSprite != null)
            {
                float sh = cam.orthographicSize * 2f;
                float sw = sh * ((float)Screen.width / Mathf.Max(1, Screen.height));
                float sw2 = sh * (1920f/1080f); // editorial fallback
                float bw = bgSprite.bounds.size.x;
                float bh = bgSprite.bounds.size.y;
                if (bw > 0.001f && bh > 0.001f)
                    bg.transform.localScale = new Vector3(Mathf.Max(sw,sw2)/bw, sh/bh, 1);
            }
            
            // Traveler
            var trav = new GameObject("Traveler");
            trav.transform.position = new Vector3(0,-2,0);
            var tSR = trav.AddComponent<SpriteRenderer>();
            tSR.sortingOrder = 0;
            tSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_idle.png");
            var anim = trav.AddComponent<Animator>();
            anim.runtimeAnimatorController = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>("Assets/Animations/Traveler.controller");
            
            // Particles
            var particles = new GameObject("WeatherParticles");
            particles.transform.position = new Vector3(0,2,0);
            var ps = particles.AddComponent<ParticleSystem>();
            ConfigureParticles(ps, scenes[si]);
            
            // Prompt
            var prompt = new GameObject("PromptDisplay");
            prompt.transform.position = new Vector3(0,3.5f,0);
            
            // Lightning (Storm only)
            if (si == 0)
            {
                var l = new GameObject("LightningOverlay");
                l.transform.position = new Vector3(0,0,0);
                var lSR = l.AddComponent<SpriteRenderer>();
                lSR.sortingOrder = 100;
                lSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/effects/lightning_full.png");
                l.SetActive(false);
            }
            
            EditorSceneManager.SaveScene(scene);
        }
        
        AssetDatabase.Refresh();
        Debug.Log("[SRP] All 4 scenes cleaned and rebuilt successfully!");
    }
    
    static void ConfigureParticles(ParticleSystem ps, string scene)
    {
        var m = ps.main; var e = ps.emission; var s = ps.shape;
        switch(scene)
        {
            case "StormScene":
                m.startLifetime=2f; m.startSpeed=new ParticleSystem.MinMaxCurve(5,15);
                m.startSize=0.08f; m.startColor=new Color(0.5f,0.6f,1f,0.6f); m.maxParticles=200;
                e.rateOverTime=100f; s.shapeType=ParticleSystemShapeType.Box;
                s.scale=new Vector3(20,1,1); s.position=new Vector3(0,5,0); break;
            case "HeatScene":
                m.startLifetime=1.5f; m.startSpeed=new ParticleSystem.MinMaxCurve(1,4);
                m.startSize=0.12f; m.startColor=new Color(1f,0.4f,0.1f,0.5f); m.maxParticles=100;
                m.gravityModifier=-0.2f; e.rateOverTime=40f;
                s.shapeType=ParticleSystemShapeType.Box; s.scale=new Vector3(15,0.5f,1);
                s.position=new Vector3(0,-2,0); break;
            case "SnowScene":
                m.startLifetime=5f; m.startSpeed=new ParticleSystem.MinMaxCurve(0.5f,2f);
                m.startSize=0.25f; m.startColor=new Color(1f,1f,1f,0.7f); m.maxParticles=150;
                m.gravityModifier=0.1f; e.rateOverTime=50f;
                s.shapeType=ParticleSystemShapeType.Box; s.scale=new Vector3(20,1,1);
                s.position=new Vector3(0,8,0); break;
            case "FadeScene":
                m.startLifetime=3f; m.startSpeed=new ParticleSystem.MinMaxCurve(0.2f,1f);
                m.startSize=0.06f; m.startColor=new Color(0.5f,0.8f,1f,0.6f); m.maxParticles=80;
                m.gravityModifier=-0.05f; e.rateOverTime=20f;
                s.shapeType=ParticleSystemShapeType.Sphere; s.radius=5f; break;
        }
        ps.Stop();
    }
}
