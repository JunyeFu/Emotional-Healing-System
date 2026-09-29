using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class RenderCameraToFile : EditorWindow
{
    [MenuItem("SRP/Render Camera To File")]
    public static void Render()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        var cam = Camera.main;
        if (cam == null)
        {
            Debug.LogError("[RENDER] No MainCamera found!");
            return;
        }

        int w = 640, h = 360;
        var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32);
        rt.Create();

        var prevTarget = cam.targetTexture;
        var prevActive = RenderTexture.active;

        cam.targetTexture = rt;
        cam.Render();

        RenderTexture.active = rt;
        var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        tex.Apply();

        // Save
        var bytes = tex.EncodeToPNG();
        var path = Application.dataPath + "/Screenshots/camera_render.png";
        System.IO.File.WriteAllBytes(path, bytes);
        Debug.Log($"[RENDER] Saved to {path} ({w}x{h})");

        // Analyze
        var pixels = tex.GetPixels();
        int black = 0, gray = 0, darkBlue = 0, colorful = 0, white = 0;
        foreach (var p in pixels)
        {
            float avg = (p.r + p.g + p.b) / 3f;
            float maxDiff = Mathf.Max(Mathf.Abs(p.r - p.g), Mathf.Abs(p.g - p.b), Mathf.Abs(p.r - p.b));

            if (avg < 0.02f) black++;
            else if (avg > 0.95f) white++;
            else if (maxDiff < 0.05f && avg > 0.3f && avg < 0.8f) gray++;
            else if (p.b > p.r && p.b > p.g && avg < 0.3f) darkBlue++;
            else if (maxDiff > 0.1f) colorful++;
        }

        int n = pixels.Length;
        Debug.Log($"[RENDER] Black={100f*black/n:F1}% White={100f*white/n:F1}% Gray(checker)={100f*gray/n:F1}% DarkBlue={100f*darkBlue/n:F1}% Colorful={100f*colorful/n:F1}%");

        // Sample corners and center
        Color c = tex.GetPixel(w/2, h/2);
        Color tl = tex.GetPixel(0, 0);
        Color tr = tex.GetPixel(w-1, 0);
        Color bl = tex.GetPixel(0, h-1);
        Color br = tex.GetPixel(w-1, h-1);
        Debug.Log($"[RENDER] Center=({c.r:F3},{c.g:F3},{c.b:F3}) TL=({tl.r:F3},{tl.g:F3},{tl.b:F3}) TR=({tr.r:F3},{tr.g:F3},{tr.b:F3})");
        Debug.Log($"[RENDER] BL=({bl.r:F3},{bl.g:F3},{bl.b:F3}) BR=({br.r:F3},{br.g:F3},{br.b:F3})");

        cam.targetTexture = prevTarget;
        RenderTexture.active = prevActive;
        Object.DestroyImmediate(tex);
        rt.Release();
        Object.DestroyImmediate(rt);
    }
}
