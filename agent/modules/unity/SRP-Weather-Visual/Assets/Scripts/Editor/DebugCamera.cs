using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class DebugCamera : EditorWindow
{
    [MenuItem("SRP/Debug Camera")]
    public static void DebugCam()
    {
        var scene = EditorSceneManager.OpenScene("Assets/Scenes/StormScene.unity", OpenSceneMode.Single);

        var cam = Camera.main;
        if (cam == null)
        {
            Debug.LogError("[DEBUG] No MainCamera found!");
            foreach (var c in Object.FindObjectsOfType<Camera>())
                Debug.Log("[DEBUG] Found camera: " + c.name + " tag=" + c.tag + " enabled=" + c.enabled);
            return;
        }

        Debug.Log("[DEBUG] Camera: " + cam.name);
        Debug.Log("[DEBUG]   Position: " + cam.transform.position);
        Debug.Log("[DEBUG]   Ortho: " + cam.orthographic + " size=" + cam.orthographicSize);
        Debug.Log("[DEBUG]   ClearFlags: " + cam.clearFlags + " bg=" + cam.backgroundColor);
        Debug.Log("[DEBUG]   CullingMask: " + cam.cullingMask);
        Debug.Log("[DEBUG]   Near=" + cam.nearClipPlane + " Far=" + cam.farClipPlane);
        Debug.Log("[DEBUG]   Enabled: " + cam.enabled);
        Debug.Log("[DEBUG]   Depth: " + cam.depth);

        // Fix camera
        cam.enabled = true;
        cam.orthographic = true;
        cam.orthographicSize = 6f;
        cam.nearClipPlane = 0.01f;
        cam.farClipPlane = 1000f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.176f, 0.176f, 0.227f);
        cam.cullingMask = -1;
        cam.depth = -1;

        // Check sprites
        var bgContainer = GameObject.Find("BackgroundContainer");
        if (bgContainer != null)
        {
            for (int i = 0; i < bgContainer.transform.childCount; i++)
            {
                var child = bgContainer.transform.GetChild(i);
                var sr = child.GetComponent<SpriteRenderer>();
                Debug.Log("[DEBUG] " + child.name + " pos=" + child.transform.position
                    + " scale=" + child.transform.localScale
                    + " sprite=" + (sr.sprite!=null?sr.sprite.name:"NULL")
                    + " enabled=" + sr.enabled
                    + " layer=" + LayerMask.LayerToName(child.gameObject.layer));
            }
        }

        var trav = GameObject.Find("Traveler");
        if (trav != null)
        {
            var sr = trav.GetComponent<SpriteRenderer>();
            Debug.Log("[DEBUG] Traveler pos=" + trav.transform.position
                + " sprite=" + (sr.sprite!=null?sr.sprite.name:"NULL")
                + " enabled=" + sr.enabled
                + " layer=" + LayerMask.LayerToName(trav.gameObject.layer));
        }

        EditorSceneManager.SaveScene(scene);
    }
}
