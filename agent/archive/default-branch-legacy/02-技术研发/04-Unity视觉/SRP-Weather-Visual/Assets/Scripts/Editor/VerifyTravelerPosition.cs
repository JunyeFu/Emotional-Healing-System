using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class VerifyTravelerPosition : EditorWindow
{
    [MenuItem("SRP/Verify Traveler Position")]
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        var traveler = GameObject.Find("Traveler");
        var travSr = traveler.GetComponent<SpriteRenderer>();
        float scale = traveler.transform.localScale.y;
        float spriteH = travSr.sprite.rect.height / travSr.sprite.pixelsPerUnit;
        float actualH = spriteH * scale;
        float centerY = traveler.transform.position.y;
        float feetY = centerY - actualH / 2f;
        float headY = centerY + actualH / 2f;

        Debug.Log($"=== TRAVELER POSITION ===");
        Debug.Log($"Center: ({traveler.transform.position.x:F3}, {centerY:F3})");
        Debug.Log($"Scale: {scale:F4} | Sprite world H: {spriteH:F2} | Actual H: {actualH:F3}");
        Debug.Log($"Feet Y: {feetY:F3} | Head Y: {headY:F3}");
        Debug.Log($"Camera view: Y=[-6, +6]");

        // Analyze background pixel at traveler's feet position
        var bg = GameObject.Find("bg_01");
        if (bg != null)
        {
            var bgSr = bg.GetComponent<SpriteRenderer>();
            var bgSprite = bgSr.sprite;
            float bgScale = bg.transform.localScale.y;
            float bgWorldH = (bgSprite.rect.height / bgSprite.pixelsPerUnit) * bgScale;
            float bgBottom = bg.transform.position.y - bgWorldH / 2f;
            float bgTop = bg.transform.position.y + bgWorldH / 2f;

            Debug.Log($"bg_01: bottom={bgBottom:F3}, top={bgTop:F3}, center={bg.transform.position.y:F3}, scale={bgScale:F4}");
            Debug.Log($"bg_01 width: {bgSprite.rect.width/32*bgScale:F2} units");

            // At traveler's X position (-6), which bg segment?
            float relX = traveler.transform.position.x - bg.transform.position.x;
            Debug.Log($"Traveler X relative to bg_01 center: {relX:F2}");
        }
    }
}
