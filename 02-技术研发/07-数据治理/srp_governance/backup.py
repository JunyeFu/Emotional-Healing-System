from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Callable

from .errors import GovernanceError
from .registry import DedupRegistry, SCHEMA_VERSION, Stage


BACKUP_DATABASE_NAME = "dedup_registry.sqlite"
BACKUP_MANIFEST_NAME = "backup_manifest.json"
_MANIFEST_DOMAIN = b"srp:g02:backup-manifest:v1\0"


@dataclass(frozen=True)
class BackupResult:
    database_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class RestoreReport:
    valid: bool
    reason_code: str
    database_path: Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_key(key_provider: Callable[[], bytes]) -> bytes:
    try:
        key = key_provider()
    except GovernanceError:
        raise
    except Exception as exc:
        raise GovernanceError("KEY_UNAVAILABLE") from exc
    if not isinstance(key, bytes) or len(key) != 32:
        raise GovernanceError("KEY_UNAVAILABLE")
    return key


def _manifest_hmac(manifest: dict, key: bytes) -> str:
    encoded = json.dumps(
        manifest,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(key, _MANIFEST_DOMAIN + encoded, hashlib.sha256).hexdigest()


def _online_copy(source_path: Path, destination_path: Path) -> None:
    try:
        with closing(sqlite3.connect(source_path)) as source, closing(
            sqlite3.connect(destination_path)
        ) as destination:
            source.backup(destination)
            destination.execute("PRAGMA journal_mode = DELETE")
            destination.commit()
    except sqlite3.Error as exc:
        raise GovernanceError("BACKUP_UNAVAILABLE") from exc


def backup_registry(
    registry: DedupRegistry,
    bundle_directory: Path,
    actor_id: str,
) -> BackupResult:
    bundle_directory = Path(bundle_directory)
    if bundle_directory.exists():
        raise GovernanceError("BACKUP_TARGET_EXISTS")
    key = _validate_key(registry.key_provider)
    registry.record_operation(
        event_type="BACKUP_CREATED",
        actor_id=actor_id,
        object_type="REGISTRY",
        object_id="DEDUP_REGISTRY",
        result="APPLIED",
        reason_code="ONLINE_BACKUP",
    )
    bundle_directory.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=".g02-backup-", dir=bundle_directory.parent
    ) as temporary:
        temporary_path = Path(temporary)
        database_path = temporary_path / BACKUP_DATABASE_NAME
        _online_copy(registry.database_path, database_path)
        backup_snapshot = DedupRegistry(
            database_path=database_path,
            key_provider=lambda: key,
            allowed_actors={actor_id},
        )
        manifest = {
            "audit_tail_hash": backup_snapshot.audit_tail_hash(),
            "created_at_utc": datetime.now(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
            "database_file": BACKUP_DATABASE_NAME,
            "database_sha256": _sha256_file(database_path),
            "database_size_bytes": database_path.stat().st_size,
            "schema_version": SCHEMA_VERSION,
        }
        manifest["manifest_hmac_sha256"] = _manifest_hmac(manifest, key)
        (temporary_path / BACKUP_MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary_path, bundle_directory)

    return BackupResult(
        bundle_directory / BACKUP_DATABASE_NAME,
        bundle_directory / BACKUP_MANIFEST_NAME,
    )


def _load_and_validate_bundle(bundle_directory: Path, key: bytes) -> tuple[Path, dict]:
    expected_files = {BACKUP_DATABASE_NAME, BACKUP_MANIFEST_NAME}
    try:
        actual_files = {item.name for item in bundle_directory.iterdir() if item.is_file()}
    except OSError as exc:
        raise GovernanceError("BACKUP_MANIFEST_INVALID") from exc
    if actual_files != expected_files:
        raise GovernanceError("BACKUP_BUNDLE_UNEXPECTED_FILE")
    manifest_path = bundle_directory / BACKUP_MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError("BACKUP_MANIFEST_INVALID") from exc
    required = {
        "audit_tail_hash",
        "created_at_utc",
        "database_file",
        "database_sha256",
        "database_size_bytes",
        "manifest_hmac_sha256",
        "schema_version",
    }
    if set(manifest) != required or manifest["database_file"] != BACKUP_DATABASE_NAME:
        raise GovernanceError("BACKUP_MANIFEST_INVALID")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise GovernanceError("SCHEMA_VERSION_UNSUPPORTED")
    authentication = manifest.get("manifest_hmac_sha256")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_hmac_sha256"}
    if not isinstance(authentication, str) or not hmac.compare_digest(
        authentication, _manifest_hmac(unsigned, key)
    ):
        raise GovernanceError("BACKUP_MANIFEST_AUTH_FAILED")
    database_path = bundle_directory / BACKUP_DATABASE_NAME
    if not database_path.is_file():
        raise GovernanceError("BACKUP_MANIFEST_INVALID")
    if (
        database_path.stat().st_size != manifest["database_size_bytes"]
        or _sha256_file(database_path) != manifest["database_sha256"]
    ):
        raise GovernanceError("BACKUP_HASH_MISMATCH")
    return database_path, manifest


def restore_registry(
    bundle_directory: Path,
    target_root: Path,
    *,
    key_provider: Callable[[], bytes],
    allowed_actors: set[str] | frozenset[str],
    actor_id: str,
) -> RestoreReport:
    if actor_id not in allowed_actors:
        raise GovernanceError("UNAUTHORIZED")
    target_root = Path(target_root)
    if target_root.exists() and any(target_root.iterdir()):
        raise GovernanceError("RESTORE_TARGET_NOT_EMPTY")
    key = _validate_key(key_provider)
    source_path, manifest = _load_and_validate_bundle(Path(bundle_directory), key)

    source_registry = DedupRegistry(
        database_path=source_path,
        key_provider=lambda: key,
        allowed_actors=allowed_actors,
    )
    audit = source_registry.verify_audit_chain()
    if not audit.valid or source_registry.audit_tail_hash() != manifest["audit_tail_hash"]:
        raise GovernanceError("AUDIT_CHAIN_INVALID")

    destination_path = target_root / "dedup" / BACKUP_DATABASE_NAME
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _online_copy(source_path, destination_path)
        restored = DedupRegistry(
            database_path=destination_path,
            key_provider=lambda: key,
            allowed_actors=allowed_actors,
        )
        if not restored.verify_audit_chain().valid:
            raise GovernanceError("AUDIT_CHAIN_INVALID")

        with tempfile.TemporaryDirectory(prefix="g02-restore-probe-") as temporary:
            probe_path = Path(temporary) / "probe.sqlite"
            _online_copy(destination_path, probe_path)
            probe = DedupRegistry(
                database_path=probe_path,
                key_provider=lambda: key,
                allowed_actors=allowed_actors,
            )
            decision = probe.check_and_reserve(
                "+8619900000000", Stage.LEVEL_B, actor_id
            )
            if not decision.allowed or not probe.verify_audit_chain().valid:
                raise GovernanceError("RESTORE_PROBE_FAILED")

        restored.record_operation(
            event_type="RESTORE_COMPLETED",
            actor_id=actor_id,
            object_type="REGISTRY",
            object_id="DEDUP_REGISTRY",
            result="APPLIED",
            reason_code="RESTORE_VERIFIED",
        )
    except Exception:
        if destination_path.exists():
            destination_path.unlink()
        dedup_directory = destination_path.parent
        if dedup_directory.exists() and not any(dedup_directory.iterdir()):
            dedup_directory.rmdir()
        if target_root.exists() and not any(target_root.iterdir()):
            target_root.rmdir()
        raise

    return RestoreReport(True, "OK", destination_path)
