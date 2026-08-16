from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import time
import tracemalloc
from typing import Any


MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from srp_session_store import RawPacket, ReplayReader, SessionArchive, load_store_config
from srp_session_store.canonical import domain_hash


def _manifest(session_id: str) -> dict[str, Any]:
    return {
        "schema_version": "2.1",
        "message_type": "session_manifest",
        "research_id": "SRP-R-P02-STRESS",
        "session_id": session_id,
        "study_stage": "stage_1",
        "runtime_mode": "dev_replay",
        "cue_mode": "scene_native",
        "assignment_arm": "scene_native",
        "allocation_index": 1,
        "randomization_stratum": "stress_fixture",
        "randomization_block": 1,
        "randomization_list_hash": "sha256:p02-stress-list",
        "weather_sequence": ["storm", "heat", "snow", "fade"],
        "module_durations": {"demo": 25, "closed_loop": 150, "lock_transition": 25},
        "protocol_config_version": "1.1",
        "randomization_version": "1.0",
        "strategy_version": None,
        "device_config": {"resp": {"source": "none"}, "ecg": {"source": "none"}},
        "unity_build_hash": "sha256:p02-stress-unity",
        "python_commit": "p02-stress-generator",
        "td_build_hash": None,
        "source_policy": "replay",
        "created_utc": "2026-08-16T00:00:00Z",
    }


def run_stress(duration_seconds: int = 800) -> dict[str, Any]:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    session_id = f"S-P02-STRESS-{duration_seconds:04d}"
    config = load_store_config()
    raw_payload = b"".join(index.to_bytes(2, "little") for index in range(400))
    polar_payload = b"".join(index.to_bytes(2, "little") for index in range(130))
    tracemalloc.start()
    started = time.perf_counter()
    baseline_memory = 0
    memory_samples: list[int] = []
    with tempfile.TemporaryDirectory(prefix="p02-stress-") as temporary:
        root = Path(temporary)
        archive = SessionArchive.create(
            root,
            _manifest(session_id),
            protocol_config_hash="sha256:p02-stress-protocol",
            store_config=config,
        )
        for second in range(duration_seconds):
            base_ns = second * 1_000_000_000
            archive.append_raw_packet(
                RawPacket(
                    source_id="plux_respiban",
                    source_policy="replay",
                    packet_seq=second,
                    device_time_ns=base_ns,
                    host_received_monotonic_ns=base_ns,
                    clock_domain_id="device:plux",
                    sample_count=400,
                    payload=raw_payload,
                )
            )
            archive.append_raw_packet(
                RawPacket(
                    source_id="polar_h10_ecg",
                    source_policy="replay",
                    packet_seq=second,
                    device_time_ns=base_ns,
                    host_received_monotonic_ns=base_ns + 1,
                    clock_domain_id="device:polar",
                    sample_count=130,
                    payload=polar_payload,
                )
            )
            for frame in range(20):
                frame_seq = second * 20 + frame
                now_ns = base_ns + frame * 50_000_000
                archive.append_l1(
                    "synced_frame",
                    {
                        "frame_seq": frame_seq,
                        "sample_count": 20,
                        "source_id": "plux_respiban",
                        "source_monotonic_ns": now_ns,
                    },
                    now_ns,
                )
            if second == min(99, duration_seconds - 1):
                baseline_memory = tracemalloc.get_traced_memory()[0]
            if second % 100 == 99 or second == duration_seconds - 1:
                memory_samples.append(tracemalloc.get_traced_memory()[0])
        seal = archive.seal(
            {"status": "COMPLETED", "reason_code": "STRESS_COMPLETE"},
            duration_seconds * 1_000_000_000,
        )
        archive.close()
        integrity = ReplayReader.open(root, session_id).verify()
        current_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.perf_counter() - started
    report = {
        "evidence_status": "P02_SYNTHETIC_STRESS_CANDIDATE",
        "duration_seconds": duration_seconds,
        "plux_sample_rate_hz": 400,
        "plux_packet_count": duration_seconds,
        "plux_sample_count": duration_seconds * 400,
        "polar_sample_rate_hz": 130,
        "polar_packet_count": duration_seconds,
        "polar_sample_count": duration_seconds * 130,
        "l1_frame_rate_hz": 20,
        "l1_frame_count": duration_seconds * 20,
        "archive_l0_count": integrity.l0_count,
        "archive_l1_count": integrity.l1_count,
        "integrity_valid": integrity.valid,
        "seal_hash": seal.seal_hash,
        "store_config_hash": config.config_hash,
        "elapsed_seconds": round(elapsed, 6),
        "memory_current_bytes": current_memory,
        "memory_peak_bytes": peak_memory,
        "memory_growth_after_warmup_bytes": max(0, current_memory - baseline_memory),
        "memory_sample_count": len(memory_samples),
        "memory_sample_span_bytes": (
            max(memory_samples) - min(memory_samples) if memory_samples else 0
        ),
    }
    stable = {key: value for key, value in report.items() if key not in {
        "elapsed_seconds", "memory_current_bytes", "memory_peak_bytes",
        "memory_growth_after_warmup_bytes", "memory_sample_span_bytes"
    }}
    report["stable_result_hash"] = domain_hash(b"srp:p02:stress-result:v1\0", stable)
    return report


def main() -> int:
    report = run_stress()
    output = Path(__file__).with_name("evidence") / "synthetic_stress_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(output)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report["integrity_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
