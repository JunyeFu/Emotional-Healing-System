from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from srp_session_store import SessionArchive


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "srp_session_store" / "contracts"


def _schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def test_generated_archive_files_match_p02_schemas(tmp_path, manifest_factory):
    manifest = manifest_factory()
    archive = SessionArchive.create(
        tmp_path,
        manifest,
        protocol_config_hash="sha256:protocol",
    )
    archive.append_l1("clock_sync", {"offset_ns": 1}, 1)
    archive.seal({"status": "COMPLETED"}, 2)
    archive.close()

    jsonschema.validate(
        json.loads((archive.path / "archive.json").read_text(encoding="utf-8")),
        _schema("archive-envelope-v1.schema.json"),
    )
    record = json.loads(
        (archive.path / "l1" / "segment-000001.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    jsonschema.validate(record, _schema("append-record-v1.schema.json"))
    jsonschema.validate(
        json.loads((archive.path / "seal.json").read_text(encoding="utf-8")),
        _schema("session-seal-v1.schema.json"),
    )
