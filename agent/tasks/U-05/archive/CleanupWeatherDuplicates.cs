using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class CleanupWeatherDuplicates : EditorWindow
{
    [MenuItem("SRP/Cleanup Weather Duplicates")]
    public static void Run()
    {
        var scene = EditorSceneManager.GetActiveScene();

        // Remove duplicate Shields under Traveler (keep the last one created by Setup)
        var traveler = GameObject.Find("Traveler");
        if (traveler != null)
        {
            var shields = traveler.GetComponentsInChildren<Transform>(true);
            int shieldCount = 0;
            GameObject lastShield = null;
            foreach (var t in shields)
            {
                if (t.name == "Shield" && t.parent == traveler.transform)
                {
                    shieldCount++;
                    int id = t.GetInstanceID();
                    int lastId = lastShield.GetInstanceID();
                    bool isNewer = (id < 0 && lastId >= 0) ||
                       (id < 0 && lastId < 0 && id < lastId) ||
                       (id >= 0 && lastId >= 0 && id > lastId);
                    if (lastShield == null || isNewer)
                        lastShield = t.gameObject;
                }
            }
            if (shieldCount > 1)
            {
                foreach (var t in shields)
                {
                    if (t.name == "Shield" && t.parent == traveler.transform && t.gameObject != lastShield)
                    {
                        Object.DestroyImmediate(t.gameObject);
                        Debug.Log($"[CLEANUP] Removed duplicate Shield {t.GetInstanceID()}");
                    }
                }
            }

            // Re-parent to the correct Shield reference
            if (lastShield != null)
            {
                lastShield.name = "Shield";
                var sr = lastShield.GetComponent<SpriteRenderer>();
                if (sr == null) sr = lastShield.AddComponent<SpriteRenderer>();
                sr.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/shield/shield_clean.png");
                sr.sortingOrder = 5;
                lastShield.SetActive(false);
            }
        }

        // Remove duplicate LightningOverlays under MainCamera
        var cam = Camera.main;
        if (cam != null)
        {
            var overlays = cam.GetComponentsInChildren<Transform>(true);
            int overlayCount = 0;
            GameObject lastOverlay = null;
            foreach (var t in overlays)
            {
                if (t.name == "LightningOverlay" && t.parent == cam.transform)
                {
                    overlayCount++;
                    int id = t.GetInstanceID();
                    int lastId = lastOverlay.GetInstanceID();
                    bool isNewer = (id < 0 && lastId >= 0) ||
                       (id < 0 && lastId < 0 && id < lastId) ||
                       (id >= 0 && lastId >= 0 && id > lastId);
                    if (lastOverlay == null || isNewer)
                        lastOverlay = t.gameObject;
                }
            }
            if (overlayCount > 1)
            {
                foreach (var t in overlays)
                {
                    if (t.name == "LightningOverlay" && t.parent == cam.transform && t.gameObject != lastOverlay)
                    {
                        Object.DestroyImmediate(t.gameObject);
                        Debug.Log($"[CLEANUP] Removed duplicate LightningOverlay {t.GetInstanceID()}");
                    }
                }
            }
            if (lastOverlay != null)
            {
                lastOverlay.name = "LightningOverlay";
                var sr = lastOverlay.GetComponent<SpriteRenderer>();
                if (sr == null) sr = lastOverlay.AddComponent<SpriteRenderer>();
                sr.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/effects/lightning_full.png");
                sr.sortingOrder = 100;
                lastOverlay.transform.localPosition = new Vector3(0, 0, 1);
                lastOverlay.transform.localScale = new Vector3(30f, 20f, 1f);
                lastOverlay.SetActive(false);
            }
        }

        // Remove old RainParticles (replaced by RainNear + RainFar)
        var oldRain = GameObject.Find("RainParticles");
        if (oldRain != null)
        {
            Object.DestroyImmediate(oldRain);
            Debug.Log("[CLEANUP] Removed old RainParticles (replaced by RainNear+RainFar).");
        }

        // Re-wire WeatherDirector references
        var wd = Object.FindObjectOfType<WeatherDirector>();
        if (wd != null)
        {
            var wdSerialized = new SerializedObject(wd);
            var travelerGO = GameObject.Find("Traveler");
            var shieldGO = travelerGO != null ? travelerGO.transform.Find("Shield")?.gameObject : null;
            var rainNearGO = GameObject.Find("RainNear");
            var rainFarGO = GameObject.Find("RainFar");
            var lightningGO = Camera.main != null ? Camera.main.transform.Find("LightningOverlay")?.gameObject : null;

            wdSerialized.FindProperty("traveler").objectReferenceValue = travelerGO;
            wdSerialized.FindProperty("shield").objectReferenceValue = shieldGO;
            wdSerialized.FindProperty("rainPSNear").objectReferenceValue = rainNearGO != null ? rainNearGO.GetComponent<ParticleSystem>() : null;
            wdSerialized.FindProperty("rainPSFar").objectReferenceValue = rainFarGO != null ? rainFarGO.GetComponent<ParticleSystem>() : null;
            wdSerialized.FindProperty("lightningOverlay").objectReferenceValue = lightningGO;
            wdSerialized.FindProperty("mainCamera").objectReferenceValue = Camera.main;
            wdSerialized.FindProperty("enableLightning").boolValue = false;
            wdSerialized.FindProperty("shieldClean").objectReferenceValue = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/traveler/shield/shield_clean.png");

            var framesProp = wdSerialized.FindProperty("shieldFrames");
            framesProp.arraySize = 9;
            for (int i = 0; i < 9; i++)
            {
                framesProp.GetArrayElementAtIndex(i).objectReferenceValue =
                    AssetDatabase.LoadAssetAtPath<Sprite>($"Assets/Sprites/traveler/shield/shield_{i:D2}.png");
            }

            wdSerialized.ApplyModifiedProperties();
            EditorUtility.SetDirty(wd);
            Debug.Log("[CLEANUP] WeatherDirector refs: RainNear+RainFar, lightning=off.");
        }

        // Disable Scene1Director
        var s1d = Object.FindObjectOfType<Scene1Director>();
        if (s1d != null)
        {
            s1d.enabled = false;
            Debug.Log("[CLEANUP] Scene1Director disabled.");
        }

        EditorSceneManager.SaveScene(scene);
        Debug.Log("[CLEANUP] Done — duplicates removed, references fixed, scene saved.");
    }
}
