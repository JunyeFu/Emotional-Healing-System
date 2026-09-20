using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace SRP.V03
{
    /// <summary>
    /// U-02 降级演示驱动（DEV ONLY，非生产接线）。
    /// 运行方式：新建空场景挂本脚本，Play 后点按钮按
    /// GOOD → DEGRADED → UNUSABLE → DISCONNECTED → ResetSession 顺序演示。
    /// 内置遥测桩按当前选定 quality 生成合法帧；链路断开走 NotifyLinkDown 无帧路径。
    /// 屏幕只读面板实时显示四层输出，用于录屏取证（AC1/AC2/AC3）。
    /// </summary>
    public sealed class V03DegradationDemoDriver : MonoBehaviour
    {
        private enum DemoStage
        {
            Good = 0,
            Degraded = 1,
            Unusable = 2,
            Disconnected = 3,
            ResetSession = 4,
        }

        private sealed class StubSource : IV03TelemetrySource
        {
            public DemoStage Stage;
            public int FrameCounter;

            public V03LinkState LinkState =>
                Stage == DemoStage.Disconnected ? V03LinkState.Disconnected
                : Stage == DemoStage.Unusable ? V03LinkState.Unusable
                : Stage == DemoStage.Degraded ? V03LinkState.Degraded
                : V03LinkState.Linked;

            public bool TryGetFrame(out V03FrameDto frame)
            {
                frame = null;
                if (Stage == DemoStage.Disconnected || Stage == DemoStage.ResetSession)
                    return false;

                FrameCounter++;
                var state = Stage == DemoStage.Unusable ? "UNUSABLE"
                    : Stage == DemoStage.Degraded ? "DEGRADED" : "GOOD";

                // 呼吸节律目标值随帧在 0~1 循环：GOOD 下四层应跟随；
                // 降级/锁定下各层按行为矩阵冻结或降级。
                float rhythm = 0.5f + 0.5f * Mathf.Sin(FrameCounter * 0.25f);

                frame = new V03FrameDto
                {
                    MessageType = "telemetry_frame",
                    SchemaVersion = "2.2",
                    FrameSeq = FrameCounter,
                    SessionId = "S-DEMO-0001",
                    ModuleId = "storm",
                    Segment = "demo_main",
                    CueMode = "rhythmic",
                    TargetPhase = "inhale_1",
                    TargetProgress = rhythm,
                    TargetCycleIndex = 1,
                    TargetStepId = "storm_inhale_v22",
                    ActualPhase = "inhale_1",
                    ActualProgress = rhythm,
                    ActualCycleIndex = 1,
                    ActualStepId = "storm_inhale_v22",
                    ActualConfidence = Stage == DemoStage.Degraded ? 0.62f : 0.93f,
                    RecoveryValue = rhythm,
                    RecoveryLocked = false,
                    SignalQualityResp = Stage == DemoStage.Degraded ? 0.71f : 0.92f,
                    SignalQualityEcg = Stage == DemoStage.Degraded ? 0.68f : 0.88f,
                    RespDeviceState = Stage == DemoStage.Unusable ? "DEGRADED" : "CONNECTED",
                    FallbackState = state,
                    FallbackReason = Stage == DemoStage.Good ? null : "demo injected fault",
                };
                return true;
            }
        }

        private const string CaptureArg = "--v03-capture=";
        private const string AutoQuitArg = "--v03-auto-quit";
        private const int FramesPerStage = 24;

        private readonly StubSource stub = new StubSource();
        private V03SceneAdapter adapter;
        private TargetLayerAdapter target;
        private ActualLayerAdapter actual;
        private RecoveryLayerAdapter recovery;
        private FallbackLayerAdapter fallback;
        private BackgroundPass background;
        private DemoStage stage = DemoStage.Good;
        private GUIStyle headerStyle;
        private GUIStyle monoStyle;
        private Texture2D clearTex;
        private string autoCaptureDir;
        private int autoFrameCounter;
        private bool autoDone;

        private void Awake()
        {
            adapter = gameObject.AddComponent<V03SceneAdapter>();
            target = gameObject.AddComponent<TargetLayerAdapter>();
            actual = gameObject.AddComponent<ActualLayerAdapter>();
            recovery = gameObject.AddComponent<RecoveryLayerAdapter>();
            fallback = gameObject.AddComponent<FallbackLayerAdapter>();
            background = gameObject.AddComponent<BackgroundPass>();
            adapter.ConfigureLayers(target, actual, recovery, fallback, background);
            adapter.Bind(stub);
            clearTex = new Texture2D(1, 1);
            clearTex.SetPixel(0, 0, new Color(0f, 0f, 0f, 0.55f));
            clearTex.Apply();

            foreach (string a in Environment.GetCommandLineArgs())
            {
                if (a.StartsWith(CaptureArg, StringComparison.Ordinal))
                    autoCaptureDir = a.Substring(CaptureArg.Length);
            }
            if (!string.IsNullOrEmpty(autoCaptureDir))
                StartCoroutine(AutoRun());
        }

        private IEnumerator AutoRun()
        {
            Directory.CreateDirectory(autoCaptureDir);
            yield return null; // 等待首帧 OnGUI 布局稳定

            DemoStage[] sequence =
            {
                DemoStage.Good, DemoStage.Degraded, DemoStage.Unusable,
                DemoStage.Disconnected, DemoStage.ResetSession
            };

            foreach (DemoStage s in sequence)
            {
                SetStage(s);
                for (int i = 0; i < FramesPerStage; i++)
                {
                    yield return new WaitForEndOfFrame();
                    CaptureFrame();
                    autoFrameCounter++;
                }
            }

            autoDone = true;
            Debug.Log("V03_DEGRADATION_DEMO_CAPTURE_DONE dir=" + autoCaptureDir
                + " frames=" + autoFrameCounter);

            if (Array.IndexOf(Environment.GetCommandLineArgs(), AutoQuitArg) >= 0)
            {
                yield return new WaitForSeconds(0.5f);
                Application.Quit(0);
            }
        }

        private void CaptureFrame()
        {
            var tex = ScreenCapture.CaptureScreenshotAsTexture();
            byte[] png = tex == null ? null : tex.EncodeToPNG();
            if (tex != null) DestroyImmediate(tex);
            if (png == null) return;
            string path = Path.Combine(autoCaptureDir,
                "frame_" + autoFrameCounter.ToString("D4") + ".png");
            File.WriteAllBytes(path, png);
        }

        private void Update()
        {
            // DISCONNECTED：只发一次无帧链路降级，随后保持
            if (stage == DemoStage.Disconnected && !disconnectedFired)
            {
                adapter.NotifyLinkDown(V03LinkState.Disconnected);
                disconnectedFired = true;
            }
            if (stage != DemoStage.Disconnected)
                disconnectedFired = false;
        }

        private bool disconnectedFired;

        private void SetStage(DemoStage next)
        {
            stage = next;
            stub.Stage = next;
            if (next == DemoStage.ResetSession)
            {
                // 会话边界重置：segment 变化 → ResetSession 解锁
                recovery.NotifySessionEnd();
                recovery.ResetSession();
                recovery.NotifySessionBegin();
                background.OnSessionSegmentChanged("demo_reset");
            }
        }

        private void OnGUI()
        {
            headerStyle ??= new GUIStyle(GUI.skin.label)
            {
                fontSize = 22, fontStyle = FontStyle.Bold, normal = { textColor = Color.white }
            };
            monoStyle ??= new GUIStyle(GUI.skin.label)
            {
                fontSize = 16, richText = true,
                normal = { textColor = new Color(0.92f, 0.96f, 1f) }
            };

            float w = Mathf.Min(720f, Screen.width - 40f);
            GUI.DrawTexture(new Rect(20f, 20f, w, Screen.height - 40f), clearTex);

            float y = 34f;
            GUI.Label(new Rect(40f, y, w - 40f, 32f),
                "U-02 Degradation Demo  |  Stage: " + StageTitle(stage), headerStyle);
            y += 46f;

            string[] labels = { "1 GOOD", "2 DEGRADED", "3 UNUSABLE", "4 DISCONNECTED", "5 ResetSession" };
            DemoStage[] vals =
            {
                DemoStage.Good, DemoStage.Degraded, DemoStage.Unusable,
                DemoStage.Disconnected, DemoStage.ResetSession
            };
            float bw = (w - 40f) / 5f;
            for (int i = 0; i < 5; i++)
            {
                if (GUI.Button(new Rect(40f + i * bw, y, bw - 6f, 38f), labels[i]))
                    SetStage(vals[i]);
            }
            y += 52f;

            string text =
                $"Target    phase=<b>{target.CurrentPhase}</b> progress={target.CurrentProgress:F3} behavior={target.LastBehavior}\n" +
                $"Actual    mode={actual.CurrentOpacityMode} opacity={actual.CurrentOpacity:F3} static={actual.IsStaticFrame} conf={actual.CurrentConfidence:F2}\n" +
                $"Recovery  locked=<b>{recovery.IsLocked}</b> out={recovery.CurrentOutputValue:F3} ignored={recovery.LockedFrameIgnoreCount}\n" +
                $"Fallback  marker={fallback.CurrentMarker} certainty={fallback.CurrentVisibleCertainty:F3} reason={fallback.CurrentReason}\n" +
                $"Background segChanges={background.SegmentChangeCount} (zero rhythm interface)\n" +
                $"Adapter   applied={adapter.AppliedFrameCount} rejected={adapter.RejectedFrameCount} quality={adapter.LastQualityState}";

            var lines = text.Split('\n');
            foreach (var line in lines)
            {
                GUI.Label(new Rect(40f, y, w - 40f, 26f), line, monoStyle);
                y += 28f;
            }

            y += 6f;
            string hint =
                "Observe: GOOD follows frames; DEGRADED low-certainty envelope;\n" +
                "UNUSABLE/DISCONNECTED freeze recovery lock (frames ignored);\n" +
                "ResetSession is the ONLY unlock path; background never carries rhythm.";
            GUI.Label(new Rect(40f, y, w - 40f, 80f), hint, monoStyle);
        }

        private static string StageTitle(DemoStage s)
        {
            switch (s)
            {
                case DemoStage.Good: return "GOOD (link normal)";
                case DemoStage.Degraded: return "DEGRADED (low certainty)";
                case DemoStage.Unusable: return "UNUSABLE (pause & lock)";
                case DemoStage.Disconnected: return "DISCONNECTED (no frame path)";
                default: return "RESET SESSION (unlock)";
            }
        }

        private void OnDestroy()
        {
            if (clearTex != null) DestroyImmediate(clearTex);
        }
    }
}
