using UnityEngine;

// ── v1.2 UDP Protocol Data Classes ──

[System.Serializable]
public class ScoresData
{
    public float breath_sync;
    public float breath_depth;
    public float hrv_coherence;
    public float eda_calm;
}

[System.Serializable]
public class WeatherData
{
    public string type;
    public float composite;
    public float intensity;
    public string trend;
    public string dominant;
}

[System.Serializable]
public class BreathData
{
    public string phase;
    public float rate;
    public float amplitude;
    public float regularity_raw;
    public float circle_radius;
    public string source;
}

[System.Serializable]
public class CardiacData
{
    public float hr;
    public float rmssd;
    public float rr;
    public float ecg_raw;
    public string source;
}

[System.Serializable]
public class EDAData
{
    public float tonic;
    public float raw;
    public string source;
}

[System.Serializable]
public class GuidanceData
{
    public string prompt;
    public float target_breath_rate;
}

[System.Serializable]
public class SRPDataV12
{
    public string version;
    public float timestamp;
    public float calm_index;
    public ScoresData scores;
    public WeatherData weather;
    public BreathData breath;
    public CardiacData cardiac;
    public EDAData eda;
    public GuidanceData guidance;
}

// ── Weather Controller ──

public class WeatherController : MonoBehaviour
{
    [Header("Particle Systems")]
    public ParticleSystem rainParticles;
    public ParticleSystem lightningParticles;
    public ParticleSystem heatParticles;
    public ParticleSystem snowParticles;
    public ParticleSystem fogParticles;
    public ParticleSystem colorSparkles;

    [Header("Background")]
    public SpriteRenderer backgroundRenderer;

    [Header("Prompt Display")]
    public PromptDisplay promptDisplay;

    [Header("Weather Colors")]
    public Color stormColor = new(0.18f, 0.18f, 0.23f);
    public Color heatColor = new(0.8f, 0.27f, 0.0f);
    public Color snowColor = new(0.69f, 0.72f, 0.75f);
    public Color fadeColor = new(0.6f, 0.6f, 0.6f);
    public Color clearColor = new(0.4f, 0.7f, 1.0f);

    public float CurrentIntensity { get; private set; }
    public string CurrentWeather { get; private set; }
    public string CurrentBreathPhase { get; private set; }
    public float CalmIndex { get; private set; }

    private UDPReceiver _udpReceiver;
    private string _lastPrompt;

    void Start()
    {
        _udpReceiver = GetComponent<UDPReceiver>();
        if (_udpReceiver)
        {
            _udpReceiver.OnMessageReceived += OnDataReceived;
        }

        if (heatParticles) heatParticles.gameObject.SetActive(false);
        if (snowParticles) snowParticles.gameObject.SetActive(false);
        if (fogParticles) fogParticles.gameObject.SetActive(false);
        if (colorSparkles) colorSparkles.gameObject.SetActive(false);

        if (rainParticles) rainParticles.gameObject.SetActive(true);
        if (lightningParticles) lightningParticles.gameObject.SetActive(true);

        if (backgroundRenderer)
            backgroundRenderer.color = clearColor;
    }

    void OnDestroy()
    {
        if (_udpReceiver)
            _udpReceiver.OnMessageReceived -= OnDataReceived;
    }

    void OnDataReceived(string json)
    {
        var data = JsonUtility.FromJson<SRPDataV12>(json);
        if (data == null || data.weather == null) return;
        ApplyData(data);
    }

    public void ApplyData(SRPDataV12 data)
    {
        string nextWeather = NormalizeWeatherType(data.weather.type);

        CalmIndex = data.calm_index;
        CurrentIntensity = Mathf.Clamp01(data.weather.intensity);

        if (data.breath != null)
            CurrentBreathPhase = data.breath.phase;

        SwitchWeather(nextWeather);
        CurrentWeather = nextWeather;
        UpdateBackground(nextWeather, CurrentIntensity);
        UpdateParticles(nextWeather, CurrentIntensity);

        if (data.guidance != null && !string.IsNullOrEmpty(data.guidance.prompt)
            && data.guidance.prompt != _lastPrompt)
        {
            _lastPrompt = data.guidance.prompt;
            if (promptDisplay)
                promptDisplay.ShowPrompt(_lastPrompt);
        }
    }

    void SwitchWeather(string type)
    {
        if (type == CurrentWeather) return;

        if (rainParticles) rainParticles.gameObject.SetActive(false);
        if (lightningParticles) lightningParticles.gameObject.SetActive(false);
        if (heatParticles) heatParticles.gameObject.SetActive(false);
        if (snowParticles) snowParticles.gameObject.SetActive(false);
        if (fogParticles) fogParticles.gameObject.SetActive(false);
        if (colorSparkles) colorSparkles.gameObject.SetActive(false);

        switch (type)
        {
            case "storm":
                if (rainParticles) rainParticles.gameObject.SetActive(true);
                if (lightningParticles) lightningParticles.gameObject.SetActive(true);
                break;
            case "heat":
                if (heatParticles) heatParticles.gameObject.SetActive(true);
                break;
            case "snow":
                if (snowParticles) snowParticles.gameObject.SetActive(true);
                if (fogParticles) fogParticles.gameObject.SetActive(true);
                break;
            case "fade":
                if (colorSparkles) colorSparkles.gameObject.SetActive(true);
                break;
        }
    }

    string NormalizeWeatherType(string type)
    {
        return type switch
        {
            "storm" => "storm",
            "heat" => "heat",
            "snow" => "snow",
            "fade" => "fade",
            _ => "storm"
        };
    }

    void UpdateBackground(string type, float intensity)
    {
        if (!backgroundRenderer) return;

        Color weatherColor = type switch
        {
            "storm" => stormColor,
            "heat" => heatColor,
            "snow" => snowColor,
            "fade" => fadeColor,
            _ => clearColor
        };

        Color target = Color.Lerp(clearColor, weatherColor, intensity);
        backgroundRenderer.color = Color.Lerp(backgroundRenderer.color, target, Time.deltaTime * 2f);
    }

    void UpdateParticles(string type, float intensity)
    {
        var ps = GetActiveParticleSystem(type);
        if (!ps) return;

        var emission = ps.emission;
        emission.rateOverTime = Mathf.Lerp(10f, 200f, intensity);

        var main = ps.main;
        main.simulationSpeed = Mathf.Lerp(0.5f, 2f, intensity);
    }

    ParticleSystem GetActiveParticleSystem(string type)
    {
        return type switch
        {
            "storm" => rainParticles && rainParticles.gameObject.activeSelf ? rainParticles : null,
            "heat" => heatParticles && heatParticles.gameObject.activeSelf ? heatParticles : null,
            "snow" => snowParticles && snowParticles.gameObject.activeSelf ? snowParticles : null,
            "fade" => colorSparkles && colorSparkles.gameObject.activeSelf ? colorSparkles : null,
            _ => null
        };
    }
}
