using UnityEngine;
using UnityEditor;

public class ImportNewSprites : EditorWindow
{
    [MenuItem("SRP/Import New RGBA Sprites")]
    public static void Run()
    {
        string[] newFiles = {
            "Assets/Sprites/traveler/walk/walk_05.png",
            "Assets/Sprites/traveler/walk/walk_06.png",
            "Assets/Sprites/traveler/pose_kneel.png",
            "Assets/Sprites/traveler/pose_kneel2.png",
            "Assets/Sprites/traveler/pose_kneel3.png",
            "Assets/Sprites/traveler/pose_run.png",
            "Assets/Sprites/traveler/pose_sit.png"
        };

        foreach (var path in newFiles)
        {
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null)
            {
                Debug.LogWarning($"[IMPORT] No importer for {path}, reimporting...");
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                importer = AssetImporter.GetAtPath(path) as TextureImporter;
            }

            if (importer != null)
            {
                importer.textureType = TextureImporterType.Sprite;
                importer.spriteImportMode = SpriteImportMode.Single;
                importer.spritePixelsPerUnit = 32;
                importer.filterMode = FilterMode.Point;
                importer.textureCompression = TextureImporterCompression.Uncompressed;
                importer.mipmapEnabled = false;
                importer.alphaIsTransparency = true;
                importer.SaveAndReimport();
                Debug.Log($"[IMPORT] Configured: {path} (RGBA, Point, 32PPU, NoCompress)");
            }
            else
            {
                Debug.LogError($"[IMPORT] Failed to get importer for {path}");
            }
        }

        AssetDatabase.Refresh();
        Debug.Log("[IMPORT] Done. All new RGBA sprites imported.");
    }
}
