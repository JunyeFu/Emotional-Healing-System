"""Commands used by agent/runtime/bigrun.py. Does not start an experiment."""
import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import time
from uuid import uuid4

import numpy as np

from .calibration import (calibrate_heart, fit_respiration, read_csv, sample_rate,
                          validate_respiration)
from .driver import BigRunDriver
from .recording import CandidateRecording, SCOPE, export_recording, inspect_recording


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2, allow_nan=False)
        handle.write("\n")


async def scan(seconds):
    from bleak import BleakScanner
    devices = await BleakScanner.discover(timeout=seconds)
    for device in devices:
        print(json.dumps({"name": device.name, "address": device.address}))


async def capture(args):
    resp_profile = json.loads(args.resp_profile.read_text(encoding="utf-8")) if args.resp_profile else None
    heart_profile = json.loads(args.heart_profile.read_text(encoding="utf-8")) if args.heart_profile else None
    if heart_profile and (args.ecg_hz is None or not np.isclose(heart_profile["ecg_hz"], args.ecg_hz)):
        raise ValueError("HEART_PROFILE_ECG_RATE_MISMATCH")
    settings = {"mode_requested": args.mode, "ecg_hz_nominal": args.ecg_hz,
                "acc_hz_nominal": args.acc_hz, "resp_profile": resp_profile,
                "heart_profile": heart_profile}
    recording = CandidateRecording(args.root, "BIGRUN-" + uuid4().hex, "real", settings)
    driver = None
    status = "ABORTED"
    frames = None
    publisher = None
    error = None
    snapshot = {"heart_profile_loaded": bool(heart_profile), "resp_warmed_up": False}
    try:
        if args.td:
            from .td_stream import TDPublisher
            publisher = TDPublisher(recording, args.ecg_hz, args.acc_hz)
        driver = BigRunDriver(args.address, recording, mode=args.mode, ecg_hz=args.ecg_hz,
                              acc_hz=args.acc_hz, resp_profile=resp_profile,
                              packet_observer=publisher.packet if publisher else None)
        if args.frames:
            frames = args.frames.open("x", encoding="utf-8")
        print(f"ARCHIVE={recording.path}", flush=True)
        print("DEVELOPMENT_UNVERIFIED; no SessionCore start, no mock input, no experiment actions.", flush=True)
        await driver.connect()
        snapshot["connection_phase"] = driver.connection_phase
        recording.connection_status(driver.connection_phase)
        if publisher:
            publisher.status(driver, snapshot)
        await driver.start_streaming()
        recording.connection_status(driver.connection_phase)
        begin = time.monotonic()
        while args.seconds is None or time.monotonic() - begin < args.seconds:
            done, _ = await asyncio.wait({driver.failure}, timeout=1)
            if done:
                await driver.failure
            if not driver.is_connected:
                raise ConnectionError("BIGRUN_DISCONNECTED")
            frame = driver.drain_frame()
            hr = (driver.hr_bpm if driver.hr_received_ns is not None and
                  time.monotonic_ns() - driver.hr_received_ns < 2_000_000_000 else None)
            hr_source = "device_hr_packet" if hr is not None else None
            if hr is None and heart_profile and args.ecg_hz:
                samples = driver.ecg_buffer.read_after(time.monotonic() - 10)
                if len(samples) >= args.ecg_hz * 5 and frame.ecg_samples:
                    import neurokit2 as nk
                    ecg = np.array([v for _, v in samples]) * heart_profile["polarity"]
                    cleaned = nk.ecg_clean(ecg, sampling_rate=int(round(args.ecg_hz)))
                    _, info = nk.ecg_peaks(cleaned, sampling_rate=int(round(args.ecg_hz)))
                    peaks = info["ECG_R_Peaks"]
                    if len(peaks) >= 3:
                        hr = float(60 * args.ecg_hz / np.median(np.diff(peaks)))
                        hr_source = "ecg_past_window_estimate"
            warmed = bool(driver.resp_estimator and driver.resp_estimator.warmed_up)
            snapshot = {
                "evidence_scope": SCOPE, "host_monotonic_s": frame.timestamp,
                "packet_counts": dict(recording.counts), "reported_config": driver.config,
                "mode_readback_verified": driver.mode_readback_verified,
                "connection_phase": driver.connection_phase,
                "heart_rate_bpm": hr, "heart_source": hr_source,
                "respiration_proxy": frame.respiration_raw if warmed else None,
                "respiration_status": "ESTIMATE_UNVERIFIED" if warmed else "UNAVAILABLE_OR_WARMUP",
                "breath_phase": "unknown", "hold": "unknown", "topup": "unknown",
                "timing": "NOMINAL_SAMPLE_INDEX_UNVERIFIED",
                "heart_profile_loaded": bool(heart_profile), "resp_warmed_up": warmed,
            }
            print(json.dumps(snapshot, allow_nan=False), flush=True)
            if publisher:
                # Scope is fixed in the transport envelope, not repeated in the payload.
                publisher.status(driver, {k: v for k, v in snapshot.items() if k != "evidence_scope"})
            if frames:
                frames.write(json.dumps({**snapshot, "raw_frame": asdict(frame)}, allow_nan=False) + "\n")
                frames.flush()
        status = "COMPLETED"
    except BaseException as exc:
        phase = driver.connection_phase if driver else "setup"
        snapshot["connection_phase"] = phase
        error = f"{type(exc).__name__}: phase={phase}: {exc}"
        print(error, flush=True)
        recording.connection_status(phase, error)
        raise
    finally:
        try:
            if driver is not None:
                await driver.stop()
                if driver.failure is not None and driver.failure.done() and not driver.failure.cancelled():
                    driver.failure.exception()
        finally:
            try:
                if publisher and driver:
                    publisher.status(driver, {k: v for k, v in snapshot.items() if k != "evidence_scope"}, error)
            finally:
                if publisher:
                    publisher.close()
                if frames:
                    frames.close()
                recording.close(status)


def main(argv=None):
    parser = argparse.ArgumentParser(description="BigRun single-device DEVELOPMENT_UNVERIFIED candidate")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("scan", help="Explicitly scan BLE devices; never auto-connect")
    p.add_argument("--seconds", type=float, default=5)
    p = sub.add_parser("capture", help="Raw capture; waits for manual experiment operation elsewhere")
    p.add_argument("--address", required=True)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3] / "local/artifacts/bigrun-preflight")
    p.add_argument("--mode", choices=["observe", "sport", "ecg", "hrv"], default="observe")
    p.add_argument("--ecg-hz", type=float)
    p.add_argument("--acc-hz", type=float)
    p.add_argument("--seconds", type=float, help="Omit to keep receiving until Ctrl+C")
    p.add_argument("--resp-profile", type=Path)
    p.add_argument("--heart-profile", type=Path)
    p.add_argument("--frames", type=Path, help="Optional candidate RawFrame JSONL, not formal UDP telemetry")
    p.add_argument("--td", action="store_true", help="Send real-only BigRun preview to local TD UDP5005; no experiment actions")
    p = sub.add_parser("export", help="Export P-02 raw data with explicitly nominal rates")
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--ecg-hz", type=float, required=True)
    p.add_argument("--acc-hz", type=float, required=True)
    p = sub.add_parser("inspect", help="Count observed streams/interleaving; no hardware PASS")
    p.add_argument("--session", type=Path, required=True)
    for command_name in ("calibrate-heart", "validate-heart"):
        p = sub.add_parser(command_name)
        p.add_argument("--ecg", type=Path, required=True)
        p.add_argument("--reference-beats", type=Path, required=True,
                       help="Independent reference R peaks: CSV time_s (seconds)")
        p.add_argument("--out", type=Path, required=True)
        if command_name == "calibrate-heart":
            p.add_argument("--polarity", type=int, choices=[-1, 1], required=True)
            p.add_argument("--reference-delay-s", type=float, default=0)
            p.add_argument("--tolerance-s", type=float, default=.1, help="Technical matching window, not an acceptance threshold")
        else:
            p.add_argument("--profile", type=Path, required=True)
    for command_name in ("calibrate-resp", "validate-resp"):
        p = sub.add_parser(command_name)
        p.add_argument("--acc", type=Path, required=True)
        p.add_argument("--reference", type=Path, required=True,
                       help="Independent respiration CSV: time_s,value; never use the guide")
        p.add_argument("--out", type=Path, required=True)
        if command_name == "calibrate-resp":
            p.add_argument("--acc-hz", type=float, required=True)
            p.add_argument("--band-hz", type=float, nargs=2, default=[.04, .8])
            p.add_argument("--reference-delay-s", type=float, default=0)
        else:
            p.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "scan":
        asyncio.run(scan(args.seconds))
    elif args.command == "capture":
        if args.seconds is not None and args.seconds <= 0:
            parser.error("--seconds must be positive")
        try:
            asyncio.run(capture(args))
        except KeyboardInterrupt:
            print("Capture interrupted; archive closed as ABORTED, not a failed experiment.")
    elif args.command == "export":
        if not all(np.isfinite(v) and v > 0 for v in (args.ecg_hz, args.acc_hz)):
            parser.error("Nominal rates must be finite and positive")
        print(json.dumps(export_recording(args.session, args.out, args.ecg_hz, args.acc_hz)))
    elif args.command == "inspect":
        print(json.dumps(inspect_recording(args.session), indent=2, allow_nan=False))
    elif args.command.endswith("heart"):
        ecg = read_csv(args.ecg, ["time_s", "value"])
        ref = read_csv(args.reference_beats, ["time_s"])[:, 0]
        if args.command == "validate-heart":
            profile = json.loads(args.profile.read_text(encoding="utf-8"))
            if args.ecg.resolve() == Path(profile["calibration_ecg"]).resolve():
                raise ValueError("VALIDATION_REQUIRES_DIFFERENT_RECORDING")
            if not np.isclose(sample_rate(ecg[:, 0]), profile["ecg_hz"]):
                raise ValueError("HEART_PROFILE_ECG_RATE_MISMATCH")
            polarity, delay, tolerance = (profile[k] for k in ("polarity", "reference_delay_s", "tolerance_s"))
        else:
            polarity, delay, tolerance = args.polarity, args.reference_delay_s, args.tolerance_s
        result = calibrate_heart(ecg[:, 0], ecg[:, 1], ref, polarity, delay, tolerance)
        result["operation"] = args.command
        result["calibration_ecg"] = str(args.ecg.resolve())
        write_json(args.out, result)
    else:
        acc = read_csv(args.acc, ["time_s", "x", "y", "z"])
        ref = read_csv(args.reference, ["time_s", "value"])
        if args.command == "calibrate-resp":
            result = fit_respiration(acc[:, 0], acc[:, 1:], ref[:, 0], ref[:, 1],
                                     args.acc_hz, args.band_hz, args.reference_delay_s)
            result["calibration_acc"] = str(args.acc.resolve())
        else:
            profile = json.loads(args.profile.read_text(encoding="utf-8"))
            if args.acc.resolve() == Path(profile["calibration_acc"]).resolve():
                raise ValueError("VALIDATION_REQUIRES_DIFFERENT_RECORDING")
            result = validate_respiration(profile, acc[:, 0], acc[:, 1:], ref[:, 0], ref[:, 1])
            result["operation"] = args.command
        write_json(args.out, result)


if __name__ == "__main__":
    main()
