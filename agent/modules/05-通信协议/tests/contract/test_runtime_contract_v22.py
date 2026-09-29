import importlib
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest
from jsonschema import Draft202012Validator, FormatChecker


sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
contract = importlib.import_module("05-通信协议.runtime_contract_v22")
ROOT = Path(__file__).resolve().parents[2]
V21_FIXTURES = ROOT / "contracts" / "fixtures" / "valid"
V22_FIXTURES = ROOT / "contracts" / "fixtures-v2.2"
SCHEMA = json.loads(
    (ROOT / "contracts" / "runtime-contract-v2.2.schema.json").read_text(
        encoding="utf-8"
    )
)
SCHEMA_VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def _v21(name: str) -> dict:
    return json.loads((V21_FIXTURES / name).read_text(encoding="utf-8"))


def manifest_v22() -> dict:
    payload = _v21("session-manifest-formal.json")
    payload.update(
        schema_version="2.2",
        breath_protocol_config_version="2.2",
        breath_protocol_config_hash="sha256:" + "a" * 64,
    )
    return payload


def telemetry_v22() -> dict:
    payload = _v21("telemetry-frame.json")
    payload.update(
        schema_version="2.2",
        target_cycle_index=0,
        target_step_id="hold_1",
        target_phase="hold",
        actual_cycle_index=0,
        actual_step_id="inhale_1",
        actual_phase="inhale",
    )
    return payload


def _v22(kind: str, name: str) -> dict:
    return json.loads((V22_FIXTURES / kind / name).read_text(encoding="utf-8"))


def _schema_accepts(payload: dict) -> bool:
    return not list(SCHEMA_VALIDATOR.iter_errors(payload))


def test_v22_manifest_and_telemetry_round_trip_all_owned_fields() -> None:
    for message_type, payload in (
        ("session_manifest", manifest_v22()),
        ("telemetry_frame", telemetry_v22()),
    ):
        assert contract.validate_and_filter(message_type, payload) == payload


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        (lambda item: item.pop("target_step_id"), "MISSING_FIELD"),
        (lambda item: item.update(target_step_id="exhale_1"), "STEP_PHASE_MISMATCH"),
        (lambda item: item.update(target_cycle_index=None), "INCOMPLETE_STEP_IDENTITY"),
        (
            lambda item: item.update(
                actual_cycle_index=None,
                actual_step_id=None,
                actual_phase="inhale",
                actual_progress=0,
            ),
            "EMPTY_STEP_STATE_MISMATCH",
        ),
    ],
)
def test_v22_step_identity_invariants_fail_closed(mutation, error_code) -> None:
    payload = telemetry_v22()
    mutation(payload)
    with pytest.raises(contract.ContractValidationError) as error:
        contract.validate_and_filter("telemetry_frame", payload)
    assert error.value.code == error_code


def test_v22_target_and_actual_may_be_different_steps() -> None:
    payload = telemetry_v22()
    filtered = contract.validate_and_filter("telemetry_frame", payload)
    assert filtered["target_step_id"] == "hold_1"
    assert filtered["actual_step_id"] == "inhale_1"
    assert deepcopy(filtered) == filtered


def test_storm_two_hold_instances_are_distinguishable() -> None:
    first = telemetry_v22()
    second = telemetry_v22()
    first["target_step_id"] = "hold_1"
    second["target_step_id"] = "hold_2"
    assert contract.validate_and_filter("telemetry_frame", first)["target_step_id"] == "hold_1"
    assert contract.validate_and_filter("telemetry_frame", second)["target_step_id"] == "hold_2"


@pytest.mark.parametrize(
    ("filename", "message_type"),
    [
        ("session-manifest-formal.json", "session_manifest"),
        ("control-event.json", "control_event"),
        ("ack.json", "ack"),
        ("policy-decision.json", "policy_decision"),
        ("render-receipt.json", "render_receipt"),
        ("telemetry-storm-hold-1.json", "telemetry_frame"),
        ("telemetry-storm-hold-2.json", "telemetry_frame"),
        ("telemetry-fade-inhale-1.json", "telemetry_frame"),
        ("telemetry-fade-inhale-2.json", "telemetry_frame"),
        ("telemetry-actual-unavailable.json", "telemetry_frame"),
    ],
)
def test_v22_legal_fixtures_match_schema_and_reference_validator(
    filename, message_type
) -> None:
    payload = _v22("valid", filename)
    assert _schema_accepts(payload)
    assert contract.validate_and_filter(message_type, payload) == payload


@pytest.mark.parametrize(
    ("filename", "message_type", "error_code"),
    [
        ("telemetry-missing-step-id.json", "telemetry_frame", "MISSING_FIELD"),
        (
            "telemetry-partial-step-identity.json",
            "telemetry_frame",
            "INCOMPLETE_STEP_IDENTITY",
        ),
        (
            "telemetry-step-phase-mismatch.json",
            "telemetry_frame",
            "STEP_PHASE_MISMATCH",
        ),
        ("telemetry-unknown-step.json", "telemetry_frame", "INVALID_STEP_ID"),
        (
            "telemetry-empty-step-state-mismatch.json",
            "telemetry_frame",
            "EMPTY_STEP_STATE_MISMATCH",
        ),
        (
            "telemetry-retired-calm-index.json",
            "telemetry_frame",
            "RETIRED_FIELD",
        ),
        (
            "session-manifest-invalid-breath-hash.json",
            "session_manifest",
            "INVALID_CONFIG_HASH",
        ),
        ("control-event-wrong-version.json", "control_event", "UNSUPPORTED_VERSION"),
    ],
)
def test_v22_invalid_fixtures_fail_closed_in_schema_and_reference_validator(
    filename, message_type, error_code
) -> None:
    payload = _v22("invalid", filename)
    assert not _schema_accepts(payload)
    with pytest.raises(contract.ContractValidationError) as error:
        contract.validate_and_filter(message_type, payload)
    assert error.value.code == error_code


def test_v22_schema_covers_reference_owned_fields() -> None:
    Draft202012Validator.check_schema(SCHEMA)
    assert SCHEMA["title"] == "SRP Runtime Contract v2.2"
    for message_type in contract.MESSAGE_TYPES:
        definition = SCHEMA["$defs"][message_type]
        assert set(definition["required"]) == set(contract.KNOWN_FIELDS[message_type])
        assert set(definition["properties"]) >= set(contract.KNOWN_FIELDS[message_type])


def test_v22_fixture_hash_manifest_uses_lf_canonical_bytes() -> None:
    manifest = ROOT / "contracts" / "fixture_hashes_v2.2.sha256"
    expected_paths = {
        path.relative_to(ROOT / "contracts").as_posix()
        for root in (
            ROOT / "contracts" / "fixtures-v2.2",
            ROOT / "contracts" / "consumer-fixtures" / "v2.2",
        )
        for suffix in ("*.json", "*.jsonl")
        for path in root.rglob(suffix)
    }
    actual_paths = set()
    for line in manifest.read_text(encoding="ascii").splitlines():
        expected, relative_path = line.split("  ", 1)
        content = (ROOT / "contracts" / relative_path).read_bytes().replace(b"\r\n", b"\n")
        assert sha256(content).hexdigest() == expected
        actual_paths.add(relative_path)
    assert actual_paths == expected_paths


@pytest.mark.parametrize(
    ("message_type", "filename"),
    [
        ("session_manifest", "session-manifest-formal.json"),
        ("control_event", "control-event.json"),
        ("ack", "ack.json"),
        ("telemetry_frame", "telemetry-storm-hold-1.json"),
        ("policy_decision", "policy-decision.json"),
        ("render_receipt", "render-receipt.json"),
    ],
)
def test_v22_schema_and_reference_share_required_field_boundaries(
    message_type, filename
) -> None:
    baseline = _v22("valid", filename)
    for field in contract.KNOWN_FIELDS[message_type]:
        payload = deepcopy(baseline)
        payload.pop(field)
        assert not _schema_accepts(payload), field
        with pytest.raises(contract.ContractValidationError):
            contract.validate_and_filter(message_type, payload)


def test_v22_unknown_compatible_field_is_ignored_after_validation() -> None:
    payload = _v22("valid", "telemetry-storm-hold-1.json")
    payload["future_display_hint"] = "ignored"
    filtered = contract.validate_and_filter("telemetry_frame", payload)
    assert "future_display_hint" not in filtered
