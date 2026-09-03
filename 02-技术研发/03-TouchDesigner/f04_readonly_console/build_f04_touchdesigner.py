"""Build the modular F-04 read-only console in TouchDesigner 2025.32820."""

from __future__ import annotations

from hashlib import sha256
import builtins
import json
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from f04_console import BANNER, PAGE_DEFINITIONS, SCENARIO_IDS, StaticFixtureAdapter


FIXTURE_PATH = BASE_DIR / "fixtures" / "f04-static-display-fixture-v1.json"
HOST_EVIDENCE = BASE_DIR / "evidence" / "host"
TD_EVIDENCE = BASE_DIR / "evidence" / "touchdesigner"
SCREENSHOT_DIR = TD_EVIDENCE / "screenshots"
TOE_PATH = BASE_DIR / "F04_ReadonlyConsole.toe"
TOX_PATH = BASE_DIR / "F04_ReadonlyConsole.tox"
ROOT_PATH = "/project1/F04_ReadonlyConsole"
PAGE_WIDTH = 1280
PAGE_HEIGHT = 480
STATE_COLORS = {
    "GOOD": (0.10, 0.78, 0.54),
    "DEGRADED": (0.95, 0.68, 0.16),
    "UNUSABLE": (0.93, 0.31, 0.30),
    "DISCONNECTED": (0.42, 0.48, 0.58),
}


def _set(node, parameter_name, value):
    parameter = getattr(node.par, parameter_name, None)
    if parameter is not None:
        parameter.val = value


def _create(parent, operator_type, name, role, permission="read_only"):
    node = parent.create(operator_type, name)
    node.store("role", role)
    node.store("permission", permission)
    return node


def _display_value(value):
    if isinstance(value, (list, tuple)):
        if len(value) > 8:
            return "[{} ... {} samples]".format(
                ", ".join(str(item) for item in value[:6]), len(value)
            )
        return json.dumps(list(value), ensure_ascii=False)
    return str(value)


def _scenario_label(scenario_id, snapshot):
    return "OUT_OF_ORDER" if scenario_id == "out_of_order_storm" else snapshot.telemetry["fallback_state"]


def _page_summary_lines(page_id, snapshot):
    telemetry = snapshot.telemetry
    display = snapshot.display_only
    summaries = {
        "session_version": (
            "SESSION  {}".format(telemetry["session_id"]),
            "SCHEMA   {}".format(telemetry["schema_version"]),
            "RUNTIME  {}".format(telemetry["runtime_mode"]),
            "CUE      {}".format(telemetry["cue_mode"]),
        ),
        "device_connection": (
            "RESP DEVICE  {}   SQI {:.2f}".format(telemetry["resp_device_state"], telemetry["signal_quality"]["resp"]),
            "ECG DEVICE   {}   SQI {:.2f}".format(telemetry["ecg_device_state"], telemetry["signal_quality"]["ecg"]),
        ),
        "respiration_waveform": (
            "SYNTHETIC RESPIRATION   {} HZ".format(display["respiration"]["sample_rate_hz"]),
            "RAW CHANNEL / FILTERED CHANNEL",
        ),
        "ecg_rr_quality": (
            "ECG SQI    {:.2f}".format(telemetry["signal_quality"]["ecg"]),
            "RR STATUS  {}".format(display["rr_quality"]["status"]),
            "RR MS      {}".format("  ".join(str(value) for value in display["rr_quality"]["rr_ms"])),
        ),
        "phase_comparison": (
            "TARGET  {}  {:.0%}".format(telemetry["target_phase"], telemetry["target_progress"]),
            "ACTUAL  {}  {:.0%}".format(telemetry["actual_phase"], telemetry["actual_progress"]),
            "CONFIDENCE  {:.0%}".format(telemetry["actual_confidence"]),
        ),
        "cycle_result": (
            "CYCLE     {}".format(display["cycle_summary"]["cycle_id"]),
            "DURATION  {:.1f} s".format(display["cycle_summary"]["duration_s"]),
            "RESULT    {}".format(display["cycle_summary"]["result"]),
        ),
        "latency_clock": (
            "OFFSET       {} ns".format(telemetry["clock_offset_ns"]),
            "DRIFT        {:.1f} ppm".format(telemetry["clock_drift_ppm"]),
            "UNCERTAINTY  {} ns".format(telemetry["sync_uncertainty_ns"]),
        ),
        "degradation": (
            "QUALITY STATE  {}".format(telemetry["fallback_state"]),
            "REASON         {}".format(
                (telemetry["fallback_reason"] or "NONE")
                .replace("STATIC_", "")
                .replace("_EXAMPLE", "")
            ),
            "RECOVERY       {:.0%}{}".format(telemetry["recovery_value"], " / LOCKED" if telemetry["recovery_locked"] else ""),
        ),
        "log_write": (
            "WRITE STATE  {}".format(display["log_status"]["write_state"]),
            "RECORD       {}".format(display["log_status"]["last_record_id"]),
            "{}".format(display["log_status"]["notice"]),
        ),
        "manual_actions": (
            "MANUAL MARK  DISABLED",
            "ABORT        DISABLED",
            "T-02 NOT ACTIVE / NO CALLBACKS",
        ),
    }
    return summaries[page_id]


def _page_text(page, snapshot):
    lines = [
        "{}".format(page["title"]),
        "SCENE   {}".format(snapshot.meta["scenario_id"]),
        "MODULE  {}  /  {}".format(
            snapshot.telemetry["module_id"],
            _scenario_label(snapshot.meta["scenario_id"], snapshot),
        ),
        "",
        *_page_summary_lines(page["id"], snapshot),
    ]
    return "\n".join(lines)


def _table(parent, name, header, rows, role):
    dat = _create(parent, tableDAT, name, role)
    dat.appendRow(header)
    for row in rows:
        dat.appendRow(row)
    return dat


def _configure_top(node, width=1280, height=720):
    _set(node, "resolutionw", width)
    _set(node, "resolutionh", height)


def _build_rectangle(parent, role, color, center_x, center_y, size_x, size_y, alpha=0.72):
    rectangle = _create(parent, rectangleTOP, role, role)
    _configure_top(rectangle, PAGE_WIDTH, PAGE_HEIGHT)
    _set(rectangle, "bgalpha", 0.0)
    _set(rectangle, "fillcolorr", color[0])
    _set(rectangle, "fillcolorg", color[1])
    _set(rectangle, "fillcolorb", color[2])
    _set(rectangle, "fillalpha", alpha)
    _set(rectangle, "centerx", center_x)
    _set(rectangle, "centery", center_y)
    _set(rectangle, "sizex", size_x)
    _set(rectangle, "sizey", size_y)
    return rectangle


def _graphical_specs(page_id, snapshot):
    telemetry = snapshot.telemetry
    display = snapshot.display_only
    state = STATE_COLORS[telemetry["fallback_state"]]
    dim = (0.13, 0.20, 0.30)
    cyan = (0.13, 0.72, 0.92)
    yellow = (0.95, 0.76, 0.20)
    red = (0.95, 0.30, 0.34)
    green = (0.12, 0.76, 0.50)
    specs = {
        "session_version": (
            ("session_card", cyan, -0.32, -0.08, 0.24, 0.26),
            ("version_card", state, 0.0, -0.08, 0.28, 0.26),
            ("source_card", yellow, 0.32, -0.08, 0.24, 0.26),
        ),
        "device_connection": (
            ("resp_connection_badge", state, -0.43, 0.0, 0.34, 0.20),
            ("ecg_connection_badge", state, 0.43, 0.0, 0.34, 0.20),
            ("freshness_bar", cyan, 0.0, -0.28, max(0.08, 0.72 * max(telemetry["signal_quality"].values())), 0.06),
        ),
        "respiration_waveform": (
            ("raw_channel_legend", red, -0.28, -0.34, 0.24, 0.04),
            ("filtered_channel_legend", yellow, 0.28, -0.34, 0.24, 0.04),
        ),
        "ecg_rr_quality": (
            ("ecg_quality_gauge", state, -0.48, -0.08, 0.18, max(0.08, 0.42 * telemetry["signal_quality"]["ecg"])),
            ("rr_interval_strip", cyan, 0.30, -0.08, 0.52 if display["rr_quality"]["rr_ms"] else 0.12, 0.10),
        ),
        "phase_comparison": (
            ("target_phase_track", cyan, -0.34 + telemetry["target_progress"] * 0.34, 0.02, 0.18 + telemetry["target_progress"] * 0.52, 0.08),
            ("actual_phase_track", yellow, -0.34 + telemetry["actual_progress"] * 0.34, -0.20, 0.18 + telemetry["actual_progress"] * 0.52, 0.08),
        ),
        "cycle_result": (
            ("cycle_summary_card", cyan, -0.35, -0.08, 0.38, 0.28),
            ("cycle_result_card", state, 0.35, -0.08, 0.38, 0.28),
        ),
        "latency_clock": (
            ("latency_bar", yellow, -0.32 + min(telemetry["sync_uncertainty_ns"] / 1_000_000.0, 1.0) * 0.32, 0.02, 0.18 + min(telemetry["sync_uncertainty_ns"] / 1_000_000.0, 1.0) * 0.54, 0.08),
            ("clock_drift_bar", cyan, -0.32 + min(abs(telemetry["clock_drift_ppm"]) / 5.0, 1.0) * 0.32, -0.20, 0.18 + min(abs(telemetry["clock_drift_ppm"]) / 5.0, 1.0) * 0.54, 0.08),
        ),
        "degradation": (
            ("quality_state_lane", state, 0.0, 0.0, 0.76, 0.16),
            ("degradation_timeline", red if telemetry["recovery_locked"] else green, -0.34 + telemetry["recovery_value"] * 0.34, -0.25, 0.10 + telemetry["recovery_value"] * 0.62, 0.06),
        ),
        "log_write": (
            ("log_write_state_card", state, -0.35, -0.08, 0.38, 0.28),
            ("log_counter_card", cyan, 0.35, -0.08, 0.38, 0.28),
        ),
        "manual_actions": (
            ("manual_mark_control_visual", dim, 0.0, 0.20, 0.78, 0.08),
            ("abort_control_visual", dim, 0.0, -0.20, 0.78, 0.08),
        ),
    }
    return tuple(
        (
            role,
            color,
            0.25 + center_x * 0.35,
            center_y,
            min(size_x * 0.42, 0.38),
            size_y * 0.84,
        )
        for role, color, center_x, center_y, size_x, size_y in specs[page_id]
    )


def _build_waveform_panel(shared, snapshots):
    panel = _create(shared, containerCOMP, "WaveformPanel", "waveform_panel")
    outputs = {}
    for scenario_index, scenario_id in enumerate(SCENARIO_IDS):
        snapshot = snapshots[scenario_id]
        scenario_comp = _create(panel, containerCOMP, scenario_id, "waveform_scenario")
        scenario_comp.nodeX = scenario_index * 280
        respiration = snapshot.display_only["respiration"]
        table = _create(scenario_comp, tableDAT, "waveform_table", "waveform_table")
        table.appendRow(["raw", *respiration["raw_25hz"]])
        table.appendRow(["filtered", *respiration["filtered_25hz"]])
        dat_to_chop = _create(scenario_comp, dattoCHOP, "dat_to_chop", "waveform_dat_to_chop")
        _set(dat_to_chop, "dat", table.path)
        _set(dat_to_chop, "output", "chanperrow")
        _set(dat_to_chop, "firstrow", "ignored")
        _set(dat_to_chop, "firstcolumn", "names")
        select = _create(scenario_comp, selectCHOP, "select", "waveform_select")
        dat_to_chop.outputConnectors[0].connect(select)
        _set(select, "channames", "raw filtered")
        math_node = _create(scenario_comp, mathCHOP, "math", "waveform_math")
        select.outputConnectors[0].connect(math_node)
        math_node.viewer = True
        view = _create(scenario_comp, opviewerTOP, "view", "waveform_view")
        _set(view, "opviewer", math_node.path)
        _configure_top(view)
        view.comment = "RAW + FILTERED / SYNTHETIC 25 HZ"
        outputs[scenario_id] = view
    return outputs


def _build_graphical_view(parent, page, snapshot, page_index, scenario_index, snapshots, waveform):
    background = _create(parent, constantTOP, "background", "page_background")
    _configure_top(background, PAGE_WIDTH, PAGE_HEIGHT)
    _set(background, "colorr", 0.018)
    _set(background, "colorg", 0.032)
    _set(background, "colorb", 0.058)
    _set(background, "alpha", 1.0)

    labels = _create(parent, textTOP, "labels", "page_labels")
    _configure_top(labels, PAGE_WIDTH, PAGE_HEIGHT)
    _set(labels, "text", _page_text(page, snapshot))
    _set(labels, "fontsize", 3)
    _set(labels, "fontcolorr", 0.88)
    _set(labels, "fontcolorg", 0.94)
    _set(labels, "fontcolorb", 1.0)
    _set(labels, "bgalpha", 0.0)
    _set(labels, "alignx", "left")
    _set(labels, "aligny", "top")
    _set(labels, "marginx", 30)
    _set(labels, "marginy", 24)

    graphical_layers = [
        _build_rectangle(parent, role, color, center_x, center_y, size_x, size_y)
        for role, color, center_x, center_y, size_x, size_y
        in _graphical_specs(page["id"], snapshot)
    ]
    if page["id"] == "manual_actions":
        for role, text, position_y in (
            ("manual_mark_control_label", "MARK  [DISABLED]", -125),
            ("abort_control_label", "ABORT  [DISABLED]", -315),
        ):
            action_label = _create(parent, textTOP, role, role)
            _configure_top(action_label, PAGE_WIDTH, PAGE_HEIGHT)
            _set(action_label, "text", text)
            _set(action_label, "fontsize", 1)
            _set(action_label, "fontcolorr", 0.72)
            _set(action_label, "fontcolorg", 0.76)
            _set(action_label, "fontcolorb", 0.82)
            _set(action_label, "bgalpha", 0.0)
            _set(action_label, "alignx", "left")
            _set(action_label, "aligny", "top")
            _set(action_label, "positionx", 790)
            _set(action_label, "positiony", position_y)
            graphical_layers.insert(0, action_label)

    view = _create(parent, compositeTOP, "view", "page_scenario_view")
    _set(view, "operand", "add")
    # Composite TOP treats its first input as the foreground for "over".
    # Keep labels and page-specific graphics above the opaque background.
    labels.outputConnectors[0].connect(view)
    for layer in graphical_layers:
        layer.outputConnectors[0].connect(view)
    if page["id"] == "respiration_waveform":
        local_waveform = _create(parent, selectTOP, "page_waveform_view", "page_waveform_view")
        _set(local_waveform, "top", waveform.path)
        _configure_top(local_waveform, PAGE_WIDTH, PAGE_HEIGHT)
        local_waveform.outputConnectors[0].connect(view)
    background.outputConnectors[0].connect(view)
    _configure_top(view, PAGE_WIDTH, PAGE_HEIGHT)
    return view


def _configure_panel(node, x, y, width, height):
    _set(node, "x", x)
    _set(node, "y", y)
    _set(node, "w", width)
    _set(node, "h", height)
    _set(node, "display", True)


def _build_local_button(parent, name, label, callback_text, role, panel_position, node_position, size):
    button = _create(parent, buttonCOMP, name, role)
    button.name = name
    _set(button, "label", label)
    _configure_panel(button, panel_position[0], panel_position[1], size[0], size[1])
    button.nodeX = node_position[0]
    button.nodeY = node_position[1]
    callback = _create(parent, panelexecuteDAT, name + "_callback", "local_navigation_callback")
    callback.nodeX = node_position[0]
    callback.nodeY = node_position[1] - 100
    _set(callback, "panel", button.path)
    _set(callback, "offtoon", True)
    callback.text = callback_text
    return button


def _build_shell(root, page_views, output_selector):
    shell = _create(root, containerCOMP, "ConsoleShell", "console_shell")
    _configure_panel(shell, 0, 0, 1280, 720)
    shell_background = _create(shell, constantTOP, "ShellBackground", "shell_background")
    _configure_top(shell_background, 1280, 720)
    _set(shell_background, "colorr", 0.008)
    _set(shell_background, "colorg", 0.014)
    _set(shell_background, "colorb", 0.026)
    _set(shell_background, "alpha", 1.0)
    _set(shell, "top", shell_background.path)
    _set(shell, "topfill", "native")
    page_viewport = _create(shell, containerCOMP, "PageViewport", "page_viewport")
    _configure_panel(page_viewport, 0, 0, PAGE_WIDTH, PAGE_HEIGHT)
    _set(page_viewport, "top", output_selector.path)
    _set(page_viewport, "topfill", "native")
    header = _create(shell, textTOP, "PersistentHeader", "persistent_header")
    _configure_top(header, 1280, 96)
    _set(header, "text", "F-04 MODULAR READ-ONLY CONSOLE\n" + BANNER)
    header_panel = _create(shell, containerCOMP, "HeaderPanel", "persistent_header_panel")
    _configure_panel(header_panel, 0, 624, 1280, 96)
    _set(header_panel, "top", header.path)
    _set(header_panel, "topfill", "native")
    page_navigation = _create(shell, containerCOMP, "PageNavigation", "page_navigation_container")
    _configure_panel(page_navigation, 20, 536, 1240, 76)
    scenario_navigation = _create(shell, containerCOMP, "ScenarioNavigation", "scenario_navigation_container")
    _configure_panel(scenario_navigation, 20, 486, 1240, 42)
    for index, page in enumerate(PAGE_DEFINITIONS):
        callback = "def onOffToOn(panelValue):\n    op({!r}).par.index = {}\n    return\n".format(output_selector.path, index)
        column = index % 5
        row = index // 5
        _build_local_button(
            page_navigation,
            "{:02d}_{}".format(index + 1, page["id"]),
            "{:02d} {}".format(index + 1, page["title"]),
            callback,
            "page_navigation",
            (column * 244, 38 - row * 38),
            (column * 180, -row * 160),
            (232, 34),
        )
    for index, scenario_id in enumerate(SCENARIO_IDS):
        assignments = "\n".join("    op('{}').par.index = {}".format(view.path, index) for view in page_views.values())
        callback = "def onOffToOn(panelValue):\n{}\n    return\n".format(assignments)
        _build_local_button(
            scenario_navigation,
            "{:02d}_{}".format(index + 1, scenario_id),
            scenario_id.replace("_", " ").upper(),
            callback,
            "scenario_navigation",
            (index * 244, 4),
            (index * 180, 0),
            (232, 34),
        )

    manual_controls = _create(shell, containerCOMP, "ManualActionControls", "manual_action_controls")
    _configure_panel(manual_controls, 650, 90, 580, 280)
    display_parameter = getattr(manual_controls.par, "display", None)
    if display_parameter is not None:
        display_parameter.expr = "op({!r}).par.index == 9".format(output_selector.path)
    for index, (action_id, label) in enumerate((
        ("manual_mark", "MANUAL MARK / T-02 NOT ACTIVE"),
        ("abort", "ABORT / T-02 NOT ACTIVE"),
    )):
        control = _create(
            manual_controls,
            buttonCOMP,
            action_id + "_disabled",
            "disabled_action_control",
            "disabled_control",
        )
        control.name = action_id + "_disabled"
        _set(control, "label", label)
        _set(control, "enable", False)
        _configure_panel(control, 20, 150 - index * 110, 540, 90)
        control.nodeX = index * 220
        control.nodeY = 0
        control.store("action_id", action_id)
        control.store("label", label)
    return shell


def _actual_inventory(root):
    inventory = []
    for node in [root] + list(root.findChildren(maxDepth=10)):
        is_button = node.OPType == "buttonCOMP"
        inventory.append({
            "path": node.path,
            "operator_type": node.OPType,
            "active": bool(node.par.active.eval()) if node.OPType == "udpinDAT" else None,
            "enabled": bool(node.par.enable.eval()) if is_button and getattr(node.par, "enable", None) is not None else None,
            "node_x": node.nodeX if is_button else None,
            "node_y": node.nodeY if is_button else None,
            "panel_x": int(node.par.x.eval()) if is_button and getattr(node.par, "x", None) is not None else None,
            "panel_y": int(node.par.y.eval()) if is_button and getattr(node.par, "y", None) is not None else None,
            "label": str(node.par.label.eval()) if is_button and getattr(node.par, "label", None) is not None else None,
            "role": node.fetch("role", None),
            "permission": node.fetch("permission", None),
        })
    return sorted(inventory, key=lambda item: item["path"])


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_sha256(path):
    return sha256(path.read_bytes()).hexdigest().upper()


def _save_top(node, path):
    node.cook(force=True)
    node.numpyArray()
    if path.exists():
        path.unlink()
    node.save(str(path), asynchronous=False)
    if not path.exists() or path.stat().st_size < 10_000:
        raise RuntimeError("invalid screenshot evidence: {}".format(path))


def _screenshot_cases():
    cases = [
        (index, 0, SCREENSHOT_DIR / ("{:02d}_{}.png".format(index + 1, page["id"])))
        for index, page in enumerate(PAGE_DEFINITIONS)
    ]
    degradation_index = next(index for index, page in enumerate(PAGE_DEFINITIONS) if page["id"] == "degradation")
    cases.extend(
        (
            degradation_index,
            scenario_index,
            SCREENSHOT_DIR / ("{:02d}_degradation_{}.png".format(evidence_index, SCENARIO_IDS[scenario_index])),
        )
        for evidence_index, scenario_index in enumerate(range(1, len(SCENARIO_IDS)), start=11)
    )
    return cases


def _prepare_screenshot_case():
    state = builtins.f04_screenshot_refresh_state
    page_index, scenario_index, _ = state["cases"][state["index"]]
    page_selector = op("{}/Output/page_selector".format(ROOT_PATH))
    _set(page_selector, "index", page_index)
    for page in PAGE_DEFINITIONS:
        _set(op("{}/Pages/{}/view".format(ROOT_PATH, page["id"])), "index", scenario_index)
    shell_viewer = op("{}/Output/shell_viewer".format(ROOT_PATH))
    shell_viewer.cook(force=True)
    shell_viewer.numpyArray()
    run("__import__('builtins').f04_capture_prepared_screenshot()", delayFrames=5)


def _capture_prepared_screenshot():
    state = builtins.f04_screenshot_refresh_state
    _, _, screenshot = state["cases"][state["index"]]
    _save_top(op("{}/Output/shell_viewer".format(ROOT_PATH)), screenshot)
    state["hashes"][screenshot.name] = _file_sha256(screenshot)
    state["index"] += 1
    if state["index"] < len(state["cases"]):
        builtins.f04_prepare_screenshot_case()
        return
    screenshot_hashes = state["hashes"]
    if len(screenshot_hashes) != 14 or len(set(screenshot_hashes.values())) != 14:
        raise RuntimeError("screenshot evidence must contain 14 distinct rendered frames")
    _set(op("{}/Output/page_selector".format(ROOT_PATH)), "index", 0)
    for page in PAGE_DEFINITIONS:
        _set(op("{}/Pages/{}/view".format(ROOT_PATH, page["id"])), "index", 0)
    manifest_path = TD_EVIDENCE / "runtime_build_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["screenshot_sha256"] = screenshot_hashes
    manifest["screenshot_state"] = "COMPLETE_POST_COOK"
    _write_json(manifest_path, manifest)
    print("F04_SCREENSHOTS_COMPLETE {} current frames".format(len(screenshot_hashes)))


def refresh_screenshots():
    builtins.f04_screenshot_refresh_state = {
        "cases": _screenshot_cases(),
        "hashes": {},
        "index": 0,
    }
    builtins.f04_prepare_screenshot_case()


def build():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    page_manifest = json.loads((HOST_EVIDENCE / "page_manifest.json").read_text(encoding="utf-8"))
    node_plan = json.loads((HOST_EVIDENCE / "node_plan.json").read_text(encoding="utf-8"))
    permissions = json.loads((HOST_EVIDENCE / "node_permissions.json").read_text(encoding="utf-8"))
    adapter = StaticFixtureAdapter(FIXTURE_PATH)
    snapshots = {}
    for scenario_id in SCENARIO_IDS:
        adapter.scenario_id = scenario_id
        snapshots[scenario_id] = adapter.read_snapshot()

    project_root = op('/project1')
    if project_root is None:
        raise RuntimeError("/project1 is required")
    existing = op('/project1/F04_ReadonlyConsole')
    if existing is not None:
        existing.destroy()
    root = _create(project_root, containerCOMP, "F04_ReadonlyConsole", "f04_root")
    root.store("owner", "F-04")
    root.store("mode", "DEV_REPLAY")
    root.store("banner", BANNER)

    sources = _create(root, containerCOMP, "Sources", "source_container")
    static_adapter = _create(sources, containerCOMP, "StaticFixtureAdapter", "static_fixture_adapter")
    fixture_dat = _create(static_adapter, textDAT, "fixture_json", "embedded_fixture")
    fixture_dat.text = json.dumps(fixture, ensure_ascii=False, indent=2)
    udp = _create(sources, udpinDAT, "UdpTelemetryPlaceholder", "udp_placeholder", "disabled_input_placeholder")
    _set(udp, "port", 5005)
    udp.par.active = False
    udp.store("label", "T-01 NOT ACTIVE")

    _table(root, "page_manifest", ["index", "page_id", "title", "banner", "visual_mechanism", "field_paths"], [[index, page["id"], page["title"], page["banner"], page["visual_mechanism"], "|".join(page["field_paths"])] for index, page in enumerate(page_manifest["pages"])], "page_manifest")
    _table(root, "node_permissions", ["path", "operator_type", "role", "permission", "active", "port", "label"], [[item.get("path", ""), item.get("operator_type", ""), item.get("role", ""), item.get("permission", ""), item.get("active", ""), item.get("port", ""), item.get("label", "")] for item in permissions["nodes"]], "permission_manifest")
    error_dat = _table(root, "node_errors", ["kind", "message"], [], "error_report")

    shared = _create(root, containerCOMP, "SharedViews", "shared_view_container")
    waveform_outputs = _build_waveform_panel(shared, snapshots)
    pages = _create(root, containerCOMP, "Pages", "page_container")
    page_views = {}
    page_outputs = {}
    scenario_render_views = {}
    for page_index, page in enumerate(page_manifest["pages"]):
        page_comp = _create(pages, containerCOMP, page["id"], "page")
        scenario_views = _create(page_comp, containerCOMP, "scenario_views", "scenario_view_container")
        page_selector = _create(page_comp, switchTOP, "view", "page_view")
        for scenario_index, scenario_id in enumerate(SCENARIO_IDS):
            adapter.scenario_id = scenario_id
            adapter.page_id = page["id"]
            snapshot = adapter.read_snapshot()
            scenario_comp = _create(scenario_views, containerCOMP, scenario_id, "page_scenario")
            scenario_view = _build_graphical_view(scenario_comp, page, snapshot, page_index, scenario_index, snapshots, waveform_outputs[scenario_id])
            scenario_render_views[(page["id"], scenario_id)] = scenario_view
            scenario_out = _create(scenario_comp, outTOP, "out", "page_scenario_output")
            scenario_view.outputConnectors[0].connect(scenario_out)
            scenario_bridge = _create(page_comp, selectTOP, "{}_bridge".format(scenario_id), "page_scenario_bridge")
            _set(scenario_bridge, "top", scenario_view.path)
            _configure_top(scenario_bridge)
            scenario_bridge.outputConnectors[0].connect(page_selector)
        _set(page_selector, "index", 0)
        page_out = _create(page_comp, outTOP, "out", "page_output")
        page_selector.outputConnectors[0].connect(page_out)
        page_views[page["id"]] = page_selector
        page_outputs[page["id"]] = page_comp

    output = _create(root, containerCOMP, "Output", "output_container")
    selector = _create(output, switchTOP, "page_selector", "display_selector")
    for index, page in enumerate(page_manifest["pages"]):
        page_bridge = _create(output, selectTOP, "{}_bridge".format(page["id"]), "page_bridge")
        _set(page_bridge, "top", page_views[page["id"]].path)
        _configure_top(page_bridge)
        page_bridge.outputConnectors[0].connect(selector)
    _set(selector, "index", 0)
    shell = _build_shell(root, page_views, selector)
    shell_viewer = _create(output, opviewerTOP, "shell_viewer", "console_shell_view")
    _set(shell_viewer, "opviewer", shell.path)
    _configure_top(shell_viewer)
    shell_viewer.store("viewer_target", shell.path)
    display_out = _create(output, outTOP, "display_out", "local_display_output")
    shell_viewer.outputConnectors[0].connect(display_out)
    display_out.display = True
    display_out.render = True

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for waveform_view in waveform_outputs.values():
        waveform_view.cook(force=True)
        waveform_view.numpyArray()
    for page_waveform in root.findChildren(maxDepth=10):
        if page_waveform.fetch("role", None) == "page_waveform_view":
            page_waveform.cook(force=True)
            page_waveform.numpyArray()
    screenshot_paths = [
        SCREENSHOT_DIR / ("{:02d}_{}.png".format(index + 1, page["id"]))
        for index, page in enumerate(PAGE_DEFINITIONS)
    ] + [
        SCREENSHOT_DIR / ("{:02d}_degradation_{}.png".format(index + 10, scenario_id))
        for index, scenario_id in enumerate(SCENARIO_IDS[1:], start=1)
    ]

    errors = root.errors(recurse=True)
    script_errors = root.scriptErrors(recurse=True)
    error_dat.appendRow(["none", "NO NODE ERRORS"] if not errors and not script_errors else ["operator", errors + script_errors])
    inventory = _actual_inventory(root)
    _write_json(TD_EVIDENCE / "node_inventory.json", {"inventory_schema_version": "f04-td-node-inventory-v2", "root": ROOT_PATH, "nodes": inventory})
    _write_json(TD_EVIDENCE / "node_errors.json", {"error_report_schema_version": "f04-td-node-errors-v2", "operator_errors": errors, "script_errors": script_errors, "pass": not errors and not script_errors})
    _write_json(TD_EVIDENCE / "runtime_build_manifest.json", {
        "manifest_schema_version": "f04-td-runtime-build-manifest-v2", "touchdesigner_version": str(app.version), "touchdesigner_build": str(app.build), "product": str(app.product), "root": ROOT_PATH,
        "page_count": len(page_views), "scenario_count": len(SCENARIO_IDS), "page_scenario_combinations": len(page_views) * len(SCENARIO_IDS),
        "page_navigation_count": len(PAGE_DEFINITIONS), "scenario_navigation_count": len(SCENARIO_IDS), "screenshot_count": len(screenshot_paths),
        "screenshot_sha256": {}, "screenshot_state": "PENDING_POST_COOK", "node_count": len(inventory), "udp_5005_active": bool(udp.par.active.eval()),
        "node_plan_schema_version": node_plan["plan_schema_version"], "evidence_boundary": "DEV_REPLAY_ONLY_NOT_LIVE",
    })
    root.save(str(TOX_PATH))
    saved = project.save(str(TOE_PATH))
    if not saved:
        raise RuntimeError("TouchDesigner project.save returned False")
    builtins.f04_refresh_screenshots = refresh_screenshots
    builtins.f04_prepare_screenshot_case = _prepare_screenshot_case
    builtins.f04_capture_prepared_screenshot = _capture_prepared_screenshot
    run("__import__('builtins').f04_refresh_screenshots()", delayFrames=5)
    print("F04_BUILD_COMPLETE {} pages {} scenarios {} nodes".format(len(page_views), len(SCENARIO_IDS), len(inventory)))
    return root


build()
