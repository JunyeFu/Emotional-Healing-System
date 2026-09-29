using UnityEngine;

public class CameraSwitch : MonoBehaviour
{
    [Header("Camera Positions (center pivot of each bg)")]
    public float[] bgCenters = new float[]
    {
        0f,       // bg_01 center
        21.333f,  // bg_02 center
        42.666f,  // bg_03 center
        64f,      // bg_04 center
        85.333f,  // bg_05 center
    };

    [Header("BG Boundaries (midpoint between bg's)")]
    public float[] bgBoundaries = new float[]
    {
        10.667f,  // bg_01 → bg_02
        32f,      // bg_02 → bg_03
        53.333f,  // bg_03 → bg_04
        74.667f,  // bg_04 → bg_05
    };

    [Header("Target")]
    public Transform traveler;

    private Transform camTransform;
    private int currentBgIndex;

    void Start()
    {
        camTransform = Camera.main != null ? Camera.main.transform : transform;
        if (traveler == null)
            traveler = GameObject.Find("Traveler")?.transform;

        currentBgIndex = -1;
        UpdateCamera();
    }

    void LateUpdate()
    {
        if (traveler == null) return;

        float x = traveler.position.x;
        int targetBg = 0;

        for (int i = 0; i < bgBoundaries.Length; i++)
        {
            if (x >= bgBoundaries[i])
                targetBg = i + 1;
            else
                break;
        }

        if (targetBg != currentBgIndex)
        {
            currentBgIndex = targetBg;
            UpdateCamera();
        }
    }

    void UpdateCamera()
    {
        if (currentBgIndex >= 0 && currentBgIndex < bgCenters.Length)
        {
            Vector3 pos = camTransform.position;
            pos.x = bgCenters[currentBgIndex];
            camTransform.position = pos;
        }
    }
}
