using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class AnalyzeBridge : EditorWindow
{
    [MenuItem("SRP/Analyze Bridge Surface")]
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        var bgSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/backgrounds/bg_01.png");
        string texPath = AssetDatabase.GetAssetPath(bgSprite.texture);
        var importer = AssetImporter.GetAtPath(texPath) as TextureImporter;
        importer.isReadable = true;
        importer.SaveAndReimport();

        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
        int texW = tex.width;
        int texH = tex.height;

        // Print color samples at every 5% of height across center column
        int cx = texW / 2;
        Debug.Log($"[BRIDGE] bg_01: {texW}x{texH}px, column {cx}");
        Debug.Log($"[BRIDGE] === Height profile (center column) ===");

        for (int pct = 0; pct <= 100; pct += 5)
        {
            int y = texH * pct / 100;
            if (y >= texH) y = texH - 1;
            Color c = tex.GetPixel(cx, y);
            Debug.Log($"[BRIDGE]   {pct}% (y={y}): RGB({c.r:F3},{c.g:F3},{c.b:F3}) gray={c.grayscale:F3}");
        }

        // Find the "ground/surface" band by looking for horizontal strips of similar color
        // Sample every row to detect color patterns
        var rowColors = new Color[21]; // 0%,5%,10%,...100%
        for (int pct = 0; pct <= 100; pct += 5)
        {
            int y = texH * pct / 100;
            if (y >= texH) y = texH - 1;
            rowColors[pct / 5] = tex.GetPixel(cx, y);
        }

        // Find the biggest color difference between adjacent 5% bands
        float maxDiff = 0;
        int maxDiffPct = 0;
        for (int i = 1; i < rowColors.Length; i++)
        {
            float diff = Mathf.Abs(rowColors[i].grayscale - rowColors[i-1].grayscale);
            // Also check actual color distance
            float colorDist = Vector3.Distance(
                new Vector3(rowColors[i].r, rowColors[i].g, rowColors[i].b),
                new Vector3(rowColors[i-1].r, rowColors[i-1].g, rowColors[i-1].b));
            if (diff > maxDiff)
            {
                maxDiff = diff;
                maxDiffPct = (i - 1) * 5;
            }
            Debug.Log($"[BRIDGE]   {((i-1)*5)}%→{i*5}%: grayDiff={diff:F3} colorDist={colorDist:F3}");
        }
        Debug.Log($"[BRIDGE] Max transition at {maxDiffPct}%~{maxDiffPct+5}% (diff={maxDiff:F3})");

        // Bridge surface is likely at the last dark-to-bright transition in lower half
        // Look for where ground colors end in the 15-40% range
        int bestBridgePct = 0;
        float bestTransition = 0;
        for (int pct = 15; pct <= 45; pct += 1)
        {
            int y = texH * pct / 100;
            if (y >= texH - 1) continue;
            Color c0 = tex.GetPixel(cx, y);
            Color c1 = tex.GetPixel(cx, y + 1);

            // Bridge surface: above is much brighter/bluer than below
            float lumJump = c1.grayscale - c0.grayscale;
            if (lumJump > bestTransition)
            {
                bestTransition = lumJump;
                bestBridgePct = pct;
            }
        }
        Debug.Log($"[BRIDGE] Best bridge surface at {bestBridgePct}% (lumJump={bestTransition:F3})");

        // Now the most important analysis: sample multiple X positions at the candidate height
        int bridgeYPixel = texH * bestBridgePct / 100;
        Debug.Log($"[BRIDGE] === Colors at bridge level y={bridgeYPixel} across width ===");
        for (int sx = 0; sx < texW; sx += texW/8)
        {
            Color cBelow = tex.GetPixel(sx, bridgeYPixel - 2);
            Color cAt = tex.GetPixel(sx, bridgeYPixel);
            Color cAbove = tex.GetPixel(sx, bridgeYPixel + 2);
            Debug.Log($"[BRIDGE]   x={sx}: below=RGB({cBelow.r:F2},{cBelow.g:F2},{cBelow.b:F2}) " +
                      $"at=RGB({cAt.r:F2},{cAt.g:F2},{cAt.b:F2}) " +
                      $"above=RGB({cAbove.r:F2},{cAbove.g:F2},{cAbove.b:F2})");
        }

        // Calculate world position and place traveler
        var bgGo = GameObject.Find("bg_01");
        float bgScale = bgGo.transform.localScale.y;
        float bgWorldH = (texH / 32f) * bgScale;
        float bgBottom = -bgWorldH / 2f;
        float bridgeWorldY = bgBottom + (bridgeYPixel / (float)texH) * bgWorldH;

        var traveler = GameObject.Find("Traveler");
        var travSr = traveler.GetComponent<SpriteRenderer>();
        float travWorldH = travSr.sprite.rect.height / travSr.sprite.pixelsPerUnit;
        float travScaledH = travWorldH * traveler.transform.localScale.y;
        float targetCenterY = bridgeWorldY + travScaledH / 2f;

        float oldY = traveler.transform.position.y;
        traveler.transform.position = new Vector3(traveler.transform.position.x, targetCenterY, 0);

        Debug.Log($"[BRIDGE] Bridge world Y: {bridgeWorldY:F3} ({bestBridgePct}% from bg bottom)");
        Debug.Log($"[BRIDGE] Traveler Y: {oldY:F3} → {targetCenterY:F3} (feet at {bridgeWorldY:F3})");

        importer.isReadable = false;
        importer.SaveAndReimport();

        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[BRIDGE] Done.");
    }
}
