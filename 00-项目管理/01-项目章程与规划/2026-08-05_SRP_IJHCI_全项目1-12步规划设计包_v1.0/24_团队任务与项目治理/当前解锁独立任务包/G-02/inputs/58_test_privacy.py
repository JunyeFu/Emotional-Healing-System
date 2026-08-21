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


@pytest.mark.parametrize(
    "value",
    [
        "Call +8613912345678 before start",
        "Call +86 139 1234 5678 before start",
        "Call 139-1234-5678 before start",
        "Send the note to owner@example.invalid before start",
        "Call +86\u00a0139\u00a01234\u00a05678 before start",
        "Call +86\t139\t1234\t5678 before start",
        "Call 139.1234.5678 before start",
        "Call +86\u200b139\u200b1234\u200b5678 before start",
        "Call +86\u034f139\u034f1234\u034f5678 before start",
        "Call +٨٦ ١٣٩ ١٢٣٤ ٥٦٧٨ before start",
        "Call 139\uff0e1234\uff0e5678 before start",
    ],
)
def test_embedded_contact_values_are_rejected_without_echo(value: str) -> None:
    payload = {"extensions": [{"value": value}]}

    with pytest.raises(GovernanceError) as error:
        privacy_lint_manifest(payload)

    assert error.value.code == "FORBIDDEN_MANIFEST_VALUE"
    assert error.value.path == "$.extensions[0].value"
    assert value not in str(error.value)


def test_unity_package_coordinate_is_not_misclassified_as_email() -> None:
    privacy_lint_manifest(
        {"extensions": [{"value": "package=com.unity.render-pipelines.universal@17.0.3"}]}
    )


def test_fullwidth_forbidden_key_is_rejected() -> None:
    with pytest.raises(GovernanceError, match="FORBIDDEN_MANIFEST_KEY"):
        privacy_lint_manifest({"ｐｈｏｎｅ": "redacted"})


def test_confusable_forbidden_key_is_rejected() -> None:
    with pytest.raises(GovernanceError, match="FORBIDDEN_MANIFEST_KEY"):
        privacy_lint_manifest({"рhone": "redacted"})


def test_research_id_is_the_only_allowed_research_identifier() -> None:
    privacy_lint_manifest(
        {
            "research_id": "SRP-R-0123456789abcdef0123456789abcdef",
            "stage": "stage_1",
            "nested": {"sequence_id": "SEQ-001", "count": 11},
        }
    )
