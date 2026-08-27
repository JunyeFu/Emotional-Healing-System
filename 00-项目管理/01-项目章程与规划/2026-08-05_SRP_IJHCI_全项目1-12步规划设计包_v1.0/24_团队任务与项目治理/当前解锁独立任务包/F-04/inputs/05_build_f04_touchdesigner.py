"""Execute inside TouchDesigner 2025.32820 to build the F-04 console.

The builder replaces exactly one F-04-owned root and never creates a network
output or an enabled request action.  Host-side validation must run before and
after this script; the embedded fixture is demonstration data only.
"""

from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
FIXTURE_PATH = BASE_DIR / "fixtures" / "f04-static-display-fixture-v1.json"
HOST_EVIDENCE = BASE_DIR / "evidence" / "host"
TD_EVIDENCE = BASE_DIR / "evidence" / "touchdesigner"
SCREENSHOT_DIR = TD_EVIDENCE / "screenshots"
TOE_PATH = BASE_DIR / "F04_ReadonlyConsole.toe"
TOX_PATH = BASE_DIR / "F04_ReadonlyConsole.tox"
ROOT_PATH = "/project1/F04_ReadonlyConsole"


def _set(node, parameter_name, value):
    parameter = getattr(node.par, parameter_name, None)
    if parameter is not None:
        parameter.val = value


def _resolve(data, dotted_path):
    current = data
    for part in dotted_path.split("."):
        current = current[part]
    return current


def _display_value(value):
    if isinstance(value, list):
        if len(value) > 8:
            return "[{} ... {} samples]".format(
                ", ".join(str(item) for item in value[:6]), len(value)
            )
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _page_text(page, scenario):
    lines = [
        "F-04  {}".format(page["title"]),
        "READ ONLY / DEV-REPLAY / NOT LIVE",
        "",
        "SCENARIO  {}".format(scenario["id"]),
        "MODULE    {}".format(scenario["telemetry"]["module_id"]),
        "",
    ]
    for field_path in page["field_paths"]:
        lines.append("{:<54} {}".format(field_path, _display_value(_resolve(scenario, field_path))))
    if page["id"] == "manual_actions":
        lines.extend(["", "NO CALLBACKS / NO REQUEST CHANNEL"])
    lines.extend([
        "",
        "Synthetic local display fixture only.",
        "Not device evidence, not state-estimation evidence, not LIVE_E2E.",
    ])
    return "\n".join(lines)


def _table(parent, name, header, rows):
    dat = parent.create(tableDAT, name)
    dat.appendRow(header)
    for row in rows:
        dat.appendRow(row)
    return dat


def _actual_inventory(root):
    inventory = []
    for node in [root] + list(root.findChildren(maxDepth=8)):
        inventory.append({
            "path": node.path,
            "operator_type": node.OPType,
            "active": bool(node.par.active.eval()) if node.OPType == "udpinDAT" else None,
        })
    return sorted(inventory, key=lambda item: item["path"])


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    page_manifest = json.loads((HOST_EVIDENCE / "page_manifest.json").read_text(encoding="utf-8"))
    node_plan = json.loads((HOST_EVIDENCE / "node_plan.json").read_text(encoding="utf-8"))
    permissions = json.loads((HOST_EVIDENCE / "node_permissions.json").read_text(encoding="utf-8"))

    project_root = op('/project1')
    if project_root is None:
        raise RuntimeError("/project1 is required")
    existing = op('/project1/F04_ReadonlyConsole')
    if existing is not None:
        existing.destroy()

    root = project_root.create(containerCOMP, "F04_ReadonlyConsole")
    root.nodeX = 0
    root.nodeY = 0
    root.store("owner", "F-04")
    root.store("mode", "DEV_REPLAY")
    root.store("banner", "READ ONLY / DEV-REPLAY / NOT LIVE")

    fixture_dat = root.create(textDAT, "fixture_json")
    fixture_dat.text = json.dumps(fixture, ensure_ascii=False, indent=2)

    _table(
        root,
        "page_manifest",
        ["index", "page_id", "title", "banner", "field_paths"],
        [
            [index, page["id"], page["title"], page["banner"], "|".join(page["field_paths"])]
            for index, page in enumerate(page_manifest["pages"])
        ],
    )
    _table(
        root,
        "node_permissions",
        ["path", "operator_type", "role", "permission", "active", "port", "label"],
        [
            [
                item.get("path", ""), item.get("operator_type", ""), item.get("role", ""),
                item.get("permission", ""), item.get("active", ""), item.get("port", ""), item.get("label", ""),
            ]
            for item in permissions["nodes"]
        ],
    )
    error_dat = _table(root, "node_errors", ["kind", "message"], [])

    udp = root.create(udpinDAT, "udp_5005_placeholder")
    _set(udp, "port", 5005)
    udp.par.active = False
    udp.store("label", "T-01 NOT ACTIVE")
    udp.comment = "T-01 NOT ACTIVE / DISABLED PLACEHOLDER"

    pages = root.create(containerCOMP, "pages")
    selector = root.create(switchTOP, "page_selector")
    scenario = fixture["scenarios"][0]
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    views = []
    for index, page in enumerate(page_manifest["pages"]):
        page_comp = pages.create(containerCOMP, page["id"])
        page_comp.nodeX = (index % 5) * 260
        page_comp.nodeY = -(index // 5) * 180
        view = page_comp.create(textTOP, "view")
        _set(view, "text", _page_text(page, scenario))
        _set(view, "resolutionw", 1280)
        _set(view, "resolutionh", 720)
        _set(view, "fontsize", 24)
        _set(view, "fontcolorr", 0.84)
        _set(view, "fontcolorg", 0.92)
        _set(view, "fontcolorb", 1.0)
        _set(view, "bgcolorr", 0.025)
        _set(view, "bgcolorg", 0.045)
        _set(view, "bgcolorb", 0.075)
        _set(view, "bgalpha", 1.0)
        _set(view, "alignx", "left")
        _set(view, "aligny", "top")
        _set(view, "marginx", 36)
        _set(view, "marginy", 30)
        view.outputConnectors[0].connect(selector.inputConnectors[index])
        view.cook(force=True)
        view.save(str(SCREENSHOT_DIR / ("{:02d}_{}.png".format(index + 1, page["id"]))))
        views.append(view)

    _set(selector, "index", 0)
    display_out = root.create(outTOP, "display_out")
    selector.outputConnectors[0].connect(display_out.inputConnectors[0])
    display_out.display = True
    display_out.render = True

    errors = root.errors(recurse=True)
    script_errors = root.scriptErrors(recurse=True)
    if errors:
        error_dat.appendRow(["operator", errors])
    if script_errors:
        error_dat.appendRow(["script", script_errors])
    if not errors and not script_errors:
        error_dat.appendRow(["none", "NO NODE ERRORS"])

    inventory = _actual_inventory(root)
    _write_json(TD_EVIDENCE / "node_inventory.json", {
        "inventory_schema_version": "f04-td-node-inventory-v1",
        "root": ROOT_PATH,
        "nodes": inventory,
    })
    _write_json(TD_EVIDENCE / "node_errors.json", {
        "error_report_schema_version": "f04-td-node-errors-v1",
        "operator_errors": errors,
        "script_errors": script_errors,
        "pass": not errors and not script_errors,
    })
    _write_json(TD_EVIDENCE / "runtime_build_manifest.json", {
        "manifest_schema_version": "f04-td-runtime-build-manifest-v1",
        "touchdesigner_version": str(app.version),
        "touchdesigner_build": str(app.build),
        "product": str(app.product),
        "root": ROOT_PATH,
        "page_count": len(views),
        "scenario_count": len(fixture["scenarios"]),
        "node_count": len(inventory),
        "udp_5005_active": bool(udp.par.active.eval()),
        "node_plan_schema_version": node_plan["plan_schema_version"],
        "evidence_boundary": "DEV_REPLAY_ONLY_NOT_LIVE",
    })

    root.save(str(TOX_PATH))
    saved = project.save(str(TOE_PATH))
    if not saved:
        raise RuntimeError("TouchDesigner project.save returned False")
    print("F04_BUILD_COMPLETE {} pages {} nodes".format(len(views), len(inventory)))
    return root


build()
