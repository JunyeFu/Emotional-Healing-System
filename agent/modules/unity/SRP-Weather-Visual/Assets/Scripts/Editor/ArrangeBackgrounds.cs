using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class ArrangeBackgrounds : EditorWindow
{
    [MenuItem("SRP/Arrange Backgrounds Right-to-Left")]
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        var bg = GameObject.Find("BackgroundContainer");
        if (bg == null) { Debug.LogError("[BG] BackgroundContainer not found!"); return; }

        float ppu = 32f;
        float bgPixelWidth = 1672f;
        float fullWidth = bgPixelWidth / ppu;
        float scale = 0.4082935f;
        float bgWorldWidth = fullWidth * scale;

        // bg_01 rightmost → bg_02 → ... → bg_05 leftmost
        // 1的左接2的右: bg_01.left = bg_02.right
        string[] names = { "bg_01", "bg_02", "bg_03", "bg_04", "bg_05" };
        for (int i = 0; i < names.Length; i++)
        {
            var child = bg.transform.Find(names[i]);
            if (child == null) { Debug.LogError($"[BG] {names[i]} not found!"); return; }

            float centerX = -i * bgWorldWidth;
            child.transform.position = new Vector3(centerX, 0, 0);
            child.transform.localScale = new Vector3(scale, scale, 1f);

            var sr = child.GetComponent<SpriteRenderer>();
            float leftEdge = centerX - bgWorldWidth / 2f;
            float rightEdge = centerX + bgWorldWidth / 2f;
            Debug.Log($"[BG] {names[i]}: center={centerX:F2} left={leftEdge:F2} right={rightEdge:F2} sprite={sr?.sprite?.name}");
        }

        // Verify gaps
        for (int i = 0; i < names.Length - 1; i++)
        {
            var a = bg.transform.Find(names[i]);
            var b = bg.transform.Find(names[i + 1]);
            float aLeft = a.transform.position.x - bgWorldWidth / 2f;
            float bRight = b.transform.position.x + bgWorldWidth / 2f;
            float gap = aLeft - bRight;
            Debug.Log($"[BG] {names[i]}.left({aLeft:F3}) = {names[i+1]}.right({bRight:F3}) gap={gap:F4} {(Mathf.Abs(gap)<0.01f ? "OK" : "GAP!")}");
        }

        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[BG] Done: bg_01(rightmost) <- bg_02 <- bg_03 <- bg_04 <- bg_05(leftmost)");
    }
}
