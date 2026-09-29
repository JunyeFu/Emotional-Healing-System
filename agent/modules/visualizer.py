"""
SRP Live Visualizer v1.1 — 6-Panel 4-Dimension Dashboard
==========================================================
UDP listener + real-time 6-panel matplotlib dashboard.

One chart per physiological signal domain, each with its independent score.
Weather composite panel integrates all 4 scores.

Usage:
    # Terminal 1: start pipeline
    python main.py --weather storm --duration 0

    # Terminal 2: start dashboard
    python visualizer.py

    python visualizer.py --port 5005 --history 25 --fps 12
"""

import argparse
import json
import queue
import socket
import threading
import time
from collections import deque

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────

UDP_HOST = "127.0.0.1"
UDP_PORT = 5005
HISTORY_SECONDS = 25
TARGET_FPS = 12
MAX_SAMPLES = 3000

# ── Color palette ─────────────────────────────────────────────────────────────

C_DARK_BG = "#0f0f1a"
C_PANEL_BG = "#161625"
C_GRID = "#1e1e35"
C_TEXT = "#b0b0c8"
C_TEXT_DIM = "#686880"
C_ACCENT = "#5b9bd5"

WEATHER_COLORS = {"storm": "#6b8fce", "heat": "#e07b4c",
                  "snow": "#a8c8e8", "fade": "#9b8ec4"}
WEATHER_EMOJI = {"storm": "Storm", "heat": "Heat", "snow": "Snow", "fade": "Fade"}
PHASE_COLORS = {"inhale": "#5da37c", "exhale": "#c47b5a", "hold": "#d4a843"}

SCORE_COLORS = {
    "breath_sync": "#5da37c", "breath_depth": "#8bcf8b",
    "hrv_coherence": "#6baed6", "eda_calm": "#c09cd8",
}
SCORE_LABELS = {
    "breath_sync": "Breath Sync", "breath_depth": "Breath Depth",
    "hrv_coherence": "HRV Coherence", "eda_calm": "EDA Calm",
}


class UDPListener(threading.Thread):
    """Background thread: continuously receives UDP JSON frames."""

    def __init__(self, host=UDP_HOST, port=UDP_PORT, data_queue=None):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.queue = data_queue or queue.Queue()
        self.running = True
        self.frame_count = 0

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.settimeout(0.5)

        while self.running:
            try:
                data, _ = sock.recvfrom(65535)
                msg = json.loads(data.decode("utf-8"))
                self.queue.put(msg)
                self.frame_count += 1
            except socket.timeout:
                continue
            except (json.JSONDecodeError, OSError):
                continue
        sock.close()

    def stop(self):
        self.running = False


class Dashboard:
    """6-panel real-time physiological monitoring dashboard."""

    def __init__(self, history_seconds=HISTORY_SECONDS):
        self.history = history_seconds

        # Data buffers
        self.ts: deque = deque(maxlen=MAX_SAMPLES)
        self.respiration_raw: deque = deque(maxlen=MAX_SAMPLES)
        self.breath_phase: deque = deque(maxlen=MAX_SAMPLES)
        self.hr: deque = deque(maxlen=MAX_SAMPLES)
        self.rmssd: deque = deque(maxlen=MAX_SAMPLES)
        self.breath_rate: deque = deque(maxlen=MAX_SAMPLES)
        self.breath_amplitude: deque = deque(maxlen=MAX_SAMPLES)
        self.breath_regularity: deque = deque(maxlen=MAX_SAMPLES)
        self.eda_tonic: deque = deque(maxlen=MAX_SAMPLES)

        # Latest scores
        self.scores: dict = {}
        self.weather: dict = {}
        self.guidance_prompt: str = ""

        self._setup_figure()

    def _setup_figure(self):
        plt.rcParams.update({
            "figure.facecolor": C_DARK_BG,
            "axes.facecolor": C_PANEL_BG,
            "axes.edgecolor": C_GRID,
            "axes.labelcolor": C_TEXT,
            "text.color": C_TEXT,
            "xtick.color": C_TEXT_DIM,
            "ytick.color": C_TEXT_DIM,
            "grid.color": C_GRID,
            "font.size": 8,
        })

        self.fig = plt.figure(figsize=(20, 11), dpi=100)
        self.fig.suptitle("SRP  Multi-Signal Physiological Dashboard",
                          fontsize=15, color="#d0d0e8", fontweight="bold", y=0.98)

        gs = GridSpec(2, 3, figure=self.fig, hspace=0.42, wspace=0.32,
                      left=0.05, right=0.97, top=0.93, bottom=0.05)

        self.ax_breath = self.fig.add_subplot(gs[0, 0])   # Panel 1
        self.ax_hr = self.fig.add_subplot(gs[0, 1])       # Panel 2
        self.ax_hrv = self.fig.add_subplot(gs[0, 2])      # Panel 3
        self.ax_quality = self.fig.add_subplot(gs[1, 0])  # Panel 4
        self.ax_eda = self.fig.add_subplot(gs[1, 1])      # Panel 5
        self.ax_weather = self.fig.add_subplot(gs[1, 2])  # Panel 6

        # ── Panel 1: Respiration Waveform ──────────────────────────────────
        self.ax_breath.set_title("1  Respiration Waveform", fontsize=10,
                                 color=C_ACCENT, fontweight="bold")
        self.ax_breath.set_ylabel("Amplitude", fontsize=7)
        self.ax_breath.set_ylim(-0.8, 0.8)
        self.ax_breath.grid(True, alpha=0.25, linewidth=0.5)
        (self.l_breath,) = self.ax_breath.plot([], [], color="#5da37c",
                                                linewidth=1.0, alpha=0.9)
        self.breath_score_text = self.ax_breath.text(
            0.01, 0.94, "", transform=self.ax_breath.transAxes,
            fontsize=8, color="#a0d0b0", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a2a1a", edgecolor="#2a4a2a", alpha=0.8))

        # ── Panel 2: Heart Rate ────────────────────────────────────────────
        self.ax_hr.set_title("2  Heart Rate (HR)", fontsize=10,
                             color=C_ACCENT, fontweight="bold")
        self.ax_hr.set_ylabel("BPM", fontsize=7)
        self.ax_hr.set_ylim(40, 120)
        self.ax_hr.grid(True, alpha=0.25, linewidth=0.5)
        (self.l_hr,) = self.ax_hr.plot([], [], color="#e07050",
                                        linewidth=1.3)
        self.hr_score_text = self.ax_hr.text(
            0.01, 0.94, "", transform=self.ax_hr.transAxes,
            fontsize=8, color="#e0a090", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#2a1a1a", edgecolor="#4a2a2a", alpha=0.8))

        # ── Panel 3: HRV Recovery ─────────────────────────────────────────
        self.ax_hrv.set_title("3  HRV Coherence (RMSSD)", fontsize=10,
                              color=C_ACCENT, fontweight="bold")
        self.ax_hrv.set_ylabel("RMSSD (ms)", fontsize=7)
        self.ax_hrv.set_ylim(0, 100)
        self.ax_hrv.grid(True, alpha=0.25, linewidth=0.5)
        (self.l_rmssd,) = self.ax_hrv.plot([], [], color="#6baed6",
                                            linewidth=1.3)
        self.hrv_score_text = self.ax_hrv.text(
            0.01, 0.94, "", transform=self.ax_hrv.transAxes,
            fontsize=8, color="#a0c8e8", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a1a2a", edgecolor="#2a3a5a", alpha=0.8))

        # ── Panel 4: Breath Depth ────────────────────────────────
        self.ax_quality.set_title("4  Breath Depth", fontsize=10,
                                  color=C_ACCENT, fontweight="bold")
        self.ax_quality.set_ylabel("Amplitude", fontsize=7)
        self.ax_quality.set_ylim(0, 1.0)
        self.ax_quality.grid(True, alpha=0.25, linewidth=0.5)
        (self.l_amp,) = self.ax_quality.plot([], [], color="#8bcf8b",
                                              linewidth=1.2, alpha=0.9, label="Amplitude")
        self.quality_score_text = self.ax_quality.text(
            0.01, 0.94, "", transform=self.ax_quality.transAxes,
            fontsize=8, color="#c0d0c0", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a2a1a", edgecolor="#2a4a2a", alpha=0.8))

        # ── Panel 5: EDA Calm ─────────────────────────────────
        self.ax_eda.set_title("5  EDA Calm (Skin Conductance)", fontsize=10,
                              color=C_ACCENT, fontweight="bold")
        self.ax_eda.set_ylabel("EDA Tonic (μS)", fontsize=7, color="#c09cd8")
        self.ax_eda.set_ylim(3, 16)
        self.ax_eda.grid(True, alpha=0.25, linewidth=0.5)
        (self.l_eda,) = self.ax_eda.plot([], [], color="#c09cd8",
                                          linewidth=1.2, alpha=0.9)
        self.eda_score_text = self.ax_eda.text(
            0.01, 0.94, "", transform=self.ax_eda.transAxes,
            fontsize=8, color="#d0c0e0", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a1a2a", edgecolor="#3a2a5a", alpha=0.8))

        # ── Panel 6: Weather Composite ─────────────────────────────────────
        self.ax_weather.set_title("6  Weather Composite", fontsize=10,
                                  color=C_ACCENT, fontweight="bold")
        self.ax_weather.axis("off")

        # Weather header (large text)
        self.weather_header = self.ax_weather.text(
            0.5, 0.90, "", transform=self.ax_weather.transAxes,
            fontsize=22, ha="center", va="top", fontweight="bold")

        self.weather_composite_text = self.ax_weather.text(
            0.5, 0.72, "", transform=self.ax_weather.transAxes,
            fontsize=13, ha="center", va="top", color=C_TEXT)

        self.weather_trend_text = self.ax_weather.text(
            0.5, 0.62, "", transform=self.ax_weather.transAxes,
            fontsize=10, ha="center", va="top")

        # Guidance prompt
        self.guidance_text = self.ax_weather.text(
            0.5, 0.48, "", transform=self.ax_weather.transAxes,
            fontsize=10, ha="center", va="center", color="#e0d890",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a0a", edgecolor="#3a3a1a", alpha=0.8))

        # 8 score contribution bars
        self.score_bars = None

        # artists for blit
        self._artists = [
            self.l_breath, self.l_hr, self.l_rmssd,
            self.l_amp, self.l_eda,
            self.breath_score_text, self.hr_score_text, self.hrv_score_text,
            self.quality_score_text, self.eda_score_text,
            self.weather_header, self.weather_composite_text,
            self.weather_trend_text, self.guidance_text,
        ]

    def feed(self, msg: dict):
        """Parse one UDP JSON message into buffers."""
        now = time.time()
        self.ts.append(now)

        breath = msg.get("breath", {})
        cardiac = msg.get("cardiac", {})
        eda = msg.get("eda", {})
        scores = msg.get("scores", {})
        weather = msg.get("weather", {})
        guidance = msg.get("guidance", {})

        self.respiration_raw.append(breath.get("depth", 0))
        self.breath_phase.append(breath.get("phase", "exhale"))
        self.hr.append(cardiac.get("hr", 0))
        self.rmssd.append(cardiac.get("rmssd", 0))
        self.breath_rate.append(breath.get("rate", 0))
        self.breath_amplitude.append(breath.get("amplitude", 0))
        self.breath_regularity.append(breath.get("regularity_raw", 0))
        self.eda_tonic.append(eda.get("tonic", 0))

        self.scores = scores
        self.weather = weather
        self.calm_index = msg.get("calm_index", sum(scores.values()) / max(len(scores), 1) if scores else 50)
        self.guidance_prompt = guidance.get("prompt", "")

    def update(self, frame):
        """matplotlib FuncAnimation callback."""
        ts = list(self.ts)
        if len(ts) < 2:
            return self._artists

        # Convert to relative seconds from start
        t_rel = [t - ts[0] for t in ts]
        t_end = t_rel[-1]
        t_start = max(0, t_end - self.history)

        def set_xlim(ax):
            ax.set_xlim(t_start, t_end + 1)

        # Panel 1: Respiration Waveform
        self.l_breath.set_data(t_rel, list(self.respiration_raw))
        set_xlim(self.ax_breath)
        bs = self.scores.get("breath_sync", 0)
        self.breath_score_text.set_text(f" Breath Sync: {bs:.0f}/100 ")

        # Panel 2: Heart Rate
        self.l_hr.set_data(t_rel, list(self.hr))
        set_xlim(self.ax_hr)
        self.hr_score_text.set_text(f" HR: {self.hr[-1]:.0f} BPM ")

        # Panel 3: HRV Coherence (RMSSD)
        self.l_rmssd.set_data(t_rel, list(self.rmssd))
        set_xlim(self.ax_hrv)
        hv = self.scores.get("hrv_coherence", 0)
        self.hrv_score_text.set_text(f" HRV Coherence: {hv:.0f}/100 ")

        # Panel 4: Breath Depth (Amplitude)
        self.l_amp.set_data(t_rel, list(self.breath_amplitude))
        set_xlim(self.ax_quality)
        bd = self.scores.get("breath_depth", 0)
        self.quality_score_text.set_text(f" Breath Depth: {bd:.0f}/100 ")

        # Panel 5: EDA Calm
        self.l_eda.set_data(t_rel, list(self.eda_tonic))
        set_xlim(self.ax_eda)
        ec = self.scores.get("eda_calm", 0)
        self.eda_score_text.set_text(f" EDA Calm: {ec:.0f}/100 ")

        # Panel 6: Weather Composite
        wt = self.weather.get("type", "storm")
        wi = self.weather.get("intensity", 0.5)
        trend = self.weather.get("trend", "stable")
        dominant = self.weather.get("dominant", "")
        calm = getattr(self, "calm_index", 50)

        trend_symbol = {"weakening": "  Clear", "stable": "  Stable",
                        "intensifying": "  Storming"}
        trend_color = {"weakening": "#5da37c", "stable": "#f0c05a",
                       "intensifying": "#e07050"}

        color = WEATHER_COLORS.get(wt, "#e0e0f0")
        self.weather_header.set_text(f"{WEATHER_EMOJI.get(wt, wt)}")
        self.weather_header.set_color(color)

        self.weather_composite_text.set_text(
            f"Calm Index: {calm:.0f}/100   Intensity: {wi:.2f}   Dominant: {dominant}")
        self.weather_trend_text.set_text(
            f"{trend_symbol.get(trend, trend)}   Guidance: {self.guidance_prompt[:30]}")
        self.weather_trend_text.set_color(trend_color.get(trend, C_TEXT))

        self.guidance_text.set_text(f"  {self.guidance_prompt}  "
                                    if self.guidance_prompt else "")

        # Redraw score bar chart in panel 6
        self._draw_score_bars()

        return self._artists

    def _draw_score_bars(self):
        """Draw horizontal bar chart of 8 score contributions in Panel 6."""
        if not self.scores:
            return

        # Remove old bars and labels from panel 6
        for child in list(self.ax_weather.get_children()):
            gid = child.get_gid() if hasattr(child, 'get_gid') else None
            if gid and gid.startswith("score_"):
                child.remove()

        labels = []
        values = []
        colors = []
        for key in ["breath_sync", "breath_depth", "hrv_coherence", "eda_calm"]:
            labels.append(SCORE_LABELS.get(key, key))
            values.append(self.scores.get(key, 50))
            colors.append(SCORE_COLORS.get(key, C_ACCENT))

        # Sort by value descending
        sorted_idx = np.argsort(values)
        labels = [labels[i] for i in sorted_idx]
        values = [values[i] for i in sorted_idx]
        colors = [colors[i] for i in sorted_idx]

        n = len(labels)
        bar_height = 0.025
        y_start = 0.32
        y_positions = [y_start - i * bar_height * 1.5 for i in range(n)]

        for i, (label, val, color) in enumerate(zip(labels, values, colors)):
            y = y_positions[i]
            # Background
            self.ax_weather.barh(y, 100, height=bar_height * 0.8, left=0,
                                 color=C_GRID,
                                 transform=self.ax_weather.transAxes,
                                 gid=f"score_bar_bg_{i}")
            # Value bar
            self.ax_weather.barh(y, val, height=bar_height * 0.8, left=0,
                                 color=color,
                                 transform=self.ax_weather.transAxes,
                                 gid=f"score_bar_{i}")
            # Label
            self.ax_weather.text(0.01, y, f"{label}", fontsize=6,
                                 color=C_TEXT, va="center",
                                 transform=self.ax_weather.transAxes,
                                 gid=f"score_label_{i}")
            # Value
            self.ax_weather.text(0.97, y, f"{val:.0f}", fontsize=6,
                                 color="#e0e0f0", va="center", ha="right",
                                 transform=self.ax_weather.transAxes,
                                 gid=f"score_val_{i}")


# ── Direct Pipeline Runner (--direct mode) ──────────────────────────────────

class DirectPipeline(threading.Thread):
    """Runs the mock pipeline internally and pushes UDP-format messages to queue."""

    def __init__(self, weather: str, data_queue: queue.Queue):
        super().__init__(daemon=True)
        self.weather = weather
        self.queue = data_queue
        self.running = True

    def run(self):
        import sys, os
        _root = os.path.dirname(os.path.abspath(__file__))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        import importlib

        mock_data = importlib.import_module("01-数据采集.mock_data")
        sig_mod = importlib.import_module("02-信号处理.signal_pipeline")
        score_mod = importlib.import_module("02-信号处理.scoring_model")
        udp_mod = importlib.import_module("05-通信协议.udp_sender")

        cfg = mock_data.MockConfig.for_weather(self.weather)
        generator = mock_data.generate_frames(duration=0, cfg=cfg)  # infinite
        pipeline = sig_mod.SignalPipeline()
        scorer = score_mod.ScoringModel(
            cfg=score_mod.ScoringConfig.for_weather(self.weather))

        for frame in generator:
            if not self.running:
                break
            processed = pipeline.feed(
                frame.timestamp, frame.respiration_raw, frame.ecg_raw,
                frame.eda_raw, frame.acc_magnitude, frame.temp_skin,
                ecg_samples=getattr(frame, "ecg_samples", None))
            if processed is None:
                continue
            score = scorer.score(processed,
                                 breath_phase=frame.breath_phase,
                                 guidance_prompt=frame.guidance_prompt,
                                 weather_type=frame.weather_type)
            msg = udp_mod.build_message(score.to_dict())
            self.queue.put(msg)
            time.sleep(0.1)  # 10 Hz

    def stop(self):
        self.running = False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SRP 6-Panel Live Dashboard")
    parser.add_argument("--host", default=UDP_HOST)
    parser.add_argument("--port", type=int, default=UDP_PORT)
    parser.add_argument("--history", type=int, default=HISTORY_SECONDS)
    parser.add_argument("--fps", type=int, default=TARGET_FPS)
    parser.add_argument("--udp", action="store_true",
                        help="Use UDP mode (needs main.py running separately)")
    parser.add_argument("--weather", type=str, default="storm",
                        choices=["storm", "heat", "snow", "fade"],
                        help="Weather type (default: storm)")
    args = parser.parse_args()

    data_queue = queue.Queue()

    if args.udp:
        runner = UDPListener(args.host, args.port, data_queue)
        runner.start()
        print(f"SRP 6-Panel Dashboard — UDP Mode ({args.host}:{args.port})")
        print(f"  Start pipeline in another terminal:")
        print(f"    python main.py --weather {args.weather} --duration 0")
    else:
        runner = DirectPipeline(args.weather, data_queue)
        runner.start()
        print(f"SRP 6-Panel Dashboard — Direct Mode ({args.weather})")
        print(f"  Pipeline running internally, no UDP needed.")

    dashboard = Dashboard(history_seconds=args.history)

    def drain_queue():
        try:
            for _ in range(50):
                msg = data_queue.get_nowait()
                dashboard.feed(msg)
        except queue.Empty:
            pass

    ani = animation.FuncAnimation(
        dashboard.fig, dashboard.update,
        interval=1000 // args.fps, blit=False, cache_frame_data=False,
    )

    _timer = dashboard.fig.canvas.new_timer(interval=1000 // args.fps)
    _timer.add_callback(drain_queue)

    print(f"  History: {args.history}s | Refresh: {args.fps} FPS")
    print(f"  Close window or Ctrl+C to exit.\n")

    _timer.start()
    plt.show()

    runner.stop()
    count = getattr(runner, "frame_count", 0)
    print(f"\nDone. Frames received: {count}")


if __name__ == "__main__":
    main()
