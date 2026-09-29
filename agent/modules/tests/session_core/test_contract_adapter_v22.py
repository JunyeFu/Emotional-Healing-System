from __future__ import annotations

import json
from pathlib import Path

import pytest

from srp_session_core.contract_adapter import validate_message
from srp_session_core import SessionCoreError


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "05-通信协议" / "contracts"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_adapter_dispatches_v21_and_v22_without_call_site_version_branch() -> None:
    v21 = _read(CONTRACTS / "fixtures" / "valid" / "telemetry-frame.json")
    v22 = _read(
        CONTRACTS
        / "fixtures-v2.2"
        / "valid"
        / "telemetry-storm-hold-2.json"
    )
    assert validate_message("telemetry_frame", v21) == v21
    assert validate_message("telemetry_frame", v22) == v22


def test_adapter_rejects_unknown_version_before_consumer_state_changes() -> None:
    payload = _read(CONTRACTS / "fixtures" / "valid" / "telemetry-frame.json")
    payload["schema_version"] = "9.9"
    with pytest.raises(SessionCoreError) as error:
        validate_message("telemetry_frame", payload)
    assert error.value.code == "CONTRACT_UNSUPPORTED_VERSION"
