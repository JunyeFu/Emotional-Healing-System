using UnityEngine;
using System.Collections;

public class WeatherDirector : MonoBehaviour
{
    [Header("References")]
    public GameObject traveler;
    public GameObject shield;
    public ParticleSystem rainPSNear;
    public ParticleSystem rainPSFar;
    public GameObject lightningOverlay;
    public Camera mainCamera;

    [Header("Toggles")]
    public bool enableLightning = false;
    public bool enableShield = false;

    [Header("Shield Sprites")]
    public Sprite shieldClean;
    public Sprite[] shieldFrames = new Sprite[9];

    [Header("Phase Thresholds")]
    public float xRainStart = 1.17f;
    public float xLightningStart = 32f;
    public float xShieldBreak = 42.667f;
    public float xRecede = 53.333f;
    public float xMinimal = 74.667f;
    public float xEnd = 88f;
    public float fallDuration = 3f;

    private Animator travAnim;
    private SpriteRenderer shieldSR;
    private bool fallTriggered;
    private bool isFalling;
    private Coroutine flashRoutine;

    void Start()
    {
        if (traveler == null) traveler = GameObject.Find("Traveler");
        if (shield == null) shield = GameObject.Find("Shield");
        if (rainPSNear == null)
        {
            var go = GameObject.Find("RainNear");
            if (go != null) rainPSNear = go.GetComponent<ParticleSystem>();
        }
        if (rainPSFar == null)
        {
            var go = GameObject.Find("RainFar");
            if (go != null) rainPSFar = go.GetComponent<ParticleSystem>();
        }
        if (lightningOverlay == null) lightningOverlay = GameObject.Find("LightningOverlay");
        if (mainCamera == null) mainCamera = Camera.main;

        travAnim = traveler != null ? traveler.GetComponent<Animator>() : null;
        shieldSR = shield != null ? shield.GetComponent<SpriteRenderer>() : null;

        if (rainPSNear != null) { var em = rainPSNear.emission; em.rateOverTime = 0f; }
        if (rainPSFar != null) { var em = rainPSFar.emission; em.rateOverTime = 0f; }
        if (shield != null) shield.SetActive(false);
        if (lightningOverlay != null) lightningOverlay.SetActive(false);

        if (enableLightning)
            flashRoutine = StartCoroutine(FlashLoop());
    }

    void Update()
    {
        if (traveler == null) return;
        float x = traveler.transform.position.x;

        if (mainCamera != null)
        {
            var camPos = mainCamera.transform.position;
            if (rainPSNear != null) rainPSNear.transform.position = camPos + new Vector3(0, 6f, 0);
            if (rainPSFar != null) rainPSFar.transform.position = camPos + new Vector3(0, 7f, 0);
        }

        UpdateRain(x);
        if (enableShield) UpdateShield(x);
        CheckFallTrigger(x);
        CheckEnd(x);
    }

    void UpdateRain(float x)
    {
        float rate = RainRate(x);
        float nearRate = rate * 0.7f;
        float farRate = rate * 0.3f;

        if (rainPSNear != null)
        {
            var em = rainPSNear.emission;
            em.rateOverTime = nearRate;
            if (rate > 0 && !rainPSNear.isPlaying) rainPSNear.Play();
            else if (rate <= 0 && rainPSNear.isPlaying) rainPSNear.Stop();
        }
        if (rainPSFar != null)
        {
            var em = rainPSFar.emission;
            em.rateOverTime = farRate;
            if (rate > 0 && !rainPSFar.isPlaying) rainPSFar.Play();
            else if (rate <= 0 && rainPSFar.isPlaying) rainPSFar.Stop();
        }
    }

    float RainRate(float x)
    {
        if (x < xRainStart) return 0f;
        if (x < xLightningStart) return Mathf.Lerp(10f, 80f, (x - xRainStart) / (xLightningStart - xRainStart));
        if (x < xShieldBreak)   return Mathf.Lerp(80f, 280f, (x - xLightningStart) / (xShieldBreak - xLightningStart));
        if (x < xRecede)        return Mathf.Lerp(280f, 200f, (x - xShieldBreak) / (xRecede - xShieldBreak));
        if (x < xMinimal)       return Mathf.Lerp(200f, 80f, (x - xRecede) / (xMinimal - xRecede));
        if (x < xEnd)           return Mathf.Lerp(80f, 10f, (x - xMinimal) / (xEnd - xMinimal));
        return 0f;
    }

    void UpdateShield(float x)
    {
        if (!enableShield || shieldSR == null || shield == null || isFalling) return;

        if (x < xRainStart)
        {
            shield.SetActive(false);
            return;
        }

        if (!shield.activeSelf)
            shield.SetActive(true);

        if (x < xShieldBreak)
        {
            float crackT = (x - xRainStart) / (xShieldBreak - xRainStart);
            int frame = Mathf.Clamp(Mathf.FloorToInt(crackT * shieldFrames.Length), 0, shieldFrames.Length - 1);
            if (shieldFrames.Length > 0 && frame < shieldFrames.Length)
                shieldSR.sprite = shieldFrames[frame];
        }
        else
        {
            shieldSR.sprite = shieldClean;
        }
    }

    void CheckFallTrigger(float x)
    {
        if (fallTriggered || x < xShieldBreak) return;
        fallTriggered = true;
        StartCoroutine(FallAndRecover());
    }

    void CheckEnd(float x)
    {
        if (x >= xEnd)
        {
            if (rainPSNear != null && rainPSNear.isPlaying) { var em = rainPSNear.emission; em.rateOverTime = 0f; rainPSNear.Stop(); }
            if (rainPSFar != null && rainPSFar.isPlaying) { var em = rainPSFar.emission; em.rateOverTime = 0f; rainPSFar.Stop(); }
            if (flashRoutine != null) StopCoroutine(flashRoutine);
            if (lightningOverlay != null) lightningOverlay.SetActive(false);
        }
    }

    IEnumerator FallAndRecover()
    {
        isFalling = true;

        // 1. Shield disappears immediately
        if (enableShield && shield != null)
        {
            if (shieldSR != null && shieldFrames.Length > 0)
                shieldSR.sprite = shieldFrames[shieldFrames.Length - 1];
            shield.SetActive(false);
        }

        // 2. 0.1s later: traveler falls
        yield return new WaitForSeconds(0.1f);
        PauseWalker(true);
        if (travAnim != null) travAnim.Play("Fall");

        // 3. Wait fallDuration from fall start
        yield return new WaitForSeconds(fallDuration);

        // 4. Shield reappears
        if (enableShield && shield != null)
        {
            shield.SetActive(true);
            if (shieldSR != null) shieldSR.sprite = shieldClean;
        }

        // 5. Stand up
        if (travAnim != null) travAnim.Play("Stand2");
        yield return new WaitForSeconds(0.4f);

        // 6. Resume walking
        if (travAnim != null) travAnim.Play("Walk");
        PauseWalker(false);
        isFalling = false;
    }

    void PauseWalker(bool pause)
    {
        if (traveler == null) return;

        var w1 = traveler.GetComponent<WalkBG01_03>();
        if (w1 != null && w1.enabled) { w1.walking = !pause; return; }

        var w4 = traveler.GetComponent<WalkBG04>();
        if (w4 != null && w4.enabled) { w4.walking = !pause; return; }
    }

    IEnumerator FlashLoop()
    {
        var lightSR = lightningOverlay != null ? lightningOverlay.GetComponent<SpriteRenderer>() : null;

        while (true)
        {
            if (traveler == null) yield break;
            float x = traveler.transform.position.x;
            float freq = LightningFreq(x);

            if (freq < 0.01f)
            {
                yield return null;
                continue;
            }

            float meanInterval = 1f / freq;
            yield return new WaitForSeconds(Random.Range(meanInterval * 0.5f, meanInterval * 1.5f));

            if (traveler == null || traveler.transform.position.x >= xEnd) break;

            if (lightningOverlay != null) lightningOverlay.SetActive(true);
            yield return new WaitForSeconds(0.06f);
            if (lightningOverlay != null) lightningOverlay.SetActive(false);
            yield return new WaitForSeconds(0.04f);
            if (lightningOverlay != null) lightningOverlay.SetActive(true);
            yield return new WaitForSeconds(0.05f);
            if (lightningOverlay != null) lightningOverlay.SetActive(false);
        }
    }

    float LightningFreq(float x)
    {
        if (x < xLightningStart) return 0f;
        if (x < xShieldBreak)  return Mathf.Lerp(0.5f, 3.0f, (x - xLightningStart) / (xShieldBreak - xLightningStart));
        if (x < xRecede)       return Mathf.Lerp(3.0f, 2.0f, (x - xShieldBreak) / (xRecede - xShieldBreak));
        if (x < xMinimal)      return Mathf.Lerp(2.0f, 0.5f, (x - xRecede) / (xMinimal - xRecede));
        if (x < xEnd)          return Mathf.Lerp(0.5f, 0.05f, (x - xMinimal) / (xEnd - xMinimal));
        return 0f;
    }
}
