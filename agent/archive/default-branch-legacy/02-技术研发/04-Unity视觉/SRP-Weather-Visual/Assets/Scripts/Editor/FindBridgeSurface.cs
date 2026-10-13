using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class FindBridgeSurface : EditorWindow
{
    [MenuItem("SRP/Find Bridge & Place Traveler")]
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        var traveler = GameObject.Find("Traveler");
        if (traveler == null) { Debug.LogError("[BRIDGE] Traveler not found!"); return; }

        var bgSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/backgrounds/bg_01.png");
        var tex = bgSprite.texture;
        int texW = tex.width;
        int texH = tex.height;

        // Enable read/write
        string texPath = AssetDatabase.GetAssetPath(tex);
        var importer = AssetImporter.GetAtPath(texPath) as TextureImporter;
        bool wasReadable = importer.isReadable;
        importer.isReadable = true;
        importer.SaveAndReimport();

        // Sample 20 columns across the width
        int numSamples = 20;
        int[] bridgeY = new int[numSamples];
        int validSamples = 0;

        for (int s = 0; s < numSamples; s++)
        {
            int sx = (int)(texW * 0.1f + (texW * 0.8f * s / numSamples));
            var col = tex.GetPixels(sx, 0, 1, texH);

            // Scan bottom-up, find first significant brightness transition
            float runningAvg = 0;
            for (int i = 0; i < 10; i++) runningAvg += col[i].grayscale;
            runningAvg /= 10f;

            int foundY = -1;
            for (int y = 15; y < texH - 5; y++)
            {
                float currentLum = col[y].grayscale;
                // Calculate local average of next 5 pixels
                float nextAvg = 0;
                for (int j = 1; j <= 5 && y + j < texH; j++)
                    nextAvg += col[y + j].grayscale;
                nextAvg /= 5f;

                float prevAvg = 0;
                for (int j = 1; j <= 5 && y - j >= 0; j++)
                    prevAvg += col[y - j].grayscale;
                prevAvg /= 5f;

                // Ground/surface is darker, above is lighter (sky/clouds)
                // Look for the LAST transition from dark to bright in the lower half
                if (y > texH * 0.1f && y < texH * 0.5f)
                {
                    if (nextAvg - prevAvg > 0.15f && currentLum > 0.3f)
                    {
                        foundY = y - 1;
                    }
                }
            }

            if (foundY > 0)
            {
                bridgeY[validSamples] = foundY;
                validSamples++;
            }
        }

        // Calculate median bridge position
        System.Array.Sort(bridgeY, 0, validSamples);
        int medianY = bridgeY[validSamples / 2];
        int minY = bridgeY[0];
        int maxY = bridgeY[validSamples - 1];

        Debug.Log($"[BRIDGE] Sampled {numSamples} columns, {validSamples} valid");
        Debug.Log($"[BRIDGE] Bridge Y range: {minY} ~ {maxY} (median: {medianY}) / {texH}");
        Debug.Log($"[BRIDGE] Bridge fraction from bottom: {medianY/(float)texH*100:F1}%");

        // Restore readable setting
        if (!wasReadable)
        {
            importer.isReadable = false;
            importer.SaveAndReimport();
        }

        // Calculate world position
        var bgGo = GameObject.Find("bg_01");
        float bgScale = bgGo.transform.localScale.y;
        float bgWorldH = (texH / 32f) * bgScale;
        float bgBottom = -bgWorldH / 2f;

        float bridgeWorldY = bgBottom + (medianY / (float)texH) * bgWorldH;

        // Traveler feet calculation
        var travSr = traveler.GetComponent<SpriteRenderer>();
        float travWorldH = travSr.sprite.rect.height / travSr.sprite.pixelsPerUnit;
        float travScaledH = travWorldH * traveler.transform.localScale.y;

        // Place feet ON bridge
        float targetCenterY = bridgeWorldY + travScaledH / 2f;
        Vector3 oldPos = traveler.transform.position;
        traveler.transform.position = new Vector3(oldPos.x, targetCenterY, oldPos.z);

        float oldFeetY = oldPos.y - travScaledH / 2f;
        float newFeetY = targetCenterY - travScaledH / 2f;

        Debug.Log($"[BRIDGE] bgWorldH: {bgWorldH:F3}, bgBottom: {bgBottom:F3}");
        Debug.Log($"[BRIDGE] Bridge world Y: {bridgeWorldY:F3}");
        Debug.Log($"[BRIDGE] Traveler scaled H: {travScaledH:F3}");
        Debug.Log($"[BRIDGE] Feet moved from Y={oldFeetY:F3} to Y={newFeetY:F3}");
        Debug.Log($"[BRIDGE] Traveler center: ({oldPos.x:F1}, {targetCenterY:F3})");

        // Print surrounding colors at bridge level from multiple columns
        Debug.Log($"[BRIDGE] === Bridge surface pixel colors ===");
        var readableTex = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
        for (int sx = texW/4; sx < texW*3/4; sx += texW/6)
        {
            Color c0 = readableTex.GetPixel(sx, medianY);
            Color c1 = readableTex.GetPixel(sx, medianY + 5);
            Debug.Log($"[BRIDGE]   x={sx}: surface=RGB({c0.r:F2},{c0.g:F2},{c0.b:F2}) above=RGB({c1.r:F2},{c1.g:F2},{c1.b:F2})");
        }

        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[BRIDGE] Scene saved. Traveler placed with multi-column detection.");
    }
}
