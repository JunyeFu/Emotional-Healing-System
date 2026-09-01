"""Build the T-01 read-only telemetry panel in TouchDesigner 2025.32820."""

from __future__ import annotations

import builtins
from hashlib import sha256
import json
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from t01_node_plan import ROOT_PATH, TD_BUILD, build_node_plan, write_host_artifacts


HOST_EVIDENCE = BASE_DIR / "evidence" / "host"
TD_EVIDENCE = BASE_DIR / "evidence" / "touchdesigner"
TOE_PATH = BASE_DIR / "T01_TelemetryPanel.toe"
TOX_PATH = BASE_DIR / "T01_TelemetryPanel.tox"
WIDTH = 1280
HEIGHT = 720


UDP_CALLBACKS = r'''
import builtins
from pathlib import Path
import sys
import time
import types


def _root():
    return op('/project1/T01_TelemetryPanel')


def _module():
    module = getattr(builtins, 'T01_TELEMETRY_MODULE', None)
    if module is None:
        name = 't01_touchdesigner_runtime_adapter'
        module = types.ModuleType(name)
        module.__file__ = str(Path(project.folder) / 't01_telemetry.py')
        module.project = project
        sys.modules[name] = module
        source = _root().op('Runtime/t01_adapter_module').text
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
        builtins.T01_TELEMETRY_MODULE = module
    return module


def _adapter():
    adapter = getattr(builtins, 'T01_TELEMETRY_ADAPTER', None)
    if adapter is None:
        module = _module()
        adapter = module.T01TelemetryAdapter(telemetry_hz=20, disconnect_timeout_ns=2_000_000_000)
        builtins.T01_TELEMETRY_ADAPTER = adapter
    return adapter


def onReceive(dat, rowIndex, message, bytes, peer):
    result = _adapter().ingest_datagram(builtins.bytes(bytes), time.monotonic_ns())
    builtins.T01_LAST_INGEST = {
        'accepted': result.accepted,
        'disposition': result.disposition,
        'code': result.code,
        'peer_address': peer.address,
        'peer_port': peer.port,
    }
    return
'''


RENDER_CALLBACKS = r'''
import builtins
from pathlib import Path
import json
import sys
import time
import types


ROOT_PATH = '/project1/T01_TelemetryPanel'


def _module():
    module = getattr(builtins, 'T01_TELEMETRY_MODULE', None)
    if module is None:
        name = 't01_touchdesigner_runtime_adapter'
        module = types.ModuleType(name)
        module.__file__ = str(Path(project.folder) / 't01_telemetry.py')
        module.project = project
        sys.modules[name] = module
        source = op(ROOT_PATH).op('Runtime/t01_adapter_module').text
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
        builtins.T01_TELEMETRY_MODULE = module
    return module


def _adapter():
    adapter = getattr(builtins, 'T01_TELEMETRY_ADAPTER', None)
    if adapter is None:
        module = _module()
        adapter = module.T01TelemetryAdapter(telemetry_hz=20, disconnect_timeout_ns=2_000_000_000)
        builtins.T01_TELEMETRY_ADAPTER = adapter
    return adapter


def _set_color(node, rgb):
    node.par.fillcolorr = rgb[0]
    node.par.fillcolorg = rgb[1]
    node.par.fillcolorb = rgb[2]


def onFrameStart(frame):
    root = op(ROOT_PATH)
    module = _module()
    snapshot = _adapter().read_snapshot(time.monotonic_ns())
    plain = module.snapshot_to_dict(snapshot)
    builtins.T01_LAST_SNAPSHOT = plain
    root.op('Runtime/panel_state').text = json.dumps(plain, ensure_ascii=False, indent=2, sort_keys=True)
    root.op('ConsoleShell/panel_text').par.text = module.snapshot_to_panel_text(snapshot)

    quality = snapshot.telemetry.get('signal_quality', {})
    resp = float(quality.get('resp', 0.0))
    ecg = float(quality.get('ecg', 0.0))
    root.op('ConsoleShell/resp_sqi_bar').par.sizex = max(0.02, 0.38 * resp)
    root.op('ConsoleShell/ecg_sqi_bar').par.sizex = max(0.02, 0.38 * ecg)
    badge = root.op('ConsoleShell/stream_badge')
    colors = {
        'WAITING': (0.42, 0.48, 0.58),
        'LIVE': (0.10, 0.78, 0.54),
        'DISCONNECTED': (0.93, 0.31, 0.30),
    }
    _set_color(badge, colors[snapshot.meta['stream_state']])
    return
'''


def _set(node, parameter_name, value):
    parameter = getattr(node.par, parameter_name, None)
    if parameter is not None:
        parameter.val = value


def _create(parent, operator_type, name, role, permission="read_only"):
    node = parent.create(operator_type, name)
    node.store("role", role)
    node.store("permission", permission)
    return node


def _configure_top(node):
    _set(node, "resolutionw", WIDTH)
    _set(node, "resolutionh", HEIGHT)


def _rectangle(parent, name, role, color, center_x, center_y, size_x, size_y):
    node = _create(parent, rectangleTOP, name, role)
    _configure_top(node)
    _set(node, "bgalpha", 0.0)
    _set(node, "fillcolorr", color[0])
    _set(node, "fillcolorg", color[1])
    _set(node, "fillcolorb", color[2])
    _set(node, "fillalpha", 0.82)
    _set(node, "centerx", center_x)
    _set(node, "centery", center_y)
    _set(node, "sizex", size_x)
    _set(node, "sizey", size_y)
    return node


def _table(parent, name, header, rows, role):
    dat = _create(parent, tableDAT, name, role)
    dat.appendRow(header)
    for row in rows:
        dat.appendRow(row)
    return dat


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")
    return sha256(content.encode("utf-8")).hexdigest().upper()


def _inventory(root):
    nodes = []
    for node in [root] + list(root.findChildren(maxDepth=10)):
        entry = {
            "path": node.path,
            "operator_type": node.OPType,
            "role": node.fetch("role", None),
            "permission": node.fetch("permission", None),
        }
        if node.OPType == "udpinDAT":
            entry.update(
                active=bool(node.par.active.eval()),
                port=int(node.par.port.eval()),
                local_address=str(node.par.localaddress.eval()),
            )
        nodes.append(entry)
    return nodes


def build():
    for name in ('T01_TELEMETRY_MODULE', 'T01_TELEMETRY_ADAPTER', 'T01_LAST_INGEST', 'T01_LAST_SNAPSHOT'):
        if hasattr(builtins, name):
            delattr(builtins, name)
    host_manifest = write_host_artifacts(HOST_EVIDENCE)
    plan = build_node_plan()
    permissions = json.loads((HOST_EVIDENCE / "node_permissions.json").read_text(encoding="utf-8"))
    project_root = op("/project1")
    if project_root is None:
        raise RuntimeError("/project1 is required")
    existing = op(ROOT_PATH)
    if existing is not None:
        existing.destroy()

    root = _create(project_root, containerCOMP, "T01_TelemetryPanel", "t01_root")
    root.store("owner", "T-01")
    root.store("authority", "PYTHON_SESSION_CORE")
    root.store("network_direction", "INPUT_ONLY")
    root.store("formal_schema_version", "2.2")
    root.nodeX = 0
    root.nodeY = 0

    sources = _create(root, containerCOMP, "Sources", "source_container")
    udp_adapter = _create(sources, containerCOMP, "UdpTelemetryAdapter", "udp_adapter")
    callbacks = _create(udp_adapter, textDAT, "udp_callbacks", "telemetry_callbacks", "local_state_update")
    callbacks.text = UDP_CALLBACKS
    udp = _create(udp_adapter, udpinDAT, "udp_in", "telemetry_input", "loopback_input")
    _set(udp, "protocol", "msging")
    _set(udp, "port", 5005)
    _set(udp, "localaddress", "127.0.0.1")
    _set(udp, "format", "permessage")
    _set(udp, "callbacks", callbacks.path)
    _set(udp, "executeloc", "callbacks")
    _set(udp, "active", True)

    runtime = _create(root, containerCOMP, "Runtime", "runtime_container")
    adapter_module = _create(runtime, textDAT, "t01_adapter_module", "embedded_adapter_module")
    adapter_module.text = (BASE_DIR / "t01_telemetry.py").read_text(encoding="utf-8")
    panel_state = _create(runtime, textDAT, "panel_state", "local_display_state")
    panel_state.text = json.dumps(
        {"meta": {"stream_state": "WAITING"}, "telemetry": {}, "display_only": {}},
        ensure_ascii=False,
        indent=2,
    )
    render = _create(runtime, executeDAT, "render_execute", "render_tick", "local_display_update")
    render.text = RENDER_CALLBACKS
    _set(render, "framestart", True)
    _set(render, "active", True)

    shell = _create(root, containerCOMP, "ConsoleShell", "console_shell")
    background = _create(shell, constantTOP, "background", "background")
    _configure_top(background)
    _set(background, "colorr", 0.025)
    _set(background, "colorg", 0.045)
    _set(background, "colorb", 0.075)
    _set(background, "colora", 1.0)
    stream_badge = _rectangle(shell, "stream_badge", "stream_badge", (0.42, 0.48, 0.58), 0.40, 0.40, 0.12, 0.08)
    resp_bar = _rectangle(shell, "resp_sqi_bar", "resp_sqi_bar", (0.13, 0.72, 0.92), 0.25, 0.13, 0.02, 0.045)
    ecg_bar = _rectangle(shell, "ecg_sqi_bar", "ecg_sqi_bar", (0.95, 0.76, 0.20), 0.25, 0.04, 0.02, 0.045)
    text = _create(shell, textTOP, "panel_text", "telemetry_text")
    _configure_top(text)
    _set(text, "text", "T-01 TELEMETRY PANEL\nREAD ONLY / WAITING FOR UDP 5005")
    _set(text, "fontsize", 2)
    _set(text, "fontcolorr", 0.88)
    _set(text, "fontcolorg", 0.94)
    _set(text, "fontcolorb", 1.0)
    _set(text, "bgalpha", 0.0)
    _set(text, "alignx", "left")
    _set(text, "aligny", "top")

    composite = _create(shell, compositeTOP, "composite", "console_composite")
    _configure_top(composite)
    _set(composite, "operand", "add")
    for layer in (background, stream_badge, resp_bar, ecg_bar, text):
        layer.outputConnectors[0].connect(composite)

    output = _create(root, containerCOMP, "Output", "output_container")
    display_source = _create(output, selectTOP, "display_source", "local_display_source")
    _set(display_source, "top", composite.path)
    display_out = _create(output, outTOP, "display_out", "local_display_output")
    display_source.outputConnectors[0].connect(display_out)
    display_out.display = True
    display_out.render = True

    _table(
        root,
        "node_permissions",
        ["path", "operator_type", "role", "permission", "active", "port", "local_address"],
        [
            [
                item.get("path", ""),
                item.get("operator_type", ""),
                item.get("role", ""),
                item.get("permission", ""),
                item.get("active", ""),
                item.get("port", ""),
                item.get("local_address", ""),
            ]
            for item in permissions["nodes"]
        ],
        "permission_manifest",
    )
    errors_dat = _table(root, "node_errors", ["kind", "message"], [], "error_report")

    root.cook(force=True, recurse=True)
    errors = root.errors(recurse=True)
    script_errors = root.scriptErrors(recurse=True)
    errors_dat.appendRow(["none", "NO NODE ERRORS"] if not errors and not script_errors else ["operator", errors + script_errors])
    inventory = _inventory(root)
    _write_json(
        TD_EVIDENCE / "node_inventory.json",
        {"inventory_schema_version": "t01-td-node-inventory-v1", "root": ROOT_PATH, "nodes": inventory},
    )
    _write_json(
        TD_EVIDENCE / "node_errors.json",
        {
            "error_report_schema_version": "t01-td-node-errors-v1",
            "operator_errors": errors,
            "script_errors": script_errors,
            "pass": not errors and not script_errors,
        },
    )
    _write_json(
        TD_EVIDENCE / "runtime_build_manifest.json",
        {
            "manifest_schema_version": "t01-td-runtime-build-manifest-v1",
            "touchdesigner_version": str(app.version),
            "touchdesigner_build": str(app.build),
            "product": str(app.product),
            "required_build": TD_BUILD,
            "root": ROOT_PATH,
            "node_count": len(inventory),
            "udp_5005_active": bool(udp.par.active.eval()),
            "udp_5005_local_address": str(udp.par.localaddress.eval()),
            "network_outputs": [],
            "spout_outputs": [],
            "file_outputs": [],
            "t02_request_callbacks": [],
            "host_manifest": host_manifest,
            "node_plan_schema_version": plan["plan_schema_version"],
            "evidence_boundary": "LOCAL_TD_RUNTIME_NOT_LIVE_E2E",
        },
    )
    TD_EVIDENCE.mkdir(parents=True, exist_ok=True)
    root.save(str(TOX_PATH))
    saved = project.save(str(TOE_PATH))
    if not saved:
        raise RuntimeError("TouchDesigner project.save returned False")
    print("T01_BUILD_COMPLETE {} nodes UDP 127.0.0.1:5005".format(len(inventory)))
    return root


build()
