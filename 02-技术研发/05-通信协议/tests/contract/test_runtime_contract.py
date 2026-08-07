import importlib
import json
from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
contract = importlib.import_module("05-通信协议.runtime_contract")
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "contracts" / "fixtures"


def load_fixture(kind: str, name: str) -> dict:
    return json.loads((FIXTURES / kind / name).read_text(encoding="utf-8"))


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
    with pytest.raises(contract.ContractValidationError) as error:
        contract.validate_and_filter(message_type, payload)
    assert error.value.code == error_code


def test_unknown_compatible_field_is_ignored():
    payload = load_fixture("valid", "telemetry-forward-compatible.json")
    filtered = contract.validate_and_filter("telemetry_frame", payload)
    assert "future_display_hint" not in filtered
    assert filtered["frame_seq"] == 11


def test_duplicate_control_cannot_advance_ledger():
    payload = load_fixture("valid", "control-event.json")
    ledger = contract.ControlEventLedger()
    ledger.accept(payload)
    with pytest.raises(contract.ContractValidationError) as error:
        ledger.accept(payload)
    assert error.value.code == "DUPLICATE_CONTROL"
    assert ledger.last_control_seq == 1


def test_stale_control_sequence_fails_closed():
    first = load_fixture("valid", "control-event.json")
    stale = dict(first, event_id="EV-0002", control_seq=0)
    ledger = contract.ControlEventLedger()
    ledger.accept(first)
    with pytest.raises(contract.ContractValidationError) as error:
        ledger.accept(stale)
    assert error.value.code == "STALE_CONTROL_SEQUENCE"


def test_schema_artifact_is_valid_json_and_covers_all_message_types():
    schema = json.loads((ROOT / "contracts" / "runtime-contract-v2.1.schema.json").read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert set(schema["$defs"]) >= contract.MESSAGE_TYPES
    for message_type in contract.MESSAGE_TYPES:
        definition = schema["$defs"][message_type]
        assert set(definition["required"]) == set(contract.KNOWN_FIELDS[message_type])
        assert set(definition["properties"]) >= set(contract.KNOWN_FIELDS[message_type])


def test_formal_manifest_requires_both_real_sources():
    payload = load_fixture("valid", "session-manifest-formal.json")
    payload["device_config"]["resp"]["source"] = "none"
    with pytest.raises(contract.ContractValidationError) as error:
        contract.validate_and_filter("session_manifest", payload)
    assert error.value.code == "FORMAL_SOURCE_REQUIRED"


def test_fixture_set_contains_no_invalid_json():
    for path in FIXTURES.rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
