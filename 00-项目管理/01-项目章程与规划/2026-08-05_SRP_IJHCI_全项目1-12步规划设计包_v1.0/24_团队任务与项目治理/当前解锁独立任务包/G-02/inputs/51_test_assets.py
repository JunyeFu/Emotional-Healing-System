from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from srp_governance import GovernanceError
from srp_governance.assets import build_asset_inventory, scan_unity_assets


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _repository(tmp_path: Path, *, sprite_status: str = "CLEARED") -> tuple[Path, Path, Path, Path]:
    repo = tmp_path / "repo"
    unity = repo / "UnityProject"
    (unity / "Assets" / "Sprites").mkdir(parents=True)
    (unity / "Assets" / "Sprites" / "scene.png").write_bytes(b"synthetic-png")
    manifest = {
        "dependencies": {
            "com.unity.2d.sprite": "1.0.0",
            "example.git.package": "https://example.invalid/package.git#0123456789abcdef0123456789abcdef01234567",
        }
    }
    packages_lock = {
        "dependencies": {
            "com.unity.2d.sprite": {
                "version": "1.0.0", "depth": 0, "source": "builtin", "dependencies": {}
            },
            "example.git.package": {
                "version": "https://example.invalid/package.git#0123456789abcdef0123456789abcdef01234567",
                "depth": 0,
                "source": "git",
                "dependencies": {},
                "hash": "0123456789abcdef0123456789abcdef01234567",
            },
        }
    }
    _write_json(unity / "Packages" / "manifest.json", manifest)
    _write_json(unity / "Packages" / "packages-lock.json", packages_lock)
    evidence = unity / "Governance" / "licenses" / "evidence.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("Synthetic fixture evidence.\n", encoding="utf-8")
    ledger = unity / "Governance" / "asset_license_ledger.json"
    _write_json(
        ledger,
        {
            "schema_version": 1,
            "groups": {
                "sprites": {
                    "author": "fixture",
                    "source_url": "https://example.invalid/sprites",
                    "obtained_on": "2026-08-12",
                    "license_name": "Fixture",
                    "license_evidence_path": "UnityProject/Governance/licenses/evidence.md",
                    "allowed_use": "test",
                    "attribution_required": False,
                    "responsible_role": "fixture-owner",
                    "status": sprite_status,
                    "replacement_deadline": "2026-08-19" if sprite_status == "REPLACE" else None,
                    "exclusion_plan": "Remove from candidate build." if sprite_status == "REPLACE" else None,
                },
                "unity-packages": {
                    "author": "Unity Technologies",
                    "source_url": "https://packages.unity.com",
                    "obtained_on": "2026-08-12",
                    "license_name": "Unity Companion License",
                    "license_evidence_path": "UnityProject/Governance/licenses/evidence.md",
                    "allowed_use": "Unity project",
                    "attribution_required": True,
                    "responsible_role": "fixture-owner",
                    "status": "CLEARED",
                },
                "example-package": {
                    "author": "fixture",
                    "source_url": "https://example.invalid/package",
                    "obtained_on": "2026-08-12",
                    "license_name": "Fixture",
                    "license_evidence_path": "UnityProject/Governance/licenses/evidence.md",
                    "allowed_use": "test",
                    "attribution_required": False,
                    "responsible_role": "fixture-owner",
                    "status": "CLEARED",
                },
            },
            "rules": [
                {"kind": "extension", "value": ".png", "license_group_id": "sprites"},
                {"kind": "package_prefix", "value": "com.unity.", "license_group_id": "unity-packages"},
                {"kind": "package_exact", "value": "example.git.package", "license_group_id": "example-package"},
            ],
        },
    )
    _git(repo, "init")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "add", ".")
    baseline = unity / "Governance" / "asset_inventory.json"
    inventory = build_asset_inventory(repo, unity, ledger)
    _write_json(baseline, inventory)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    return repo, unity, ledger, baseline


def test_cleared_tracked_assets_and_direct_packages_pass(tmp_path) -> None:
    repo, unity, ledger, baseline = _repository(tmp_path)

    report = scan_unity_assets(repo, unity, ledger, baseline)

    assert report.release_allowed is True
    assert report.blockers == ()
    assert {item["asset_type"] for item in report.inventory["items"]} == {
        "IMAGE", "UNITY_PACKAGE"
    }
    assert {item["package_id"] for item in report.inventory["items"] if "package_id" in item} == {
        "com.unity.2d.sprite", "example.git.package"
    }
    assert report.inventory["license_ledger_sha256"]


def test_untracked_asset_and_registered_hash_change_block_release(tmp_path) -> None:
    repo, unity, ledger, baseline = _repository(tmp_path)
    (unity / "Assets" / "Sprites" / "untracked.png").write_bytes(b"untracked")

    untracked = scan_unity_assets(repo, unity, ledger, baseline)
    assert untracked.release_allowed is False
    assert "UNTRACKED_FILE" in {item.code for item in untracked.blockers}

    (unity / "Assets" / "Sprites" / "untracked.png").unlink()
    (unity / "Assets" / "Sprites" / "scene.png").write_bytes(b"changed")
    changed = scan_unity_assets(repo, unity, ledger, baseline)
    assert changed.release_allowed is False
    assert "HASH_CHANGED" in {item.code for item in changed.blockers}


def test_ignored_asset_blocks_release(tmp_path) -> None:
    repo, unity, ledger, baseline = _repository(tmp_path)
    (repo / ".gitignore").write_text("UnityProject/Assets/ignored.png\n", encoding="utf-8")
    (unity / "Assets" / "ignored.png").write_bytes(b"ignored")

    report = scan_unity_assets(repo, unity, ledger, baseline)

    assert report.release_allowed is False
    assert "IGNORED_RELEASE_FILE" in {item.code for item in report.blockers}


def test_tracked_embedded_package_content_is_in_inventory(tmp_path) -> None:
    repo, unity, ledger, _baseline = _repository(tmp_path)
    embedded = unity / "Packages" / "com.local.embedded" / "Runtime.dll"
    embedded.parent.mkdir(parents=True)
    embedded.write_bytes(b"embedded")
    _git(repo, "add", ".")

    inventory = build_asset_inventory(repo, unity, ledger)
    item = next(
        item for item in inventory["items"] if item["git_path"].endswith("Runtime.dll")
    )
    assert item["asset_type"] == "MANAGED_OR_NATIVE_PLUGIN"
    assert item["license_group_id"] == "UNREGISTERED"


def test_file_package_outside_unity_authority_is_rejected(tmp_path) -> None:
    repo, unity, ledger, _baseline = _repository(tmp_path)
    local_package = repo / "LocalPackages" / "com.local.mutable"
    local_package.mkdir(parents=True)
    (local_package / "Runtime.dll").write_bytes(b"mutable")
    manifest_path = unity / "Packages" / "manifest.json"
    lock_path = unity / "Packages" / "packages-lock.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    specification = "file:../../LocalPackages/com.local.mutable"
    manifest["dependencies"]["com.local.mutable"] = specification
    lock["dependencies"]["com.local.mutable"] = {
        "version": specification,
        "depth": 0,
        "source": "local",
        "dependencies": {},
    }
    _write_json(manifest_path, manifest)
    _write_json(lock_path, lock)

    with pytest.raises(GovernanceError, match="DIRECT_PACKAGE_OUTSIDE_AUTHORITY"):
        build_asset_inventory(repo, unity, ledger)


def test_file_package_outside_enumerated_packages_directory_is_rejected(tmp_path) -> None:
    repo, unity, ledger, _baseline = _repository(tmp_path)
    local_package = unity / "LocalPackages" / "com.local.mutable"
    local_package.mkdir(parents=True)
    (local_package / "Runtime.dll").write_bytes(b"mutable")
    manifest_path = unity / "Packages" / "manifest.json"
    lock_path = unity / "Packages" / "packages-lock.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    specification = "file:../LocalPackages/com.local.mutable"
    manifest["dependencies"]["com.local.mutable"] = specification
    lock["dependencies"]["com.local.mutable"] = {
        "version": specification,
        "depth": 0,
        "source": "local",
        "dependencies": {},
    }
    _write_json(manifest_path, manifest)
    _write_json(lock_path, lock)

    with pytest.raises(GovernanceError, match="DIRECT_PACKAGE_OUTSIDE_AUTHORITY"):
        build_asset_inventory(repo, unity, ledger)


def test_replace_status_with_complete_plan_remains_blocking(tmp_path) -> None:
    repo, unity, ledger, baseline = _repository(tmp_path, sprite_status="REPLACE")

    report = scan_unity_assets(repo, unity, ledger, baseline)

    blockers = [item for item in report.blockers if item.code == "LICENSE_REPLACE"]
    assert report.release_allowed is False
    assert len(blockers) == 1
    assert blockers[0].replacement_plan_valid is True


def test_missing_ledger_group_fails_closed(tmp_path) -> None:
    repo, unity, ledger, baseline = _repository(tmp_path)
    value = json.loads(ledger.read_text(encoding="utf-8"))
    del value["groups"]["example-package"]
    _write_json(ledger, value)

    report = scan_unity_assets(repo, unity, ledger, baseline)

    assert report.release_allowed is False
    assert {"LICENSE_LEDGER_CHANGED", "LICENSE_GROUP_MISSING"} <= {
        item.code for item in report.blockers
    }


def test_git_package_requires_exact_locked_commit(tmp_path) -> None:
    repo, unity, ledger, baseline = _repository(tmp_path)
    manifest_path = unity / "Packages" / "manifest.json"
    lock_path = unity / "Packages" / "packages-lock.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    mutable = "https://example.invalid/package.git#main"
    manifest["dependencies"]["example.git.package"] = mutable
    lock["dependencies"]["example.git.package"]["version"] = mutable
    _write_json(manifest_path, manifest)
    _write_json(lock_path, lock)

    with pytest.raises(GovernanceError) as error:
        build_asset_inventory(repo, unity, ledger)

    assert getattr(error.value, "code", None) == "DIRECT_PACKAGE_MUTABLE"
