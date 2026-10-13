using UnityEngine;

public class TravelerAnim : MonoBehaviour
{
    [Header("References")]
    public WeatherController weatherController;

    [Header("Movement")]
    public float baseWalkSpeed = 0.3f;
    public float maxWalkSpeed = 1.5f;
    public float bobHeight = 0.05f;
    public float bobFrequency = 4f;

    [Header("Visual States")]
    public Color intenseColor = new(0.4f, 0.4f, 0.5f);
    public Color clearColor = Color.white;

    private SpriteRenderer _spriteRenderer;
    private Vector3 _startPos;
    private float _bobTimer;
    private float _walkTimer;

    void Start()
    {
        _spriteRenderer = GetComponent<SpriteRenderer>();
        _startPos = transform.position;

        if (!weatherController)
            weatherController = FindFirstObjectByType<WeatherController>();
    }

    void Update()
    {
        if (!weatherController) return;

        float intensity = weatherController.CurrentIntensity;

        // Walk speed: slow when stormy (high intensity), faster as sky clears
        float speed = Mathf.Lerp(maxWalkSpeed, baseWalkSpeed, intensity);
        transform.position += Vector3.right * (speed * Time.deltaTime);

        // Wrap horizontally
        if (transform.position.x > 5f)
            transform.position = new Vector3(-5f, transform.position.y, transform.position.z);

        // Breathing bob
        _bobTimer += Time.deltaTime * bobFrequency * (1f + intensity);
        float bob = Mathf.Sin(_bobTimer) * bobHeight * (1f - intensity);
        transform.position = new Vector3(transform.position.x, _startPos.y + bob, _startPos.z);

        // Color: darker tint when stormy
        if (_spriteRenderer)
            _spriteRenderer.color = Color.Lerp(clearColor, intenseColor, intensity);
    }
}
