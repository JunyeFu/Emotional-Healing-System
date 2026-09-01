"""Verify and capture the saved T-01 project after a clean TouchDesigner reopen."""

from __future__ import annotations

import builtins
from hashlib import sha256
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE_DIR / "evidence" / "touchdesigner"
SCREENSHOT_DIR = EVIDENCE_DIR / "screenshots"
STATE_DIR = EVIDENCE_DIR / "states"
REPORT_PATH = EVIDENCE_DIR / "reopen_report.json"
CAPTURE_MANIFEST_PATH = EVIDENCE_DIR / "capture_manifest.json"
ROOT_PATH = "/project1/T01_TelemetryPanel"
ALLOWED_CAPTURE_LABELS = {
    "publisher_live",
    "fixture_good",
    "out_of_order",
    "disconnected",
    "recovered",
}
FORBIDDEN_OPERATOR_TYPES = {
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
FORBIDDEN_CALLBACK_TOKENS = (".send(", ".sendBytes(", ".sendOSC(", "socket.socket(", "port=5010")


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def verify():
    root = op(ROOT_PATH)
    if root is None:
        raise RuntimeError("T01 root missing")
    udp = root.op("Sources/UdpTelemetryAdapter/udp_in")
    callbacks = root.op("Sources/UdpTelemetryAdapter/udp_callbacks")
    render = root.op("Runtime/render_execute")
    display_source = root.op("Output/display_source")
    display = root.op("Output/display_out")
    nodes = [root] + list(root.findChildren(maxDepth=10))
    callback_text = "\n".join(
        node.text for node in nodes if node.OPType in {"textDAT", "executeDAT"}
    )
    forbidden_nodes = [node.path for node in nodes if node.OPType in FORBIDDEN_OPERATOR_TYPES]
    forbidden_callbacks = [token for token in FORBIDDEN_CALLBACK_TOKENS if token in callback_text]
    operator_errors = root.errors(recurse=True)
    script_errors = root.scriptErrors(recurse=True)
    checks = {
        "touchdesigner_build_2025_32820": str(app.build) == "2025.32820",
        "root_present": root is not None,
        "udp_input_present": udp is not None and udp.OPType == "udpinDAT",
        "udp_5005_active": udp is not None and int(udp.par.port.eval()) == 5005 and bool(udp.par.active.eval()),
        "udp_loopback_only": udp is not None and str(udp.par.localaddress.eval()) == "127.0.0.1",
        "udp_callbacks_present": callbacks is not None and "def onReceive" in callbacks.text,
        "render_tick_present": render is not None and "def onFrameStart" in render.text,
        "display_output_present": (
            display_source is not None
            and display_source.OPType == "selectTOP"
            and display is not None
            and display.OPType == "outTOP"
            and display.width == 1280
            and display.height == 720
        ),
        "no_forbidden_output_nodes": not forbidden_nodes,
        "no_network_send_callbacks": not forbidden_callbacks,
        "no_node_errors": not operator_errors and not script_errors,
        "python_authority_unchanged": root.fetch("authority", None) == "PYTHON_SESSION_CORE",
    }
    report = {
        "report_schema_version": "t01-td-reopen-report-v1",
        "touchdesigner_version": str(app.version),
        "touchdesigner_build": str(app.build),
        "root": ROOT_PATH,
        "node_count": len(nodes),
        "checks": checks,
        "forbidden_nodes": forbidden_nodes,
        "forbidden_callback_tokens": forbidden_callbacks,
        "operator_errors": operator_errors,
        "script_errors": script_errors,
        "pass": all(checks.values()),
        "evidence_boundary": "LOCAL_TD_RUNTIME_NOT_LIVE_E2E",
    }
    _write_json(REPORT_PATH, report)
    if not report["pass"]:
        raise RuntimeError("T01_REOPEN_FAIL " + json.dumps(checks, sort_keys=True))
    print("T01_REOPEN_PASS {} nodes UDP 127.0.0.1:5005".format(len(nodes)))
    return report


def capture(label: str):
    if label not in ALLOWED_CAPTURE_LABELS:
        raise ValueError("unsupported capture label: " + str(label))
    root = op(ROOT_PATH)
    snapshot = getattr(builtins, "T01_LAST_SNAPSHOT", None)
    if not isinstance(snapshot, dict):
        raise RuntimeError("no T01 runtime snapshot available")
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    screenshot = SCREENSHOT_DIR / (label + ".png")
    state = STATE_DIR / (label + ".json")
    output = root.op("Output/display_out")
    output.cook(force=True)
    output.save(str(screenshot))
    _write_json(state, snapshot)
    manifest = (
        json.loads(CAPTURE_MANIFEST_PATH.read_text(encoding="utf-8"))
        if CAPTURE_MANIFEST_PATH.is_file()
        else {"manifest_schema_version": "t01-capture-manifest-v1", "captures": {}}
    )
    manifest["captures"][label] = {
        "screenshot": screenshot.name,
        "screenshot_sha256": _sha256(screenshot),
        "state": state.name,
        "state_sha256": _sha256(state),
    }
    _write_json(CAPTURE_MANIFEST_PATH, manifest)
    print("T01_CAPTURE {} {}".format(label, screenshot))
    return manifest["captures"][label]


builtins.t01_verify = verify
builtins.t01_capture = capture
verify()
