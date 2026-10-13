"""Deterministic host-side node and permission plan for T-01."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


TD_BUILD = "2025.32820"
ROOT_PATH = "/project1/T01_TelemetryPanel"
PORT = 5005
LOCAL_ADDRESS = "127.0.0.1"


def _node(path: str, operator_type: str, role: str, permission: str = "read_only", **extra: Any) -> dict[str, Any]:
    return {
        "path": path,
        "operator_type": operator_type,
        "role": role,
        "permission": permission,
        **extra,
    }


def build_node_plan() -> dict[str, Any]:
    nodes = [
        _node(ROOT_PATH, "containerCOMP", "t01_root"),
        _node(f"{ROOT_PATH}/Sources", "containerCOMP", "source_container"),
        _node(f"{ROOT_PATH}/Sources/UdpTelemetryAdapter", "containerCOMP", "udp_adapter"),
        _node(
            f"{ROOT_PATH}/Sources/UdpTelemetryAdapter/udp_in",
            "udpinDAT",
            "telemetry_input",
            permission="loopback_input",
            active=True,
            port=PORT,
            local_address=LOCAL_ADDRESS,
            callback_format="one_per_message",
        ),
        _node(
            f"{ROOT_PATH}/Sources/UdpTelemetryAdapter/udp_callbacks",
            "textDAT",
            "telemetry_callbacks",
            permission="local_state_update",
            callback="onReceive",
        ),
        _node(f"{ROOT_PATH}/Runtime", "containerCOMP", "runtime_container"),
        _node(f"{ROOT_PATH}/Runtime/t01_adapter_module", "textDAT", "embedded_adapter_module"),
        _node(f"{ROOT_PATH}/Runtime/panel_state", "textDAT", "local_display_state"),
        _node(
            f"{ROOT_PATH}/Runtime/render_execute",
            "executeDAT",
            "render_tick",
            permission="local_display_update",
            callback="onFrameStart",
            maximum_hz=20,
        ),
        _node(f"{ROOT_PATH}/ConsoleShell", "containerCOMP", "console_shell"),
        _node(f"{ROOT_PATH}/ConsoleShell/background", "constantTOP", "background"),
        _node(f"{ROOT_PATH}/ConsoleShell/stream_badge", "rectangleTOP", "stream_badge"),
        _node(f"{ROOT_PATH}/ConsoleShell/resp_sqi_bar", "rectangleTOP", "resp_sqi_bar"),
        _node(f"{ROOT_PATH}/ConsoleShell/ecg_sqi_bar", "rectangleTOP", "ecg_sqi_bar"),
        _node(f"{ROOT_PATH}/ConsoleShell/panel_text", "textTOP", "telemetry_text"),
        _node(f"{ROOT_PATH}/ConsoleShell/composite", "compositeTOP", "console_composite"),
        _node(f"{ROOT_PATH}/Output", "containerCOMP", "output_container"),
        _node(f"{ROOT_PATH}/Output/display_source", "selectTOP", "local_display_source"),
        _node(f"{ROOT_PATH}/Output/display_out", "outTOP", "local_display_output"),
        _node(f"{ROOT_PATH}/node_permissions", "tableDAT", "permission_manifest"),
        _node(f"{ROOT_PATH}/node_errors", "tableDAT", "error_report"),
    ]
    return {
        "plan_schema_version": "t01-node-plan-v1",
        "touchdesigner_required_build": TD_BUILD,
        "replace_scope": ROOT_PATH,
        "replacement_policy": "replace_exact_root_only",
        "network_contract": {
            "direction": "input_only",
            "address": LOCAL_ADDRESS,
            "port": PORT,
            "telemetry_hz": 20,
            "authoritative_state_write": False,
        },
        "nodes": nodes,
    }


def _canonical_json(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, data: Any) -> str:
    content = _canonical_json(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return sha256(content).hexdigest().upper()


def write_host_artifacts(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    plan = build_node_plan()
    permissions = {
        "permission_manifest_schema_version": "t01-node-permissions-v1",
        "authority": "PYTHON_SESSION_CORE",
        "network_outputs": [],
        "spout_outputs": [],
        "file_outputs": [],
        "t02_request_callbacks": [],
        "nodes": [
            {
                key: node[key]
                for key in node
                if key in {
                    "path",
                    "operator_type",
                    "role",
                    "permission",
                    "active",
                    "port",
                    "local_address",
                    "callback",
                    "maximum_hz",
                }
            }
            for node in plan["nodes"]
        ],
    }
    fields = {
        "field_manifest_schema_version": "t01-fields-v1",
        "contract_fields": [
            "schema_version",
            "session_id",
            "runtime_mode",
            "frame_seq",
            "resp_device_state",
            "ecg_device_state",
            "signal_quality.resp",
            "signal_quality.ecg",
            "target_cycle_index",
            "target_step_id",
            "target_phase",
            "target_progress",
            "actual_cycle_index",
            "actual_step_id",
            "actual_phase",
            "actual_progress",
            "source_monotonic_ns",
            "received_monotonic_ns",
            "sent_monotonic_ns",
            "clock_offset_ns",
            "clock_drift_ppm",
            "sync_uncertainty_ns",
            "fallback_state",
            "fallback_reason",
        ],
        "display_only_fields": [
            "stream_state",
            "frame_age_ms",
            "accepted_interval_ms",
            "lost_frames",
            "duplicate_frames",
            "out_of_order_frames",
            "invalid_frames",
            "reconnect_count",
            "last_error",
        ],
        "forbidden_inference": ["target_step_id_from_phase", "actual_step_id_from_history"],
    }
    hashes = {
        "node_plan.json": _write_json(output / "node_plan.json", plan),
        "node_permissions.json": _write_json(output / "node_permissions.json", permissions),
        "field_manifest.json": _write_json(output / "field_manifest.json", fields),
    }
    manifest = {
        "manifest_schema_version": "t01-host-build-manifest-v1",
        "touchdesigner_required_build": TD_BUILD,
        "node_count": len(plan["nodes"]),
        "artifact_hashes": hashes,
        "evidence_boundary": "HOST_PLAN_ONLY_NOT_TOUCHDESIGNER_RUNTIME",
    }
    _write_json(output / "host_build_manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    print(json.dumps(write_host_artifacts(base / "evidence" / "host"), ensure_ascii=False, indent=2))
