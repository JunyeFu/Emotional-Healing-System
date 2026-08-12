from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from .errors import GovernanceError


_ASSET_TYPES = {
    ".png": "IMAGE",
    ".jpg": "IMAGE",
    ".jpeg": "IMAGE",
    ".gif": "IMAGE",
    ".webp": "IMAGE",
    ".psd": "IMAGE_SOURCE",
    ".wav": "AUDIO",
    ".mp3": "AUDIO",
    ".ogg": "AUDIO",
    ".flac": "AUDIO",
    ".ttf": "FONT",
    ".otf": "FONT",
    ".woff": "FONT",
    ".woff2": "FONT",
    ".mp4": "VIDEO",
    ".mov": "VIDEO",
    ".webm": "VIDEO",
    ".avi": "VIDEO",
    ".dll": "MANAGED_OR_NATIVE_PLUGIN",
    ".so": "NATIVE_PLUGIN",
    ".dylib": "NATIVE_PLUGIN",
    ".bundle": "NATIVE_PLUGIN",
    ".aar": "NATIVE_PLUGIN",
    ".jar": "PLUGIN_ARCHIVE",
}
_ALLOWED_STATUSES = {"PROJECT_ORIGINAL", "CLEARED"}
_ALL_STATUSES = _ALLOWED_STATUSES | {"REPLACE", "UNKNOWN", "BLOCKED"}
_GIT_COMMIT_SPEC = re.compile(r"#([0-9a-fA-F]{40})$")


@dataclass(frozen=True)
class AssetBlocker:
    code: str
    subject: str
    replacement_plan_valid: bool = False


@dataclass(frozen=True)
class AssetScanReport:
    release_allowed: bool
    inventory: dict
    blockers: tuple[AssetBlocker, ...]

    def to_dict(self) -> dict:
        return {
            "release_allowed": self.release_allowed,
            "inventory": self.inventory,
            "blockers": [asdict(item) for item in self.blockers],
        }


def _git_paths(repo_root: Path, *arguments: str) -> list[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise GovernanceError("GIT_INVENTORY_UNAVAILABLE")
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, error_code: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError(error_code) from exc
    if not isinstance(value, dict):
        raise GovernanceError(error_code)
    return value


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise GovernanceError("UNITY_ROOT_OUTSIDE_REPOSITORY") from exc


def _license_group(ledger: dict, *, path: str | None = None, package_id: str | None = None) -> str:
    rules = ledger.get("rules")
    if not isinstance(rules, list):
        raise GovernanceError("LICENSE_LEDGER_INVALID")
    for rule in rules:
        if not isinstance(rule, dict):
            raise GovernanceError("LICENSE_LEDGER_INVALID")
        kind = rule.get("kind")
        value = rule.get("value")
        group = rule.get("license_group_id")
        if not all(isinstance(item, str) and item for item in (kind, value, group)):
            raise GovernanceError("LICENSE_LEDGER_INVALID")
        if kind == "extension" and path and Path(path).suffix.lower() == value.lower():
            return group
        if kind == "path_prefix" and path and path.startswith(value):
            return group
        if kind == "package_exact" and package_id == value:
            return group
        if kind == "package_prefix" and package_id and package_id.startswith(value):
            return group
    return "UNREGISTERED"


def _tracked_release_files(repo_root: Path, unity_relative: str) -> list[str]:
    tracked = _git_paths(repo_root, "ls-files", "-z", "--", unity_relative)
    release_files: list[str] = []
    assets_prefix = f"{unity_relative}/Assets/"
    for path in tracked:
        if path.startswith(assets_prefix) and Path(path).suffix.lower() != ".meta":
            release_files.append(path)
    return sorted(release_files)


def _direct_packages(unity_root: Path) -> list[dict[str, Any]]:
    manifest = _load_json(unity_root / "Packages" / "manifest.json", "PACKAGE_MANIFEST_INVALID")
    lock = _load_json(unity_root / "Packages" / "packages-lock.json", "PACKAGE_LOCK_INVALID")
    dependencies = manifest.get("dependencies")
    locked_dependencies = lock.get("dependencies")
    if not isinstance(dependencies, dict) or not isinstance(locked_dependencies, dict):
        raise GovernanceError("PACKAGE_LOCK_INVALID")
    result: list[dict[str, Any]] = []
    for package_id, specification in sorted(dependencies.items()):
        locked = locked_dependencies.get(package_id)
        if (
            not isinstance(package_id, str)
            or not isinstance(specification, str)
            or not isinstance(locked, dict)
            or locked.get("depth") != 0
            or locked.get("version") != specification
        ):
            raise GovernanceError("DIRECT_PACKAGE_UNLOCKED")
        if locked.get("source") == "git":
            commit_match = _GIT_COMMIT_SPEC.search(specification)
            if commit_match is None or locked.get("hash", "").casefold() != commit_match.group(1).casefold():
                raise GovernanceError("DIRECT_PACKAGE_MUTABLE")
        identity = {
            "package_id": package_id,
            "specification": specification,
            "lock_hash": locked.get("hash"),
            "source": locked.get("source"),
        }
        digest = hashlib.sha256(
            json.dumps(identity, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        result.append({**identity, "sha256": digest})
    return result


def build_asset_inventory(repo_root: Path, unity_root: Path, ledger_path: Path) -> dict:
    repo_root = Path(repo_root)
    unity_root = Path(unity_root)
    ledger = _load_json(Path(ledger_path), "LICENSE_LEDGER_INVALID")
    unity_relative = _repo_relative(repo_root, unity_root)
    items: list[dict[str, Any]] = []
    for git_path in _tracked_release_files(repo_root, unity_relative):
        absolute = repo_root / Path(git_path)
        suffix = absolute.suffix.lower()
        items.append(
            {
                "asset_type": _ASSET_TYPES.get(suffix, "UNITY_ASSET"),
                "git_path": git_path,
                "license_group_id": _license_group(ledger, path=git_path),
                "sha256": _sha256_file(absolute),
            }
        )
    for package in _direct_packages(unity_root):
        package_id = package["package_id"]
        items.append(
            {
                "asset_type": "UNITY_PACKAGE",
                "git_path": f"package://{package_id}",
                "license_group_id": _license_group(ledger, package_id=package_id),
                **package,
            }
        )
    return {
        "schema_version": 1,
        "authority_root": unity_relative,
        "license_ledger_path": _repo_relative(repo_root, Path(ledger_path)),
        "license_ledger_sha256": _sha256_file(Path(ledger_path)),
        "items": sorted(items, key=lambda item: item["git_path"]),
    }


def _validate_group(
    repo_root: Path,
    tracked_paths: set[str],
    group_id: str,
    group: Any,
) -> list[AssetBlocker]:
    if not isinstance(group, dict):
        return [AssetBlocker("LICENSE_LEDGER_INVALID", group_id)]
    required = {
        "author",
        "source_url",
        "obtained_on",
        "license_name",
        "license_evidence_path",
        "allowed_use",
        "attribution_required",
        "responsible_role",
        "status",
    }
    if not required <= set(group) or group.get("status") not in _ALL_STATUSES:
        return [AssetBlocker("LICENSE_LEDGER_INVALID", group_id)]
    if any(not isinstance(group.get(field), str) or not group[field] for field in required - {"attribution_required"}):
        return [AssetBlocker("LICENSE_LEDGER_INVALID", group_id)]
    if not isinstance(group.get("attribution_required"), bool):
        return [AssetBlocker("LICENSE_LEDGER_INVALID", group_id)]
    evidence = group["license_evidence_path"]
    if evidence not in tracked_paths or not (repo_root / Path(evidence)).is_file():
        return [AssetBlocker("LICENSE_EVIDENCE_MISSING", group_id)]
    status = group["status"]
    if status in _ALLOWED_STATUSES:
        return []
    if status == "REPLACE":
        plan_valid = all(
            isinstance(group.get(field), str) and bool(group[field])
            for field in ("responsible_role", "replacement_deadline", "exclusion_plan")
        )
        return [AssetBlocker("LICENSE_REPLACE", group_id, plan_valid)]
    return [AssetBlocker(f"LICENSE_{status}", group_id)]


def scan_unity_assets(
    repo_root: Path,
    unity_root: Path,
    ledger_path: Path,
    baseline_path: Path,
) -> AssetScanReport:
    repo_root = Path(repo_root)
    unity_root = Path(unity_root)
    unity_relative = _repo_relative(repo_root, unity_root)
    current = build_asset_inventory(repo_root, unity_root, ledger_path)
    baseline = _load_json(Path(baseline_path), "ASSET_BASELINE_INVALID")
    ledger = _load_json(Path(ledger_path), "LICENSE_LEDGER_INVALID")
    blockers: list[AssetBlocker] = []

    if baseline.get("license_ledger_sha256") != current["license_ledger_sha256"]:
        blockers.append(AssetBlocker("LICENSE_LEDGER_CHANGED", current["license_ledger_path"]))

    untracked = _git_paths(
        repo_root,
        "ls-files",
        "-z",
        "--others",
        "--exclude-standard",
        "--",
        unity_relative,
    )
    blockers.extend(AssetBlocker("UNTRACKED_FILE", path) for path in sorted(untracked))

    baseline_items = {
        item["git_path"]: item
        for item in baseline.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("git_path"), str)
    }
    current_items = {item["git_path"]: item for item in current["items"]}
    for path, item in current_items.items():
        prior = baseline_items.get(path)
        if prior is None:
            blockers.append(AssetBlocker("ASSET_UNREGISTERED", path))
        elif prior.get("sha256") != item.get("sha256"):
            blockers.append(AssetBlocker("HASH_CHANGED", path))
        elif prior.get("license_group_id") != item.get("license_group_id"):
            blockers.append(AssetBlocker("LICENSE_GROUP_CHANGED", path))
    for path in sorted(set(baseline_items) - set(current_items)):
        blockers.append(AssetBlocker("ASSET_REMOVED", path))

    tracked_paths = set(_git_paths(repo_root, "ls-files", "-z"))
    groups = ledger.get("groups")
    if not isinstance(groups, dict):
        raise GovernanceError("LICENSE_LEDGER_INVALID")
    for group_id in sorted({item["license_group_id"] for item in current["items"]}):
        if group_id not in groups:
            blockers.append(AssetBlocker("LICENSE_GROUP_MISSING", group_id))
        else:
            blockers.extend(_validate_group(repo_root, tracked_paths, group_id, groups[group_id]))

    unique = {
        (item.code, item.subject, item.replacement_plan_valid): item for item in blockers
    }
    ordered = tuple(unique[key] for key in sorted(unique))
    return AssetScanReport(not ordered, current, ordered)
