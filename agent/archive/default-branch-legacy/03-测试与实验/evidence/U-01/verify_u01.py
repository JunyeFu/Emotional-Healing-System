from __future__ import annotations

import json
import importlib.util
import sys
import types
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent

EXPECTED_TESTS = {
    "editmode-results.xml": {
        "SRP.U01.Tests.U01EditModeTests.AckSerializationKeepsPythonContractNullSemantics",
        "SRP.U01.Tests.U01EditModeTests.ConfirmedReceiptSurvivesDuplicateControlWithoutMirrorDrift",
        "SRP.U01.Tests.U01EditModeTests.DeliveryFactoryPreservesIdentityAndRejectsInvalidFailureReceipt",
        "SRP.U01.Tests.U01EditModeTests.DisposeDoesNotWaitForABlockedSendLock",
        "SRP.U01.Tests.U01EditModeTests.ExactRetryIsIdempotentButAlteredDuplicateAndOldSequenceAreRejected",
        "SRP.U01.Tests.U01EditModeTests.FailedOldConnectionIsDisposedWithoutTouchingNewGeneration",
        "SRP.U01.Tests.U01EditModeTests.FormalV21AndWrongHandshakeFailClosed",
        "SRP.U01.Tests.U01EditModeTests.GoldenControlTraceIsMirroredWithoutLocalSequencing",
        "SRP.U01.Tests.U01EditModeTests.IncomingFrameLimitIncludesLineFeed",
        "SRP.U01.Tests.U01EditModeTests.NullableCycleIdentityIsPreservedAndNegativeCycleIsRejected",
        "SRP.U01.Tests.U01EditModeTests.ReliableClientReconnectsAndKeepsTheSameIdentity",
        "SRP.U01.Tests.U01EditModeTests.StaleAndMismatchedTelemetryCannotOverwriteLatestMirrorFrame",
        "SRP.U01.Tests.U01EditModeTests.V21TelemetryAndSharedStateRulesMatchTheAuthoritativeContract",
        "SRP.U01.Tests.U01EditModeTests.V22TelemetryFixturesMatchTheAuthoritativeContract",
    },
    "playmode-results.xml": {
        "SRP.U01.Tests.U01PlayModeTests.DisableAndEnablePreservesTheActiveMirror",
        "SRP.U01.Tests.U01PlayModeTests.RenderReceiptRequiresAnExplicitFrameConfirmation",
        "SRP.U01.Tests.U01PlayModeTests.UnityFramesDoNotAdvanceTheSessionMirror",
    },
}


def load_json(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def load_golden() -> dict:
    path = ROOT.parents[2] / "02-技术研发" / "srp_session_core" / "fixtures" / "golden" / "four-module-trace-v1.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_contract_modules() -> tuple[object, object]:
    protocol_dir = ROOT.parents[2] / "02-技术研发" / "05-通信协议"
    package_name = "05-通信协议"
    package = types.ModuleType(package_name)
    package.__path__ = [str(protocol_dir)]
    sys.modules[package_name] = package

    modules = []
    for short_name in ("runtime_contract", "runtime_contract_v22"):
        name = f"{package_name}.{short_name}"
        spec = importlib.util.spec_from_file_location(name, protocol_dir / f"{short_name}.py")
        require(spec is not None and spec.loader is not None, f"cannot load {short_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    return modules[0], modules[1]


def verify_test_result(name: str) -> None:
    run = ET.parse(ROOT / name).getroot()
    expected = EXPECTED_TESTS[name]
    cases = list(run.iter("test-case"))
    require(run.attrib.get("result") == "Passed", f"{name}: test run did not pass")
    require(int(run.attrib.get("total", "-1")) == len(expected), f"{name}: unexpected test count")
    require(int(run.attrib.get("failed", "-1")) == 0, f"{name}: failures present")
    require(len(cases) == len(expected), f"{name}: test cases are missing")
    require({case.attrib.get("fullname") for case in cases} == expected,
            f"{name}: test case identity mismatch")
    require(all(case.attrib.get("result") == "Passed" for case in cases),
            f"{name}: a test case did not pass")


def main() -> int:
    verify_test_result("editmode-results.xml")
    verify_test_result("playmode-results.xml")

    trace = load_json("state-mirror-trace.json")
    rows = trace.get("rows", [])
    golden = load_golden()
    controls = golden["control_events"]
    expected_rows = []
    status, module_id, segment = "Created", "", ""
    for control in controls:
        event_type = control["event_type"]
        if event_type == "prepare": status = "Prepared"
        elif event_type == "start": status = "Running"
        elif event_type == "end": status = "Completed"
        elif event_type == "module":
            module_id, segment = control["payload"]["module_id"], ""
        elif event_type == "segment": segment = control["payload"]["segment"]
        expected_rows.append({"sequence": control["control_seq"], "event_type": event_type,
                              "result": "applied", "status": status,
                              "module_id": module_id, "segment": segment})
    require(rows == expected_rows, "state mirror trace does not match the golden control semantics")

    deliveries = load_json("ack-render-receipt-sequence.json")
    acks = deliveries.get("acks", [])
    receipts = deliveries.get("render_receipts", [])
    segment_controls = [item for item in controls if item["event_type"] == "segment"]
    expected_acks = [
        {
            "schema_version": item["schema_version"],
            "message_type": "ack",
            "session_id": item["session_id"],
            "event_id": item["event_id"],
            "received_monotonic_ns": item["effective_monotonic_ns"],
            "applied_monotonic_ns": item["effective_monotonic_ns"],
            "unity_frame": item["control_seq"],
            "result": "applied",
            "error_code": None,
        }
        for item in controls
    ]
    expected_receipts = [
        {
            "schema_version": item["schema_version"],
            "message_type": "render_receipt",
            "receipt_id": f"RR-U01-EVIDENCE-{item['event_id']}",
            "session_id": item["session_id"],
            "event_id": item["event_id"],
            "frame_seq": item["control_seq"],
            "unity_frame": item["control_seq"],
            "rendered_monotonic_ns": item["effective_monotonic_ns"],
            "module_id": item["payload"]["module_id"],
            "segment": item["payload"]["segment"],
            "result": "rendered",
            "error_code": None,
        }
        for item in segment_controls
    ]
    require(acks == expected_acks, "ACK evidence does not exactly match the golden control deliveries")
    require(receipts == expected_receipts, "render receipt evidence does not exactly match the golden segment deliveries")
    contract_v21, contract_v22 = load_contract_modules()
    for item in acks:
        contract = contract_v22 if item["schema_version"] == "2.2" else contract_v21
        contract.validate_and_filter("ack", item)
    for item in receipts:
        contract = contract_v22 if item["schema_version"] == "2.2" else contract_v21
        contract.validate_and_filter("render_receipt", item)

    network = load_json("network-fault-log.json")
    expected_network = {
        "wrong_schema_welcome": "rejected",
        "reconnect_same_client_identity": "test_passed",
        "closed_socket_send": "send_returns_false",
    }
    rows = network.get("rows", [])
    require(len(rows) == len(expected_network), "network matrix must contain three cases")
    require({row["case_id"] for row in rows} == set(expected_network),
            "network matrix cases are missing or duplicated")
    require(all(row["expected"] == expected_network[row["case_id"]] and
                row["observed"] == expected_network[row["case_id"]] and row["result"] == "PASS"
                for row in rows), "network matrix contains failure")

    require(deliveries.get("evidence_scope") == "contract_golden_fixture", "delivery evidence scope is missing")

    print("U01_EVIDENCE_VERIFIED editmode=14 playmode=3 controls=19 acks=19 receipts=12 network=3")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, ValueError, ET.ParseError) as exc:
        print(f"U01_EVIDENCE_INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1)
