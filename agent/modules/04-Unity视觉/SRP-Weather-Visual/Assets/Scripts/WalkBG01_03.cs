using UnityEngine;

[System.Serializable]
public class BridgeZone
{
    public string label;
    public float xStart;
    public float xEnd;
    public float bridgeWorldY;
}

public class WalkBG01_03 : MonoBehaviour
{
    [Header("Bridge Zones (bg01, bg02, bg03)")]
    public BridgeZone[] zones = new BridgeZone[]
    {
        new BridgeZone { label = "bg01", xStart = -8.34f,  xEnd = 10.667f,  bridgeWorldY = -1.7f },
        new BridgeZone { label = "bg02", xStart = 10.667f,  xEnd = 32f,       bridgeWorldY = -1.7f },
        new BridgeZone { label = "bg03", xStart = 32f,      xEnd = 53.333f,   bridgeWorldY = -1.7f },
    };

    [Header("Chain")]
    public MonoBehaviour nextWalker;

    [Header("Walking")]
    public float walkSpeed = 2.2f;

    private Animator animator;
    private SpriteRenderer spriteRenderer;
    private float currentX;
    public bool walking;

    void OnEnable()
    {
        animator = GetComponent<Animator>();
        spriteRenderer = GetComponent<SpriteRenderer>();

        currentX = zones[0].xStart;
        UpdatePosition();
        animator.Play("Walk");
        walking = true;
    }

    float GetBridgeY(float x)
    {
        foreach (var zone in zones)
            if (x >= zone.xStart && x < zone.xEnd)
                return zone.bridgeWorldY;
        return zones[zones.Length - 1].bridgeWorldY;
    }

    void Update()
    {
        if (!walking) return;

        currentX += walkSpeed * Time.deltaTime;
        if (currentX >= zones[zones.Length - 1].xEnd)
        {
            currentX = zones[zones.Length - 1].xEnd;
            walking = false;
            enabled = false;
            if (nextWalker != null) nextWalker.enabled = true;
        }

        UpdatePosition();
        if (spriteRenderer) spriteRenderer.flipX = true;
    }

    void UpdatePosition()
    {
        transform.position = new Vector3(currentX, GetBridgeY(currentX), 0);
    }
}
