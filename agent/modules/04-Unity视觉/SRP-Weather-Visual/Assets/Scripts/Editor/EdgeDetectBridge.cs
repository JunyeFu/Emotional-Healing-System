using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class EdgeDetectBridge : EditorWindow
{
    [MenuItem("SRP/Edge-Detect Bridge")]
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        var bgSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Sprites/backgrounds/bg_01.png");
        string texPath = AssetDatabase.GetAssetPath(bgSprite.texture);
        var importer = AssetImporter.GetAtPath(texPath) as TextureImporter;
        importer.isReadable = true;
        importer.SaveAndReimport();

        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
        int W = tex.width, H = tex.height;

        // Edge detection: compute vertical gradient magnitude for each row
        // Sum the absolute gradient across all columns to find strong horizontal edges
        float[] rowGradient = new float[H];
        float[] rowAvgColor = new float[H];

        // Sample every 4th column for performance
        for (int x = 0; x < W; x += 4)
        {
            for (int y = 1; y < H; y++)
            {
                Color c0 = tex.GetPixel(x, y - 1);
                Color c1 = tex.GetPixel(x, y);
                float grad = Mathf.Abs(c1.grayscale - c0.grayscale);
                // Also check RGB color gradient
                float colorGrad = Mathf.Abs(c1.r - c0.r) + Mathf.Abs(c1.g - c0.g) + Mathf.Abs(c1.b - c0.b);
                rowGradient[y] += colorGrad;
                rowAvgColor[y] += c1.grayscale;
            }
        }

        int colsSampled = W / 4;
        for (int y = 0; y < H; y++)
        {
            rowGradient[y] /= colsSampled;
            rowAvgColor[y] /= colsSampled;
        }

        // Find the strongest horizontal edges in the lower 50% of the image
        var edges = new System.Collections.Generic.List<(int y, float grad)>();
        for (int y = (int)(H * 0.15f); y < H * 0.5f; y++)
        {
            // Local maximum in gradient
            if (y > 1 && y < H - 1 &&
                rowGradient[y] > rowGradient[y-1] &&
                rowGradient[y] > rowGradient[y+1])
            {
                edges.Add((y, rowGradient[y]));
            }
        }

        edges.Sort((a, b) => b.grad.CompareTo(a.grad));

        Debug.Log($"[EDGE] === Top horizontal edges in lower 15-50% of bg ===");
        for (int i = 0; i < Mathf.Min(10, edges.Count); i++)
        {
            float pct = (float)edges[i].y / H * 100f;
            float worldY = -6f + (edges[i].y / (float)H) * 12f;
            Debug.Log($"[EDGE]   #{i+1}: y={edges[i].y} ({pct:F1}%) worldY={worldY:F3} gradient={edges[i].grad:F4}");
        }

        // Also print smoothed gradient profile around the top edges
        if (edges.Count > 0)
        {
            int bestY = edges[0].y;
            Debug.Log($"[EDGE] === Gradient profile around best edge y={bestY} ===");
            for (int y = bestY - 10; y <= bestY + 10; y++)
            {
                float pct = (float)y / H * 100f;
                Debug.Log($"[EDGE]   y={y} ({pct:F1}%): grad={rowGradient[y]:F4} color={rowAvgColor[y]:F3}");
            }
        }

        // Place traveler at the best edge
        if (edges.Count > 0)
        {
            int bridgeY = edges[0].y;
            float bridgeWorldY = -6f + (bridgeY / (float)H) * 12f;

            var traveler = GameObject.Find("Traveler");
            var travSr = traveler.GetComponent<SpriteRenderer>();
            float travWorldH = travSr.sprite.rect.height / travSr.sprite.pixelsPerUnit;
            float travScaledH = travWorldH * traveler.transform.localScale.y;
            float targetCenterY = bridgeWorldY + travScaledH / 2f;

            traveler.transform.position = new Vector3(traveler.transform.position.x, targetCenterY, 0);

            Debug.Log($"[EDGE] Bridge edge at y={bridgeY} ({bridgeY/(float)H*100:F1}%) worldY={bridgeWorldY:F3}");
            Debug.Log($"[EDGE] Traveler placed at center Y={targetCenterY:F3}, feet at Y={bridgeWorldY:F3}");

            // Also check 2nd and 3rd best edges for reference
            if (edges.Count >= 3)
            {
                Debug.Log($"[EDGE] Alternative edges:");
                for (int i = 1; i < Mathf.Min(4, edges.Count); i++)
                    Debug.Log($"[EDGE]   y={edges[i].y} ({edges[i].y/(float)H*100:F1}%) worldY={-6f + (edges[i].y/(float)H)*12f:F3}");
            }
        }

        importer.isReadable = false;
        importer.SaveAndReimport();

        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[EDGE] Done.");
    }
}
