using UnityEngine;
using TMPro;

public class PromptDisplay : MonoBehaviour
{
    public TextMeshProUGUI promptText;
    public float fadeInDuration = 0.8f;
    public float holdDuration = 3.0f;
    public float fadeOutDuration = 1.2f;

    private float _timer;
    private enum State { FadingIn, Holding, FadingOut, Idle }
    private State _state = State.Idle;

    public void ShowPrompt(string text)
    {
        if (promptText) promptText.text = text;
        _timer = 0f;
        _state = State.FadingIn;
    }

    void Update()
    {
        switch (_state)
        {
            case State.FadingIn:
                _timer += Time.deltaTime;
                SetAlpha(Mathf.Clamp01(_timer / fadeInDuration));
                if (_timer >= fadeInDuration) { _timer = 0f; _state = State.Holding; }
                break;
            case State.Holding:
                _timer += Time.deltaTime;
                if (_timer >= holdDuration) { _timer = 0f; _state = State.FadingOut; }
                break;
            case State.FadingOut:
                _timer += Time.deltaTime;
                SetAlpha(1f - Mathf.Clamp01(_timer / fadeOutDuration));
                if (_timer >= fadeOutDuration) { SetAlpha(0f); _state = State.Idle; }
                break;
        }
    }

    void SetAlpha(float a)
    {
        if (!promptText) return;
        var c = promptText.color;
        c.a = a;
        promptText.color = c;
    }
}
