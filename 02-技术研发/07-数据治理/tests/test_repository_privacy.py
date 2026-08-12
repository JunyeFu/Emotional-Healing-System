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
