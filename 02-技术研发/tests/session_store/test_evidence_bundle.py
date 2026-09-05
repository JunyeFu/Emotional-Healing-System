from __future__ import annotations

import hashlib
from pathlib import Path

from srp_session_store.evidence_bundle import REQUIRED_FAMILIES, validate_bundle


def bundle(tmp_path: Path) -> dict:
    artifacts = []
    for family in sorted(REQUIRED_FAMILIES):
        path = tmp_path / f"{family}.json"
        path.write_text(family, encoding="utf-8")
        artifacts.append(
            {
                "family": family,
                "artifact_id": family + "-1",
                "location_type": "local_file",
                "location": path.name,
                "content_kind": "raw_evidence",
                "hash_strategy": "byte_sha256",
                "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "observed_or_derived": "observed",
                "reason_code": None,
            }
        )
    return {
        "schema_version": "1.0",
        "bundle_id": "fixture-bundle",
        "session_ref": "fixture-session",
        "families": sorted(REQUIRED_FAMILIES),
        "artifacts": artifacts,
    }


def test_complete_bundle_validates(tmp_path: Path):
    assert validate_bundle(bundle(tmp_path), tmp_path)["ok"]


def test_non_wave_original_changes_input_identity(tmp_path: Path):
    first = bundle(tmp_path)
    first_result = validate_bundle(first, tmp_path)
    questionnaire = next(item for item in first["artifacts"] if item["family"] == "questionnaires")
    questionnaire_path = tmp_path / questionnaire["location"]
    questionnaire_path.write_text("changed questionnaire", encoding="utf-8")
    questionnaire["content_sha256"] = hashlib.sha256(questionnaire_path.read_bytes()).hexdigest()
    second_result = validate_bundle(first, tmp_path)
    assert first_result["input_identity"] != second_result["input_identity"]


def test_missing_questionnaire_fails_closed(tmp_path: Path):
    candidate = bundle(tmp_path)
    candidate["artifacts"] = [
        item for item in candidate["artifacts"] if item["family"] != "questionnaires"
    ]
    result = validate_bundle(candidate, tmp_path)
    assert not result["ok"]
    assert any(item.startswith("FAMILIES_WITHOUT_ARTIFACT:") for item in result["errors"])


def test_byte_tamper_is_detected(tmp_path: Path):
    candidate = bundle(tmp_path)
    first = candidate["artifacts"][0]
    (tmp_path / first["location"]).write_text("tampered", encoding="utf-8")
    assert any(
        item.endswith("CONTENT_HASH_MISMATCH")
        for item in validate_bundle(candidate, tmp_path)["errors"]
    )


def test_normalized_text_hash_is_stable_across_line_endings(tmp_path: Path):
    candidate = bundle(tmp_path)
    first = candidate["artifacts"][0]
    path = tmp_path / first["location"]
    path.write_bytes(b"alpha  \r\nbeta\r\n")
    normalized = b"alpha\nbeta\n"
    first["hash_strategy"] = "normalized_text_sha256"
    first["content_kind"] = "source_text"
    first["content_sha256"] = hashlib.sha256(normalized).hexdigest()
    assert validate_bundle(candidate, tmp_path)["ok"]


def test_restricted_original_requires_content_hash(tmp_path: Path):
    candidate = bundle(tmp_path)
    first = candidate["artifacts"][0]
    first.update(
        location_type="restricted_ref",
        location="restricted://source-1",
        hash_strategy="byte_sha256",
        content_sha256=None,
    )
    result = validate_bundle(candidate, tmp_path)
    assert not result["ok"]
    assert any(item.endswith("CONTENT_HASH_REQUIRED") for item in result["errors"])


def test_local_file_requires_base_directory(tmp_path: Path):
    result = validate_bundle(bundle(tmp_path))
    assert not result["ok"]
    assert any(item.endswith("BASE_DIR_REQUIRED_FOR_LOCAL_FILE") for item in result["errors"])


def test_structured_identity_cannot_collide_through_delimiters(tmp_path: Path):
    first = bundle(tmp_path)
    second = bundle(tmp_path)
    for candidate in (first, second):
        for item in candidate["artifacts"]:
            item["location_type"] = "restricted_ref"
            item["location"] = "restricted://" + item["artifact_id"]
    left = first["artifacts"][0]
    right = second["artifacts"][0]
    left.update(
        location_type="restricted_ref",
        artifact_id="x|restricted_ref",
        location="loc",
    )
    right.update(
        location_type="restricted_ref",
        artifact_id="x",
        location="restricted_ref|loc",
    )
    first_result = validate_bundle(first)
    second_result = validate_bundle(second)
    assert first_result["ok"] and second_result["ok"]
    assert first_result["input_identity"] != second_result["input_identity"]


def test_required_family_cannot_be_satisfied_by_explicit_none(tmp_path: Path):
    candidate = bundle(tmp_path)
    first = candidate["artifacts"][0]
    first.update(
        location_type="explicit_none",
        location="none://missing",
        content_kind="raw_evidence",
        hash_strategy=None,
        content_sha256=None,
        reason_code="NOT_COLLECTED",
    )
    result = validate_bundle(candidate, tmp_path)
    assert not result["ok"]
    assert any("REQUIRED_ARTIFACT_MISSING" in item for item in result["errors"])


def test_runtime_validator_enforces_top_level_schema_fields(tmp_path: Path):
    candidate = bundle(tmp_path)
    candidate["bundle_id"] = ""
    candidate["session_ref"] = ""
    candidate["unexpected"] = True
    candidate["artifacts"][0]["location"] = ""
    result = validate_bundle(candidate, tmp_path)
    assert not result["ok"]
    assert "TOP_LEVEL_FIELDS_INVALID" in result["errors"]
    assert "BUNDLE_ID_INVALID" in result["errors"]
    assert "SESSION_REF_INVALID" in result["errors"]
    assert any(item.endswith("LOCATION_INVALID") for item in result["errors"])


def test_invalid_family_and_reason_types_fail_without_exception(tmp_path: Path):
    candidate = bundle(tmp_path)
    candidate["families"].append({"invalid": True})
    candidate["artifacts"][0]["reason_code"] = {"invalid": True}
    result = validate_bundle(candidate, tmp_path)
    assert not result["ok"]
    assert "FAMILY_ITEMS_INVALID" in result["errors"]
    assert any(item.endswith("REASON_CODE_INVALID") for item in result["errors"])


def test_invalid_artifact_family_type_fails_without_exception(tmp_path: Path):
    candidate = bundle(tmp_path)
    candidate["artifacts"][0]["family"] = {"invalid": True}
    result = validate_bundle(candidate, tmp_path)
    assert not result["ok"]
    assert any(item.endswith("FAMILY_INVALID") for item in result["errors"])


def test_invalid_artifact_enum_types_fail_without_exception(tmp_path: Path):
    expected = {
        "location_type": "LOCATION_TYPE_INVALID",
        "content_kind": "CONTENT_KIND_INVALID",
        "hash_strategy": "HASH_STRATEGY_INVALID",
        "observed_or_derived": "OBSERVATION_NAMESPACE_INVALID",
    }
    for field, error in expected.items():
        candidate = bundle(tmp_path)
        candidate["artifacts"][0][field] = {"invalid": True}
        result = validate_bundle(candidate, tmp_path)
        assert not result["ok"]
        assert any(item.endswith(error) for item in result["errors"])
