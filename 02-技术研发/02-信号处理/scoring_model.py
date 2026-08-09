"""
SRP Scoring Model v2.1 — 4 independent dimensions → weather composite.

4 non-overlapping physiological pathways, each backed by SCI Q1 literature.
See: srp参考文献/06-scoring-model-evidence/README.md (16 papers)
     dimension_spec.py for dimension metadata and presets

Architecture:
  4 raw signals → 4 independent scores → 1 weather composite

  breath_sync    RR tracking accuracy     呼吸→副交感     PLUX呼吸带
  breath_depth   Amplitude / RSA depth    呼吸→副交感     PLUX呼吸带
  hrv_coherence  RMSSD recovery           副交感(迷走)    Polar H10
  eda_calm       SCL decrease             交感(皮肤电)    EDA腕带
"""

from dataclasses import dataclass, field
from typing import Optional
import math


# ── Configuration ──────────────────────────────────────────────────────────

@dataclass
class ScoringConfig:
    """Per-weather scoring targets and weights (4 dimensions).

    Maps to dimension_spec.WEATHER_DIMENSION_PRESETS for metadata.
    """

    # Targets (per-dimension gold standard metrics)
    target_rr: float = 10.0            # breath_sync: bpm
    target_amplitude: float = 0.5      # breath_depth: normalized
    target_rmssd: float = 50.0         # hrv_coherence: ms
    target_eda: float = 5.0            # eda_calm: μS target SCL

    # 4 independent score weights → weather composite (equal: 0.25 each)
    w_breath_sync: float = 0.25
    w_breath_depth: float = 0.25
    w_hrv_coherence: float = 0.25
    w_eda_calm: float = 0.25

    # Smoothing
    smoothing_alpha: float = 0.3

    @property
    def dimension_targets(self) -> dict[str, float]:
        """Return {dim_key: target_value} for all 4 dimensions."""
        return {
            "breath_sync": self.target_rr,
            "breath_depth": self.target_amplitude,
            "hrv_coherence": self.target_rmssd,
            "eda_calm": self.target_eda,
        }

    @classmethod
    def for_weather(cls, weather_type: str) -> "ScoringConfig":
        return WEATHER_SCORING_PRESETS.get(weather_type, WEATHER_SCORING_PRESETS["storm"])


# ── Per-weather presets ─────────────────────────────────────────────────────

WEATHER_SCORING_PRESETS: dict[str, ScoringConfig] = {
    #                  sync(bpm)  depth     hrv(ms)    eda(μS)
    "storm": ScoringConfig(  # 焦虑 → 4-2-6 box breathing
        target_rr=5.0, target_amplitude=0.50, target_rmssd=40.0, target_eda=7.0,
    ),
    "heat": ScoringConfig(  # 烦躁 → 3-6 long-exhale cooling
        target_rr=6.67, target_amplitude=0.60, target_rmssd=45.0, target_eda=9.0,
    ),
    "snow": ScoringConfig(  # 低落 → 5-5 steady activating
        target_rr=6.0, target_amplitude=0.40, target_rmssd=55.0, target_eda=4.0,
    ),
    "fade": ScoringConfig(  # 孤独 → 3.5-4.5 natural companion
        target_rr=7.5, target_amplitude=0.35, target_rmssd=60.0, target_eda=4.5,
    ),
}


# ── Per-Dimension Score Calculators ────────────────────────────────────────

def score_breath_sync(rr: float, target_rr: float) -> float:
    """How close is breathing rate to the guidance target? Gaussian decay.

    Literature: slow breathing meta-analysis (2022); Balaji et al. (2025)
    — 0.10 Hz resonance frequency maximizes vagal tone.
    """
    sigma = 3.0
    diff = rr - target_rr
    return 100.0 * math.exp(-(diff ** 2) / (2 * sigma ** 2))


def score_breath_depth(amplitude: float, target_amplitude: float) -> float:
    """Breathing depth quality relative to target. Gaussian centered at target.

    Literature: Pranayama RCT (2021) — depth independently contributes
    to parasympathetic response (logRMSSD ↑0.2–0.5, p<0.01).
    """
    sigma = target_amplitude * 0.5
    diff = amplitude - target_amplitude
    return 100.0 * math.exp(-(diff ** 2) / (2 * sigma ** 2))


def score_hrv_coherence(rmssd: float, target_rmssd: float) -> float:
    """RMSSD recovery toward target. Linear, clip at 100.

    Literature: Schneider et al. (2025) — RMSSD is the most consistent
    parasympathetic emotion regulation index (36 studies, N=5,501).
    """
    if math.isnan(rmssd) or rmssd <= 0:
        return 50.0
    max_val = target_rmssd * 1.5
    return max(0.0, min(100.0, (rmssd / max_val) * 100.0))


def score_eda_calm(eda_tonic: float, init_eda: float) -> float:
    """EDA calm: decreasing skin conductance = calming down.

    Literature: Nagai et al. (2019) — GSR biofeedback significantly
    reduces skin conductance via sympathetic arousal reduction.

    Score increases as EDA drops below initial baseline.
    """
    if init_eda == 0:
        return 50.0
    drop = init_eda - eda_tonic
    # Each 0.5 μS drop = 10 points
    base = 50.0 + drop * 20.0
    return max(0.0, min(100.0, base))


# ── Weather Mapping ─────────────────────────────────────────────────────────

def _weather_intensity(composite: float) -> float:
    """Composite calm → weather intensity. 100=clear, 0=severe."""
    return 1.0 - (composite / 100.0)


def _weather_trend(current: float, previous: float) -> str:
    diff = current - previous
    if diff > 2:
        return "weakening"
    elif diff < -2:
        return "intensifying"
    else:
        return "stable"


def _dominant_domain(scores: dict) -> str:
    """Which score domain is currently contributing most."""
    if not scores:
        return "—"
    return max(scores, key=scores.get)


# ── Scoring Output ─────────────────────────────────────────────────────────

@dataclass
class ScoreFrame:
    """One scored frame with 4 independent scores + weather composite."""
    timestamp: float

    # 4 independent per-signal scores (0-100)
    breath_sync: float
    breath_depth: float
    hrv_coherence: float
    eda_calm: float

    # Weather composite
    calm_index: float                # 0-100, equal-weighted average of 4 scores
    weather_intensity: float         # 0-1, derived from calm_index
    weather_trend: str               # weakening / stable / intensifying
    dominant_domain: str             # which score leads

    # Raw inputs (for CSV completeness)
    rr: float
    hr: float
    rmssd: float
    respiration_raw: float
    respiration_amplitude: float
    breath_regularity_raw: float
    ecg_raw: float
    eda_raw: float
    eda_tonic: float

    # Metadata
    breath_phase: str = "exhale"
    respiration_depth: float = 0.5     # 0-1, for ring animation
    guidance_prompt: str = ""
    weather_type: str = "storm"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            # 4 independent scores
            "breath_sync": round(self.breath_sync, 1),
            "breath_depth": round(self.breath_depth, 1),
            "hrv_coherence": round(self.hrv_coherence, 1),
            "eda_calm": round(self.eda_calm, 1),
            # Weather composite
            "calm_index": round(self.calm_index, 1),
            "weather_intensity": round(self.weather_intensity, 4),
            "weather_trend": self.weather_trend,
            "dominant_domain": self.dominant_domain,
            # Raw signals
            "rr": round(self.rr, 2),
            "hr": round(self.hr, 1),
            "rmssd": round(self.rmssd, 1),
            "respiration_raw": round(self.respiration_raw, 4),
            "respiration_amplitude": round(self.respiration_amplitude, 4),
            "breath_regularity_raw": round(self.breath_regularity_raw, 4),
            "ecg_raw": round(self.ecg_raw, 4),
            "eda_raw": round(self.eda_raw, 4),
            "eda_tonic": round(self.eda_tonic, 2),
            # Metadata
            "breath_phase": self.breath_phase,
            "respiration_depth": round(self.respiration_depth, 4),
            "guidance_prompt": self.guidance_prompt,
            "weather_type": self.weather_type,
        }

    def score_list(self) -> list[tuple[str, float]]:
        """Return all 4 scores as ordered (name, value) pairs for display."""
        return [
            ("Breath Sync", self.breath_sync),
            ("Breath Depth", self.breath_depth),
            ("HRV Coherence", self.hrv_coherence),
            ("EDA Calm", self.eda_calm),
        ]


# ── Scoring Model ──────────────────────────────────────────────────────────

class ScoringModel:
    """Translates ProcessedFrame features into 4 independent scores + weather."""

    def __init__(self, cfg: ScoringConfig | None = None):
        self.cfg = cfg or ScoringConfig()
        self._prev_calm: float = 50.0
        self._prev_intensity: float = 0.5
        self._prev_hr: float = 72.0
        self._prev_rr: float = 14.0
        self._init_eda: Optional[float] = None
        self._warmup_frames: int = 0

    def score(self, processed, breath_phase: str = "exhale",
              respiration_depth: float = 0.5,
              guidance_prompt: str = "", weather_type: str = "storm") -> ScoreFrame:
        """Compute all 4 independent scores from a ProcessedFrame."""

        if processed is None:
            return self._neutral_frame(breath_phase, guidance_prompt, weather_type, respiration_depth)

        # Capture initial EDA baseline (first 5 processed frames avg)
        if self._init_eda is None:
            self._init_eda = processed.eda_tonic if processed.eda_tonic > 0 else 8.0
        elif self._warmup_frames < 50:
            self._init_eda = self._init_eda * 0.9 + processed.eda_tonic * 0.1
        self._warmup_frames += 1

        # Compute 4 independent scores
        s1 = score_breath_sync(processed.rr, self.cfg.target_rr)
        s2 = score_breath_depth(processed.respiration_amplitude, self.cfg.target_amplitude)
        s3 = score_hrv_coherence(processed.rmssd, self.cfg.target_rmssd)
        s4 = score_eda_calm(processed.eda_tonic, self._init_eda)

        # Equal-weighted calm_index
        w = self.cfg
        raw_calm = (
            s1 * w.w_breath_sync +
            s2 * w.w_breath_depth +
            s3 * w.w_hrv_coherence +
            s4 * w.w_eda_calm
        )

        # EMA smoothing
        alpha = self.cfg.smoothing_alpha
        previous_calm = self._prev_calm
        calm = alpha * raw_calm + (1 - alpha) * previous_calm

        intensity = alpha * _weather_intensity(calm) + (1 - alpha) * self._prev_intensity
        trend = _weather_trend(calm, previous_calm)

        # Commit history only after all deltas have been evaluated.
        self._prev_calm = calm
        self._prev_intensity = intensity

        scores_dict = {
            "breath_sync": s1, "breath_depth": s2,
            "hrv_coherence": s3, "eda_calm": s4,
        }
        dominant = _dominant_domain(scores_dict)

        # Update state
        self._prev_hr = processed.hr
        self._prev_rr = processed.rr

        return ScoreFrame(
            timestamp=processed.timestamp,
            breath_sync=s1, breath_depth=s2,
            hrv_coherence=s3, eda_calm=s4,
            calm_index=calm,
            weather_intensity=intensity,
            weather_trend=trend,
            dominant_domain=dominant,
            rr=processed.rr, hr=processed.hr, rmssd=processed.rmssd,
            respiration_raw=processed.respiration_raw,
            respiration_amplitude=processed.respiration_amplitude,
            breath_regularity_raw=processed.breath_regularity,
            ecg_raw=processed.ecg_raw,
            eda_raw=processed.eda_raw,
            eda_tonic=processed.eda_tonic,
            breath_phase=breath_phase,
            respiration_depth=respiration_depth,
            guidance_prompt=guidance_prompt,
            weather_type=weather_type,
        )

    def _neutral_frame(self, phase: str, prompt: str, weather: str,
                       resp_depth: float = 0.5) -> ScoreFrame:
        return ScoreFrame(
            timestamp=0,
            breath_sync=50, breath_depth=50,
            hrv_coherence=50, eda_calm=50,
            calm_index=50, weather_intensity=0.5,
            weather_trend="stable", dominant_domain="—",
            rr=0, hr=0, rmssd=0,
            respiration_raw=0, respiration_amplitude=0,
            breath_regularity_raw=0,
            ecg_raw=0, eda_raw=0, eda_tonic=0,
            breath_phase=phase, respiration_depth=resp_depth,
            guidance_prompt=prompt, weather_type=weather,
        )


# ── Self-test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dataclasses import dataclass as _dc

    @_dc
    class _PF:
        timestamp: float = 0; rr: float = 0; respiration_amplitude: float = 0
        breath_regularity: float = 0; hr: float = 0; rmssd: float = 0
        eda_tonic: float = 0
        respiration_raw: float = 0; ecg_raw: float = 0; eda_raw: float = 0

    for weather in ["storm", "heat", "snow", "fade"]:
        cfg = ScoringConfig.for_weather(weather)
        model = ScoringModel(cfg)
        print(f"\n=== {weather} ===")
        print(f"Targets: RR={cfg.target_rr} Amp={cfg.target_amplitude} RMSSD={cfg.target_rmssd}")

        frames = [
            _PF(0, rr=14, respiration_amplitude=0.3, breath_regularity=0.5,
                hr=85, rmssd=30, eda_tonic=10,
                respiration_raw=0.1, ecg_raw=0.1, eda_raw=10),
            _PF(1, rr=10, respiration_amplitude=0.5, breath_regularity=0.7,
                hr=78, rmssd=42, eda_tonic=8,
                respiration_raw=0.3, ecg_raw=0.2, eda_raw=8),
            _PF(2, rr=6, respiration_amplitude=0.55, breath_regularity=0.85,
                hr=72, rmssd=50, eda_tonic=7,
                respiration_raw=0.5, ecg_raw=0.3, eda_raw=7),
        ]
        for pf in frames:
            sf = model.score(pf)
            print(f"  t={sf.timestamp:.0f}s calm={sf.calm_index:.0f} "
                  f"intensity={sf.weather_intensity:.2f} trend={sf.weather_trend} "
                  f"dominant={sf.dominant_domain}")
