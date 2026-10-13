"""
SRP 4-Dimension Physiological Specification v1.0
==================================================
Each dimension maps to one independent ANS pathway with dedicated sensor
and gold-standard metric. Non-overlapping by design.

Literature: srp参考文献/06-scoring-model-evidence/README.md (16 SCI Q1 papers)

  4 independent ANS pathways → 4 scores → 1 weather composite

  Dimension        ANS Branch         Device        Gold Standard
  ─────────────────────────────────────────────────────────────────
  breath_sync      呼吸→副交感         PLUX呼吸带     RR tracking accuracy
  breath_depth     呼吸→副交感         PLUX呼吸带     Amplitude / RSA magnitude
  hrv_coherence    副交感(迷走)        Polar H10      RMSSD
  eda_calm         交感(纯皮肤电)       EDA腕带        SCL decrease
"""

from dataclasses import dataclass, field
from typing import Optional
import math


# ── Dimension Metadata ────────────────────────────────────────────────────

@dataclass(frozen=True)
class DimensionSpec:
    """Immutable specification for one physiological scoring dimension.

    Each dimension is backed by 3-6 SCI Q1 papers (see evidence README).
    """
    key: str                    # e.g. 'breath_sync'
    name_en: str                # English display name
    name_cn: str                # Chinese display name
    ans_branch: str             # ANS branch (呼吸→副交感 / 副交感(迷走) / 交感(皮肤电))
    device: str                 # Sensor device model
    gold_standard: str          # Gold-standard physiological metric
    unit: str                   # Measurement unit
    evidence: str               # Evidence level summary
    # Scoring defaults
    score_func: str             # Scoring function name (in scoring_model.py)

    def format_raw(self, raw_value: float, target_value: float = 0) -> str:
        """Format raw physiological value with unit for display."""
        return f"{raw_value:.1f}{self.unit}"

    def format_score(self, raw: float, target: float, score: float) -> str:
        """Format a one-line dimension status for console output."""
        raw_str = self.format_raw(raw, target)
        tgt_str = self.format_raw(target, target)
        return (f"  {self.key:16s} {score:5.0f}/100  "
                f"{raw_str:>8s} → {tgt_str:>8s}  ({self.ans_branch})")


# ── The 4 Dimensions ─────────────────────────────────────────────────────

DIM_BREATH_SYNC = DimensionSpec(
    key="breath_sync",
    name_en="Breath Rhythm Sync",
    name_cn="呼吸节律跟随",
    ans_branch="呼吸→副交感",
    device="PLUX呼吸带",
    gold_standard="RR tracking accuracy",
    unit="bpm",
    evidence="Meta + 大数据(N=70K)",
    score_func="score_breath_sync",
)

DIM_BREATH_DEPTH = DimensionSpec(
    key="breath_depth",
    name_en="Breath Depth",
    name_cn="呼吸深度",
    ans_branch="呼吸→副交感",
    device="PLUX呼吸带",
    gold_standard="Amplitude / RSA magnitude",
    unit="",
    evidence="RCT(46+36人) + 系统综述",
    score_func="score_breath_depth",
)

DIM_HRV_COHERENCE = DimensionSpec(
    key="hrv_coherence",
    name_en="HRV Coherence",
    name_cn="迷走神经张力",
    ans_branch="副交感(迷走)",
    device="Polar H10",
    gold_standard="RMSSD",
    unit="ms",
    evidence="系统综述(36+8+77篇) + fMRI(N=70)",
    score_func="score_hrv_coherence",
)

DIM_EDA_CALM = DimensionSpec(
    key="eda_calm",
    name_en="EDA Calm",
    name_cn="皮肤电平静度",
    ans_branch="交感(皮肤电)",
    device="EDA腕带",
    gold_standard="SCL decrease from baseline",
    unit="μS",
    evidence="Meta + 系统综述(2篇)",
    score_func="score_eda_calm",
)

# Ordered dimension list
DIMENSIONS: list[DimensionSpec] = [
    DIM_BREATH_SYNC,
    DIM_BREATH_DEPTH,
    DIM_HRV_COHERENCE,
    DIM_EDA_CALM,
]

DIMENSION_MAP: dict[str, DimensionSpec] = {d.key: d for d in DIMENSIONS}


# ── Dimension-specific Weather Presets ────────────────────────────────────

@dataclass
class DimensionPreset:
    """Weather-specific physiological targets for one dimension.

    Defines both what the mock data generator should produce (raw)
    and what the scoring model should target.
    """
    # Raw signal simulation params
    raw_value: float = 0.0        # Typical raw value for this weather
    raw_std: float = 0.0          # Natural variation (1σ)

    # Scoring target
    target_value: float = 0.0     # Optimal value for 100-point score


@dataclass
class WeatherDimensionPresets:
    """Complete 4-dimension physiological preset for one weather type.

    Each dimension has independent simulation params and scoring targets,
    grounded in the literature for that emotional state.
    """
    weather_type: str
    breath_sync: DimensionPreset = field(default_factory=DimensionPreset)
    breath_depth: DimensionPreset = field(default_factory=DimensionPreset)
    hrv_coherence: DimensionPreset = field(default_factory=DimensionPreset)
    eda_calm: DimensionPreset = field(default_factory=DimensionPreset)

    def get(self, dim_key: str) -> DimensionPreset:
        return getattr(self, dim_key)

    def to_dict(self) -> dict:
        return {
            "weather_type": self.weather_type,
            "breath_sync": {"raw_value": self.breath_sync.raw_value,
                            "target_value": self.breath_sync.target_value},
            "breath_depth": {"raw_value": self.breath_depth.raw_value,
                             "target_value": self.breath_depth.target_value},
            "hrv_coherence": {"raw_value": self.hrv_coherence.raw_value,
                              "target_value": self.hrv_coherence.target_value},
            "eda_calm": {"raw_value": self.eda_calm.raw_value,
                         "target_value": self.eda_calm.target_value},
        }


# ── 4 Weather × 4 Dimension Preset Matrix ────────────────────────────────
#
# Raw values represent the physiological state BEFORE the breathing exercise
# (elevated HR/stress for storm/heat, low arousal for snow/fade).
# Target values are the desired post-exercise state.
#
# Literature anchors:
#   Slow breathing meta: 6 bpm (0.10 Hz) maximizes vagal tone
#   Schneider 2025: RMSSD=30-60ms resting young adults
#   Nagai 2019: SCL decrease of 0.5μS per 10-point calm improvement
#   Pranayama RCT 2021: amplitude independently boosts logRMSSD

WEATHER_DIMENSION_PRESETS: dict[str, WeatherDimensionPresets] = {
    "storm": WeatherDimensionPresets(
        weather_type="storm",
        breath_sync=DimensionPreset(
            raw_value=12.0,       # pre-exercise: elevated RR (anxiety)
            target_value=5.0,     # target: 4-2-6 box breathing → 5 bpm
        ),
        breath_depth=DimensionPreset(
            raw_value=0.35,       # pre: shallow breathing
            target_value=0.50,    # target: moderate depth
        ),
        hrv_coherence=DimensionPreset(
            raw_value=30.0,       # pre: low RMSSD (stress)
            target_value=40.0,    # target: recovered to 40ms
        ),
        eda_calm=DimensionPreset(
            raw_value=10.0,       # pre: elevated SCL (sympathetic)
            target_value=7.0,     # target: 3μS drop → calm
        ),
    ),
    "heat": WeatherDimensionPresets(
        weather_type="heat",
        breath_sync=DimensionPreset(
            raw_value=15.0,       # pre: rapid breathing (irritability)
            target_value=6.67,    # target: 3-6 long exhale → 6.67 bpm
        ),
        breath_depth=DimensionPreset(
            raw_value=0.45,       # pre: moderate
            target_value=0.60,    # target: deep cooling breath
        ),
        hrv_coherence=DimensionPreset(
            raw_value=35.0,       # pre: moderate-low RMSSD
            target_value=45.0,    # target: improved coherence
        ),
        eda_calm=DimensionPreset(
            raw_value=14.0,       # pre: high SCL (irritation)
            target_value=9.0,     # target: 5μS drop
        ),
    ),
    "snow": WeatherDimensionPresets(
        weather_type="snow",
        breath_sync=DimensionPreset(
            raw_value=8.0,        # pre: slow breathing (low mood)
            target_value=6.0,     # target: 5-5 steady → 6 bpm
        ),
        breath_depth=DimensionPreset(
            raw_value=0.25,       # pre: shallow (low energy)
            target_value=0.40,    # target: gentle activating
        ),
        hrv_coherence=DimensionPreset(
            raw_value=45.0,       # pre: moderate RMSSD
            target_value=55.0,    # target: increased vagal tone
        ),
        eda_calm=DimensionPreset(
            raw_value=5.0,        # pre: low SCL (low arousal)
            target_value=4.0,     # target: slight further calm
        ),
    ),
    "fade": WeatherDimensionPresets(
        weather_type="fade",
        breath_sync=DimensionPreset(
            raw_value=10.0,       # pre: irregular rhythm
            target_value=7.5,     # target: 3.5-4.5 natural → 7.5 bpm
        ),
        breath_depth=DimensionPreset(
            raw_value=0.25,       # pre: shallow
            target_value=0.35,    # target: light companion breath
        ),
        hrv_coherence=DimensionPreset(
            raw_value=50.0,       # pre: moderate RMSSD
            target_value=60.0,    # target: highest relaxation RMSSD
        ),
        eda_calm=DimensionPreset(
            raw_value=6.0,        # pre: moderate SCL
            target_value=4.5,     # target: gentle calming
        ),
    ),
}


# ── Dimension-aware Simulation Functions ──────────────────────────────────
#
# Each function maps: raw physiological value → [0,100] score
# These mirror scoring_model.py but are dimension-spec-aware, providing
# human-readable labels for console output.

def sim_breath_sync_score(rr: float, target_rr: float,
                          dim: DimensionSpec = DIM_BREATH_SYNC) -> tuple[float, str]:
    """Score breath rate tracking accuracy. Gaussian decay around target.

    Returns (score, description_string).
    """
    sigma = 3.0
    diff = rr - target_rr
    score = 100.0 * math.exp(-(diff ** 2) / (2 * sigma ** 2))
    desc = f"{dim.name_cn}: RR={rr:.1f}→{target_rr:.1f}{dim.unit} score={score:.0f}"
    return score, desc


def sim_breath_depth_score(amplitude: float, target_amp: float,
                           dim: DimensionSpec = DIM_BREATH_DEPTH) -> tuple[float, str]:
    """Score breathing amplitude quality. Gaussian centered at target.

    Returns (score, description_string).
    """
    sigma = target_amp * 0.5
    diff = amplitude - target_amp
    score = 100.0 * math.exp(-(diff ** 2) / (2 * sigma ** 2))
    desc = f"{dim.name_cn}: Amp={amplitude:.2f}→{target_amp:.2f} score={score:.0f}"
    return score, desc


def sim_hrv_coherence_score(rmssd: float, target_rmssd: float,
                            dim: DimensionSpec = DIM_HRV_COHERENCE) -> tuple[float, str]:
    """Score RMSSD recovery toward target. Linear scale, clip at 100.

    Returns (score, description_string).
    """
    max_val = target_rmssd * 1.5
    score = max(0.0, min(100.0, (rmssd / max_val) * 100.0))
    desc = f"{dim.name_cn}: RMSSD={rmssd:.0f}→{target_rmssd:.0f}{dim.unit} score={score:.0f}"
    return score, desc


def sim_eda_calm_score(eda_tonic: float, baseline: float,
                       dim: DimensionSpec = DIM_EDA_CALM) -> tuple[float, str]:
    """Score EDA calming: SCL decrease from baseline → [0,100].

    Returns (score, description_string).
    """
    if baseline == 0:
        return 50.0, f"{dim.name_cn}: no baseline"
    drop = baseline - eda_tonic
    score = max(0.0, min(100.0, 50.0 + drop * 20.0))
    desc = (f"{dim.name_cn}: SCL={eda_tonic:.1f}→基线{baseline:.1f}{dim.unit} "
            f"Δ={drop:+.1f} score={score:.0f}")
    return score, desc


# ── Dimension Report Generator ────────────────────────────────────────────

def format_dimension_report(
    scores: dict[str, float],
    raw_values: dict[str, float],
    targets: dict[str, float],
    calm_index: float = 50.0,
    weather_type: str = "storm",
    weather_intensity: float = 0.5,
    weather_trend: str = "stable",
) -> str:
    """Generate a formatted 4-dimension status report for console output.

    Args:
        scores: {dim_key: score_0_100}
        raw_values: {dim_key: raw_physiological_value}
        targets: {dim_key: target_value}
        calm_index: overall calm index (0-100)
        weather_type: current weather
        weather_intensity: 0-1 weather intensity
        weather_trend: weakening/stable/intensifying

    Returns:
        Multi-line formatted string.
    """
    lines = []
    lines.append("── 4-Dimension Scores ──────────────────────────────────")

    for dim in DIMENSIONS:
        key = dim.key
        s = scores.get(key, 50)
        raw = raw_values.get(key, 0)
        tgt = targets.get(key, 0)

        if key == "breath_sync":
            raw_str = f"RR={raw:.1f}{dim.unit}"
            tgt_str = f"→{tgt:.1f}{dim.unit}"
        elif key == "breath_depth":
            raw_str = f"Amp={raw:.2f}"
            tgt_str = f"→{tgt:.2f}"
        elif key == "hrv_coherence":
            raw_str = f"RMSSD={raw:.0f}{dim.unit}"
            tgt_str = f"→{tgt:.0f}{dim.unit}"
        elif key == "eda_calm":
            raw_str = f"SCL={raw:.1f}{dim.unit}"
            tgt_str = f"↓{tgt:.1f}{dim.unit}"
        else:
            raw_str = f"{raw:.1f}{dim.unit}"
            tgt_str = f"→{tgt:.1f}{dim.unit}"

        lines.append(f"  {dim.name_cn:<10s} {s:5.0f}/100  "
                     f"{raw_str:>14s} {tgt_str:>12s}  [{dim.ans_branch}]")

    lines.append("  " + "─" * 54)
    trend_icon = {"weakening": "↓", "stable": "→", "intensifying": "↑"}.get(
        weather_trend, "?")
    lines.append(f"  Calm Index: {calm_index:.0f}/100  |  "
                 f"Weather: {weather_type}  "
                 f"intensity={weather_intensity:.2f}  {trend_icon}{weather_trend}")
    lines.append("──" + "─" * 54)

    return "\n".join(lines)


def format_dimension_header(weather_type: str,
                            presets: WeatherDimensionPresets) -> str:
    """Generate startup header showing 4-dimension targets for this weather."""
    lines = []
    lines.append("4-Dimension Physiological Targets:")
    lines.append(f"  {'Dimension':<16s} {'Target':>10s}  {'ANS Branch':<16s}  Evidence")
    lines.append(f"  {'─'*16} {'─'*10}  {'─'*16}  {'─'*8}")
    for dim in DIMENSIONS:
        preset = presets.get(dim.key)
        if dim.key == "breath_sync":
            tgt_str = f"{preset.target_value:.1f} bpm"
        elif dim.key == "breath_depth":
            tgt_str = f"{preset.target_value:.2f}"
        elif dim.key == "hrv_coherence":
            tgt_str = f"{preset.target_value:.0f} ms"
        elif dim.key == "eda_calm":
            tgt_str = f"{preset.target_value:.1f} μS"
        else:
            tgt_str = f"{preset.target_value:.1f}"
        lines.append(f"  {dim.key:<16s} {tgt_str:>10s}  "
                     f"{dim.ans_branch:<16s}  {dim.evidence}")
    return "\n".join(lines)


# ── Self-test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("SRP 4-Dimension Specification v1.0")
    print("=" * 60)
    for dim in DIMENSIONS:
        print(f"\n{dim.key}:")
        print(f"  Name:     {dim.name_en} ({dim.name_cn})")
        print(f"  ANS:      {dim.ans_branch}")
        print(f"  Device:   {dim.device}")
        print(f"  Metric:   {dim.gold_standard}")
        print(f"  Evidence: {dim.evidence}")

    print("\n" + "=" * 60)
    print("Weather × Dimension Preset Matrix:")
    for w in ["storm", "heat", "snow", "fade"]:
        presets = WEATHER_DIMENSION_PRESETS[w]
        print(f"\n  [{w}]")
        for dim in DIMENSIONS:
            p = presets.get(dim.key)
            print(f"    {dim.key:<16s} raw={p.raw_value:.1f} → target={p.target_value:.1f}")

    print("\n" + "=" * 60)
    print("Dimension Simulation Functions:")
    score1, desc1 = sim_breath_sync_score(6.2, 5.0)
    print(f"  {desc1}")
    score2, desc2 = sim_breath_depth_score(0.45, 0.50)
    print(f"  {desc2}")
    score3, desc3 = sim_hrv_coherence_score(40.0, 40.0)
    print(f"  {desc3}")
    score4, desc4 = sim_eda_calm_score(7.0, 10.0)
    print(f"  {desc4}")

    print("\n" + format_dimension_report(
        scores={"breath_sync": 72, "breath_depth": 58,
                "hrv_coherence": 68, "eda_calm": 71},
        raw_values={"breath_sync": 6.2, "breath_depth": 0.45,
                    "hrv_coherence": 40, "eda_calm": 7.0},
        targets={"breath_sync": 5.0, "breath_depth": 0.50,
                 "hrv_coherence": 40, "eda_calm": 10.0},
        calm_index=67, weather_type="storm",
        weather_intensity=0.33, weather_trend="weakening",
    ))
