using UnityEngine;
using System.Collections;

public class Scene1Director : MonoBehaviour
{
    [Header("Scene References")]
    public GameObject traveler;
    public GameObject shield;
    public ParticleSystem rainPS;
    public GameObject lightningOverlay;
    public GameObject backgroundContainer;
    public Camera mainCamera;

    [Header("Shield Frames (0=intact, 8=broken)")]
    public Sprite[] shieldSprites;

    [Header("Timing")]
    public float idleDuration = 3f;
    public float walkSpeed = 2.2f;

    // Boundaries (world X, bg_01 center at 0)
    private const float BG_WIDTH = 21.333f;
    private const float BG1_BG2_EDGE = -10.667f;  // half of bgWidth
    private const float BG2_BG3_EDGE = -32f;
    private const float BG3_BG4_EDGE = -53.333f;
    private const float STOP_X = -85f;

    private Animator travAnim;
    private SpriteRenderer shieldSR;
    private ParticleSystem.EmissionModule rainEmission;
    private bool rainStarted;
    private bool shieldCracking;
    private float rainZoneProgress;

    void Awake()
    {
        if (traveler == null) traveler = GameObject.Find("Traveler");
        if (shield == null) shield = GameObject.Find("Traveler/Shield");
        if (mainCamera == null) mainCamera = Camera.main;
        if (backgroundContainer == null) backgroundContainer = GameObject.Find("BackgroundContainer");
        if (rainPS == null) rainPS = GetComponentInChildren<ParticleSystem>();
        if (lightningOverlay == null) lightningOverlay = GameObject.Find("LightningOverlay");
    }

    void Start()
    {
        travAnim = traveler != null ? traveler.GetComponent<Animator>() : null;
        shieldSR = shield != null ? shield.GetComponent<SpriteRenderer>() : null;
        if (rainPS != null)
        {
            rainEmission = rainPS.emission;
            rainEmission.rateOverTime = 0f;
        }
        if (shield != null) shield.SetActive(false);
        StartCoroutine(Timeline());
    }

    IEnumerator Timeline()
    {
        if (traveler == null || travAnim == null) yield break;

        // === Phase 0: Idle on wasteland (bg_01) ===
        travAnim.Play("Idle");
        yield return new WaitForSeconds(idleDuration);

        // === Phase 1-5: Walk left across all backgrounds ===
        travAnim.Play("Walk");
        float x = traveler.transform.position.x;
        rainStarted = false;
        shieldCracking = false;

        while (x > STOP_X)
        {
            x -= walkSpeed * Time.deltaTime;
            traveler.transform.position = new Vector3(x, traveler.transform.position.y, 0);

            // Camera follows with smooth lag
            if (mainCamera != null)
            {
                float targetCamX = Mathf.Min(x + 7f, 0f);
                Vector3 camPos = mainCamera.transform.position;
                camPos.x = Mathf.Lerp(camPos.x, targetCamX, 0.1f);
                mainCamera.transform.position = camPos;
            }

            // Rain zone: bg_02 through bg_03
            if (x <= BG1_BG2_EDGE && rainPS != null)
            {
                rainZoneProgress = Mathf.Clamp01((BG1_BG2_EDGE - x) / (BG1_BG2_EDGE - BG3_BG4_EDGE));

                if (!rainStarted)
                {
                    rainStarted = true;
                    if (shield != null) shield.SetActive(true);
                    if (shieldSR != null && shieldSprites.Length > 0) shieldSR.sprite = shieldSprites[0];
                    rainPS.Play();
                    if (lightningOverlay != null) StartCoroutine(FlashLoop());
                }

                // Rain intensifies: 60 → 260 particles/s
                rainEmission.rateOverTime = 60f + rainZoneProgress * 220f;

                // Shield starts cracking at 40% through storm zone
                if (!shieldCracking && rainZoneProgress > 0.4f)
                {
                    shieldCracking = true;
                    StartCoroutine(CrackShield());
                }
            }

            yield return null;
        }

        // === End: Stop and idle ===
        travAnim.Play("Idle");
        if (rainPS != null)
        {
            rainEmission.rateOverTime = 0f;
            rainPS.Stop();
        }
        if (shield != null && shield.activeSelf)
            shield.SetActive(false);
    }

    IEnumerator FlashLoop()
    {
        while (traveler != null && lightningOverlay != null)
        {
            yield return new WaitForSeconds(Random.Range(1.5f, 4f));
            if (traveler.transform.position.x > BG1_BG2_EDGE) break;
            lightningOverlay.SetActive(true);
            yield return new WaitForSeconds(0.06f);
            lightningOverlay.SetActive(false);
            yield return new WaitForSeconds(0.04f);
            lightningOverlay.SetActive(true);
            yield return new WaitForSeconds(0.05f);
            lightningOverlay.SetActive(false);
        }
    }

    IEnumerator CrackShield()
    {
        if (shield == null || shieldSR == null || shieldSprites.Length == 0) yield break;
        int frame = 0;
        while (frame < shieldSprites.Length - 1 && shield.activeSelf)
        {
            float p = Mathf.Clamp01(
                (BG1_BG2_EDGE - traveler.transform.position.x) / (BG1_BG2_EDGE - BG3_BG4_EDGE));
            float shieldP = Mathf.Clamp01((p - 0.4f) / 0.6f);
            int targetFrame = Mathf.Min((int)(shieldP * (shieldSprites.Length - 1)), shieldSprites.Length - 1);

            if (targetFrame > frame)
            {
                frame = targetFrame;
                shieldSR.sprite = shieldSprites[frame];
            }

            if (shieldP >= 1f)
            {
                shieldSR.sprite = shieldSprites[shieldSprites.Length - 1];
                yield return new WaitForSeconds(0.5f);
                shield.SetActive(false);
                break;
            }

            yield return null;
        }
    }
}
