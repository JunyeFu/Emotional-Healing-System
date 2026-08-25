from __future__ import annotations

import json
from pathlib import Path

from verify_repository_privacy import find_privacy_violations


EVIDENCE_PATH = "02-技术研发/07-数据治理/evidence/report.json"


def _write(repo: Path, relative: str, value: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def test_clean_hash_artifact_is_allowed(tmp_path: Path) -> None:
    _write(
        tmp_path,
        EVIDENCE_PATH,
        json.dumps({"sha256": "51322480098991a4eb3ff0f90729fb4ff8cae"}),
    )

    assert find_privacy_violations(tmp_path, [EVIDENCE_PATH]) == []


def test_contact_values_and_fields_are_rejected_without_echo(tmp_path: Path) -> None:
    _write(
        tmp_path,
        EVIDENCE_PATH,
        json.dumps({"phone_hash": "hidden", "note": "+8613912345678"}),
    )

    violations = find_privacy_violations(tmp_path, [EVIDENCE_PATH])

    assert {item["code"] for item in violations} == {
        "E164_VALUE",
        "FORBIDDEN_IDENTITY_FIELD",
        "PHONE_VALUE",
    }
    assert "13912345678" not in json.dumps(violations)


def test_tracked_governance_database_is_rejected(tmp_path: Path) -> None:
    violations = find_privacy_violations(tmp_path, ["private/dedup.sqlite"])

    assert violations == [
        {"code": "FORBIDDEN_TRACKED_FILE", "path": "private/dedup.sqlite"}
    ]


def test_tracked_log_outside_evidence_roots_is_scanned(tmp_path: Path) -> None:
    path = "work/session.log"
    _write(tmp_path, path, "contact=+8613912345678\n")

    violations = find_privacy_violations(tmp_path, [path])

    assert {item["code"] for item in violations} == {"E164_VALUE", "PHONE_VALUE"}


def test_unicode_separated_phone_in_log_is_detected(tmp_path: Path) -> None:
    path = "work/session.log"
    _write(tmp_path, path, "contact=+86\u00a0139\u00a01234\u00a05678\n")

    violations = find_privacy_violations(tmp_path, [path])

    assert {item["code"] for item in violations} == {"PHONE_VALUE"}


def test_zero_width_and_fullwidth_separators_in_log_are_detected(tmp_path: Path) -> None:
    for index, value in enumerate(
        ("+86\u200b139\u200b1234\u200b5678", "139\uff0e1234\uff0e5678")
    ):
        path = f"work/session-{index}.log"
        _write(tmp_path, path, f"contact={value}\n")
        violations = find_privacy_violations(tmp_path, [path])
        assert {item["code"] for item in violations} >= {"PHONE_VALUE"}


def test_unicode_decimal_phone_and_confusable_key_are_detected(tmp_path: Path) -> None:
    path = EVIDENCE_PATH
    _write(tmp_path, path, '{"рhone":"+٨٦ ١٣٩ ١٢٣٤ ٥٦٧٨"}\n')

    violations = find_privacy_violations(tmp_path, [path])

    assert {item["code"] for item in violations} >= {
        "FORBIDDEN_IDENTITY_FIELD",
        "PHONE_VALUE",
    }
