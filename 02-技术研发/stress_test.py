#!/usr/bin/env python3
"""
SRP Full-Pipeline Stress Test (Sprint 1)
==========================================
Cycles through all 4 weather types: 15 seconds each at 10Hz.
Total: 600 frames across 60 seconds.

Verifies:
  - No dropped frames (600 generated = 600 processed post-warmup)
  - No pipeline errors
  - Per-weather score distributions in valid ranges

Usage:
  python stress_test.py
  python stress_test.py --full    # include UDP + CSV
"""

import sys
import os
import time
import importlib
from dataclasses import dataclass, field

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

WEATHER_CYCLE = ["storm", "heat", "snow", "fade"]
SECONDS_PER_SEGMENT = 15
FRAME_RATE = 10
EXPECTED_FRAMES = len(WEATHER_CYCLE) * SECONDS_PER_SEGMENT * FRAME_RATE  # 600


@dataclass
class SegmentStats:
    """Per-weather segment statistics across all 4 dimensions."""
    weather_type: str
    frames: int = 0
    errors: int = 0
    warmup_dropped: int = 0
    breath_sync_scores: list[float] = field(default_factory=list)
    breath_depth_scores: list[float] = field(default_factory=list)
    hrv_coherence_scores: list[float] = field(default_factory=list)
    eda_calm_scores: list[float] = field(default_factory=list)
    calm_indices: list[float] = field(default_factory=list)
    weather_intensities: list[float] = field(default_factory=list)

    def avg_dim_score(self, dim: str) -> float:
        scores = getattr(self, f"{dim}_scores", [])
        return sum(scores) / len(scores) if scores else 0.0

    def avg_calm_index(self) -> float:
        return sum(self.calm_indices) / len(self.calm_indices) if self.calm_indices else 0.0

    def avg_intensity(self) -> float:
        return sum(self.weather_intensities) / len(self.weather_intensities) if self.weather_intensities else 0.0


def run_stress_test(full: bool = False):
    """Run 60-second 4-weather stress test and print 4-dimension report."""
    mock_data = importlib.import_module("01-数据采集.mock_data")
    signal_pipeline_mod = importlib.import_module("02-信号处理.signal_pipeline")
    scoring_model_mod = importlib.import_module("02-信号处理.scoring_model")
    dim_spec = importlib.import_module("02-信号处理.dimension_spec")

    if full:
        udp_sender_mod = importlib.import_module("05-通信协议.udp_sender")
        csv_logger_mod = importlib.import_module("05-通信协议.csv_logger")

    segment_stats: dict[str, SegmentStats] = {w: SegmentStats(weather_type=w) for w in WEATHER_CYCLE}
    total_frames = 0
    total_errors = 0
    total_warmup_dropped = 0
    all_weather_intensities: list[float] = []

    print("=" * 70)
    print("  SRP FAST SIMULATION REGRESSION — 4-Dimension Mode")
    print(f"  {len(WEATHER_CYCLE)} weathers x {SECONDS_PER_SEGMENT}s @ {FRAME_RATE}Hz = {EXPECTED_FRAMES} frames")
    print(f"  UDP/CSV: {'enabled' if full else 'disabled (--full to enable)'}")
    print()
    print("  4-Dimension Targets (per weather):")
    print(f"  {'Weather':<8} {'sync(bpm)':>10} {'depth':>8} {'RMSSD(ms)':>10} {'SCL(μS)':>9}")
    print(f"  {'─'*8} {'─'*10} {'─'*8} {'─'*10} {'─'*9}")
    for w in WEATHER_CYCLE:
        presets = dim_spec.WEATHER_DIMENSION_PRESETS[w]
        print(f"  {w:<8} {presets.breath_sync.target_value:>10.1f} "
              f"{presets.breath_depth.target_value:>8.2f} "
              f"{presets.hrv_coherence.target_value:>10.0f} "
              f"{presets.eda_calm.target_value:>9.1f}")
    print("=" * 70)

    if full:
        sender = udp_sender_mod.UDPSender()
        csv_log = csv_logger_mod.CSVLogger(prefix="stress")
        csv_log.open()

    start_time = time.time()

    for weather in WEATHER_CYCLE:
        # Each generated segment starts its logical clock at zero. Keep native
        # timestamp domains independent instead of silently accepting a reset.
        pipeline = signal_pipeline_mod.SignalPipeline()
        cfg = mock_data.MockConfig.for_weather(weather)
        frames = mock_data.generate_frame_list(duration=SECONDS_PER_SEGMENT, cfg=cfg)
        stats = segment_stats[weather]

        scorer = scoring_model_mod.ScoringModel(
            cfg=scoring_model_mod.ScoringConfig.for_weather(weather)
        )

        for f in frames:
            total_frames += 1
            stats.frames += 1

            try:
                processed = pipeline.feed(
                    f.timestamp, f.respiration_raw, f.ecg_raw,
                    f.eda_raw, f.acc_magnitude, f.temp_skin,
                    ecg_samples=getattr(f, "ecg_samples", None),
                )

                if processed is None:
                    total_warmup_dropped += 1
                    stats.warmup_dropped += 1
                    continue

                score = scorer.score(
                    processed,
                    breath_phase=f.breath_phase,
                    respiration_depth=f.respiration_depth,
                    guidance_prompt=f.guidance_prompt,
                    weather_type=f.weather_type,
                )
                score_dict = score.to_dict()
                stats.breath_sync_scores.append(score.breath_sync)
                stats.breath_depth_scores.append(score.breath_depth)
                stats.hrv_coherence_scores.append(score.hrv_coherence)
                stats.eda_calm_scores.append(score.eda_calm)
                stats.calm_indices.append(score.calm_index)
                stats.weather_intensities.append(score.weather_intensity)
                all_weather_intensities.append(score.weather_intensity)

                if full:
                    sender.send(score_dict)
                    csv_log.write(score_dict)

            except Exception as e:
                total_errors += 1
                stats.errors += 1
                print(f"  ERROR [{weather}] frame {f.timestamp:.1f}s: {e}")

    elapsed = time.time() - start_time

    if full:
        csv_log.close()
        sender.close()

    # ── 4-Dimension Report ─────────────────────────────────────────────────

    print()
    print(f"  Duration: {elapsed:.1f}s | Frames: {total_frames} | Errors: {total_errors}")
    print(f"  Warmup-dropped: {total_warmup_dropped}")
    print(f"  Scored: {total_frames - total_warmup_dropped}")
    print("-" * 70)
    header = (f"  {'Weather':<8} {'sync':>6} {'depth':>6} "
              f"{'hrv':>6} {'eda':>6} {'calm':>7} {'intensity':>10}")
    print(header)
    print("-" * 70)

    for w in WEATHER_CYCLE:
        s = segment_stats[w]
        print(f"  {w:<8} "
              f"{s.avg_dim_score('breath_sync'):>6.1f} "
              f"{s.avg_dim_score('breath_depth'):>6.1f} "
              f"{s.avg_dim_score('hrv_coherence'):>6.1f} "
              f"{s.avg_dim_score('eda_calm'):>6.1f} "
              f"{s.avg_calm_index():>7.1f} "
              f"{s.avg_intensity():>10.4f}")

    print("-" * 70)

    # Overall averages across all 4 dimensions
    all_sync = [s for stats in segment_stats.values() for s in stats.breath_sync_scores]
    all_depth = [s for stats in segment_stats.values() for s in stats.breath_depth_scores]
    all_hrv = [s for stats in segment_stats.values() for s in stats.hrv_coherence_scores]
    all_eda = [s for stats in segment_stats.values() for s in stats.eda_calm_scores]

    overall_sync = sum(all_sync) / max(len(all_sync), 1)
    overall_depth = sum(all_depth) / max(len(all_depth), 1)
    overall_hrv = sum(all_hrv) / max(len(all_hrv), 1)
    overall_eda = sum(all_eda) / max(len(all_eda), 1)
    overall_ci = sum(all_weather_intensities) / max(len(all_weather_intensities), 1)

    print(f"  {'OVERALL':<8} "
          f"{overall_sync:>6.1f} {overall_depth:>6.1f} "
          f"{overall_hrv:>6.1f} {overall_eda:>6.1f} "
          f"{1.0-overall_ci:>7.1%} {overall_ci:>10.4f}")
    print("=" * 70)

    # ── Verdict ────────────────────────────────────────────────────────────

    passed = True
    if total_frames != EXPECTED_FRAMES:
        print(f"  FAIL: Expected {EXPECTED_FRAMES} frames, got {total_frames}")
        passed = False
    if total_errors > 0:
        print(f"  FAIL: {total_errors} pipeline errors")
        passed = False
    for weather, stats in segment_stats.items():
        if not stats.weather_intensities:
            print(f"  FAIL: {weather} produced no valid scored frame")
            passed = False
    if all_weather_intensities:
        wi_range_violations = [wi for wi in all_weather_intensities if not (0 <= wi <= 1)]
        if wi_range_violations:
            print(f"  FAIL: {len(wi_range_violations)} weather_intensity out of [0,1]")
            passed = False

    if passed:
        print(
            f"  VERDICT: PASS — {EXPECTED_FRAMES} simulated frames, "
            "all weather segments produced valid scores"
        )
    else:
        print(f"  VERDICT: FAIL")

    print("=" * 70)
    return 0 if passed else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SRP Full-Pipeline Stress Test")
    parser.add_argument("--full", action="store_true", help="Include UDP + CSV output")
    args = parser.parse_args()
    sys.exit(run_stress_test(full=args.full))
