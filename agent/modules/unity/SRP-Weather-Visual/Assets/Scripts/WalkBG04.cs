using UnityEngine;

public class WalkBG04 : MonoBehaviour
{
    [Header("Bridge Zone (bg04)")]
    public float xStart = 53.333f;
    public float xEnd = 74.667f;
    public float bridgeWorldY = -2.63f;

    [Header("Chain")]
    public MonoBehaviour nextWalker;

    [Header("Walking")]
    public float walkSpeed = 1.76f;

    private Animator animator;
    private SpriteRenderer spriteRenderer;
    private float currentX;
    public bool walking;
    private Vector3 originalScale;

    void OnEnable()
    {
        animator = GetComponent<Animator>();
        spriteRenderer = GetComponent<SpriteRenderer>();

        originalScale = transform.localScale;
        transform.localScale = originalScale * 0.75f;

        currentX = xStart;
        UpdatePosition();
        animator.Play("Walk");
        walking = true;
    }

    void OnDisable()
    {
        transform.localScale = originalScale;
    }

    void Update()
    {
        if (!walking) return;

        currentX += walkSpeed * Time.deltaTime;
        if (currentX >= xEnd)
        {
            currentX = xEnd;
            walking = false;
            enabled = false;
            if (nextWalker != null) nextWalker.enabled = true;
        }

        UpdatePosition();
        if (spriteRenderer) spriteRenderer.flipX = true;
    }

    void UpdatePosition()
    {
        transform.position = new Vector3(currentX, bridgeWorldY, 0);
    }
}
