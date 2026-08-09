"""
SRP Mock Data Generator v0.4 — Physiologically-grounded synthetic signals.

Generates simulated multi-sensor physiological data at 10 Hz for pipeline
development before real Polar H10 + respiratory belt + EDA sensors are available.

Physiological basis (see srp参考文献/06-scoring-model-evidence/README.md):
  - RSA (Respiratory Sinus Arrhythmia): HR ↑ during inhale, ↓ during exhale.
    Primary mechanism behind HRV. Amplitude 5–15 bpm in young adults.
  - Resonance frequency breathing: ~0.1 Hz (6 breaths/min) maximizes vagal tone.
    (Lehrer 2013; McCraty 2022)
  - Asymmetric I:E ratio: exhale > inhale activates vagus nerve.
    Pranayama RCT: I:E = 1:1.5–2.0 independently increases logRMSSD (p<0.01).
  - EDA phasic SCR: exponential decay τ ≈ 2–3 s. 1–3 peaks/min at rest.
    (Nagai et al. 2019 — GSR biofeedback reduces sympathetic arousal)
  - Peripheral temperature: vasodilation during relaxation → +0.5 °C over 5 min.

Output (per frame, 10 Hz):
  - Respiration waveform (asymmetric I:E, weather-specific pattern)
  - ECG-like signal with RSA (variable R–R interval coupled to breathing)
  - EDA (tonic drift + phasic SCR with exponential decay)
  - ACC magnitude (body motion, settling-down envelope)
  - Skin temperature (slow warming + respiratory oscillation)
  - Breath phase classification (inhale / hold / exhale)
  - Guidance prompt text
"""

import time
import math
from typing import Generator
from dataclasses import dataclass
import numpy as np


# ── Literature-based physiological ranges (young adults, 18–25) ───────────
# HR rest: 60–80 bpm   |  HR mild stress: 80–100 bpm
# RR rest: 12–18 br/min | RR slow breathing: 6–10 br/min
# RMSSD rest: 30–60 ms  | RMSSD stress: 15–30 ms
# EDA tonic rest: 2–10 μS | EDA tonic stress: 10–25 μS
# SCR rate rest: 1–3/min  | SCR rate stress: 5–15/min
# SCR amplitude: 0.2–2.0 μS | SCR decay τ: 2–3 s
# RSA amplitude: 5–15 bpm (young adults)
# Temp peripheral: 32–35 °C (rest), 30–33 °C (stress vasoconstriction)
# ACC rest seated: 0.01–0.05 g | ACC fidgeting: 0.05–0.15 g

# ── 4-Dimension Literature Anchors ────────────────────────────────────────
# See: srp参考文献/06-scoring-model-evidence/README.md (16 SCI Q1 papers)
#
# Dimension 1 — breath_sync:     RR tracking accuracy    呼吸→副交感
# Dimension 2 — breath_depth:    Amplitude quality       呼吸→副交感
# Dimension 3 — hrv_coherence:   RMSSD recovery           副交感(迷走)
# Dimension 4 — eda_calm:        SCL decrease             交感(皮肤电)

# ── Weather-specific Breathing Configs ────────────────────────────────────
# Each weather config groups parameters by the 4 physiological dimensions.
# Flat keys maintained for backward compatibility.

WEATHER_BREATHING_CONFIG: dict[str, dict] = {
    "storm": {
        # Anxiety → 4-2-6 box breathing (resonance frequency ~5 bpm)
        # ── dim1: breath_sync ──
        "breath_rate_hz": 1.0 / 12.0,
        "inhale_duration": 4.0,
        "hold_duration": 2.0,
        "exhale_duration": 6.0,
        # ── dim2: breath_depth ──
        "breath_amplitude": 0.5,
        # ── dim3: hrv_coherence ──
        "hr_start": 100, "hr_end": 60,  # elevated → calm
        "hr_trend_duration": 120.0,
        "rsa_amplitude": 8.0,       # bpm swing, lower RSA under stress
        # ── dim4: eda_calm ──
        "eda_tonic_base": 10.0,     # elevated sympathetic tone
        "scr_rate": 4.0,            # SCR peaks/min (moderate stress)
        # ── auxiliary ──
        "acc_rest_level": 0.06,     # slightly fidgety
        # ── dimension presets (scoring targets) ──
        "dim_targets": {"breath_sync": 5.0, "breath_depth": 0.50,
                        "hrv_coherence": 40.0, "eda_calm": 7.0},
    },
    "heat": {
        # Irritability → 3-6 long-exhale cooling (I:E = 1:2)
        # ── dim1: breath_sync ──
        "breath_rate_hz": 1.0 / 9.0,
        "inhale_duration": 3.0,
        "hold_duration": 0.0,
        "exhale_duration": 6.0,
        # ── dim2: breath_depth ──
        "breath_amplitude": 0.6,
        # ── dim3: hrv_coherence ──
        "hr_start": 105, "hr_end": 60,  # irritable → calm
        "hr_trend_duration": 120.0,
        "rsa_amplitude": 10.0,
        # ── dim4: eda_calm ──
        "eda_tonic_base": 14.0,     # high sympathetic activation
        "scr_rate": 6.0,
        # ── auxiliary ──
        "acc_rest_level": 0.08,     # agitated
        # ── dimension presets ──
        "dim_targets": {"breath_sync": 6.67, "breath_depth": 0.60,
                        "hrv_coherence": 45.0, "eda_calm": 9.0},
    },
    "snow": {
        # Low mood → 5-5 steady activating breath (symmetric)
        # ── dim1: breath_sync ──
        "breath_rate_hz": 1.0 / 10.0,
        "inhale_duration": 5.0,
        "hold_duration": 0.0,
        "exhale_duration": 5.0,
        # ── dim2: breath_depth ──
        "breath_amplitude": 0.4,
        # ── dim3: hrv_coherence ──
        "hr_start": 75, "hr_end": 55,  # low → gently activated
        "hr_trend_duration": 120.0,
        "rsa_amplitude": 12.0,      # healthy RSA
        # ── dim4: eda_calm ──
        "eda_tonic_base": 5.0,      # low arousal
        "scr_rate": 2.0,
        # ── auxiliary ──
        "acc_rest_level": 0.02,     # still
        # ── dimension presets ──
        "dim_targets": {"breath_sync": 6.0, "breath_depth": 0.40,
                        "hrv_coherence": 55.0, "eda_calm": 4.0},
    },
    "fade": {
        # Loneliness → 3.5-4.5 free natural breathing
        # ── dim1: breath_sync ──
        "breath_rate_hz": 1.0 / 8.0,
        "inhale_duration": 3.5,
        "hold_duration": 0.0,
        "exhale_duration": 4.5,
        # ── dim2: breath_depth ──
        "breath_amplitude": 0.35,
        # ── dim3: hrv_coherence ──
        "hr_start": 80, "hr_end": 55,  # lonely → companion calm
        "hr_trend_duration": 120.0,
        "rsa_amplitude": 14.0,      # strongest RSA (relaxed)
        # ── dim4: eda_calm ──
        "eda_tonic_base": 6.0,
        "scr_rate": 1.5,
        # ── auxiliary ──
        "acc_rest_level": 0.03,
        # ── dimension presets ──
        "dim_targets": {"breath_sync": 7.5, "breath_depth": 0.35,
                        "hrv_coherence": 60.0, "eda_calm": 4.5},
    },
}


# ── Configuration ─────────────────────────────────────────────────────────

@dataclass
class MockConfig:
    """Configurable parameters for physiologically-grounded mock signals.

    Parameters are organized by the 4 physiological dimensions:
      dim1 — breath_sync:    RR timing pattern (rate, I:E ratio, hold)
      dim2 — breath_depth:   Amplitude quality
      dim3 — hrv_coherence:  HR + RSA → RMSSD
      dim4 — eda_calm:       Skin conductance (tonic + phasic SCR)

    Default values represent a healthy resting young adult.
    """
    # ── dim1: breath_sync (呼吸→副交感, RR tracking) ──
    breath_rate_hz: float = 0.2          # 12 breaths/min (resting)
    inhale_duration: float = 2.0
    hold_duration: float = 0.0
    exhale_duration: float = 3.0

    # ── dim2: breath_depth (呼吸→副交感, amplitude) ──
    breath_amplitude: float = 0.5
    breath_noise_std: float = 0.02

    # ── dim3: hrv_coherence (副交感·迷走, RMSSD via RSA) ──
    hr_start: float = 100.0               # HR at session start (stress state)
    hr_end: float = 60.0                  # HR target after calming down
    hr_trend_duration: float = 120.0      # seconds for linear HR downward trend
    rsa_amplitude: float = 10.0          # bpm swing per breath cycle
    rsa_lag: float = 0.8                 # seconds, HR lags respiration peak
    ecg_noise_std: float = 0.01

    @property
    def hr_bpm(self) -> float:
        """Backward-compat: mid-trend HR (~80 bpm)."""
        return (self.hr_start + self.hr_end) / 2

    # ── dim4: eda_calm (交感·皮肤电, SCL decrease) ──
    eda_tonic_base: float = 8.0
    scr_rate: float = 2.0                # spontaneous SCR peaks/min
    scr_amplitude: float = 0.8           # μS peak height
    scr_decay_tau: float = 2.5           # seconds, exponential decay
    eda_noise_std: float = 0.03

    # ── Auxiliary (not scored, for realism) ──
    acc_rest_level: float = 0.04
    acc_motion_rate: float = 1.5         # movement bursts/min
    acc_burst_amplitude: float = 0.3     # g peak
    acc_noise_std: float = 0.005
    temp_base: float = 34.0
    temp_warming_total: float = 0.5      # °C rise over 5 min relaxation
    temp_warming_tau: float = 120.0      # seconds, time constant
    temp_noise_std: float = 0.02

    # Output
    frame_rate: float = 10.0

    # Weather simulation
    weather_type: str = "clear"
    weather_intensity_base: float = 0.5

    @classmethod
    def for_weather(cls, weather_type: str, intensity: float = 0.5) -> "MockConfig":
        params = WEATHER_BREATHING_CONFIG.get(weather_type,
                                              WEATHER_BREATHING_CONFIG["storm"])
        return cls(
            breath_rate_hz=params["breath_rate_hz"],
            inhale_duration=params["inhale_duration"],
            hold_duration=params["hold_duration"],
            exhale_duration=params["exhale_duration"],
            hr_start=params.get("hr_start", 100),
            hr_end=params.get("hr_end", 60),
            hr_trend_duration=params.get("hr_trend_duration", 120.0),
            rsa_amplitude=params["rsa_amplitude"],
            breath_amplitude=params["breath_amplitude"],
            eda_tonic_base=params["eda_tonic_base"],
            scr_rate=params["scr_rate"],
            acc_rest_level=params["acc_rest_level"],
            weather_type=weather_type,
            weather_intensity_base=intensity,
        )

    def get_dim_targets(self) -> dict[str, float]:
        """Return 4-dimension scoring targets for this config's weather.

        Maps to the dimension_spec.WEATHER_DIMENSION_PRESETS targets.
        """
        params = WEATHER_BREATHING_CONFIG.get(
            self.weather_type, WEATHER_BREATHING_CONFIG["storm"])
        return params.get("dim_targets", {
            "breath_sync": 6.0, "breath_depth": 0.5,
            "hrv_coherence": 50.0, "eda_calm": 5.0,
        })

    def get_dim_params(self) -> dict:
        """Return dimension-grouped parameter summary for logging."""
        return {
            "breath_sync": {
                "rate_hz": self.breath_rate_hz,
                "inhale_s": self.inhale_duration,
                "hold_s": self.hold_duration,
                "exhale_s": self.exhale_duration,
                "i_e_ratio": f"{self.inhale_duration:.1f}:{self.exhale_duration:.1f}",
            },
            "breath_depth": {
                "amplitude": self.breath_amplitude,
            },
            "hrv_coherence": {
                "hr_start": self.hr_start,
                "hr_end": self.hr_end,
                "hr_trend_s": self.hr_trend_duration,
                "rsa_amplitude_bpm": self.rsa_amplitude,
            },
            "eda_calm": {
                "tonic_base_us": self.eda_tonic_base,
                "scr_per_min": self.scr_rate,
            },
        }


# ── Dimension-aware Simulation Functions ──────────────────────────────────
#
# Each function simulates one physiological dimension's raw data output.
# These are the public API for dimension-specific testing and debugging.

def sim_dim_breath_sync_params(cfg: MockConfig) -> dict:
    """Extract breath_sync dimension params from config.

    Returns dict with: breath_rate_hz, inhale_duration, hold_duration,
    exhale_duration, total_cycle_duration, i_e_ratio.
    """
    total = cfg.inhale_duration + cfg.hold_duration + cfg.exhale_duration
    return {
        "breath_rate_hz": cfg.breath_rate_hz,
        "inhale_duration": cfg.inhale_duration,
        "hold_duration": cfg.hold_duration,
        "exhale_duration": cfg.exhale_duration,
        "total_cycle_duration": total,
        "i_e_ratio": cfg.inhale_duration / max(cfg.exhale_duration, 0.1),
        "ans_branch": "呼吸→副交感",
        "gold_standard": "RR tracking accuracy (bpm)",
    }


def sim_dim_breath_depth_params(cfg: MockConfig) -> dict:
    """Extract breath_depth dimension params from config."""
    return {
        "breath_amplitude": cfg.breath_amplitude,
        "breath_noise_std": cfg.breath_noise_std,
        "ans_branch": "呼吸→副交感",
        "gold_standard": "Amplitude / RSA magnitude",
    }


def sim_dim_hrv_coherence_params(cfg: MockConfig) -> dict:
    """Extract hrv_coherence dimension params from config."""
    mid_hr = cfg.hr_bpm  # midpoint for rough RMSSD estimate
    return {
        "hr_start": cfg.hr_start,
        "hr_end": cfg.hr_end,
        "hr_trend_s": cfg.hr_trend_duration,
        "rsa_amplitude_bpm": cfg.rsa_amplitude,
        "rsa_lag_s": cfg.rsa_lag,
        "expected_rmssd_range": f"{max(15, mid_hr*0.3 - 10):.0f}-{mid_hr*0.3 + 20:.0f} ms",
        "ans_branch": "副交感(迷走)",
        "gold_standard": "RMSSD (ms)",
    }


def sim_dim_eda_calm_params(cfg: MockConfig) -> dict:
    """Extract eda_calm dimension params from config."""
    return {
        "tonic_base_us": cfg.eda_tonic_base,
        "scr_rate_per_min": cfg.scr_rate,
        "scr_amplitude_us": cfg.scr_amplitude,
        "scr_decay_tau_s": cfg.scr_decay_tau,
        "ans_branch": "交感(皮肤电)",
        "gold_standard": "SCL decrease (μS)",
    }


def sim_all_dim_params(cfg: MockConfig) -> dict:
    """Get combined 4-dimension simulation parameters."""
    return {
        "breath_sync": sim_dim_breath_sync_params(cfg),
        "breath_depth": sim_dim_breath_depth_params(cfg),
        "hrv_coherence": sim_dim_hrv_coherence_params(cfg),
        "eda_calm": sim_dim_eda_calm_params(cfg),
    }


# ── Respiration: Asymmetric I:E waveform ─────────────────────────────────
#
# Uses a phase accumulator to produce smooth, physiologically realistic
# breathing waveforms with configurable inhale:exhale ratio.
#
# Inhale:  sin-based rise from -amp to +amp (concave-up → convex)
# Hold:    flat plateau at +amp (used in box breathing)
# Exhale:  cos-based fall from +amp to -amp (typically longer than inhale)
#
# I:E ratio = inhale_duration : exhale_duration
# For vagal activation, exhale > inhale (typical I:E = 1:1.5 to 1:2).

def _respiration(t: float, cfg: MockConfig) -> float:
    """Asymmetric respiration waveform with configurable I:E ratio."""
    cycle = cfg.inhale_duration + cfg.hold_duration + cfg.exhale_duration
    if cycle <= 0:
        return 0.0

    phase = (t % cycle) / cycle  # 0..1 within current cycle
    amp = cfg.breath_amplitude

    inhale_frac = cfg.inhale_duration / cycle
    hold_frac = cfg.hold_duration / cycle
    # exhale_frac = cfg.exhale_duration / cycle  # remainder

    if phase < inhale_frac:
        # Inhale: -amp → +amp using sine quarter-wave
        # sin(π/2 * x) maps [0, 1] smoothly to [0, 1]
        progress = phase / inhale_frac
        val = -amp + 2.0 * amp * math.sin(math.pi * 0.5 * progress)
    elif phase < inhale_frac + hold_frac:
        # Hold: plateau at +amp
        val = +amp
    else:
        # Exhale: +amp → -amp using cosine quarter-wave
        exhale_start = inhale_frac + hold_frac
        exhale_frac = 1.0 - exhale_start
        progress = (phase - exhale_start) / exhale_frac
        val = amp * math.cos(math.pi * 0.5 * progress)

    # Add physiological tremor noise
    val += np.random.normal(0, cfg.breath_noise_std)
    return val


# ── ECG with Respiratory Sinus Arrhythmia ────────────────────────────────
#
# RSA: HR increases during inhalation, decreases during exhalation.
# We model this by making instantaneous HR a function of the respiration
# waveform at a short lag (HR lags respiration peak by ~0.5–1.5 s).
#
# R–R interval at time t:
#   rr_interval(t) = 60 / (base_hr + rsa_amplitude * resp(t - rsa_lag))
#
# QRS complex: Gaussian peak at ~30% of each cardiac cycle.
# T-wave: smaller Gaussian at ~70% of each cardiac cycle.
#
# This naturally produces RMSSD variation that reflects ANS state.

class _ECGState:
    """Per-generator state for ECG with RSA — tracks next QRS timing."""

    def __init__(self):
        self.next_beat_t: float = 0.0
        self.last_beat_t: float = -1.0
        self.prev_rr: float = 0.8  # seconds, seed for first interval


def _ecg_signal(t: float, cfg: MockConfig, dt: float, state: _ECGState) -> float:
    """Sparse beat-indicator signal for pipeline development.

    Produces a sharp pulse at each R-peak (amplitude ~0.85) with near-zero
    baseline between beats so peak detection works reliably at 10 Hz.
    RSA coupling modulates the beat-to-beat interval via respiration phase.
    """
    if t >= state.next_beat_t:
        state.last_beat_t = state.next_beat_t

        # Time-dependent base HR: linear ramp from hr_start → hr_end
        frac = min(t / max(cfg.hr_trend_duration, 1.0), 1.0)
        hr_base = cfg.hr_start + (cfg.hr_end - cfg.hr_start) * frac

        # RSA modulation on top of trending base
        resp_at_beat = _respiration(max(0, t - cfg.rsa_lag), cfg)
        hr_inst = hr_base + cfg.rsa_amplitude * (resp_at_beat / cfg.breath_amplitude)
        hr_inst = max(40.0, min(120.0, hr_inst))

        rr_interval = 60.0 / hr_inst
        state.next_beat_t = t + rr_interval
        state.prev_rr = rr_interval

    if state.last_beat_t < 0:
        return np.random.normal(0, cfg.ecg_noise_std * 0.3)

    elapsed = t - state.last_beat_t

    # QRS-like peak spanning ~3 samples at 10 Hz for sub-sample interpolation
    qrs_width = 0.150  # seconds — wide enough that neighbors see >60% amplitude
    peak = 0.85 * math.exp(-(elapsed / qrs_width) ** 2)

    # Low noise floor between beats
    noise = np.random.normal(0, cfg.ecg_noise_std * 0.3)
    return peak + noise


# ── EDA: Tonic + Phasic SCR with exponential decay ───────────────────────
#
# Tonic: slowly decreasing baseline (calming trend over minutes).
#   drift(t) = -amplitude * (1 - exp(-t / tau))
#   Starts at baseline and drifts downward as user relaxes.
#
# Phasic: spontaneous skin conductance responses (SCR).
#   Each SCR rises quickly (~1s) then decays exponentially (τ ≈ 2–3s).
#   At rest: 1–3 SCR/min. Under stress: 5–15 SCR/min.
#
# Ref: Nagai et al. (2019) — GSR biofeedback and sympathetic arousal.

class _EDAState:
    """Per-generator state for EDA phasic SCR tracking."""

    def __init__(self):
        self.scr_events: list[tuple[float, float]] = []  # [(onset_t, amplitude)]
        self._next_scr_t: float = 2.0  # first SCR after warmup


def _eda_signal(t: float, cfg: MockConfig, state: _EDAState) -> float:
    """Skin conductance: tonic drift + independent phasic SCRs with decay."""
    # Tonic: exponential drift toward a lower baseline (calming)
    tonic_drop = 2.0  # μS total drop over several minutes
    tonic = cfg.eda_tonic_base - tonic_drop * (1.0 - math.exp(-t / 90.0))

    # Generate new SCR events on schedule
    scr_interval = 60.0 / max(cfg.scr_rate, 0.1)
    while state._next_scr_t <= t:
        # Randomize amplitude and timing slightly
        amp = cfg.scr_amplitude * (0.5 + 0.5 * np.random.random())
        jitter = np.random.uniform(-scr_interval * 0.2, scr_interval * 0.2)
        state.scr_events.append((state._next_scr_t, amp))
        state._next_scr_t += scr_interval + jitter

    # Clean up old SCR events (older than 5× decay tau)
    cutoff = t - 5.0 * cfg.scr_decay_tau
    state.scr_events = [(onset, amp) for onset, amp in state.scr_events
                        if onset > cutoff]

    # Sum contributions from all active SCR events
    scr_total = 0.0
    for onset_t, amp in state.scr_events:
        age = t - onset_t
        if age < 0:
            continue
        # Rise phase: linear ramp over first ~0.8 s
        if age < 0.8:
            scr_total += amp * (age / 0.8)
        else:
            # Decay phase: exponential with configurable τ
            scr_total += amp * math.exp(-(age - 0.8) / cfg.scr_decay_tau)

    return tonic + scr_total + np.random.normal(0, cfg.eda_noise_std)


# ── ACC: Body Motion ─────────────────────────────────────────────────────
#
# Settling-down envelope: motion decreases as user relaxes into the exercise.
# Occasional movement bursts (postural adjustments) at low frequency.

def _acc_magnitude(t: float, cfg: MockConfig) -> float:
    """Body motion: low baseline + settling-down envelope + rare bursts."""
    # Settling-down: motion halves over ~90 s
    envelope = 0.5 + 0.5 * math.exp(-t / 90.0)

    baseline = cfg.acc_rest_level * envelope

    # Occasional movement burst (postural adjustment)
    burst_interval = 60.0 / max(cfg.acc_motion_rate, 0.1)
    burst_phase = (t % burst_interval) / burst_interval
    burst = 0.0
    if burst_phase < 0.06:
        burst = cfg.acc_burst_amplitude * envelope * \
                math.exp(-((burst_phase * burst_interval) / 0.4) ** 2)

    return baseline + burst + np.random.normal(0, cfg.acc_noise_std)


# ── Skin Temperature ─────────────────────────────────────────────────────
#
# Peripheral vasodilation during relaxation → warming trend.
#  ~0.5 °C rise over 5 min of slow breathing (literature: peripheral temp
#  increases as sympathetic tone drops and vessels dilate).
#  Small respiratory-synchronous oscillation (~0.02 °C).

def _temp_skin(t: float, cfg: MockConfig) -> float:
    """Skin temperature: warming trend + respiratory micro-oscillation."""
    # Warming: first-order approach toward base + total_warming
    warming = cfg.temp_warming_total * (1.0 - math.exp(-t / cfg.temp_warming_tau))

    # Respiratory-synchronous oscillation (peripheral blood flow)
    resp_osc = 0.02 * math.sin(2 * math.pi * cfg.breath_rate_hz * t)

    return cfg.temp_base + warming + resp_osc + \
        np.random.normal(0, cfg.temp_noise_std)


# ── Breath Phase Classifier ──────────────────────────────────────────────

def _breath_phase(t: float, cfg: MockConfig) -> str:
    """Classify breath phase from elapsed time in cycle.

    Returns 'inhale', 'hold', or 'exhale'.
    """
    cycle = cfg.inhale_duration + cfg.hold_duration + cfg.exhale_duration
    if cycle <= 0:
        return "exhale"
    cycle_pos = t % cycle

    if cycle_pos < cfg.inhale_duration:
        return "inhale"
    elif cycle_pos < cfg.inhale_duration + cfg.hold_duration:
        return "hold"
    else:
        return "exhale"


# ── Respiration amplitude (for circle_radius computation) ────────────────
#
# Returns the normalized respiration depth at time t (0 = end-exhale,
# 1 = peak-inhale), useful for driving visual ring animation.

def _respiration_depth(t: float, cfg: MockConfig) -> float:
    """Normalized respiration depth: 0=bottom(exhale end), 1=top(inhale peak).

    Drives the inner ring radius animation — maps to circle_radius.
    """
    cycle = cfg.inhale_duration + cfg.hold_duration + cfg.exhale_duration
    if cycle <= 0:
        return 0.5
    phase = (t % cycle) / cycle
    inhale_frac = cfg.inhale_duration / cycle
    hold_frac = cfg.hold_duration / cycle
    exhale_start = inhale_frac + hold_frac
    exhale_frac = 1.0 - exhale_start

    if phase < inhale_frac:
        return math.sin(math.pi * 0.5 * (phase / inhale_frac))
    elif phase < exhale_start:
        return 1.0
    else:
        progress = (phase - exhale_start) / exhale_frac
        return math.cos(math.pi * 0.5 * progress)


# ── Guidance Text ────────────────────────────────────────────────────────

_WEATHER_PROMPTS: dict[str, dict[str, str]] = {
    "storm": {
        "inhale": "慢慢吸气...4秒",
        "hold": "屏住呼吸...2秒",
        "exhale": "缓缓呼出...6秒",
    },
    "heat": {
        "inhale": "深吸气...3秒",
        "hold": "",
        "exhale": "长长呼出...6秒",
    },
    "snow": {
        "inhale": "平稳吸气...5秒",
        "hold": "",
        "exhale": "缓缓呼气...5秒",
    },
    "fade": {
        "inhale": "自然吸气...",
        "hold": "",
        "exhale": "轻轻呼出...",
    },
}


def _guidance_prompt(phase: str, cfg: MockConfig) -> str:
    weather_prompts = _WEATHER_PROMPTS.get(cfg.weather_type,
                                           _WEATHER_PROMPTS["storm"])
    return weather_prompts.get(phase, "")


# ── Frame Definition ─────────────────────────────────────────────────────

@dataclass
class MockFrame:
    """A single 10 Hz frame of simulated multi-sensor physiological data."""

    timestamp: float

    # Primary biosignals
    respiration_raw: float
    ecg_raw: float

    # Auxiliary biosignals
    eda_raw: float
    acc_magnitude: float
    temp_skin: float

    # Derived / metadata
    breath_phase: str
    guidance_prompt: str
    weather_type: str
    weather_intensity_base: float
    ecg_samples: tuple[tuple[float, float], ...] = ()
    respiration_depth: float = 0.5    # 0–1, for ring animation (last for backward compat)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "respiration_raw": round(self.respiration_raw, 4),
            "ecg_raw": round(self.ecg_raw, 4),
            "eda_raw": round(self.eda_raw, 4),
            "acc_magnitude": round(self.acc_magnitude, 4),
            "temp_skin": round(self.temp_skin, 2),
            "breath_phase": self.breath_phase,
            "respiration_depth": round(self.respiration_depth, 4),
            "guidance_prompt": self.guidance_prompt,
            "weather_type": self.weather_type,
            "weather_intensity_base": round(self.weather_intensity_base, 4),
        }


# ── Frame Generator ──────────────────────────────────────────────────────

def generate_frames(
    duration: float = 60.0,
    cfg: MockConfig | None = None,
) -> Generator[MockFrame, None, None]:
    """Generate multi-sensor mock data frames at 10 Hz.

    Args:
        duration: seconds. 0 = infinite (until generator is closed).
        cfg: MockConfig with weather-specific parameters.

    Yields:
        MockFrame at 10 Hz.
    """
    if cfg is None:
        cfg = MockConfig()

    import itertools
    dt = 1.0 / cfg.frame_rate

    if duration <= 0:
        iterator = itertools.count()
    else:
        iterator = range(int(duration * cfg.frame_rate))

    ecg_state = _ECGState()
    ecg_rate_hz = 130.0
    ecg_samples_per_frame = max(1, round(ecg_rate_hz / cfg.frame_rate))
    eda_state = _EDAState()

    for i in iterator:
        t = i * dt
        ecg_samples = tuple(
            (
                t + sample_index / ecg_rate_hz,
                _ecg_signal(
                    t + sample_index / ecg_rate_hz,
                    cfg,
                    1.0 / ecg_rate_hz,
                    ecg_state,
                ),
            )
            for sample_index in range(ecg_samples_per_frame)
        )
        yield MockFrame(
            timestamp=t,
            respiration_raw=_respiration(t, cfg),
            ecg_raw=ecg_samples[-1][1],
            ecg_samples=ecg_samples,
            eda_raw=_eda_signal(t, cfg, eda_state),
            acc_magnitude=_acc_magnitude(t, cfg),
            temp_skin=_temp_skin(t, cfg),
            breath_phase=_breath_phase(t, cfg),
            respiration_depth=_respiration_depth(t, cfg),
            guidance_prompt=_guidance_prompt(_breath_phase(t, cfg), cfg),
            weather_type=cfg.weather_type,
            weather_intensity_base=cfg.weather_intensity_base,
        )


# ── Convenience ──────────────────────────────────────────────────────────

def generate_frame_list(duration: float = 60.0,
                        cfg: MockConfig | None = None) -> list[MockFrame]:
    return list(generate_frames(duration, cfg))


# ── Self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("MockDataGenerator self-test v0.4 — physiologically-grounded")
    print()

    for weather in ["storm", "heat", "snow", "fade"]:
        cfg = MockConfig.for_weather(weather)
        frames = generate_frame_list(duration=15.0, cfg=cfg)
        print(f"--- {weather} ({len(frames)} frames, 15s) ---")

        # Respiration waveform analysis
        resp_vals = [f.respiration_raw for f in frames]
        print(f"  Respiration: [{min(resp_vals):+.3f}, {max(resp_vals):+.3f}] "
              f"mean={np.mean(resp_vals):+.3f}")

        # ECG with RSA — check RR intervals
        ecg_vals = [f.ecg_raw for f in frames]
        print(f"  ECG: [{min(ecg_vals):.3f}, {max(ecg_vals):.3f}] "
              f"std={np.std(ecg_vals):.3f}")

        # EDA — check tonic drift + SCR
        eda_vals = [f.eda_raw for f in frames]
        print(f"  EDA: [{min(eda_vals):.2f}, {max(eda_vals):.2f}] "
              f"start={eda_vals[0]:.2f} end={eda_vals[-1]:.2f} μS")

        # Respiration depth for ring animation
        depths = [f.respiration_depth for f in frames]
        print(f"  RespirationDepth: [{min(depths):.3f}, {max(depths):.3f}]")

        # Breath phase distribution
        phases = [f.breath_phase for f in frames]
        inhale_n = phases.count("inhale")
        hold_n = phases.count("hold")
        exhale_n = phases.count("exhale")
        total = len(phases)
        print(f"  Phases: inhale={inhale_n/total:.0%} "
              f"hold={hold_n/total:.0%} exhale={exhale_n/total:.0%} "
              f"(I:E={cfg.inhale_duration}:{cfg.exhale_duration})")
        print()
