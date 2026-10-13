"""Verify the saved F-04 project after a clean TouchDesigner reopen."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ROOT_PATH = "/project1/F04_ReadonlyConsole"
REPORT_PATH = BASE_DIR / "evidence" / "touchdesigner" / "reopen_report.json"
TOE_PATH = BASE_DIR / "F04_ReadonlyConsole.toe"
PAGE_IDS = (
    "session_version", "device_connection", "respiration_waveform",
    "ecg_rr_quality", "phase_comparison", "cycle_result",
    "latency_clock", "degradation", "log_write", "manual_actions",
)
SCENARIO_IDS = (
    "good_storm", "degraded_heat", "unusable_snow",
    "disconnected_fade", "out_of_order_storm",
)
VISUAL_ROLE_REQUIREMENTS = {
    "session_version": {"session_card", "version_card", "source_card"},
    "device_connection": {"resp_connection_badge", "ecg_connection_badge", "freshness_bar"},
    "respiration_waveform": {"page_waveform_view", "raw_channel_legend", "filtered_channel_legend"},
    "ecg_rr_quality": {"ecg_quality_gauge", "rr_interval_strip"},
    "phase_comparison": {"target_phase_track", "actual_phase_track"},
    "cycle_result": {"cycle_summary_card", "cycle_result_card"},
    "latency_clock": {"latency_bar", "clock_drift_bar"},
    "degradation": {"quality_state_lane", "degradation_timeline"},
    "log_write": {"log_write_state_card", "log_counter_card"},
    "manual_actions": {
        "manual_mark_control_visual",
        "abort_control_visual",
        "manual_mark_control_label",
        "abort_control_label",
    },
}


def _button_layout(parent_path, names):
    buttons = [op("{}/{}".format(parent_path, name)) for name in names]
    node_positions = {
        (button.nodeX, button.nodeY)
        for button in buttons
        if button is not None
    }
    panel_positions = {
        (int(button.par.x.eval()), int(button.par.y.eval()))
        for button in buttons
        if button is not None
    }
    return buttons, node_positions, panel_positions


def verify():
    root = op(ROOT_PATH)
    if root is None:
        raise RuntimeError("missing {}".format(ROOT_PATH))
    pages = [op("{}/Pages/{}".format(ROOT_PATH, page_id)) for page_id in PAGE_IDS]
    scenario_switches = [page.op("view") if page is not None else None for page in pages]
    output = op("{}/Output/page_selector".format(ROOT_PATH))
    shell = op("{}/ConsoleShell".format(ROOT_PATH))
    shell_viewer = op("{}/Output/shell_viewer".format(ROOT_PATH))
    display_out = op("{}/Output/display_out".format(ROOT_PATH))
    udp = op("{}/Sources/UdpTelemetryPlaceholder".format(ROOT_PATH))
    page_names = ["{:02d}_{}".format(index + 1, page_id) for index, page_id in enumerate(PAGE_IDS)]
    scenario_names = ["{:02d}_{}".format(index + 1, scenario_id) for index, scenario_id in enumerate(SCENARIO_IDS)]
    page_buttons, page_node_positions, page_panel_positions = _button_layout(
        "{}/ConsoleShell/PageNavigation".format(ROOT_PATH), page_names
    )
    scenario_buttons, scenario_node_positions, scenario_panel_positions = _button_layout(
        "{}/ConsoleShell/ScenarioNavigation".format(ROOT_PATH), scenario_names
    )
    manual_controls = [
        op("{}/ConsoleShell/ManualActionControls/{}".format(ROOT_PATH, action_id))
        for action_id in ("manual_mark_disabled", "abort_disabled")
    ]
    manual_callbacks = [
        node
        for node in op("{}/ConsoleShell/ManualActionControls".format(ROOT_PATH)).children
        if node.OPType in ("panelExecuteDAT", "parameterExecuteDAT")
    ]

    visual_roles_complete = True
    visual_roles_observed = {}
    for page_id, required_roles in VISUAL_ROLE_REQUIREMENTS.items():
        visual_roles_observed[page_id] = {}
        for scenario_id in SCENARIO_IDS:
            scenario = op("{}/Pages/{}/scenario_views/{}".format(ROOT_PATH, page_id, scenario_id))
            observed = {
                node.fetch("role", None)
                for node in scenario.findChildren(maxDepth=3)
            } if scenario is not None else set()
            visual_roles_observed[page_id][scenario_id] = sorted(role for role in observed if role)
            visual_roles_complete = visual_roles_complete and required_roles <= observed

    combinations_checked = 0
    combinations_rendered = True
    for page_index, scenario_switch in enumerate(scenario_switches):
        output.par.index = page_index
        for scenario_index in range(len(SCENARIO_IDS)):
            scenario_switch.par.index = scenario_index
            shell_viewer.cook(force=True)
            combinations_checked += 1
            combinations_rendered = combinations_rendered and not shell_viewer.errors(recurse=True)
        scenario_switch.par.index = 0
    output.par.index = 0
    errors = root.errors(recurse=True)
    script_errors = root.scriptErrors(recurse=True)
    checks = {
        "root_present": True,
        "page_count_10": all(page is not None for page in pages),
        "scenario_inputs_5_each": all(node is not None and len(node.inputs) == 5 for node in scenario_switches),
        "page_inputs_10": output is not None and len(output.inputs) == 10,
        "page_navigation_visible_unique": (
            all(button is not None and bool(button.par.display.eval()) for button in page_buttons)
            and len(page_node_positions) == 10
            and len(page_panel_positions) == 10
        ),
        "scenario_navigation_visible_unique": (
            all(button is not None and bool(button.par.display.eval()) for button in scenario_buttons)
            and len(scenario_node_positions) == 5
            and len(scenario_panel_positions) == 5
        ),
        "shell_is_final_output": (
            shell is not None
            and shell_viewer is not None
            and shell_viewer.fetch("viewer_target", None) == shell.path
            and display_out is not None
            and len(display_out.inputs) == 1
            and display_out.inputs[0] == shell_viewer
        ),
        "page_graphics_complete_50": visual_roles_complete,
        "manual_controls_visible_disabled_no_callbacks": (
            len(manual_controls) == 2
            and all(
                control is not None
                and control.fetch("role", None) == "disabled_action_control"
                and control.fetch("permission", None) == "disabled_control"
                and control.fetch("action_id", None) in ("manual_mark", "abort")
                and str(control.par.label.eval()).endswith("T-02 NOT ACTIVE")
                and not bool(control.par.enable.eval())
                and bool(control.par.display.eval())
                for control in manual_controls
            )
            and not manual_callbacks
        ),
        "page_scenario_combinations_rendered_50": combinations_checked == 50 and combinations_rendered,
        "udp_5005_disabled": udp is not None and int(udp.par.port.eval()) == 5005 and not bool(udp.par.active.eval()),
        "no_node_errors": not errors and not script_errors,
        "toe_exists": TOE_PATH.is_file(),
    }
    report = {
        "report_schema_version": "f04-td-reopen-report-v2",
        "touchdesigner_build": str(app.build),
        "root": ROOT_PATH,
        "checks": checks,
        "page_navigation_node_positions": sorted(page_node_positions),
        "page_navigation_panel_positions": sorted(page_panel_positions),
        "scenario_navigation_node_positions": sorted(scenario_node_positions),
        "scenario_navigation_panel_positions": sorted(scenario_panel_positions),
        "visual_roles_observed": visual_roles_observed,
        "page_scenario_combinations_checked": combinations_checked,
        "operator_errors": errors,
        "script_errors": script_errors,
        "toe_sha256": sha256(TOE_PATH.read_bytes()).hexdigest().upper(),
        "pass": all(checks.values()),
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["pass"]:
        raise RuntimeError("F04_REOPEN_FAIL {}".format(checks))
    print("F04_REOPEN_PASS 10 pages 5 scenarios visible shell 50 combinations")
    return report


verify()
