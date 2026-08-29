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


def verify():
    root = op(ROOT_PATH)
    if root is None:
        raise RuntimeError("missing {}".format(ROOT_PATH))
    pages = [op("{}/Pages/{}".format(ROOT_PATH, page_id)) for page_id in PAGE_IDS]
    scenario_switches = [page.op("view") if page is not None else None for page in pages]
    output = op("{}/Output/page_selector".format(ROOT_PATH))
    udp = op("{}/Sources/UdpTelemetryPlaceholder".format(ROOT_PATH))
    errors = root.errors(recurse=True)
    script_errors = root.scriptErrors(recurse=True)
    checks = {
        "root_present": True,
        "page_count_10": all(page is not None for page in pages),
        "scenario_inputs_5_each": all(node is not None and len(node.inputs) == 5 for node in scenario_switches),
        "page_inputs_10": output is not None and len(output.inputs) == 10,
        "udp_5005_disabled": udp is not None and int(udp.par.port.eval()) == 5005 and not bool(udp.par.active.eval()),
        "no_node_errors": not errors and not script_errors,
        "toe_exists": TOE_PATH.is_file(),
    }
    report = {
        "report_schema_version": "f04-td-reopen-report-v1",
        "touchdesigner_build": str(app.build),
        "root": ROOT_PATH,
        "checks": checks,
        "operator_errors": errors,
        "script_errors": script_errors,
        "toe_sha256": sha256(TOE_PATH.read_bytes()).hexdigest().upper(),
        "pass": all(checks.values()),
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["pass"]:
        raise RuntimeError("F04_REOPEN_FAIL {}".format(checks))
    print("F04_REOPEN_PASS 10 pages 5 scenarios")
    return report


verify()
