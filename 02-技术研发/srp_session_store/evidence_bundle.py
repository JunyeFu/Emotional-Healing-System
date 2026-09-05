"""Validate complete raw evidence bundle metadata for downstream reconstruction."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_FAMILIES = {
    "device_streams",
    "runtime_facts",
    "questionnaires",
    "allocations",
    "annotations",
    "configuration_build",
}
VALID_LOCATION_TYPES = {"local_file", "restricted_ref", "explicit_none"}
VALID_HASH_STRATEGIES = {"byte_sha256", "normalized_text_sha256"}
VALID_CONTENT_KINDS = {"raw_evidence", "binary", "build_artifact", "source_text"}
BYTE_HASH_KINDS = {"raw_evidence", "binary", "build_artifact"}
TOP_LEVEL_FIELDS = {"schema_version", "bundle_id", "session_ref", "families", "artifacts"}
ARTIFACT_FIELDS = {
    "family", "artifact_id", "location_type", "location", "content_kind",
    "hash_strategy", "content_sha256", "observed_or_derived", "reason_code",
}


def _content_for_hash(path: Path, strategy: str) -> bytes:
    content = path.read_bytes()
    if strategy == "byte_sha256":
        return content
    text = content.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return ("\n".join(line.rstrip(" \t") for line in text.split("\n"))).encode("utf-8")


def validate_bundle(bundle: dict[str, Any], base_dir: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    if set(bundle) != TOP_LEVEL_FIELDS:
        errors.append("TOP_LEVEL_FIELDS_INVALID")
    if bundle.get("schema_version") != "1.0":
        errors.append("UNSUPPORTED_SCHEMA_VERSION")
    if not isinstance(bundle.get("bundle_id"), str) or not bundle["bundle_id"].strip():
        errors.append("BUNDLE_ID_INVALID")
    if not isinstance(bundle.get("session_ref"), str) or not bundle["session_ref"].strip():
        errors.append("SESSION_REF_INVALID")
    family_list = bundle.get("families")
    if not isinstance(family_list, list):
        family_list = []
        errors.append("FAMILIES_NOT_LIST")
    if any(not isinstance(item, str) for item in family_list):
        errors.append("FAMILY_ITEMS_INVALID")
    string_families = [item for item in family_list if isinstance(item, str)]
    families = set(string_families)
    if len(families) != len(string_families):
        errors.append("FAMILIES_NOT_UNIQUE")
    if missing := REQUIRED_FAMILIES - families:
        errors.append("MISSING_FAMILIES:" + ",".join(sorted(missing)))
    if extras := families - REQUIRED_FAMILIES:
        errors.append("UNKNOWN_FAMILIES:" + ",".join(sorted(extras)))

    identities: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []
        errors.append("ARTIFACTS_NOT_LIST")
    for index, artifact in enumerate(artifacts):
        path = f"$.artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(path + ":NOT_OBJECT")
            continue
        if set(artifact) != ARTIFACT_FIELDS:
            errors.append(path + ":FIELDS_INVALID")
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            errors.append(path + ":ARTIFACT_ID_INVALID")
            continue
        if artifact_id in seen_ids:
            errors.append(path + ":DUPLICATE_ARTIFACT_ID")
        seen_ids.add(artifact_id)
        family = artifact.get("family")
        if not isinstance(family, str) or family not in REQUIRED_FAMILIES:
            errors.append(path + ":FAMILY_INVALID")
        observed_or_derived = artifact.get("observed_or_derived")
        if not isinstance(observed_or_derived, str) or observed_or_derived not in {"observed", "derived"}:
            errors.append(path + ":OBSERVATION_NAMESPACE_INVALID")
        reason_code = artifact.get("reason_code")
        if reason_code is not None and not isinstance(reason_code, str):
            errors.append(path + ":REASON_CODE_INVALID")
        location_type = artifact.get("location_type")
        if not isinstance(location_type, str) or location_type not in VALID_LOCATION_TYPES:
            errors.append(path + ":LOCATION_TYPE_INVALID")
        if not isinstance(artifact.get("location"), str) or not artifact["location"].strip():
            errors.append(path + ":LOCATION_INVALID")
        strategy = artifact.get("hash_strategy")
        digest = artifact.get("content_sha256")
        content_kind = artifact.get("content_kind")
        if not isinstance(content_kind, str) or content_kind not in VALID_CONTENT_KINDS:
            errors.append(path + ":CONTENT_KIND_INVALID")
        if isinstance(content_kind, str) and content_kind in BYTE_HASH_KINDS and strategy != "byte_sha256":
            errors.append(path + ":BYTE_HASH_STRATEGY_REQUIRED")
        if content_kind == "source_text" and strategy != "normalized_text_sha256":
            errors.append(path + ":NORMALIZED_TEXT_HASH_STRATEGY_REQUIRED")
        if family == "device_streams" and content_kind != "raw_evidence":
            errors.append(path + ":DEVICE_STREAM_MUST_BE_RAW_EVIDENCE")
        if isinstance(location_type, str) and location_type in {"local_file", "restricted_ref"}:
            if not isinstance(strategy, str) or strategy not in VALID_HASH_STRATEGIES:
                errors.append(path + ":HASH_STRATEGY_INVALID")
            if not isinstance(digest, str) or re.fullmatch(r"[A-Fa-f0-9]{64}", digest) is None:
                errors.append(path + ":CONTENT_HASH_REQUIRED")
        if (
            location_type == "local_file"
            and isinstance(digest, str)
            and isinstance(strategy, str)
            and strategy in VALID_HASH_STRATEGIES
        ):
            if base_dir is None:
                errors.append(path + ":BASE_DIR_REQUIRED_FOR_LOCAL_FILE")
            else:
                candidate = (base_dir / str(artifact.get("location", ""))).resolve()
                if base_dir.resolve() not in candidate.parents or not candidate.is_file():
                    errors.append(path + ":LOCAL_FILE_MISSING")
                else:
                    try:
                        observed = hashlib.sha256(_content_for_hash(candidate, strategy)).hexdigest()
                    except UnicodeDecodeError:
                        errors.append(path + ":NORMALIZED_TEXT_NOT_UTF8")
                    else:
                        if observed.lower() != digest.lower():
                            errors.append(path + ":CONTENT_HASH_MISMATCH")
        elif location_type == "explicit_none":
            if not isinstance(reason_code, str) or not reason_code.strip():
                errors.append(path + ":REASON_CODE_REQUIRED")
            if strategy is not None or digest is not None:
                errors.append(path + ":EXPLICIT_NONE_MUST_NOT_HAVE_HASH")
            errors.append(path + f":REQUIRED_ARTIFACT_MISSING:{family}")
        identities.append(
            {
                field: artifact.get(field)
                for field in (
                    "family", "artifact_id", "location_type", "location",
                    "content_kind", "hash_strategy", "content_sha256",
                    "observed_or_derived", "reason_code",
                )
            }
        )

    represented = {
        family
        for item in artifacts
        if isinstance(item, dict) and isinstance((family := item.get("family")), str)
    }
    if missing_artifacts := REQUIRED_FAMILIES - represented:
        errors.append("FAMILIES_WITHOUT_ARTIFACT:" + ",".join(sorted(missing_artifacts)))

    identity_payload = json.dumps(
        {
            "schema_version": bundle.get("schema_version"),
            "bundle_id": bundle.get("bundle_id"),
            "session_ref": bundle.get("session_ref"),
            "families": sorted(families),
            "artifacts": sorted(
                identities,
                key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
            ),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "ok": not errors,
        "errors": errors,
        "input_identity": hashlib.sha256(identity_payload).hexdigest().upper(),
        "authorization": False,
    }


def load_and_validate(path: Path) -> dict[str, Any]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return validate_bundle(bundle, path.parent)
