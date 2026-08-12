from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from srp_governance import GovernanceError, privacy_lint_manifest


ROOT = Path(__file__).resolve().parents[3]
FORMAL_MANIFEST = (
    ROOT
    / "02-技术研发"
    / "05-通信协议"
    / "contracts"
    / "fixtures"
    / "valid"
    / "session-manifest-formal.json"
)


def test_runtime_contract_formal_manifest_passes_privacy_gate() -> None:
    manifest = json.loads(FORMAL_MANIFEST.read_text(encoding="utf-8"))
    original = deepcopy(manifest)

    privacy_lint_manifest(manifest)

    assert manifest == original


@pytest.mark.parametrize(
    ("payload", "expected_path"),
    [
        ({"participantName": "synthetic"}, "$.participantName"),
        ({"nested": [{"phone_hash": "abc"}]}, "$.nested[0].phone_hash"),
        ({"meta": {"联系方式": "synthetic"}}, "$.meta.联系方式"),
        ({"contact_hash": "abc"}, "$.contact_hash"),
        ({"dedupToken": "abc"}, "$.dedupToken"),
    ],
)
def test_forbidden_contact_keys_are_rejected_by_json_path(
    payload: dict, expected_path: str
) -> None:
    with pytest.raises(GovernanceError) as error:
        privacy_lint_manifest(payload)

    assert error.value.code == "FORBIDDEN_MANIFEST_KEY"
    assert error.value.path == expected_path


@pytest.mark.parametrize(
    ("value", "expected_path"),
    [
        ("synthetic@example.invalid", "$.extensions[0].value"),
        ("+1 (415) 555-2671", "$.extensions[0].value"),
        ("13800138000", "$.extensions[0].value"),
    ],
)
def test_contact_like_extension_values_are_rejected_without_echo(
    value: str, expected_path: str
) -> None:
    payload = {"extensions": [{"value": value}]}

    with pytest.raises(GovernanceError) as error:
        privacy_lint_manifest(payload)

    assert error.value.code == "FORBIDDEN_MANIFEST_VALUE"
    assert error.value.path == expected_path
    assert value not in str(error.value)


def test_research_id_is_the_only_allowed_research_identifier() -> None:
    privacy_lint_manifest(
        {
            "research_id": "SRP-R-0123456789abcdef0123456789abcdef",
            "stage": "stage_1",
            "nested": {"sequence_id": "SEQ-001", "count": 11},
        }
    )
