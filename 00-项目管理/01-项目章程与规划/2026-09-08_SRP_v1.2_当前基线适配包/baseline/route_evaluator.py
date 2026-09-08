"""Evaluate A-06 route evidence. This never authorizes a research activity."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any


CONTRACT = Path(__file__).with_name("release_routes_v1.0.json")


def _stage3_activity_count(
    activity_evidence: dict[str, Any], sources: list[str], evidence_root: Path | None
) -> int:
    if evidence_root is None or not evidence_root.is_absolute() or not evidence_root.is_dir():
        raise ValueError("activity evidence root is unavailable")
    if set(activity_evidence) != set(sources):
        raise ValueError("activity evidence sources do not match contract")
    root = evidence_root.resolve()
    seen_paths: set[Path] = set()
    total = 0
    for source in sources:
        record = activity_evidence.get(source)
        if not isinstance(record, dict):
            raise ValueError(f"missing activity evidence for {source}")
        if set(record) != {"path", "byte_sha256", "record_count"}:
            raise ValueError(f"invalid activity evidence fields for {source}")
        relative = record.get("path")
        expected_hash = record.get("byte_sha256")
        expected_count = record.get("record_count")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ValueError(f"invalid activity path for {source}")
        if relative.replace("\\", "/") != f"{source}.jsonl":
            raise ValueError(f"activity path is not bound to source {source}")
        path = (root / relative).resolve()
        if path in seen_paths:
            raise ValueError("activity evidence files must be distinct")
        seen_paths.add(path)
        if root not in path.parents or not path.is_file():
            raise ValueError(f"activity evidence unavailable for {source}")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest().upper() != expected_hash:
            raise ValueError(f"activity evidence hash mismatch for {source}")
        lines = [line for line in content.splitlines() if line.strip()]
        if type(expected_count) is not int or expected_count < 0 or len(lines) != expected_count:
            raise ValueError(f"activity record count mismatch for {source}")
        try:
            for line in lines:
                json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"activity evidence is not JSONL for {source}") from exc
        total += expected_count
    return total


def evaluate_route(
    route: str,
    completed_tasks: set[str],
    activity_evidence: dict[str, int],
    receipt: dict[str, Any],
    result_families: set[str] | None = None,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    errors: list[str] = []
    route_spec = contract["routes"].get(route)
    if route_spec is None:
        return {"ok": False, "errors": ["UNKNOWN_ROUTE"], "authorization": False}

    required = set(route_spec["required_done"])
    if missing := required - completed_tasks:
        errors.append("MISSING_TASKS:" + ",".join(sorted(missing)))

    for field in (
        "record_id", "candidate_identity", "reviewer", "review_method",
        "signed_ref", "signed_ref_sha256",
    ):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            errors.append("MISSING_RECEIPT_FIELD:" + field)
    if receipt.get("status") != "PASS":
        errors.append("ROUTE_NOT_SIGNED_PASS")
    if receipt.get("scope") != route_spec["required_human_receipt_scope"]:
        errors.append("ROUTE_SCOPE_MISMATCH")

    try:
        activity_count = _stage3_activity_count(
            activity_evidence, contract["stage3_started_evidence_sources"], evidence_root
        )
    except ValueError:
        activity_count = -1
        errors.append("INVALID_STAGE3_ACTIVITY_EVIDENCE")

    if route_spec.get("must_have_no_stage3_activity") and activity_count != 0:
        errors.append("CANNOT_HIDE_STAGE3_ACTIVITY")
    if route_spec.get("must_have_stage3_activity") and activity_count <= 0:
        errors.append("STAGE3_ACTIVITY_NOT_EVIDENCED")

    required_results = set(route_spec.get("required_result_families", []))
    if missing_results := required_results - (result_families or set()):
        errors.append("MISSING_RESULT_FAMILIES:" + ",".join(sorted(missing_results)))

    return {
        "ok": not errors,
        "errors": errors,
        "stage3_activity_count": activity_count,
        "authorization": False,
        "scope": "A06_ROUTE_METADATA_ONLY",
    }
