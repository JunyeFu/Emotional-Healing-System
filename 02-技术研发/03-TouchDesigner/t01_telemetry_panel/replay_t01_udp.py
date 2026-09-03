"""Drive the T-01 UDP input with signed v2.2 fixtures or the real publisher."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
import time


BASE_DIR = Path(__file__).resolve().parent
TECH_ROOT = BASE_DIR.parents[1]
if str(TECH_ROOT) not in sys.path:
    sys.path.insert(0, str(TECH_ROOT))

from srp_session_core import (  # noqa: E402
    AssignmentBundle,
    OperatorRequest,
    SessionCore,
    load_breath_protocol_config,
)
from srp_session_core.transport import TelemetryPublisher  # noqa: E402


FIXTURE_DIR = TECH_ROOT / "05-通信协议" / "contracts" / "fixtures-v2.2" / "valid"
TARGET = ("127.0.0.1", 5005)
SESSION_ID = "S-20260901-0001"
CLOCK_DOMAIN = "python:t01-panel-evidence"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _send_frames(frames: list[dict], *, interval_s: float = 0.055) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for frame in frames:
            sock.sendto(
                json.dumps(frame, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                TARGET,
            )
            time.sleep(interval_s)


def fixture_frames(repeat_count: int = 1) -> list[dict]:
    names = (
        "telemetry-storm-hold-1.json",
        "telemetry-storm-hold-2.json",
        "telemetry-fade-inhale-1.json",
        "telemetry-fade-inhale-2.json",
        "telemetry-actual-unavailable.json",
    )
    frames = []
    seq = 0
    for _ in range(repeat_count):
        for name in names:
            seq += 1
            frame = _fixture(name)
            frame.update(session_id=SESSION_ID, clock_domain_id=CLOCK_DOMAIN, frame_seq=seq)
            frames.append(frame)
    return frames


def anomaly_frames(continuation_count: int = 0) -> list[dict]:
    base = _fixture("telemetry-fade-inhale-1.json")
    base.update(session_id=SESSION_ID, clock_domain_id=CLOCK_DOMAIN)
    frames = []
    for seq in (100, 103, 103, 102):
        frame = deepcopy(base)
        frame["frame_seq"] = seq
        frames.append(frame)
    for seq in range(104, 104 + continuation_count):
        frame = deepcopy(base)
        frame["frame_seq"] = seq
        frames.append(frame)
    return frames


def recovery_frames(count: int = 1) -> list[dict]:
    frames = []
    for seq in range(1, count + 1):
        frame = _fixture("telemetry-fade-inhale-2.json")
        frame.update(
            session_id=SESSION_ID,
            clock_domain_id="python:t01-panel-recovery",
            frame_seq=seq,
        )
        frames.append(frame)
    return frames


def _manifest() -> dict:
    breath = load_breath_protocol_config()
    return {
        "schema_version": "2.2",
        "message_type": "session_manifest",
        "research_id": "SRP-R-0123456789abcdef0123456789abcdef",
        "session_id": SESSION_ID,
        "study_stage": "stage_1",
        "runtime_mode": "dev_replay",
        "cue_mode": "scene_native",
        "assignment_arm": "scene_native",
        "allocation_index": 7,
        "randomization_stratum": "na_pre_low",
        "randomization_block": 1,
        "randomization_list_hash": "sha256:t01-evidence-list",
        "weather_sequence": ["fade", "storm", "heat", "snow"],
        "module_durations": {"demo": 25, "closed_loop": 150, "lock_transition": 25},
        "protocol_config_version": "1.1",
        "randomization_version": "1.0",
        "strategy_version": None,
        "device_config": {"resp": {"source": "none"}, "ecg": {"source": "none"}},
        "unity_build_hash": "sha256:t01-evidence-unity",
        "python_commit": "t01-candidate",
        "td_build_hash": None,
        "source_policy": "replay",
        "created_utc": "2026-09-01T00:00:00Z",
        "breath_protocol_config_version": breath.breath_protocol_config_version,
        "breath_protocol_config_hash": breath.config_hash,
    }


def _assignment(manifest: dict) -> AssignmentBundle:
    sequence = tuple(manifest["weather_sequence"])
    remaining = list(sequence)
    decisions = []
    for position, selected in enumerate(sequence):
        candidates = list(remaining)
        decisions.append(
            {
                "schema_version": "2.2",
                "message_type": "policy_decision",
                "decision_id": f"PD-T01-{position}",
                "session_id": SESSION_ID,
                "stage": "stage_1",
                "position": position,
                "candidate_actions": candidates,
                "selected_action": selected,
                "behavior_probability": 1 / len(candidates),
                "target_policy_probability": None,
                "state_snapshot_hash": f"sha256:t01-state-{position}",
                "random_draw": position / 10,
                "reason_code": "FIXED_SEQUENCE_ASSIGNMENT",
                "fallback_applied": False,
                "fallback_reason": None,
                "policy_version": None,
                "created_monotonic_ns": position,
            }
        )
        remaining.remove(selected)
    return AssignmentBundle(
        allocation_index=7,
        randomization_list_hash=manifest["randomization_list_hash"],
        weather_sequence=sequence,
        policy_decisions=tuple(decisions),
        permit_id="PERMIT-T01",
        reservation_id="RES-T01",
    )


def publish_from_real_session_core(count: int = 5) -> None:
    manifest = _manifest()
    core = SessionCore()
    core.prepare(manifest, _assignment(manifest), 0)
    core.apply_operator_request(OperatorRequest("REQ-T01-START", "start"), 0)
    snapshot = core.snapshot()
    template = _fixture("telemetry-fade-inhale-1.json")
    publisher = TelemetryPublisher(core, targets=(TARGET,))
    try:
        for seq in range(1, count + 1):
            now_ns = time.monotonic_ns()
            frame = deepcopy(template)
            frame.update(
                session_id=snapshot.session_id,
                frame_seq=seq,
                clock_domain_id="python:t01-session-core",
                source_monotonic_ns=now_ns - 2_000_000,
                received_monotonic_ns=now_ns - 1_000_000,
                sent_monotonic_ns=now_ns,
                module_id=snapshot.module_id,
                module_position=snapshot.module_position,
                segment=snapshot.segment,
                cue_mode=snapshot.cue_mode,
                runtime_mode=snapshot.runtime_mode,
                policy_decision_id="PD-T01-0",
            )
            if not publisher.publish(frame):
                raise RuntimeError("real TelemetryPublisher unexpectedly throttled a 20 Hz frame")
            time.sleep(0.055)
    finally:
        publisher.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("publisher", "fixtures", "anomaly", "recover"))
    parser.add_argument("--count", type=int, default=None)
    args = parser.parse_args()
    if args.mode == "publisher":
        publish_from_real_session_core(args.count or 5)
    elif args.mode == "fixtures":
        _send_frames(fixture_frames(args.count or 1))
    elif args.mode == "anomaly":
        _send_frames(anomaly_frames(args.count or 0))
    else:
        _send_frames(recovery_frames(args.count or 1))
    print(f"T01_UDP_REPLAY_COMPLETE mode={args.mode} target={TARGET[0]}:{TARGET[1]}")


if __name__ == "__main__":
    main()
