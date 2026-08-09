#!/usr/bin/env python3
"""
SRP Data Pipeline — Main Entry Point v0.4
===========================================
4-dimension physiological pipeline:
  mock data → signal processing → 4 independent scores → weather composite → UDP + CSV.

4 dimensions (non-overlapping ANS pathways):
  breath_sync    RR tracking accuracy     呼吸→副交感    PLUX呼吸带
  breath_depth   Amplitude / RSA depth    呼吸→副交感    PLUX呼吸带
  hrv_coherence  RMSSD recovery           副交感(迷走)   Polar H10
  eda_calm       SCL decrease             交感(皮肤电)   EDA腕带

Usage:
  python main.py --weather storm --duration 60
  python main.py --weather heat --duration 0     # infinite until Ctrl+C
  python main.py --weather snow --no-udp         # offline CSV only
  python main.py --real --weather storm --dur 300  # real device mode (stage 3)
  python main.py --real --no-ecg                   # skip ECG (demo mode)
"""

import sys
import os
import time
import atexit
import argparse
import logging
import signal
import importlib

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# How often to print each type of status
COMPACT_INTERVAL = 50     # every 5s: compact 1-line status
DETAIL_INTERVAL = 300     # every 30s: detailed 4-dimension table

LOCK_FILE = os.path.join(_root, ".pipeline.lock")


def _acquire_lock() -> bool:
    """Create PID lock file. Return False if another instance is running."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)
            except OSError:
                pass  # PID is dead, safe to overwrite
            else:
                logger.error(
                    f"Pipeline already running (PID {old_pid}). "
                    f"Stop it first or remove {LOCK_FILE}."
                )
                return False
        except (ValueError, FileNotFoundError):
            pass
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(_release_lock)
    return True


def _release_lock():
    try:
        os.remove(LOCK_FILE)
    except Exception:
        pass


def _import(module_name: str):
    return importlib.import_module(module_name)


def run_pipeline(args: argparse.Namespace):
    if not _acquire_lock():
        sys.exit(1)

    dur_label = f"{args.duration:.0f}s" if args.duration > 0 else "infinite (Ctrl+C to stop)"
    mock_label = "Real Device" if args.real else "Mock"

    # ── Startup header ────────────────────────────────────────────────────
    dim_spec = _import("02-信号处理.dimension_spec")
    presets = dim_spec.WEATHER_DIMENSION_PRESETS.get(
        args.weather, dim_spec.WEATHER_DIMENSION_PRESETS["storm"]
    )

    logger.info("=" * 60)
    logger.info(f"  SRP Data Pipeline v0.4 — 4-Dimension Mode")
    logger.info(f"  Mode: {mock_label} | Duration: {dur_label} | Weather: {args.weather}")
    logger.info("")
    logger.info(dim_spec.format_dimension_header(args.weather, presets))
    logger.info("")
    logger.info("  For live dashboard:  python visualizer.py --weather " + args.weather)
    logger.info("=" * 60)

    # ── Phase 1: Data Source ──────────────────────────────────────────────
    device_manager = None
    frame_generator = None

    if args.real:
        # ── Real Device Mode ──
        _01_path = os.path.join(_root, "01-数据采集")
        if _01_path not in sys.path:
            sys.path.insert(0, _01_path)
        from device_manager import DeviceManager
        from ring_buffer import RingBuffer

        device_manager = DeviceManager(rate_hz=10.0)

        # Register available devices based on CLI flags
        if not args.no_ecg:
            logger.warning(
                "Polar H10 driver not yet implemented (Phase C). "
                "Use --mock for simulated pipeline testing."
            )
        if not args.no_resp:
            logger.warning(
                "Respiration belt driver not yet implemented (Phase F). "
                "Use --mock for simulated pipeline testing."
            )
        if not args.no_eda:
            logger.warning(
                "EDA wristband driver not yet implemented (Phase F). "
                "Use --mock for simulated pipeline testing."
            )

        if not device_manager._drivers:
            logger.error("No devices registered. Use --mock mode for testing.")
            sys.exit(1)

        device_manager.start()
        logger.info(f"Connected devices: {device_manager.connected_devices}")

    else:
        # ── Mock Mode ──
        mock_data = _import("01-数据采集.mock_data")
        cfg = mock_data.MockConfig.for_weather(args.weather)
        frame_generator = mock_data.generate_frames(duration=args.duration, cfg=cfg)

    # ── Phase 2: Signal Processing ────────────────────────────────────────
    signal_pipeline_mod = _import("02-信号处理.signal_pipeline")
    scoring_model_mod = _import("02-信号处理.scoring_model")
    pipeline = signal_pipeline_mod.SignalPipeline()
    scorer = scoring_model_mod.ScoringModel(
        cfg=scoring_model_mod.ScoringConfig.for_weather(args.weather)
    )

    # ── Phase 3: Outputs ──────────────────────────────────────────────────
    udp_sender_mod = _import("05-通信协议.udp_sender")
    osc_sender_mod = _import("05-通信协议.osc_sender")
    csv_logger_mod = _import("05-通信协议.csv_logger")
    udp_sender = udp_sender_mod.UDPSender() if not args.no_udp else None
    osc_sender = osc_sender_mod.OSCSender() if not args.no_osc else None
    csv_log = csv_logger_mod.CSVLogger(prefix=f"sim_{args.weather}")
    csv_log.open()
    if udp_sender:
        logger.info(f"UDP → {[f'{h}:{p}' for h, p in udp_sender.targets]}")
    if osc_sender:
        logger.info(f"OSC → {osc_sender.host}:{osc_sender.port}")
    logger.info(f"CSV → {csv_log.filename}")
    logger.info("Pipeline running... (Ctrl+C to stop)")
    logger.info("")

    # ── Dimension scoring targets for display ─────────────────────────────
    dim_targets = {
        "breath_sync": presets.breath_sync.target_value,
        "breath_depth": presets.breath_depth.target_value,
        "hrv_coherence": presets.hrv_coherence.target_value,
        "eda_calm": presets.eda_calm.target_value,
    }

    # ── Phase 4: Main Loop ────────────────────────────────────────────────
    start_time = time.time()
    frame_idx = 0
    processed_count = 0
    shutdown = False

    def handle_signal(signum, frame):
        nonlocal shutdown
        logger.info("Shutdown signal received, stopping...")
        shutdown = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Source metadata for UDP v1.2
    udp_sources = {}
    if args.real:
        udp_sources = {
            "breath": "belt" if not args.no_resp else "none",
            "cardiac": "polar_h10" if not args.no_ecg else "none",
            "eda": "wristband" if not args.no_eda else "none",
        }
    else:
        udp_sources = {"breath": "mock", "cardiac": "mock", "eda": "mock"}

    try:
        while True:
            if shutdown:
                break

            # ── Read frame from source ──
            if device_manager:
                raw_frame = device_manager.read_frame(timeout=0.5)
                if raw_frame is None:
                    if not device_manager.is_running:
                        break
                    continue
            elif frame_generator:
                try:
                    raw_frame = next(frame_generator)
                except StopIteration:
                    break
            else:
                break

            frame_idx += 1

            processed = pipeline.feed(
                raw_frame.timestamp,
                raw_frame.respiration_raw,
                raw_frame.ecg_raw,
                raw_frame.eda_raw,
                raw_frame.acc_magnitude,
                raw_frame.temp_skin,
                ecg_samples=getattr(raw_frame, "ecg_samples", None),
            )

            # Warmup, missing channels, and invalid signal windows are not
            # business values. Do not emit neutral-looking telemetry or CSV.
            if processed is None:
                if not args.real:
                    time.sleep(0.1)
                continue

            score = scorer.score(
                processed,
                breath_phase=raw_frame.breath_phase,
                respiration_depth=raw_frame.respiration_depth,
                guidance_prompt=raw_frame.guidance_prompt,
                weather_type=raw_frame.weather_type,
            )

            score_dict = score.to_dict()

            # Build UDP meta for v1.2 (device status, signal quality)
            # Mock timestamps are logical replay time, not Unix wall time.
            pipeline_latency = (
                (time.time() - raw_frame.timestamp) * 1000 if args.real else 0.0
            )
            if device_manager:
                udp_meta = {
                    "frame_id": frame_idx,
                    "devices": {
                        name: "connected" if name in device_manager.connected_devices else "no_signal"
                        for name in ("ecg", "resp", "eda")
                    },
                    "signal_quality": device_manager.signal_quality,
                    "pipeline_latency_ms": pipeline_latency,
                    "buffer_backlog_frames": device_manager.queue_backlog,
                }
            else:
                udp_meta = {
                    "frame_id": frame_idx,
                    "devices": {"ecg": "mock", "resp": "mock", "eda": "mock"},
                    "signal_quality": {"ecg": "mock", "resp": "mock", "eda": "mock"},
                    "pipeline_latency_ms": pipeline_latency,
                    "buffer_backlog_frames": 0,
                }

            if udp_sender:
                udp_sender.send(score_dict, meta=udp_meta, sources=udp_sources)
            if osc_sender:
                osc_sender.send(udp_sender_mod.build_message(score_dict, meta=udp_meta, sources=udp_sources))
            csv_log.write(score_dict)
            processed_count += 1

            # Real-time pacing: 10 Hz → 100ms per frame (mock only; real paced by FrameClock)
            if not args.real:
                time.sleep(0.1)

            # ── Console Status ────────────────────────────────────────────
            if frame_idx % COMPACT_INTERVAL == 0:
                elapsed = time.time() - start_time
                _log_compact(elapsed, frame_idx, score, dim_targets)
            if frame_idx % DETAIL_INTERVAL == 0:
                elapsed = time.time() - start_time
                _log_detailed(elapsed, frame_idx, score, dim_targets, logger)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise
    finally:
        if device_manager:
            device_manager.stop()
        csv_log.close()
        if udp_sender:
            udp_sender.close()
        if osc_sender:
            osc_sender.close()

        elapsed = time.time() - start_time
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"  Pipeline complete in {elapsed:.1f}s")
        logger.info(f"  Frames generated: {frame_idx}")
        logger.info(f"  Frames processed: {processed_count}")
        logger.info(f"  Drop rate: {100*(frame_idx-processed_count)/max(frame_idx,1):.1f}%")
        if udp_sender:
            logger.info(f"  UDP: {udp_sender.stats()}")
        if osc_sender:
            logger.info(f"  OSC: {osc_sender.stats()}")
        logger.info(f"  CSV: {csv_log.stats()}")
        logger.info("=" * 60)


# ── Console Output Formatters ─────────────────────────────────────────────

def _log_compact(elapsed: float, frame_idx: int, score, targets: dict):
    """Compact single-line status showing 4 dimensions with raw→target values."""
    sync_str = f"sync={score.breath_sync:4.0f}(RR{score.rr:.0f}→{targets['breath_sync']:.0f}bpm)"
    depth_str = f"depth={score.breath_depth:4.0f}(amp{score.respiration_amplitude:.2f})"
    hrv_str = f"hrv={score.hrv_coherence:4.0f}(RMS{score.rmssd:.0f}→{targets['hrv_coherence']:.0f}ms)"
    eda_str = f"eda={score.eda_calm:4.0f}(SCL{score.eda_tonic:.1f}μS)"

    trend_icon = {"weakening": "↓", "stable": "→", "intensifying": "↑"}.get(
        score.weather_trend, "?")
    calm_str = f"calm={score.calm_index:.0f} {score.weather_type}{trend_icon}"

    logger.info(
        f"[{elapsed:5.0f}s] f={frame_idx:>4d} | "
        f"{sync_str} {depth_str} {hrv_str} {eda_str} | {calm_str}"
    )


def _log_detailed(elapsed: float, frame_idx: int, score, targets: dict, log):
    """Detailed 4-dimension table, printed every DETAIL_INTERVAL frames."""
    dim_spec_mod = _import("02-信号处理.dimension_spec")

    raw_vals = {
        "breath_sync": score.rr,
        "breath_depth": score.respiration_amplitude,
        "hrv_coherence": score.rmssd,
        "eda_calm": score.eda_tonic,
    }
    scores = {
        "breath_sync": score.breath_sync,
        "breath_depth": score.breath_depth,
        "hrv_coherence": score.hrv_coherence,
        "eda_calm": score.eda_calm,
    }

    report = dim_spec_mod.format_dimension_report(
        scores=scores,
        raw_values=raw_vals,
        targets=targets,
        calm_index=score.calm_index,
        weather_type=score.weather_type,
        weather_intensity=score.weather_intensity,
        weather_trend=score.weather_trend,
    )
    log.info(f"[{elapsed:.0f}s] f={frame_idx} — Detailed Report:\n" + report)


def main():
    parser = argparse.ArgumentParser(
        description="SRP 4-Dimension Physiological Pipeline — mock → scores → UDP + CSV",
    )
    parser.add_argument("--mock", action="store_true", default=True,
                        help="Use simulated data (default)")
    parser.add_argument("--real", action="store_true",
                        help="Use real devices (stage 3)")
    parser.add_argument("--no-ecg", action="store_true",
                        help="Skip ECG device (Polar H10)")
    parser.add_argument("--no-resp", action="store_true",
                        help="Skip respiration belt")
    parser.add_argument("--no-eda", action="store_true",
                        help="Skip EDA wristband")
    parser.add_argument("--duration", type=float, default=60.0,
                        help="Runtime in seconds. 0 = until Ctrl+C (default: 60)")
    parser.add_argument("--weather", type=str, default="storm",
                        choices=["storm", "heat", "snow", "fade"],
                        help="Weather type (default: storm)")
    parser.add_argument("--no-udp", action="store_true",
                        help="Disable UDP sending")
    parser.add_argument("--no-osc", action="store_true",
                        help="Disable OSC sending (to TD)")

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
