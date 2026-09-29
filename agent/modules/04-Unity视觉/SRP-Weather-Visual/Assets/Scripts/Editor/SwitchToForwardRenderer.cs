using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public class SwitchToForwardRenderer : EditorWindow
{
    [MenuItem("SRP/Switch to Forward Renderer")]
    public static void Run()
    {
        // Create ForwardRenderer asset
        var frData = ScriptableObject.CreateInstance<UniversalRendererData>();
        frData.name = "ForwardRenderer";
        AssetDatabase.CreateAsset(frData, "Assets/Settings/ForwardRenderer.asset");
        AssetDatabase.SaveAssets();
        Debug.Log("[SWITCH] Created ForwardRenderer.asset");

        // Get URP asset
        var urpAsset = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>("Assets/Settings/UniversalRP.asset");
        if (urpAsset == null)
        {
            Debug.LogError("[SWITCH] Could not load UniversalRP.asset");
            return;
        }

        // Set the renderer list via reflection
        var listField = urpAsset.GetType().GetField("m_RendererDataList",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        if (listField == null)
        {
            Debug.LogError("[SWITCH] Could not find m_RendererDataList field");
            return;
        }

        // The list is ScriptableRendererData[]
        var list = listField.GetValue(urpAsset) as System.Collections.IList;
        if (list == null)
        {
            Debug.LogError("[SWITCH] RendererDataList is null");
            return;
        }

        // Replace first entry with ForwardRenderer
        list[0] = frData;
        listField.SetValue(urpAsset, list);

        // Set default index to 0
        var idxField = urpAsset.GetType().GetField("m_DefaultRendererIndex",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        if (idxField != null)
            idxField.SetValue(urpAsset, 0);

        EditorUtility.SetDirty(urpAsset);
        AssetDatabase.SaveAssets();
        Debug.Log("[SWITCH] URP now uses ForwardRenderer at index 0");
    }
}
