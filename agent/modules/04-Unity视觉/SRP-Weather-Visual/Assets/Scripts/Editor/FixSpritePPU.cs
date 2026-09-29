using UnityEngine;
using UnityEditor;
using System.Collections.Generic;

public class FixSpritePPU : EditorWindow
{
    [MenuItem("SRP/Fix Sprite PPU — Normalize Character Size")]
    public static void Run()
    {
        // Reference: idle char area = 623*880 = 548240 px² at 32 PPU
        const float REF_AREA = 548240f;
        const float REF_PPU = 32f;

        // Each entry: (path, char_pixel_area)
        var sprites = new (string path, float charArea)[]
        {
            ("Assets/Sprites/traveler/traveler_idle.png",     623*880),
            ("Assets/Sprites/traveler/traveler_lookdown.png",  590*703),
            ("Assets/Sprites/traveler/walk/walk_01.png",       627*827),
            ("Assets/Sprites/traveler/walk/walk_02.png",       593*789),
            ("Assets/Sprites/traveler/walk/walk_03.png",       506*680),
            ("Assets/Sprites/traveler/walk/walk_04.png",       623*797),
            ("Assets/Sprites/traveler/walk/walk_05.png",       513*756),
            ("Assets/Sprites/traveler/walk/walk_06.png",       507*706),
            ("Assets/Sprites/traveler/fall/fall_1.png",        1254*1254),
            ("Assets/Sprites/traveler/fall/fall_2.png",        1254*1254),
            ("Assets/Sprites/traveler/fall/fall_3.png",        1254*1254),
            ("Assets/Sprites/traveler/fall/fall_4.png",        1254*1254),
            ("Assets/Sprites/traveler/fall/fall_5.png",        1254*1254),
            ("Assets/Sprites/traveler/fall/fall_6.png",        1254*1254),
            ("Assets/Sprites/traveler/fall/fall_7.png",        1254*1254),
            ("Assets/Sprites/traveler/fall/fall_8.png",        876*254),
            ("Assets/Sprites/traveler/pose_stand2.png",        545*779),
        };

        foreach (var (path, charArea) in sprites)
        {
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null) { Debug.LogWarning($"[PPU] Importer not found: {path}"); continue; }

            float scaleFactor = Mathf.Sqrt(charArea / REF_AREA);
            int newPPU = Mathf.RoundToInt(REF_PPU * scaleFactor);
            int oldPPU = (int)importer.spritePixelsPerUnit;

            if (newPPU != oldPPU)
            {
                importer.spritePixelsPerUnit = newPPU;
                importer.SaveAndReimport();
                Debug.Log($"[PPU] {System.IO.Path.GetFileName(path)}: {oldPPU} → {newPPU} (scale_factor={scaleFactor:F3})");
            }
            else
            {
                Debug.Log($"[PPU] {System.IO.Path.GetFileName(path)}: {oldPPU} (unchanged)");
            }
        }

        AssetDatabase.Refresh();
        Debug.Log("[PPU] Done. All sprites normalized to idle character size.");
    }
}
