from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


BASE = Path(__file__).resolve().parents[1]
TECH_ROOT = BASE.parents[1]
F05_STREAM = (
    TECH_ROOT
    / "05-通信协议"
    / "contracts"
    / "consumer-fixtures"
    / "v2.2"
    / "touchdesigner"
    / "phase-instance-stream.jsonl"
)
F04_FIXTURE = (
    TECH_ROOT
    / "03-TouchDesigner"
    / "f04_readonly_console"
    / "fixtures"
    / "f04-static-display-fixture-v1.json"
)


sys.path.insert(0, str(BASE))
from t01_telemetry import (  # noqa: E402
    T01TelemetryAdapter,
    snapshot_to_dict,
    snapshot_to_panel_text,
)
from t01_node_plan import ROOT_PATH, build_node_plan, write_host_artifacts  # noqa: E402


def v22_frames() -> list[dict]:
    return [json.loads(line) for line in F05_STREAM.read_text(encoding="utf-8").splitlines()]


def v21_dev_frame() -> dict:
    fixture = json.loads(F04_FIXTURE.read_text(encoding="utf-8"))
    return fixture["scenarios"][0]["telemetry"]


def encode(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def render_after(adapter: T01TelemetryAdapter, now_ns: int):
    return adapter.read_snapshot(now_ns + adapter.render_interval_ns)


def test_f05_stream_preserves_step_instances_and_empty_actual_identity() -> None:
    adapter = T01TelemetryAdapter()
    frames = v22_frames()
    observed = []
    now_ns = 0
    for frame in frames:
        result = adapter.ingest_datagram(encode(frame), now_ns)
        assert result.accepted
        snapshot = render_after(adapter, now_ns)
        observed.append(
            (
                snapshot.telemetry["target_step_id"],
                snapshot.telemetry["actual_step_id"],
            )
        )
        now_ns += adapter.render_interval_ns

    assert observed == [
        ("hold_1", "inhale_1"),
        ("hold_2", "exhale_1"),
        ("inhale_1", "inhale_1"),
        ("inhale_2", "inhale_1"),
        ("exhale_1", None),
    ]
    assert adapter.read_snapshot(now_ns).display_only["phase_identity"]["actual_step"] == "UNAVAILABLE"


def test_snapshot_to_dict_converts_nested_immutable_mappings() -> None:
    adapter = T01TelemetryAdapter()
    frame = v22_frames()[0]
    assert adapter.ingest_datagram(encode(frame), 0).accepted
    plain = snapshot_to_dict(render_after(adapter, 0))
    assert isinstance(plain["telemetry"]["signal_quality"], dict)
    json.dumps(plain, ensure_ascii=False)


def test_formal_v21_is_rejected_but_dev_replay_v21_stays_compatible() -> None:
    adapter = T01TelemetryAdapter()
    dev = v21_dev_frame()
    assert adapter.ingest_datagram(encode(dev), 0).accepted
    snapshot = render_after(adapter, 0)
    assert snapshot.telemetry["schema_version"] == "2.1"
    assert snapshot.display_only["phase_identity"]["target_step"] == "UNAVAILABLE"

    formal = deepcopy(dev)
    formal["frame_seq"] += 1
    formal["runtime_mode"] = "formal_stage_1"
    result = adapter.ingest_datagram(encode(formal), adapter.render_interval_ns)
    assert not result.accepted
    assert result.code == "FORMAL_V21_REJECTED"
    assert adapter.read_snapshot(adapter.render_interval_ns * 2).telemetry["frame_seq"] == dev["frame_seq"]


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (lambda item: item.update(target_step_id="unknown"), "CONTRACT_INVALID_STEP_ID"),
        (lambda item: item.update(target_step_id="exhale_1"), "CONTRACT_STEP_PHASE_MISMATCH"),
        (lambda item: item.update(actual_cycle_index=None), "CONTRACT_INCOMPLETE_STEP_IDENTITY"),
    ],
)
def test_invalid_v22_identity_fails_closed(mutation, expected_code) -> None:
    adapter = T01TelemetryAdapter()
    frame = v22_frames()[0]
    mutation(frame)
    result = adapter.ingest_datagram(encode(frame), 0)
    assert not result.accepted
    assert result.code == expected_code
    assert not adapter.read_snapshot(adapter.render_interval_ns).telemetry


def test_unknown_compatible_field_is_filtered() -> None:
    adapter = T01TelemetryAdapter()
    frame = v22_frames()[0]
    frame["future_display_hint"] = "ignore"
    assert adapter.ingest_datagram(encode(frame), 0).accepted
    assert "future_display_hint" not in render_after(adapter, 0).telemetry


def test_gap_duplicate_and_out_of_order_do_not_replace_newest_frame() -> None:
    adapter = T01TelemetryAdapter()
    first = v22_frames()[0]
    assert adapter.ingest_datagram(encode(first), 0).disposition == "ACCEPTED"

    jumped = deepcopy(first)
    jumped["frame_seq"] = 23
    assert adapter.ingest_datagram(encode(jumped), 50_000_000).disposition == "ACCEPTED_WITH_GAP"

    duplicate = deepcopy(jumped)
    assert adapter.ingest_datagram(encode(duplicate), 60_000_000).disposition == "DUPLICATE"

    old = deepcopy(first)
    old["frame_seq"] = 22
    assert adapter.ingest_datagram(encode(old), 70_000_000).disposition == "OUT_OF_ORDER"

    snapshot = adapter.read_snapshot(100_000_000)
    assert snapshot.telemetry["frame_seq"] == 23
    transport = snapshot.display_only["transport"]
    assert transport["lost_frames"] == 2
    assert transport["duplicate_frames"] == 1
    assert transport["out_of_order_frames"] == 1


def test_session_and_clock_domain_changes_create_new_sequence_epochs() -> None:
    adapter = T01TelemetryAdapter()
    first = v22_frames()[0]
    adapter.ingest_datagram(encode(first), 0)

    new_session = deepcopy(first)
    new_session["session_id"] = "S-NEW"
    new_session["frame_seq"] = 0
    assert adapter.ingest_datagram(encode(new_session), 50_000_000).accepted

    restarted = deepcopy(new_session)
    restarted["clock_domain_id"] = "python-session-2"
    restarted["frame_seq"] = 0
    assert adapter.ingest_datagram(encode(restarted), 100_000_000).accepted

    snapshot = adapter.read_snapshot(150_000_000)
    transport = snapshot.display_only["transport"]
    assert snapshot.meta["epoch_index"] == 3
    assert transport["session_change_count"] == 1
    assert transport["source_restart_count"] == 1


def test_disconnect_and_recovery_require_a_new_valid_frame() -> None:
    adapter = T01TelemetryAdapter(disconnect_timeout_ns=2_000_000_000)
    first = v22_frames()[0]
    adapter.ingest_datagram(encode(first), 0)
    assert adapter.read_snapshot(50_000_000).meta["stream_state"] == "LIVE"
    assert adapter.read_snapshot(2_000_000_000).meta["stream_state"] == "DISCONNECTED"

    duplicate = adapter.ingest_datagram(encode(first), 2_100_000_000)
    assert duplicate.disposition == "DUPLICATE"
    assert adapter.read_snapshot(2_100_000_000).meta["stream_state"] == "DISCONNECTED"

    recovered = deepcopy(first)
    recovered["frame_seq"] += 1
    assert adapter.ingest_datagram(encode(recovered), 2_200_000_000).accepted
    snapshot = adapter.read_snapshot(2_200_000_000)
    assert snapshot.meta["stream_state"] == "LIVE"
    assert snapshot.display_only["transport"]["reconnect_count"] == 1


def test_invalid_data_does_not_replace_or_refresh_last_valid_frame() -> None:
    adapter = T01TelemetryAdapter(disconnect_timeout_ns=2_000_000_000)
    first = v22_frames()[0]
    adapter.ingest_datagram(encode(first), 0)
    assert adapter.ingest_datagram(b"not-json", 1_000_000_000).code == "INVALID_JSON"
    snapshot = adapter.read_snapshot(2_000_000_000)
    assert snapshot.meta["stream_state"] == "DISCONNECTED"
    assert snapshot.telemetry["frame_seq"] == first["frame_seq"]
    assert snapshot.display_only["transport"]["invalid_frames"] == 1


def test_render_snapshot_is_throttled_to_twenty_hz_while_ingest_counts_every_packet() -> None:
    adapter = T01TelemetryAdapter(telemetry_hz=20)
    waiting = adapter.read_snapshot(0)
    first = v22_frames()[0]
    adapter.ingest_datagram(encode(first), 1_000_000)
    assert adapter.read_snapshot(49_999_999) is waiting

    live = adapter.read_snapshot(50_000_000)
    assert live.meta["stream_state"] == "LIVE"
    duplicate = deepcopy(first)
    adapter.ingest_datagram(encode(duplicate), 55_000_000)
    assert adapter.read_snapshot(99_999_999) is live
    refreshed = adapter.read_snapshot(100_000_000)
    assert refreshed.display_only["transport"]["duplicate_frames"] == 1


def test_snapshot_exposes_contract_timing_without_claiming_cross_process_latency() -> None:
    adapter = T01TelemetryAdapter()
    frame = v22_frames()[0]
    adapter.ingest_datagram(encode(frame), 10_000_000)
    timing = render_after(adapter, 10_000_000).display_only["timing"]
    assert timing == {
        "source_to_received_ms": 0.05,
        "received_to_sent_ms": 0.05,
        "source_to_sent_ms": 0.1,
        "clock_offset_ns": 15000,
        "clock_drift_ppm": 0.4,
        "sync_uncertainty_ns": 8000,
    }
    text = snapshot_to_panel_text(render_after(adapter, 10_000_000))
    assert "STEP hold_1" in text
    assert "PYTHON FALLBACK GOOD" in text
    assert "NO AUTHORITY WRITEBACK" in text


def test_snapshot_is_deeply_immutable() -> None:
    adapter = T01TelemetryAdapter()
    adapter.ingest_datagram(encode(v22_frames()[0]), 0)
    snapshot = render_after(adapter, 0)
    with pytest.raises(TypeError):
        snapshot.telemetry["frame_seq"] = 999
    with pytest.raises(TypeError):
        snapshot.display_only["transport"]["lost_frames"] = 999


def test_node_plan_has_one_loopback_input_and_no_output_capabilities() -> None:
    plan = build_node_plan()
    assert plan["replace_scope"] == "/project1/T01_TelemetryPanel"
    inputs = [node for node in plan["nodes"] if node["operator_type"] == "udpinDAT"]
    assert inputs == [
        {
            "path": f"{ROOT_PATH}/Sources/UdpTelemetryAdapter/udp_in",
            "operator_type": "udpinDAT",
            "role": "telemetry_input",
            "permission": "loopback_input",
            "active": True,
            "port": 5005,
            "local_address": "127.0.0.1",
            "callback_format": "one_per_message",
        }
    ]
    forbidden = {
        "udpoutDAT",
        "tcpipDAT",
        "webclientDAT",
        "oscOutCHOP",
        "spoutOutTOP",
        "fileoutDAT",
        "fileoutCHOP",
        "fileoutTOP",
        "moviefileoutTOP",
    }
    assert not [node for node in plan["nodes"] if node["operator_type"] in forbidden]
    assert not [node for node in plan["nodes"] if "T-02" in str(node)]


def test_host_artifacts_are_deterministic_and_permission_closed(tmp_path: Path) -> None:
    first = write_host_artifacts(tmp_path)
    first_bytes = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    second = write_host_artifacts(tmp_path)
    assert first == second
    assert first_bytes == {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    permissions = json.loads((tmp_path / "node_permissions.json").read_text(encoding="utf-8"))
    assert permissions["network_outputs"] == []
    assert permissions["spout_outputs"] == []
    assert permissions["file_outputs"] == []
    assert permissions["t02_request_callbacks"] == []


def test_touchdesigner_builder_has_exact_root_and_read_only_callbacks() -> None:
    source = (BASE / "build_t01_touchdesigner.py").read_text(encoding="utf-8")
    assert "existing = op(ROOT_PATH)" in source
    assert "existing.destroy()" in source
    assert "def onReceive(dat, rowIndex, message, bytes, peer):" in source
    assert "def onFrameStart(frame):" in source
    assert "127.0.0.1" in source and "5005" in source
    assert "T01_TelemetryPanel.toe" in source
    assert "T01_TelemetryPanel.tox" in source
    for forbidden in ("udpoutDAT", "tcpipDAT", "spoutOutTOP", "moviefileoutTOP"):
        assert forbidden not in source
