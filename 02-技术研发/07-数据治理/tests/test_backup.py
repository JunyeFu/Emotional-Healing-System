from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from srp_governance import GovernanceError
from srp_governance.backup import backup_registry, restore_registry
from srp_governance.registry import DedupRegistry, Stage


PHONE = "+8613800138000"


@pytest.fixture
def registry(tmp_path):
    result = DedupRegistry(
        database_path=tmp_path / "governance" / "dedup" / "dedup_registry.sqlite",
        key_provider=lambda: b"K" * 32,
        allowed_actors={"data-admin"},
    )
    decision = result.check_and_reserve(PHONE, Stage.LEVEL_B, "data-admin")
    result.mark_exposed(decision.reservation_id, "data-admin")
    return result


def test_online_backup_and_empty_directory_restore_preserve_decision(registry, tmp_path) -> None:
    bundle = tmp_path / "backup-bundle"
    backup = backup_registry(registry, bundle, "data-admin")

    assert backup.database_path.exists()
    manifest_text = backup.manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    assert PHONE not in manifest_text
    assert "13800138000" not in manifest_text
    assert (b"K" * 32).hex() not in manifest_text
    assert len(manifest["manifest_hmac_sha256"]) == 64

    target = tmp_path / "restored-root"
    report = restore_registry(
        bundle,
        target,
        key_provider=lambda: b"K" * 32,
        allowed_actors={"data-admin"},
        actor_id="data-admin",
    )

    assert report.valid is True
    restored = DedupRegistry(
        database_path=report.database_path,
        key_provider=lambda: b"K" * 32,
        allowed_actors={"data-admin"},
    )
    decision = restored.check_and_reserve(PHONE, Stage.STAGE_3, "data-admin")
    assert decision.allowed is False
    assert decision.reason_code == "PRIOR_EXPOSURE"
    assert restored.verify_audit_chain().valid is True


def test_tampered_backup_hash_is_rejected_before_target_creation(registry, tmp_path) -> None:
    bundle = tmp_path / "backup-bundle"
    backup = backup_registry(registry, bundle, "data-admin")
    with backup.database_path.open("ab") as handle:
        handle.write(b"tampered")

    target = tmp_path / "restore-target"
    with pytest.raises(GovernanceError) as error:
        restore_registry(
            bundle,
            target,
            key_provider=lambda: b"K" * 32,
            allowed_actors={"data-admin"},
            actor_id="data-admin",
        )

    assert error.value.code == "BACKUP_HASH_MISMATCH"
    assert not target.exists()


def test_rehashed_audit_tamper_is_still_rejected(registry, tmp_path) -> None:
    bundle = tmp_path / "backup-bundle"
    backup = backup_registry(registry, bundle, "data-admin")
    with sqlite3.connect(backup.database_path) as connection:
        connection.execute("UPDATE audit_events SET result = 'tampered' WHERE sequence = 1")
        connection.commit()
    manifest = json.loads(backup.manifest_path.read_text(encoding="utf-8"))
    manifest["database_sha256"] = hashlib.sha256(backup.database_path.read_bytes()).hexdigest()
    backup.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(GovernanceError) as error:
        restore_registry(
            bundle,
            tmp_path / "restore-target",
            key_provider=lambda: b"K" * 32,
            allowed_actors={"data-admin"},
            actor_id="data-admin",
        )

    assert error.value.code == "BACKUP_MANIFEST_AUTH_FAILED"


def test_manifest_metadata_tamper_is_rejected_by_hmac(registry, tmp_path) -> None:
    bundle = tmp_path / "backup-bundle"
    backup = backup_registry(registry, bundle, "data-admin")
    manifest = json.loads(backup.manifest_path.read_text(encoding="utf-8"))
    manifest["created_at_utc"] = "2099-01-01T00:00:00Z"
    backup.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(GovernanceError) as error:
        restore_registry(
            bundle,
            tmp_path / "restore-target",
            key_provider=lambda: b"K" * 32,
            allowed_actors={"data-admin"},
            actor_id="data-admin",
        )

    assert error.value.code == "BACKUP_MANIFEST_AUTH_FAILED"


def test_restore_requires_key_authorization_and_empty_target(registry, tmp_path) -> None:
    bundle = tmp_path / "backup-bundle"
    backup_registry(registry, bundle, "data-admin")

    with pytest.raises(GovernanceError) as unauthorized:
        restore_registry(
            bundle,
            tmp_path / "unauthorized",
            key_provider=lambda: b"K" * 32,
            allowed_actors={"data-admin"},
            actor_id="observer",
        )
    assert unauthorized.value.code == "UNAUTHORIZED"

    with pytest.raises(GovernanceError) as missing_key:
        restore_registry(
            bundle,
            tmp_path / "missing-key",
            key_provider=lambda: (_ for _ in ()).throw(GovernanceError("KEY_UNAVAILABLE")),
            allowed_actors={"data-admin"},
            actor_id="data-admin",
        )
    assert missing_key.value.code == "KEY_UNAVAILABLE"

    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "keep.txt").write_text("keep", encoding="ascii")
    with pytest.raises(GovernanceError) as target_error:
        restore_registry(
            bundle,
            nonempty,
            key_provider=lambda: b"K" * 32,
            allowed_actors={"data-admin"},
            actor_id="data-admin",
        )
    assert target_error.value.code == "RESTORE_TARGET_NOT_EMPTY"
    assert (nonempty / "keep.txt").read_text(encoding="ascii") == "keep"


def test_existing_backup_target_does_not_record_success(registry, tmp_path) -> None:
    target = tmp_path / "existing-backup"
    target.mkdir()
    before = registry.verify_audit_chain().checked_events

    with pytest.raises(GovernanceError) as error:
        backup_registry(registry, target, "data-admin")

    assert error.value.code == "BACKUP_TARGET_EXISTS"
    assert registry.verify_audit_chain().checked_events == before


def test_copy_failure_records_failure_but_not_success(
    registry, tmp_path, monkeypatch
) -> None:
    import srp_governance.backup as backup_module

    def fail_copy(_source, _destination):
        raise GovernanceError("BACKUP_UNAVAILABLE")

    monkeypatch.setattr(backup_module, "_online_copy", fail_copy)
    bundle = tmp_path / "failed-backup"

    with pytest.raises(GovernanceError, match="BACKUP_UNAVAILABLE"):
        backup_registry(registry, bundle, "data-admin")

    assert not bundle.exists()
    with sqlite3.connect(registry.database_path) as connection:
        events = connection.execute(
            "SELECT event_type, result FROM audit_events ORDER BY sequence"
        ).fetchall()
    assert ("BACKUP_FAILED", "FAILED") in events
    assert ("BACKUP_CREATED", "APPLIED") not in events


def test_unauthorized_backup_is_rejected_before_copy_or_publication(
    registry, tmp_path, monkeypatch
) -> None:
    import srp_governance.backup as backup_module

    called = False

    def observe_copy(_source, _destination):
        nonlocal called
        called = True

    monkeypatch.setattr(backup_module, "_online_copy", observe_copy)
    bundle = tmp_path / "unauthorized-backup"

    with pytest.raises(GovernanceError, match="UNAUTHORIZED"):
        backup_registry(registry, bundle, "observer")

    assert called is False
    assert not bundle.exists()
