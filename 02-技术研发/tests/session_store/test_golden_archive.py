from __future__ import annotations

import json
from pathlib import Path

from srp_session_store import ReplayReader, SessionReplayer
from srp_session_store.canonical import file_sha256
from srp_session_store.generate_golden_archive import build_archive
from srp_session_store.generate_stress_report import run_stress


def test_full_p01_golden_trace_is_recorded_and_replayed(tmp_path):
    evidence = build_archive(tmp_path)
    assert evidence["control_count"] == 19
    assert evidence["ack_count"] == 19
    assert evidence["render_receipt_count"] == 12
    assert evidence["session_event_count"] == 54
    assert evidence["operation_count"] == 46
    assert evidence["replay_valid"] is True


def test_accelerated_stress_fixture_keeps_exact_counts():
    report = run_stress(duration_seconds=3)
    assert report["plux_sample_count"] == 1200
    assert report["polar_sample_count"] == 390
    assert report["l1_frame_count"] == 60
    assert report["archive_l0_count"] == 6
    assert report["archive_l1_count"] == 61
    assert report["integrity_valid"] is True
    assert report["memory_stable"] is True
    assert "memory_live_growth_after_warmup_bytes" in report
    assert "memory_slope_bytes_per_100_seconds" in report
    assert "memory_growth_limit_bytes" in report
    assert "memory_slope_limit_bytes_per_100_seconds" in report


def test_committed_golden_archive_hashes_and_replay_are_stable(tmp_path):
    fixture = (
        Path(__file__).resolve().parents[2]
        / "srp_session_store"
        / "fixtures"
        / "golden"
        / "session-archive-v1"
    )
    evidence = json.loads((fixture / "evidence.json").read_text(encoding="utf-8"))
    for item in evidence["files"]:
        path = fixture / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert file_sha256(path) == item["sha256"]
    reader = ReplayReader.open(fixture, "S-P01-GOLDEN-0001")
    assert reader.verify().valid
    assert SessionReplayer(reader).replay_core().actual_final_hash == evidence["replay_hash"]

    regenerated = build_archive(tmp_path)
    for key in (
        "control_count",
        "ack_count",
        "render_receipt_count",
        "session_event_count",
        "l1_count",
        "seal_hash",
        "final_state_hash",
        "replay_hash",
        "operation_count",
        "trace_hash",
    ):
        assert regenerated[key] == evidence[key]
