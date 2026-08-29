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


def _navigation_lines(page_index, scenario_index, snapshots):
    page_labels = [
        "[{:02d} {}]".format(index + 1, page["title"])
        if index == page_index else "{:02d} {}".format(index + 1, page["title"])
        for index, page in enumerate(PAGE_DEFINITIONS)
    ]
    scenario_labels = [
        "[{}]".format(_scenario_label(scenario_id, snapshots[scenario_id]))
        if index == scenario_index else _scenario_label(scenario_id, snapshots[scenario_id])
        for index, scenario_id in enumerate(SCENARIO_IDS)
    ]
    return [
        "PAGES  " + "  |  ".join(page_labels[:4]),
        "       " + "  |  ".join(page_labels[4:7]),
        "       " + "  |  ".join(page_labels[7:]),
        "SCENARIOS  " + "  |  ".join(scenario_labels[:3]),
        "           " + "  |  ".join(scenario_labels[3:]),
    ]


def _page_text(page, snapshot, page_index, scenario_index, snapshots):
    lines = [
        "F-04  {}".format(page["title"]), BANNER,
        *_navigation_lines(page_index, scenario_index, snapshots), "",
        "SCENARIO  {}".format(snapshot.meta["scenario_id"]),
        "MODULE    {}".format(snapshot.telemetry["module_id"]),
        "STATE     {}".format(_scenario_label(snapshot.meta["scenario_id"], snapshot)), "",
    ]
    for field_path in page["field_paths"]:
        lines.append("{:<48} {}".format(field_path, _display_value(snapshot.resolve(field_path))))
    if page["id"] == "manual_actions":
        lines.extend(["", "T-02 NOT ACTIVE", "NO CALLBACKS / NO REQUEST CHANNEL"])
    lines.extend(["", "Synthetic local display fixture only.", "Not device evidence, not state-estimation evidence, not LIVE_E2E."])
    return "\n".join(lines)


def _visual_metric(page_id, snapshot):
    telemetry = snapshot.telemetry
    display = snapshot.display_only
    values = {
        "device_connection": max(telemetry["signal_quality"]["resp"], telemetry["signal_quality"]["ecg"]),
        "ecg_rr_quality": telemetry["signal_quality"]["ecg"],
        "phase_comparison": telemetry["actual_confidence"],
        "cycle_result": min(float(display["cycle_summary"]["duration_s"]) / 10.0, 1.0),
        "latency_clock": min(float(telemetry["sync_uncertainty_ns"]) / 1_000_000.0, 1.0),
        "degradation": float(telemetry["recovery_value"]),
        "log_write": 1.0 if display["log_status"]["write_state"] == "SIMULATED_OK" else 0.55,
        "manual_actions": 0.0,
    }
    return values.get(page_id, 0.72)


def _table(parent, name, header, rows, role):
    dat = _create(parent, tableDAT, name, role)
    dat.appendRow(header)
    for row in rows:
        dat.appendRow(row)
    return dat


def _configure_top(node, width=1280, height=720):
    _set(node, "resolutionw", width)
    _set(node, "resolutionh", height)


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
    _configure_top(background)
    _set(background, "colorr", 0.018)
    _set(background, "colorg", 0.032)
    _set(background, "colorb", 0.058)
    _set(background, "alpha", 1.0)

    color = STATE_COLORS[snapshot.telemetry["fallback_state"]]
    metric = _visual_metric(page["id"], snapshot)
    indicator = _create(parent, rectangleTOP, "indicator", "page_indicator")
    _configure_top(indicator)
    _set(indicator, "bgalpha", 0.0)
    _set(indicator, "fillcolorr", color[0])
    _set(indicator, "fillcolorg", color[1])
    _set(indicator, "fillcolorb", color[2])
    _set(indicator, "fillalpha", 0.78)
    _set(indicator, "sizex", max(0.04, 0.88 * metric))
    _set(indicator, "sizey", 0.06)
    _set(indicator, "centery", -0.40)

    labels = _create(parent, textTOP, "labels", "page_labels")
    _configure_top(labels)
    _set(labels, "text", _page_text(page, snapshot, page_index, scenario_index, snapshots))
    _set(labels, "fontsize", 7)
    _set(labels, "fontcolorr", 0.88)
    _set(labels, "fontcolorg", 0.94)
    _set(labels, "fontcolorb", 1.0)
    _set(labels, "bgalpha", 0.0)
    _set(labels, "alignx", "left")
    _set(labels, "aligny", "top")
    _set(labels, "marginx", 30)
    _set(labels, "marginy", 24)

    view = _create(parent, compositeTOP, "view", "page_scenario_view")
    _set(view, "operand", "add")
    # Composite TOP treats its first input as the foreground for "over".
    # Keep labels and the state indicator above the opaque background.
    labels.outputConnectors[0].connect(view)
    indicator.outputConnectors[0].connect(view)
    if page["id"] == "respiration_waveform":
        local_waveform = _create(parent, selectTOP, "waveform", "page_waveform_view")
        _set(local_waveform, "top", waveform.path)
        _configure_top(local_waveform)
        local_waveform.outputConnectors[0].connect(view)
    background.outputConnectors[0].connect(view)
    _configure_top(view)
    return view


def _build_local_button(parent, name, label, callback_text, role):
    button = _create(parent, buttonCOMP, name, role)
    _set(button, "label", label)
    callback = _create(parent, panelexecuteDAT, name + "_callback", "local_navigation_callback")
    _set(callback, "panel", button.path)
    _set(callback, "offtoon", True)
    callback.text = callback_text
    return button


def _build_shell(root, page_views, output_selector):
    shell = _create(root, containerCOMP, "ConsoleShell", "console_shell")
    header = _create(shell, textTOP, "PersistentHeader", "persistent_header")
    _configure_top(header, 1280, 96)
    _set(header, "text", "F-04 MODULAR READ-ONLY CONSOLE\n" + BANNER)
    page_navigation = _create(shell, containerCOMP, "PageNavigation", "page_navigation_container")
    scenario_navigation = _create(shell, containerCOMP, "ScenarioNavigation", "scenario_navigation_container")
    for index, page in enumerate(PAGE_DEFINITIONS):
        callback = "def onOffToOn(panelValue):\n    op({!r}).par.index = {}\n    return\n".format(output_selector.path, index)
        _build_local_button(page_navigation, "{:02d}_{}".format(index + 1, page["id"]), "{:02d} {}".format(index + 1, page["title"]), callback, "page_navigation")
    for index, scenario_id in enumerate(SCENARIO_IDS):
        assignments = "\n".join("    op('{}').par.index = {}".format(view.path, index) for view in page_views.values())
        callback = "def onOffToOn(panelValue):\n{}\n    return\n".format(assignments)
        _build_local_button(scenario_navigation, "{:02d}_{}".format(index + 1, scenario_id), scenario_id.replace("_", " ").upper(), callback, "scenario_navigation")
    return shell


def _actual_inventory(root):
    inventory = []
    for node in [root] + list(root.findChildren(maxDepth=10)):
        inventory.append({
            "path": node.path,
            "operator_type": node.OPType,
            "active": bool(node.par.active.eval()) if node.OPType == "udpinDAT" else None,
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


def refresh_screenshots():
    screenshot_paths = []
    for index, page in enumerate(PAGE_DEFINITIONS):
        render_view = op("{}/Pages/{}/scenario_views/{}/view".format(ROOT_PATH, page["id"], SCENARIO_IDS[0]))
        screenshot = SCREENSHOT_DIR / ("{:02d}_{}.png".format(index + 1, page["id"]))
        _save_top(render_view, screenshot)
        screenshot_paths.append(screenshot)
    for evidence_index, scenario_id in enumerate(SCENARIO_IDS[1:], start=11):
        render_view = op("{}/Pages/degradation/scenario_views/{}/view".format(ROOT_PATH, scenario_id))
        screenshot = SCREENSHOT_DIR / ("{:02d}_degradation_{}.png".format(evidence_index, scenario_id))
        _save_top(render_view, screenshot)
        screenshot_paths.append(screenshot)
    screenshot_hashes = {path.name: _file_sha256(path) for path in screenshot_paths}
    if len(set(screenshot_hashes.values())) != len(screenshot_paths):
        raise RuntimeError("screenshot evidence must contain 14 distinct rendered frames")
    manifest_path = TD_EVIDENCE / "runtime_build_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["screenshot_sha256"] = screenshot_hashes
    _write_json(manifest_path, manifest)
    print("F04_SCREENSHOTS_COMPLETE {} current frames".format(len(screenshot_paths)))


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
    display_out = _create(output, outTOP, "display_out", "local_display_output")
    selector.outputConnectors[0].connect(display_out)
    display_out.display = True
    display_out.render = True
    _build_shell(root, page_views, selector)

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for waveform_view in waveform_outputs.values():
        waveform_view.cook(force=True)
        waveform_view.numpyArray()
    for page_waveform in root.findChildren(maxDepth=10):
        if page_waveform.fetch("role", None) == "page_waveform_view":
            page_waveform.cook(force=True)
            page_waveform.numpyArray()
    screenshot_paths = []
    for index, page in enumerate(page_manifest["pages"]):
        view = page_views[page["id"]]
        _set(view, "index", 0)
        render_view = scenario_render_views[(page["id"], SCENARIO_IDS[0])]
        if page["id"] == "respiration_waveform":
            render_waveform = render_view.parent().op("waveform")
            render_waveform.cook(force=True)
            render_waveform.numpyArray()
        screenshot = SCREENSHOT_DIR / ("{:02d}_{}.png".format(index + 1, page["id"]))
        _save_top(render_view, screenshot)
        screenshot_paths.append(screenshot)
    degradation_view = page_views["degradation"]
    for evidence_index, scenario_index in enumerate(range(1, len(SCENARIO_IDS)), start=11):
        _set(degradation_view, "index", scenario_index)
        render_view = scenario_render_views[("degradation", SCENARIO_IDS[scenario_index])]
        screenshot = SCREENSHOT_DIR / ("{:02d}_degradation_{}.png".format(evidence_index, SCENARIO_IDS[scenario_index]))
        _save_top(render_view, screenshot)
        screenshot_paths.append(screenshot)
    for view in page_views.values():
        _set(view, "index", 0)

    screenshot_hashes = {path.name: _file_sha256(path) for path in screenshot_paths}
    if len(set(screenshot_hashes.values())) != len(screenshot_paths):
        raise RuntimeError("screenshot evidence must contain 14 distinct rendered frames")

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
        "screenshot_sha256": screenshot_hashes, "node_count": len(inventory), "udp_5005_active": bool(udp.par.active.eval()),
        "node_plan_schema_version": node_plan["plan_schema_version"], "evidence_boundary": "DEV_REPLAY_ONLY_NOT_LIVE",
    })
    root.save(str(TOX_PATH))
    saved = project.save(str(TOE_PATH))
    if not saved:
        raise RuntimeError("TouchDesigner project.save returned False")
    builtins.f04_refresh_screenshots = refresh_screenshots
    run("__import__('builtins').f04_refresh_screenshots()", delayFrames=5)
    print("F04_BUILD_COMPLETE {} pages {} scenarios {} nodes".format(len(page_views), len(SCENARIO_IDS), len(inventory)))
    return root


build()
