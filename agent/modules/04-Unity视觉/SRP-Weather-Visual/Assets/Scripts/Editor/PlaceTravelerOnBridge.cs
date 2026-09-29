using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class PlaceTravelerOnBridge : EditorWindow
{
    [MenuItem("SRP/Place Traveler on Bridge")]
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        var traveler = GameObject.Find("Traveler");
        if (traveler == null) { Debug.LogError("[BRIDGE] Traveler not found!"); return; }

        // Analyze bg_01 to find bridge surface
        var bgSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/backgrounds/bg_01.png");
        if (bgSprite == null) { Debug.LogError("[BRIDGE] bg_01 not found!"); return; }

        var tex = bgSprite.texture;
        int texW = tex.width;   // 1672
        int texH = tex.height;  // 941

        // Read pixels - need Read/Write enabled
        string texPath = AssetDatabase.GetAssetPath(tex);
        var importer = AssetImporter.GetAtPath(texPath) as TextureImporter;
        bool wasReadable = importer.isReadable;
        if (!wasReadable)
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
        }

        // Sample center column to find bridge surface
        int sampleX = texW / 2;
        var pixels = tex.GetPixels(sampleX, 0, 1, texH);

        // Find the bridge surface: transition from ground/bridge color to sky
        // Bridge colors tend to be brown/grey/dark, sky tends to be lighter/blue
        int bridgeTopPixelY = -1;
        float prevLuminance = 0;

        // Scan from bottom up
        for (int y = 1; y < texH; y++)
        {
            float lum = pixels[y].grayscale;
            float prevLum = pixels[y - 1].grayscale;

            // Look for significant brightness jump (ground→sky transition)
            if (lum - prevLum > 0.25f && y > texH * 0.1f)
            {
                bridgeTopPixelY = y - 1;
                Debug.Log($"[BRIDGE] Bridge surface detected at pixel y={bridgeTopPixelY}/{texH} " +
                          $"(luminance jump: {prevLum:F3} → {lum:F3})");
                break;
            }
            prevLuminance = lum;
        }

        // Also sample multiple columns to be robust
        if (bridgeTopPixelY < 0)
        {
            // Try sampling multiple columns
            for (int sx = texW / 4; sx < texW * 3 / 4; sx += 100)
            {
                var colPixels = tex.GetPixels(sx, 0, 1, texH);
                for (int y = 1; y < texH; y++)
                {
                    float lum = colPixels[y].grayscale;
                    float prevLum = colPixels[y - 1].grayscale;
                    if (lum - prevLum > 0.2f && y > texH * 0.08f)
                    {
                        bridgeTopPixelY = y - 1;
                        Debug.Log($"[BRIDGE] Bridge found at x={sx}, pixel y={bridgeTopPixelY}");
                        break;
                    }
                }
                if (bridgeTopPixelY > 0) break;
            }
        }

        if (!wasReadable)
        {
            importer.isReadable = false;
            importer.SaveAndReimport();
        }

        if (bridgeTopPixelY < 0)
        {
            // Fallback: estimate bridge at 30% from bottom of background
            bridgeTopPixelY = (int)(texH * 0.28f);
            Debug.LogWarning($"[BRIDGE] Could not detect bridge. Using estimate: y={bridgeTopPixelY}/{texH}");
        }

        // Calculate world position
        // Background: 941px tall, scaled 0.408, spans y=-6 to y=+6
        float bgScale = 12f / (texH / 32f);  // 12 / (941/32) ≈ 0.408
        float bgWorldH = (texH / 32f) * bgScale; // = 12
        float bgBottom = -bgWorldH / 2f; // = -6

        // Bridge surface in world: from bottom of bg
        float bridgeFraction = (float)bridgeTopPixelY / texH;
        float bridgeWorldY = bgBottom + bridgeFraction * bgWorldH;

        Debug.Log($"[BRIDGE] bgScale={bgScale:F4}, bgWorldH={bgWorldH:F3}, bgBottom={bgBottom:F3}");
        Debug.Log($"[BRIDGE] Bridge pixel: {bridgeTopPixelY}/{texH} = {bridgeFraction:F4}");
        Debug.Log($"[BRIDGE] Bridge world Y: {bridgeWorldY:F3}");

        // Traveler's feet position
        // Need to know traveler sprite's bottom in local space
        var travSr = traveler.GetComponent<SpriteRenderer>();
        var travSprite = travSr.sprite;
        float travPixelH = travSprite.rect.height;
        float travWorldH = travPixelH / travSprite.pixelsPerUnit; // full sprite world height
        float travScale = traveler.transform.localScale.y;
        float travScaledH = travWorldH * travScale;
        float travCenterY = traveler.transform.position.y;
        float travFeetY = travCenterY - travScaledH / 2f;

        Debug.Log($"[BRIDGE] Traveler: pixelH={travPixelH}, worldH={travWorldH:F2}, scale={travScale:F4}, scaledH={travScaledH:F3}");
        Debug.Log($"[BRIDGE] Traveler center Y={travCenterY:F3}, feet Y={travFeetY:F3}");

        // Place traveler feet ON the bridge surface
        float targetCenterY = bridgeWorldY + travScaledH / 2f;
        traveler.transform.position = new Vector3(traveler.transform.position.x, targetCenterY, 0);

        Debug.Log($"[BRIDGE] Bridge surface Y: {bridgeWorldY:F3}");
        Debug.Log($"[BRIDGE] Traveler new center Y: {targetCenterY:F3} (feet at {bridgeWorldY:F3})");
        Debug.Log($"[BRIDGE] Adjustment: {targetCenterY - travCenterY:F3} units");

        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[BRIDGE] Done. Traveler placed on bridge.");
    }
}
