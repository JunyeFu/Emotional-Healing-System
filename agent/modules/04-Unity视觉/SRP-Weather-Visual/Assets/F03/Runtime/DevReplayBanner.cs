using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace SRP.F03
{
    public sealed class DevReplayBanner : MonoBehaviour
    {
        private const string CaptureArgument = "--f03-capture=";
        private const string AutoQuitArgument = "--f03-auto-quit";

        [SerializeField] private string buildCommit = "WORKTREE";
        [SerializeField] private string buildUtc = "NOT BUILT";
        [SerializeField] private string unityRevision = "6000.4.9f1 (f7258d6eebbe)";

        private GUIStyle modeStyle;
        private GUIStyle evidenceStyle;

        public string ModeLabel => "DEV-REPLAY";
        public string FormalityLabel => "NOT FORMAL";
        public string BuildCommit => buildCommit;
        public string BuildUtc => buildUtc;
        public string UnityRevision => unityRevision;

        public void ConfigureBuildEvidence(string commit, string utc, string revision)
        {
            buildCommit = string.IsNullOrWhiteSpace(commit) ? "UNKNOWN" : commit;
            buildUtc = string.IsNullOrWhiteSpace(utc) ? "UNKNOWN" : utc;
            unityRevision = string.IsNullOrWhiteSpace(revision) ? Application.unityVersion : revision;
        }

        private void Start()
        {
            Debug.Log($"F03_DEV_REPLAY_READY commit={buildCommit} unity={unityRevision}");
            var capturePath = ReadArgument(CaptureArgument);
            if (!string.IsNullOrWhiteSpace(capturePath))
            {
                StartCoroutine(CaptureEvidence(capturePath, HasArgument(AutoQuitArgument)));
            }
        }

        private void OnGUI()
        {
            modeStyle ??= new GUIStyle(GUI.skin.label)
            {
                alignment = TextAnchor.MiddleLeft,
                fontSize = Mathf.Clamp(Screen.height / 28, 20, 32),
                fontStyle = FontStyle.Bold,
                normal = { textColor = Color.white }
            };
            evidenceStyle ??= new GUIStyle(GUI.skin.label)
            {
                alignment = TextAnchor.MiddleLeft,
                fontSize = Mathf.Clamp(Screen.height / 48, 13, 18),
                normal = { textColor = new Color(0.9f, 0.92f, 0.96f, 1f) }
            };

            GUI.backgroundColor = new Color(0.55f, 0.08f, 0.08f, 1f);
            GUI.Box(new Rect(0f, 0f, Screen.width, Mathf.Max(84f, Screen.height * 0.12f)), GUIContent.none);
            GUI.backgroundColor = Color.white;
            GUI.Label(new Rect(16f, 4f, Screen.width - 32f, 42f), $"{ModeLabel}  |  {FormalityLabel}", modeStyle);
            GUI.Label(
                new Rect(16f, 43f, Screen.width - 32f, 30f),
                $"Unity {unityRevision}  |  Commit {buildCommit}  |  Built {buildUtc}",
                evidenceStyle);
        }

        private static string ReadArgument(string prefix)
        {
            foreach (var argument in Environment.GetCommandLineArgs())
            {
                if (argument.StartsWith(prefix, StringComparison.Ordinal))
                {
                    return argument.Substring(prefix.Length).Trim('"');
                }
            }
            return null;
        }

        private static bool HasArgument(string expected)
        {
            foreach (var argument in Environment.GetCommandLineArgs())
            {
                if (string.Equals(argument, expected, StringComparison.Ordinal))
                {
                    return true;
                }
            }
            return false;
        }

        private static IEnumerator CaptureEvidence(string capturePath, bool autoQuit)
        {
            var directory = Path.GetDirectoryName(capturePath);
            if (!string.IsNullOrWhiteSpace(directory))
            {
                Directory.CreateDirectory(directory);
            }

            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(capturePath);
            for (var frame = 0; frame < 180 && !File.Exists(capturePath); frame++)
            {
                yield return null;
            }

            Debug.Log(File.Exists(capturePath)
                ? $"F03_DEV_REPLAY_SCREENSHOT_WRITTEN path={capturePath}"
                : $"F03_DEV_REPLAY_SCREENSHOT_MISSING path={capturePath}");
            if (autoQuit)
            {
                Application.Quit(File.Exists(capturePath) ? 0 : 2);
            }
        }
    }
}
