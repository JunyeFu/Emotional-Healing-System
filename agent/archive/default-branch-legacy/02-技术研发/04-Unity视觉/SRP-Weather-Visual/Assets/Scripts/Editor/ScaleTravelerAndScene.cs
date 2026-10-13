using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering.Universal;

public class ScaleTravelerAndScene : EditorWindow
{
    [MenuItem("SRP/Scale Traveler + 1080p Setup")]
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        // ======= 1. SCALE TRAVELER =======
        var traveler = GameObject.Find("Traveler");
        if (traveler == null)
        {
            Debug.LogError("[SCALE] Traveler not found!");
            return;
        }

        var travSr = traveler.GetComponent<SpriteRenderer>();
        float travWorldH = travSr.sprite.rect.height / travSr.sprite.pixelsPerUnit; // 39.19
        float targetH = 1.875f; // target height in world units (2.5 * 0.75)
        float scale = targetH / travWorldH;

        traveler.transform.localScale = new Vector3(scale, scale, 1f);
        Debug.Log($"[SCALE] Traveler scaled to {scale:F4} (world height: {travWorldH:F1} -> {targetH:F1})");

        // Position traveler at reasonable starting point (near left, ground level)
        // Camera center is (0,0), viewport is 21.33x12 units
        // Ground is roughly at y=-4 (bottom of bg sprites at scale 0.408)
        traveler.transform.position = new Vector3(-6f, -3f, 0f);
        Debug.Log($"[SCALE] Traveler positioned at {traveler.transform.position}");

        // Scale Shield child too
        var shield = traveler.transform.Find("Shield");
        if (shield != null)
        {
            shield.transform.localScale = Vector3.one; // relative to parent
            var shieldSr = shield.GetComponent<SpriteRenderer>();
            if (shieldSr != null && shieldSr.sprite != null)
            {
                float shieldH = shieldSr.sprite.rect.height / shieldSr.sprite.pixelsPerUnit;
                float shieldScale = targetH / shieldH;
                shield.transform.localScale = new Vector3(shieldScale, shieldScale, 1f);
                Debug.Log($"[SCALE] Shield scaled to {shieldScale:F4} (world height: {shieldH:F1})");
            }
        }

        // ======= 2. CAMERA SETUP =======
        var cam = Camera.main;
        cam.orthographic = true;
        cam.orthographicSize = 6f;       // 12 units vertical
        cam.nearClipPlane = 0.01f;
        cam.farClipPlane = 1000f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.08f, 0.08f, 0.15f, 1f);
        cam.depth = 0;
        cam.enabled = true;
        cam.allowHDR = false;
        cam.allowMSAA = false;

        var urpData = cam.GetComponent<UniversalAdditionalCameraData>();
        if (urpData == null)
            urpData = cam.gameObject.AddComponent<UniversalAdditionalCameraData>();
        urpData.renderPostProcessing = false;
        urpData.antialiasing = AntialiasingMode.None;
        urpData.renderShadows = false;
        urpData.stopNaN = false;
        urpData.dithering = false;
        urpData.allowXRRendering = false;

        // ======= 3. SAVE FIRST (before GameView which may fail) =======
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[SCALE] Scene saved. Traveler scaled to fit scene.");

        // ======= 4. GAME VIEW 1920x1080 =======
        try { SetGameView1080p(); }
        catch (System.Exception e) { Debug.LogWarning($"[SCALE] GameView 1080p failed (non-critical): {e.Message}"); }
    }

    public static void SetGameView1080p()
    {
        var gameViewType = System.Type.GetType("UnityEditor.GameView,UnityEditor");
        if (gameViewType == null) { Debug.LogWarning("[SCALE] GameView type not found"); return; }

        // Use ScriptableSingleton<GameViewSizes> to get the singleton
        var singletonType = typeof(ScriptableSingleton<>).MakeGenericType(
            System.Type.GetType("UnityEditor.GameViewSizes,UnityEditor"));
        var instanceProp = singletonType.GetProperty("instance",
            System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
        if (instanceProp == null) { Debug.LogWarning("[SCALE] ScriptableSingleton.instance not found"); return; }

        var sizes = instanceProp.GetValue(null);
        if (sizes == null) { Debug.LogWarning("[SCALE] GameViewSizes null"); return; }

        var currentGroupProp = sizes.GetType().GetProperty("currentGroup",
            System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
        if (currentGroupProp == null) { Debug.LogWarning("[SCALE] currentGroup prop not found"); return; }

        var currentGroup = currentGroupProp.GetValue(sizes);
        if (currentGroup == null) { Debug.LogWarning("[SCALE] currentGroup null"); return; }

        var getDisplayTexts = currentGroup.GetType().GetMethod("GetDisplayTexts",
            System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
        var texts = getDisplayTexts.Invoke(currentGroup, null) as string[];

        int idx1080 = -1;
        if (texts != null)
        {
            for (int i = 0; i < texts.Length; i++)
                if (texts[i] != null && texts[i].Contains("1920")) { idx1080 = i; break; }
        }

        if (idx1080 < 0)
        {
            var addCustomSize = currentGroup.GetType().GetMethod("AddCustomSize",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            if (addCustomSize != null)
            {
                var enumType = addCustomSize.GetParameters()[0].ParameterType;
                addCustomSize.Invoke(currentGroup, new object[] {
                    System.Enum.ToObject(enumType, 1), 1920, 1080, "Full HD (1920x1080)"
                });
                Debug.Log("[SCALE] Added Game View size: 1920x1080");
                texts = getDisplayTexts.Invoke(currentGroup, null) as string[];
                if (texts != null)
                    for (int i = 0; i < texts.Length; i++)
                        if (texts[i] != null && texts[i].Contains("1920")) { idx1080 = i; break; }
            }
        }

        if (idx1080 >= 0)
        {
            var gameView = EditorWindow.GetWindow(gameViewType);
            var sizeIndexProp = gameViewType.GetProperty("selectedSizeIndex",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            if (sizeIndexProp != null)
            {
                sizeIndexProp.SetValue(gameView, idx1080);
                Debug.Log($"[SCALE] Game View set to index {idx1080} (1920x1080)");
            }
        }
    }
}
