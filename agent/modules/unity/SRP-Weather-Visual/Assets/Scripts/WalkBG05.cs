using UnityEngine;

public class WalkBG05 : MonoBehaviour
{
    [Header("Bridge Zone (bg05)")]
    public float xStart = 74.667f;
    public float xStop = 88f;
    public float bridgeWorldY = -0.7f;

    [Header("Walking")]
    public float walkSpeed = 1.98f;

    [Header("Ending")]
    public float lookdownDuration = 2f;
    public Sprite lookdownSprite;
    public Sprite idleSprite;

    private enum State { Walking, LookingDown, Done }
    private State state;
    private Animator animator;
    private SpriteRenderer spriteRenderer;
    private float currentX;
    private float stateTimer;

    void Awake()
    {
        animator = GetComponent<Animator>();
        spriteRenderer = GetComponent<SpriteRenderer>();
    }

    void OnEnable()
    {
        if (idleSprite == null && spriteRenderer != null)
            idleSprite = spriteRenderer.sprite;

        currentX = xStart;
        state = State.Walking;
        stateTimer = 0f;
        UpdatePosition();
        animator.enabled = true;
        animator.Play("Walk");
    }

    void Update()
    {
        switch (state)
        {
            case State.Walking:
                currentX += walkSpeed * Time.deltaTime;
                if (currentX >= xStop)
                {
                    currentX = xStop;
                    state = State.LookingDown;
                    stateTimer = 0f;
                    animator.Play("Lookdown");
                }
                UpdatePosition();
                break;

            case State.LookingDown:
                stateTimer += Time.deltaTime;
                UpdatePosition();
                if (stateTimer >= lookdownDuration)
                {
                    state = State.Done;
                    // Disable Animator (WriteDefaults keeps nulling the sprite)
                    animator.enabled = false;
                    if (spriteRenderer != null && idleSprite != null)
                        spriteRenderer.sprite = idleSprite;
                }
                break;

            case State.Done:
                UpdatePosition();
                stateTimer += Time.deltaTime;
                if (stateTimer >= lookdownDuration + 0.5f)
                {
#if UNITY_EDITOR
                    UnityEditor.EditorApplication.isPlaying = false;
#endif
                }
                break;
        }

        if (spriteRenderer != null) spriteRenderer.flipX = true;
    }

    // Catch any null-sprite frames before Animator is disabled
    void LateUpdate()
    {
        if (spriteRenderer == null || spriteRenderer.sprite != null) return;

        if (state == State.LookingDown && lookdownSprite != null)
            spriteRenderer.sprite = lookdownSprite;
    }

    void UpdatePosition()
    {
        transform.position = new Vector3(currentX, bridgeWorldY, 0);
    }
}
