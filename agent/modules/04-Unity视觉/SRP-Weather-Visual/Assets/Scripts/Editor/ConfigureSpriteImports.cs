using UnityEngine;
using UnityEditor;

public class ConfigureSpriteImports : EditorWindow
{
    [MenuItem("SRP/Configure All Sprite Imports")]
    public static void ConfigureAll()
    {
        var guids = AssetDatabase.FindAssets("t:Texture2D", new[]{"Assets/Sprites"});
        foreach (var guid in guids)
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            var imp = AssetImporter.GetAtPath(path) as TextureImporter;
            if (imp == null) continue;
            imp.textureType = TextureImporterType.Sprite;
            imp.filterMode = FilterMode.Point;
            imp.textureCompression = TextureImporterCompression.Uncompressed;
            imp.spritePixelsPerUnit = 32;
            imp.SaveAndReimport();
        }
        AssetDatabase.Refresh();
        Debug.Log("[SRP] Configured " + guids.Length + " sprites as Sprite/Point/Uncompressed");
    }
}
