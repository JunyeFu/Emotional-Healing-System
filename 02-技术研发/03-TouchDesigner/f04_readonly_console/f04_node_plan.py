"""Deterministic external plan and evidence files for the F-04 TD builder."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from f04_console import BANNER, PAGE_DEFINITIONS, load_and_validate_fixture


TD_BUILD = "2025.32820"
ROOT_PATH = "/project1/F04_ReadonlyConsole"


def _node(path: str, operator_type: str, role: str, permission: str = "read_only", **extra: Any) -> dict[str, Any]:
    return {
        "path": path,
        "operator_type": operator_type,
        "role": role,
        "permission": permission,
        **extra,
    }


def build_node_plan() -> dict[str, Any]:
    nodes = [
        _node(ROOT_PATH, "containerCOMP", "f04_root"),
        _node(f"{ROOT_PATH}/fixture_json", "textDAT", "embedded_fixture"),
        _node(f"{ROOT_PATH}/page_manifest", "tableDAT", "page_manifest"),
        _node(f"{ROOT_PATH}/node_permissions", "tableDAT", "permission_manifest"),
        _node(f"{ROOT_PATH}/node_errors", "tableDAT", "error_report"),
        _node(
            f"{ROOT_PATH}/udp_5005_placeholder",
            "udpinDAT",
            "udp_placeholder",
            permission="disabled_input_placeholder",
            port=5005,
            active=False,
            label="T-01 NOT ACTIVE",
        ),
        _node(f"{ROOT_PATH}/pages", "containerCOMP", "page_container"),
    ]
    for page in PAGE_DEFINITIONS:
        page_path = f"{ROOT_PATH}/pages/{page['id']}"
        nodes.append(_node(page_path, "containerCOMP", "page", page_id=page["id"]))
        nodes.append(
            _node(
                f"{page_path}/view",
                "textTOP",
                "page_view",
                page_id=page["id"],
                banner=BANNER,
                field_paths=list(page["field_paths"]),
            )
        )
    nodes.extend(
        [
            _node(f"{ROOT_PATH}/page_selector", "switchTOP", "display_selector"),
            _node(f"{ROOT_PATH}/display_out", "outTOP", "local_display_output"),
        ]
    )
    return {
        "plan_schema_version": "f04-node-plan-v1",
        "touchdesigner_required_build": TD_BUILD,
        "replace_scope": ROOT_PATH,
        "replacement_policy": "replace_exact_root_only",
        "nodes": nodes,
    }


def _canonical_json(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, data: Any) -> str:
    content = _canonical_json(data)
    path.write_bytes(content)
    return sha256(content).hexdigest().upper()


def write_host_artifacts(output_dir: str | Path, fixture_path: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    fixture = load_and_validate_fixture(fixture_path)
    plan = build_node_plan()
    pages = {
        "page_manifest_schema_version": "f04-page-manifest-v1",
        "banner": BANNER,
        "pages": list(PAGE_DEFINITIONS),
    }
    permissions = {
        "permission_manifest_schema_version": "f04-node-permissions-v1",
        "fixture_permissions": fixture["permissions"],
        "nodes": [
            {key: node[key] for key in node if key in {"path", "operator_type", "role", "permission", "active", "port", "label"}}
            for node in plan["nodes"]
        ],
    }
    artifact_hashes = {
        "page_manifest.json": _write_json(output / "page_manifest.json", pages),
        "node_plan.json": _write_json(output / "node_plan.json", plan),
        "node_permissions.json": _write_json(output / "node_permissions.json", permissions),
    }
    fixture_bytes = Path(fixture_path).read_bytes()
    manifest = {
        "manifest_schema_version": "f04-host-build-manifest-v1",
        "touchdesigner_required_build": TD_BUILD,
        "fixture_schema_version": fixture["fixture_schema_version"],
        "fixture_sha256": sha256(fixture_bytes).hexdigest().upper(),
        "page_count": len(PAGE_DEFINITIONS),
        "scenario_count": len(fixture["scenarios"]),
        "artifact_hashes": artifact_hashes,
        "evidence_boundary": "STATIC_HOST_ONLY_NOT_TOUCHDESIGNER_RUNTIME_NOT_LIVE",
    }
    _write_json(output / "host_build_manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    written = write_host_artifacts(
        base / "evidence" / "host",
        base / "fixtures" / "f04-static-display-fixture-v1.json",
    )
    print(json.dumps(written, ensure_ascii=False, indent=2))
