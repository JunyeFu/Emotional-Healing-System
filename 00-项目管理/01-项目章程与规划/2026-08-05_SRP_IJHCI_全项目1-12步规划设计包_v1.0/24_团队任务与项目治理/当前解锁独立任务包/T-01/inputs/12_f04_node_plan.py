"""Deterministic external plan and evidence files for the F-04 TD builder."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from f04_console import BANNER, PAGE_DEFINITIONS, SCENARIO_IDS, load_and_validate_fixture


TD_BUILD = "2025.32820"
ROOT_PATH = "/project1/F04_ReadonlyConsole"
VISUAL_MECHANISMS = {
    "session_version": "status_cards",
    "device_connection": "connection_badges_and_freshness_bars",
    "respiration_waveform": "dual_chop_waveform",
    "ecg_rr_quality": "quality_gauge_and_rr_strip",
    "phase_comparison": "dual_phase_tracks",
    "cycle_result": "summary_cards",
    "latency_clock": "latency_and_clock_bars",
    "degradation": "state_lane_and_timeline",
    "log_write": "write_state_and_counter_cards",
    "manual_actions": "disabled_action_controls",
}
VISUAL_ROLE_REQUIREMENTS = {
    "session_version": ("session_card", "version_card", "source_card"),
    "device_connection": ("resp_connection_badge", "ecg_connection_badge", "freshness_bar"),
    "respiration_waveform": ("page_waveform_view", "raw_channel_legend", "filtered_channel_legend"),
    "ecg_rr_quality": ("ecg_quality_gauge", "rr_interval_strip"),
    "phase_comparison": ("target_phase_track", "actual_phase_track"),
    "cycle_result": ("cycle_summary_card", "cycle_result_card"),
    "latency_clock": ("latency_bar", "clock_drift_bar"),
    "degradation": ("quality_state_lane", "degradation_timeline"),
    "log_write": ("log_write_state_card", "log_counter_card"),
    "manual_actions": (
        "manual_mark_control_visual",
        "abort_control_visual",
        "manual_mark_control_label",
        "abort_control_label",
    ),
}


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
        _node(ROOT_PATH, "containerCOMP", "f04_root"),
        _node(f"{ROOT_PATH}/ConsoleShell", "containerCOMP", "console_shell"),
        _node(f"{ROOT_PATH}/ConsoleShell/PersistentHeader", "textTOP", "persistent_header", banner=BANNER),
        _node(f"{ROOT_PATH}/ConsoleShell/PageNavigation", "containerCOMP", "page_navigation_container"),
        _node(f"{ROOT_PATH}/ConsoleShell/ScenarioNavigation", "containerCOMP", "scenario_navigation_container"),
        _node(f"{ROOT_PATH}/ConsoleShell/navigation_callbacks", "panelExecuteDAT", "local_navigation_callbacks"),
        _node(f"{ROOT_PATH}/ConsoleShell/ManualActionControls", "containerCOMP", "manual_action_controls"),
        _node(
            f"{ROOT_PATH}/ConsoleShell/ManualActionControls/manual_mark_disabled",
            "buttonCOMP",
            "disabled_action_control",
            permission="disabled_control",
            action_id="manual_mark",
            enabled=False,
            visible_in_shell=True,
            visible_on_page="manual_actions",
            label="MANUAL MARK / T-02 NOT ACTIVE",
            callback=None,
        ),
        _node(
            f"{ROOT_PATH}/ConsoleShell/ManualActionControls/abort_disabled",
            "buttonCOMP",
            "disabled_action_control",
            permission="disabled_control",
            action_id="abort",
            enabled=False,
            visible_in_shell=True,
            visible_on_page="manual_actions",
            label="ABORT / T-02 NOT ACTIVE",
            callback=None,
        ),
        _node(f"{ROOT_PATH}/Sources", "containerCOMP", "source_container"),
        _node(f"{ROOT_PATH}/Sources/StaticFixtureAdapter", "containerCOMP", "static_fixture_adapter"),
        _node(f"{ROOT_PATH}/Sources/StaticFixtureAdapter/fixture_json", "textDAT", "embedded_fixture"),
        _node(f"{ROOT_PATH}/page_manifest", "tableDAT", "page_manifest"),
        _node(f"{ROOT_PATH}/node_permissions", "tableDAT", "permission_manifest"),
        _node(f"{ROOT_PATH}/node_errors", "tableDAT", "error_report"),
        _node(
            f"{ROOT_PATH}/Sources/UdpTelemetryPlaceholder",
            "udpinDAT",
            "udp_placeholder",
            permission="disabled_input_placeholder",
            port=5005,
            active=False,
            label="T-01 NOT ACTIVE",
        ),
        _node(f"{ROOT_PATH}/SharedViews", "containerCOMP", "shared_view_container"),
        _node(f"{ROOT_PATH}/SharedViews/WaveformPanel", "containerCOMP", "waveform_panel"),
        _node(f"{ROOT_PATH}/Pages", "containerCOMP", "page_container"),
    ]
    for scenario_id in SCENARIO_IDS:
        waveform_path = f"{ROOT_PATH}/SharedViews/WaveformPanel/{scenario_id}"
        nodes.extend([
            _node(waveform_path, "containerCOMP", "waveform_scenario", scenario_id=scenario_id),
            _node(f"{waveform_path}/waveform_table", "tableDAT", "waveform_table", scenario_id=scenario_id),
            _node(f"{waveform_path}/dat_to_chop", "dattoCHOP", "waveform_dat_to_chop", scenario_id=scenario_id),
            _node(f"{waveform_path}/select", "selectCHOP", "waveform_select", scenario_id=scenario_id),
            _node(f"{waveform_path}/math", "mathCHOP", "waveform_math", scenario_id=scenario_id),
            _node(f"{waveform_path}/view", "opviewerTOP", "waveform_view", scenario_id=scenario_id),
        ])
    for index, page in enumerate(PAGE_DEFINITIONS):
        nodes.append(
            _node(
                f"{ROOT_PATH}/ConsoleShell/PageNavigation/{index + 1:02d}_{page['id']}",
                "buttonCOMP",
                "page_navigation",
                page_id=page["id"],
                selector_index=index,
                panel_position=[20 + (index % 5) * 244, 32 - (index // 5) * 32],
                visible_in_shell=True,
            )
        )
        page_path = f"{ROOT_PATH}/Pages/{page['id']}"
        nodes.append(_node(page_path, "containerCOMP", "page", page_id=page["id"]))
        nodes.append(_node(f"{page_path}/scenario_views", "containerCOMP", "scenario_view_container", page_id=page["id"]))
        for scenario_id in SCENARIO_IDS:
            scenario_path = f"{page_path}/scenario_views/{scenario_id}"
            nodes.extend([
                _node(scenario_path, "containerCOMP", "page_scenario", page_id=page["id"], scenario_id=scenario_id),
                _node(f"{scenario_path}/background", "constantTOP", "page_background", page_id=page["id"], scenario_id=scenario_id),
                _node(f"{scenario_path}/labels", "textTOP", "page_labels", page_id=page["id"], scenario_id=scenario_id),
                _node(f"{scenario_path}/view", "compositeTOP", "page_scenario_view", page_id=page["id"], scenario_id=scenario_id),
            ])
            for role in VISUAL_ROLE_REQUIREMENTS[page["id"]]:
                operator_type = (
                    "selectTOP" if role == "page_waveform_view"
                    else "textTOP" if role.endswith("_control_label")
                    else "rectangleTOP"
                )
                nodes.append(
                    _node(
                        f"{scenario_path}/{role}",
                        operator_type,
                        role,
                        page_id=page["id"],
                        scenario_id=scenario_id,
                    )
                )
        nodes.append(
            _node(
                f"{page_path}/view",
                "switchTOP",
                "page_view",
                page_id=page["id"],
                banner=BANNER,
                field_paths=list(page["field_paths"]),
                visual_mechanism=VISUAL_MECHANISMS[page["id"]],
            )
        )
    for index, scenario_id in enumerate(SCENARIO_IDS):
        nodes.append(
            _node(
                f"{ROOT_PATH}/ConsoleShell/ScenarioNavigation/{index + 1:02d}_{scenario_id}",
                "buttonCOMP",
                "scenario_navigation",
                scenario_id=scenario_id,
                selector_index=index,
                panel_position=[20 + index * 244, 0],
                visible_in_shell=True,
            )
        )
    nodes.extend(
        [
            _node(
                f"{ROOT_PATH}/ConsoleShell/ShellBackground",
                "constantTOP",
                "shell_background",
            ),
            _node(
                f"{ROOT_PATH}/ConsoleShell/PageViewport",
                "containerCOMP",
                "page_viewport",
                input_role="display_selector",
            ),
            _node(f"{ROOT_PATH}/Output", "containerCOMP", "output_container"),
            _node(f"{ROOT_PATH}/Output/page_selector", "switchTOP", "display_selector"),
            _node(
                f"{ROOT_PATH}/Output/shell_viewer",
                "opviewerTOP",
                "console_shell_view",
                viewer_target=f"{ROOT_PATH}/ConsoleShell",
            ),
            _node(
                f"{ROOT_PATH}/Output/display_out",
                "outTOP",
                "local_display_output",
                input_role="console_shell_view",
            ),
        ]
    )
    return {
        "plan_schema_version": "f04-node-plan-v2",
        "touchdesigner_required_build": TD_BUILD,
        "replace_scope": ROOT_PATH,
        "replacement_policy": "replace_exact_root_only",
        "nodes": nodes,
    }


def _canonical_json(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, data: Any) -> str:
    content = _canonical_json(data)
    path.write_bytes(content)
    return sha256(content).hexdigest().upper()


def write_host_artifacts(output_dir: str | Path, fixture_path: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    fixture = load_and_validate_fixture(fixture_path)
    plan = build_node_plan()
    pages = {
        "page_manifest_schema_version": "f04-page-manifest-v2",
        "banner": BANNER,
        "scenarios": list(SCENARIO_IDS),
        "pages": [
            {**page, "visual_mechanism": VISUAL_MECHANISMS[page["id"]]}
            for page in PAGE_DEFINITIONS
        ],
    }
    permissions = {
        "permission_manifest_schema_version": "f04-node-permissions-v1",
        "fixture_permissions": fixture["permissions"],
        "nodes": [
            {
                key: node[key]
                for key in node
                if key in {
                    "path", "operator_type", "role", "permission", "active", "port", "label",
                    "enabled", "action_id", "visible_in_shell", "panel_position", "input_role", "viewer_target",
                }
            }
            for node in plan["nodes"]
        ],
    }
    artifact_hashes = {
        "page_manifest.json": _write_json(output / "page_manifest.json", pages),
        "node_plan.json": _write_json(output / "node_plan.json", plan),
        "node_permissions.json": _write_json(output / "node_permissions.json", permissions),
    }
    fixture_bytes = Path(fixture_path).read_bytes()
    manifest = {
        "manifest_schema_version": "f04-host-build-manifest-v1",
        "touchdesigner_required_build": TD_BUILD,
        "fixture_schema_version": fixture["fixture_schema_version"],
        "fixture_sha256": sha256(fixture_bytes).hexdigest().upper(),
        "page_count": len(PAGE_DEFINITIONS),
        "scenario_count": len(fixture["scenarios"]),
        "page_scenario_combinations": len(PAGE_DEFINITIONS) * len(fixture["scenarios"]),
        "artifact_hashes": artifact_hashes,
        "evidence_boundary": "STATIC_HOST_ONLY_NOT_TOUCHDESIGNER_RUNTIME_NOT_LIVE",
    }
    _write_json(output / "host_build_manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    written = write_host_artifacts(
        base / "evidence" / "host",
        base / "fixtures" / "f04-static-display-fixture-v1.json",
    )
    print(json.dumps(written, ensure_ascii=False, indent=2))
