import importlib
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator, FormatChecker


sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
contract = importlib.import_module("05-通信协议.runtime_contract")
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "contracts" / "fixtures"
SCHEMA_PATH = ROOT / "contracts" / "runtime-contract-v2.1.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
SCHEMA_VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def load_fixture(kind: str, name: str) -> dict:
    return json.loads((FIXTURES / kind / name).read_text(encoding="utf-8"))


def schema_accepts(payload: dict) -> bool:
    return not list(SCHEMA_VALIDATOR.iter_errors(payload))


@pytest.mark.parametrize(
    ("filename", "message_type"),
    [
        ("session-manifest-formal.json", "session_manifest"),
        ("control-event.json", "control_event"),
        ("ack.json", "ack"),
        ("telemetry-frame.json", "telemetry_frame"),
        ("policy-decision.json", "policy_decision"),
        ("render-receipt.json", "render_receipt"),
    ],
)
def test_all_legal_fixtures_pass(filename, message_type):
    payload = load_fixture("valid", filename)
    assert schema_accepts(payload)
    assert contract.validate_and_filter(message_type, payload) == payload


@pytest.mark.parametrize(
    ("filename", "message_type", "error_code"),
    [
        ("session-manifest-missing-field.json", "session_manifest", "MISSING_FIELD"),
        ("session-manifest-formal-mock.json", "session_manifest", "FORMAL_MOCK_FORBIDDEN"),
        ("control-event-wrong-version.json", "control_event", "UNSUPPORTED_VERSION"),
        ("telemetry-retired-calm-index.json", "telemetry_frame", "RETIRED_FIELD"),
    ],
)
def test_invalid_fixtures_fail_closed(filename, message_type, error_code):
    payload = load_fixture("invalid", filename)
    assert not schema_accepts(payload)
    with pytest.raises(contract.ContractValidationError) as error:
        contract.validate_and_filter(message_type, payload)
    assert error.value.code == error_code


def test_unknown_compatible_field_is_ignored():
    payload = load_fixture("valid", "telemetry-forward-compatible.json")
    filtered = contract.validate_and_filter("telemetry_frame", payload)
    assert "future_display_hint" not in filtered
    assert filtered["frame_seq"] == 11


@pytest.mark.parametrize(
    ("message_type", "filename", "mutate", "error_code"),
    [
        (
            "session_manifest", "session-manifest-formal.json",
            lambda item: item.update(runtime_mode="formal_stage_3"),
            "STAGE_MODE_MISMATCH",
        ),
        (
            "session_manifest", "session-manifest-formal.json",
            lambda item: item["device_config"]["resp"].update(future_override=True),
            "UNKNOWN_FIELD",
        ),
        (
            "control_event", "control-event.json",
            lambda item: item.update(event_type="module", payload={}),
            "EMPTY_CONTROL_PAYLOAD",
        ),
        (
            "ack", "ack.json",
            lambda item: item.update(error_code="UNEXPECTED"),
            "INCONSISTENT_ACK",
        ),
    ],
)
def test_schema_and_python_reject_cross_field_or_nested_invalid_state(
    message_type, filename, mutate, error_code
):
    payload = load_fixture("valid", filename)
    mutate(payload)
    assert not schema_accepts(payload)
    with pytest.raises(contract.ContractValidationError) as error:
        contract.validate_and_filter(message_type, payload)
    assert error.value.code == error_code


@pytest.mark.parametrize(
    ("message_type", "filename", "mutate"),
    [
        (
            "control_event", "control-event.json",
            lambda item: item.update(effective_monotonic_ns=item["issued_monotonic_ns"] - 1),
        ),
        (
            "ack", "ack.json",
            lambda item: item.update(applied_monotonic_ns=item["received_monotonic_ns"] - 1),
        ),
        (
            "telemetry_frame", "telemetry-frame.json",
            lambda item: item.update(sent_monotonic_ns=item["source_monotonic_ns"] - 1),
        ),
    ],
)
def test_python_rejects_time_order_invariants(message_type, filename, mutate):
    payload = load_fixture("valid", filename)
    mutate(payload)
    with pytest.raises(contract.ContractValidationError) as error:
        contract.validate_and_filter(message_type, payload)
    assert error.value.code == "INVALID_TIME_ORDER"


def test_duplicate_control_cannot_advance_ledger():
    payload = load_fixture("valid", "control-event.json")
    ledger = contract.ControlEventLedger()
    ledger.accept(payload)
    with pytest.raises(contract.ContractValidationError) as error:
        ledger.accept(payload)
    assert error.value.code == "DUPLICATE_CONTROL"
    assert ledger.last_control_seq == 1
    assert ledger.audit_log[-1] == contract.ControlAuditRecord(
        event_id="EV-0001", control_seq=1,
        result="duplicate_ignored", error_code="DUPLICATE_CONTROL",
    )


def test_stale_control_sequence_fails_closed():
    first = load_fixture("valid", "control-event.json")
    stale = dict(first, event_id="EV-0002", control_seq=0)
    ledger = contract.ControlEventLedger()
    ledger.accept(first)
    with pytest.raises(contract.ContractValidationError) as error:
        ledger.accept(stale)
    assert error.value.code == "STALE_CONTROL_SEQUENCE"
    assert ledger.last_control_seq == 1
    assert ledger.audit_log[-1].result == "rejected"
    assert ledger.audit_log[-1].error_code == "STALE_CONTROL_SEQUENCE"


def test_schema_artifact_is_valid_json_and_covers_all_message_types():
    Draft202012Validator.check_schema(SCHEMA)
    assert SCHEMA["$schema"].endswith("2020-12/schema")
    assert set(SCHEMA["$defs"]) >= contract.MESSAGE_TYPES
    for message_type in contract.MESSAGE_TYPES:
        definition = SCHEMA["$defs"][message_type]
        assert set(definition["required"]) == set(contract.KNOWN_FIELDS[message_type])
        assert set(definition["properties"]) >= set(contract.KNOWN_FIELDS[message_type])


def test_formal_manifest_requires_both_real_sources():
    payload = load_fixture("valid", "session-manifest-formal.json")
    payload["device_config"]["resp"]["source"] = "none"
    with pytest.raises(contract.ContractValidationError) as error:
        contract.validate_and_filter("session_manifest", payload)
    assert error.value.code == "FORMAL_SOURCE_REQUIRED"
    assert not schema_accepts(payload)


@pytest.mark.parametrize(
    ("message_type", "filename", "mutation"),
    [
        ("session_manifest", "session-manifest-formal.json", "unknown_build"),
        ("session_manifest", "session-manifest-formal.json", "build_with_newline"),
        ("session_manifest", "session-manifest-formal.json", "formal_mock_policy"),
        ("session_manifest", "session-manifest-formal.json", "unknown_duration"),
        ("session_manifest", "session-manifest-formal.json", "replay_with_mock"),
        ("telemetry_frame", "telemetry-frame.json", "good_with_reason"),
        ("telemetry_frame", "telemetry-frame.json", "degraded_without_reason"),
        ("policy_decision", "policy-decision.json", "selected_not_candidate"),
        ("policy_decision", "policy-decision.json", "bad_stage_1_probability"),
        ("policy_decision", "policy-decision.json", "false_fallback_with_reason"),
        ("control_event", "control-event.json", "malformed_enum"),
        ("policy_decision", "policy-decision.json", "malformed_candidates"),
    ],
)
def test_schema_and_python_reject_same_semantic_mutations(message_type, filename, mutation):
    payload = load_fixture("valid", filename)
    if mutation == "unknown_build":
        payload["unity_build_hash"] = "UNKNOWN"
    elif mutation == "build_with_newline":
        payload["unity_build_hash"] = "build-ok\n"
    elif mutation == "formal_mock_policy":
        payload["source_policy"] = "mock"
    elif mutation == "unknown_duration":
        payload["module_durations"]["future"] = 1
    elif mutation == "replay_with_mock":
        payload.update(runtime_mode="dev_replay", source_policy="mock")
        payload["device_config"]["resp"]["source"] = "mock"
        payload["device_config"]["ecg"]["source"] = "mock"
    elif mutation == "good_with_reason":
        payload["fallback_reason"] = "unexpected"
    elif mutation == "degraded_without_reason":
        payload["fallback_state"] = "DEGRADED"
        payload["fallback_reason"] = None
    elif mutation == "selected_not_candidate":
        payload["candidate_actions"] = ["heat", "snow", "fade"]
    elif mutation == "bad_stage_1_probability":
        payload["behavior_probability"] = 0.9
    elif mutation == "false_fallback_with_reason":
        payload["fallback_reason"] = "unexpected"
    elif mutation == "malformed_enum":
        payload["event_type"] = []
    elif mutation == "malformed_candidates":
        payload["candidate_actions"] = [{}]

    assert not schema_accepts(payload)
    with pytest.raises(contract.ContractValidationError):
        contract.validate_and_filter(message_type, payload)


def test_development_manifest_mock_sources_are_consistent():
    payload = load_fixture("valid", "session-manifest-formal.json")
    payload.update(runtime_mode="dev_mock", source_policy="mock", unity_build_hash="unknown")
    payload["device_config"]["resp"]["source"] = "mock"
    payload["device_config"]["ecg"]["source"] = "mock"
    assert schema_accepts(payload)
    assert contract.validate_and_filter("session_manifest", payload) == payload


def test_replay_manifest_requires_replay_provenance_without_mock_sources():
    payload = load_fixture("valid", "session-manifest-formal.json")
    payload.update(runtime_mode="dev_replay", source_policy="replay", unity_build_hash="unknown")
    payload["device_config"]["resp"]["source"] = "none"
    payload["device_config"]["ecg"]["source"] = "none"
    assert schema_accepts(payload)
    assert contract.validate_and_filter("session_manifest", payload) == payload


def test_json_schema_integer_semantics_accept_integral_number():
    payload = load_fixture("valid", "control-event.json")
    payload["control_seq"] = 1.0
    assert schema_accepts(payload)
    assert contract.validate_and_filter("control_event", payload) == payload


def test_json_schema_integer_semantics_accept_arbitrary_precision_integer():
    payload = load_fixture("valid", "control-event.json")
    payload["control_seq"] = json.loads("1" + "0" * 400)
    assert schema_accepts(payload)
    assert contract.validate_and_filter("control_event", payload) == payload


def test_applied_audit_is_appended_before_ledger_state_advances():
    payload = load_fixture("valid", "control-event.json")
    ledger = contract.ControlEventLedger()

    class ObservingAuditLog(list):
        def append(self, record):
            if record.result == "applied":
                assert ledger.last_control_seq == -1
                assert ledger.event_ids == set()
            super().append(record)

    ledger.audit_log = ObservingAuditLog()
    ledger.accept(payload)
    assert ledger.last_control_seq == 1


@pytest.mark.parametrize(
    ("filename", "message_type"),
    [
        ("session-manifest-formal.json", "session_manifest"),
        ("control-event.json", "control_event"),
        ("ack.json", "ack"),
        ("telemetry-frame.json", "telemetry_frame"),
        ("policy-decision.json", "policy_decision"),
        ("render-receipt.json", "render_receipt"),
    ],
)
def test_schema_and_python_share_required_and_type_boundaries(filename, message_type):
    baseline = load_fixture("valid", filename)
    for field in contract.KNOWN_FIELDS[message_type]:
        missing = deepcopy(baseline)
        missing.pop(field)
        assert not schema_accepts(missing), field
        with pytest.raises(contract.ContractValidationError):
            contract.validate_and_filter(message_type, missing)

        malformed = deepcopy(baseline)
        malformed[field] = []
        assert not schema_accepts(malformed), field
        with pytest.raises(contract.ContractValidationError):
            contract.validate_and_filter(message_type, malformed)


def test_public_api_rejects_unhashable_message_type_with_contract_error():
    with pytest.raises(contract.ContractValidationError) as error:
        contract.validate_and_filter([], {})
    assert error.value.code == "UNKNOWN_MESSAGE_TYPE"


def test_fixture_hash_manifest_uses_lf_canonical_bytes():
    manifest = ROOT / "contracts" / "fixture_hashes.sha256"
    for line in manifest.read_text(encoding="ascii").splitlines():
        expected, relative_path = line.split("  ", 1)
        content = (ROOT / "contracts" / relative_path).read_bytes().replace(b"\r\n", b"\n")
        assert sha256(content).hexdigest() == expected


def test_powershell_consumer_reads_forward_compatible_fixture():
    script = ROOT / "contracts" / "verify_non_python_consumer.ps1"
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(script)],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS_NON_PYTHON_CONSUMER" in result.stdout


def test_fixture_set_contains_no_invalid_json():
    for path in FIXTURES.rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
