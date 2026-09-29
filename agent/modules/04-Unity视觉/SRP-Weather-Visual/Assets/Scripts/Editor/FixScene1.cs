using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class FixScene1 : EditorWindow
{
    [MenuItem("SRP/Fix Scene 1 - Verify & Repair")]
    public static void Fix()
    {
        // Re-import all sprites first
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

        // Check background sprites
        var bgContainer = GameObject.Find("BackgroundContainer");
        if (bgContainer != null)
        {
            for (int i = 0; i < 5; i++)
            {
                var child = bgContainer.transform.Find("bg_0" + (i+1));
                if (child == null) { Debug.LogError("[FIX] bg_0"+(i+1)+" not found!"); continue; }
                var sr = child.GetComponent<SpriteRenderer>();
                var path = "Assets/Sprites/backgrounds/bg_0" + (i+1) + ".png";
                var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(path);
                if (sprite == null)
                {
                    Debug.LogError("[FIX] bg_0"+(i+1)+" sprite is NULL at path: " + path);
                    // Try to find by GUID
                    var g2 = AssetDatabase.FindAssets("bg_0"+(i+1));
                    foreach (var g in g2)
                    {
                        var p = AssetDatabase.GUIDToAssetPath(g);
                        if (p.EndsWith(".png")) { sprite = AssetDatabase.LoadAssetAtPath<Sprite>(p); break; }
                    }
                }
                sr.sprite = sprite;
                Debug.Log("[FIX] bg_0"+(i+1)+" sprite=" + (sprite!=null?sprite.name:"NULL") + " renderer.sprite=" + (sr.sprite!=null?sr.sprite.name:"NULL") + " enabled=" + sr.enabled);
            }
        }

        // Check Traveler
        var trav = GameObject.Find("Traveler");
        if (trav != null)
        {
            var tSR = trav.GetComponent<SpriteRenderer>();
            if (tSR.sprite == null || tSR.sprite.name != "traveler_idle")
            {
                tSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/traveler_idle.png");
                Debug.Log("[FIX] Traveler sprite reloaded: " + (tSR.sprite!=null?tSR.sprite.name:"NULL"));
            }
            else Debug.Log("[FIX] Traveler sprite OK: " + tSR.sprite.name);

            // Ensure animator controller
            var anim = trav.GetComponent<Animator>();
            if (anim.runtimeAnimatorController == null)
            {
                anim.runtimeAnimatorController = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>("Assets/Animations/Traveler.controller");
                Debug.Log("[FIX] Traveler controller reloaded");
            }
        }

        // Check Shield child
        var shield = GameObject.Find("Shield");
        if (shield != null)
        {
            var sSR = shield.GetComponent<SpriteRenderer>();
            if (sSR.sprite == null)
            {
                sSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/shield/shield_00.png");
                Debug.Log("[FIX] Shield sprite reloaded");
            }
        }

        // Check Lightning
        var lightGO = GameObject.Find("LightningOverlay");
        if (lightGO != null)
        {
            var lSR = lightGO.GetComponent<SpriteRenderer>();
            if (lSR.sprite == null)
            {
                lSR.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/effects/lightning_full.png");
                Debug.Log("[FIX] Lightning sprite reloaded");
            }
        }

        // Check Scene1Director references
        var dirGO = GameObject.Find("Scene1Director");
        if (dirGO != null)
        {
            var director = dirGO.GetComponent<Scene1Director>();
            if (director != null)
            {
                var so = new SerializedObject(director);
                var travProp = so.FindProperty("traveler");
                if (travProp.objectReferenceValue == null && trav != null) travProp.objectReferenceValue = trav;
                var shieldProp = so.FindProperty("shield");
                if (shieldProp.objectReferenceValue == null && shield != null) shieldProp.objectReferenceValue = shield;
                var camProp = so.FindProperty("mainCamera");
                if (camProp.objectReferenceValue == null) camProp.objectReferenceValue = Camera.main;
                so.ApplyModifiedProperties();
                Debug.Log("[FIX] Scene1Director references repaired");
            }
        }

        EditorSceneManager.SaveScene(scene);
        Debug.Log("[SRP] Scene 1 fix complete!");
    }
}
