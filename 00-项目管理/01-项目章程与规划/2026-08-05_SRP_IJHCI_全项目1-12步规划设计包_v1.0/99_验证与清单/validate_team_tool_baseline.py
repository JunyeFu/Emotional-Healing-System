"""Validate the SRP team tool baseline and optionally inspect a local role."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import pathlib
import platform
import re
import subprocess
import sys


HERE = pathlib.Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
PROJECT_ROOT = PACKAGE_ROOT.parents[2]
GOVERNANCE_DIR = next(PACKAGE_ROOT.glob("24_*"))
BASELINE_PATH = GOVERNANCE_DIR / "team_tool_baseline_v1.0.json"
TECH_ROOT = next(PROJECT_ROOT.glob("02-*"))
PYTHON_BASELINE = TECH_ROOT / "requirements-baseline-py3.14.txt"
UNITY_ROOT = next(TECH_ROOT.glob("04-*")) / "SRP-Weather-Visual"
UNITY_VERSION_FILE = UNITY_ROOT / "ProjectSettings" / "ProjectVersion.txt"
UNITY_MANIFEST = UNITY_ROOT / "Packages" / "manifest.json"
UNITY_LOCK = UNITY_ROOT / "Packages" / "packages-lock.json"

EXPECTED_COMMON = {
    "powershell",
    "git",
    "git_lfs",
    "openssh",
    "python",
    "pip",
    "pytest",
    "vscode",
    "unity",
    "touchdesigner",
    "python_science_stack",
}
EXPECTED_ROLES = {
    "common",
    "design",
    "unity",
    "python_data",
    "experiment_td_governance",
}
EXPECTED_ROLE_ADDITIONS = {
    "common": set(),
    "design": {"zotero"},
    "unity": set(),
    "python_data": set(),
    "experiment_td_governance": {"zotero"},
}


def run(command: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        return 127, "MISSING"
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return result.returncode, output


def file_product_version(path: pathlib.Path) -> str | None:
    if not path.is_file():
        return None
    escaped = str(path).replace("'", "''")
    code, output = run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-Item -LiteralPath '{escaped}').VersionInfo.ProductVersion",
        ]
    )
    return output.splitlines()[0].strip() if code == 0 and output else None


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def parse_direct_requirements(path: pathlib.Path) -> dict[str, str]:
    requirements: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ValueError(f"requirement is not exact: {line}")
        name, version = line.split("==", 1)
        requirements[name.lower()] = version
    return requirements


def validate_authority(baseline: dict[str, object]) -> list[str]:
    errors: list[str] = []
    tools = baseline.get("tools", {})
    common = set(baseline.get("common_tool_ids", []))
    roles = baseline.get("role_profiles", {})

    if baseline.get("baseline_id") != "SRP-TEAM-TOOLS-v1.0":
        errors.append("unexpected baseline_id")
    if baseline.get("status") != "ACTIVE_FOR_TEAM_SETUP":
        errors.append("baseline must be ACTIVE_FOR_TEAM_SETUP")
    if baseline.get("workspace") != r"D:\Agent\03-SRP":
        errors.append("workspace must remain D:\\Agent\\03-SRP")
    if common != EXPECTED_COMMON:
        errors.append(f"common tool set mismatch: {sorted(common)}")
    if set(roles) != EXPECTED_ROLES:
        errors.append(f"role profile set mismatch: {sorted(roles)}")

    shared_library = baseline.get("common_access_requirements", {}).get(
        "zotero_shared_library", {}
    )
    if shared_library != {
        "minimum_access": "read",
        "local_install_required": False,
        "validation": "manual_open_project_collection_and_assigned_record",
    }:
        errors.append("Zotero shared-library access requirement mismatch")

    referenced_tools = set(common)
    for role, profile in roles.items():
        additions = profile.get("additional_tool_ids", [])
        if len(additions) != len(set(additions)):
            errors.append(f"{role}: duplicate additional tool")
        if set(additions) != EXPECTED_ROLE_ADDITIONS[role]:
            errors.append(f"{role}: unexpected additional tools {additions}")
        if not profile.get("primary_ownership"):
            errors.append(f"{role}: primary_ownership is required")
        referenced_tools.update(additions)
    missing_tools = referenced_tools - set(tools)
    if missing_tools:
        errors.append(f"undefined tool ids: {sorted(missing_tools)}")

    for tool_id, item in tools.items():
        if not isinstance(item, dict) or not item.get("version") or not item.get("policy"):
            errors.append(f"{tool_id}: version and policy are required")

    if not PYTHON_BASELINE.is_file():
        errors.append("Python direct dependency baseline is missing")
    else:
        requirements = parse_direct_requirements(PYTHON_BASELINE)
        expected = {key.lower(): value for key, value in baseline["python_direct_dependencies"].items()}
        if requirements != expected:
            errors.append("Python direct dependency file does not match machine authority")

    version_text = UNITY_VERSION_FILE.read_text(encoding="utf-8-sig")
    expected_unity = tools["unity"]
    if f"m_EditorVersion: {expected_unity['version']}" not in version_text:
        errors.append("Unity ProjectVersion does not match baseline")
    if expected_unity["revision"] not in version_text:
        errors.append("Unity revision does not match baseline")

    manifest = json.loads(UNITY_MANIFEST.read_text(encoding="utf-8-sig"))
    lock = json.loads(UNITY_LOCK.read_text(encoding="utf-8-sig"))
    dependencies = manifest["dependencies"]
    locked = lock["dependencies"]
    for package_id, expected_version in baseline["unity_packages"].items():
        if package_id == "com.coplaydev.unity-mcp":
            actual = locked.get(package_id, {}).get("hash")
        else:
            actual = dependencies.get(package_id)
        if actual != expected_version:
            errors.append(f"Unity package mismatch {package_id}: {actual!r}")

    mcp_source = dependencies.get("com.coplaydev.unity-mcp", "")
    if "#main" not in mcp_source:
        errors.append("known Unity MCP #main drift marker changed without baseline review")

    return errors


def add_check(
    observations: dict[str, str],
    errors: list[str],
    key: str,
    actual: str | None,
    expected: str,
) -> None:
    value = actual or "MISSING"
    observations[key] = value
    if value != expected:
        errors.append(f"{key}: expected {expected!r}, found {value!r}")


def first_match(output: str, pattern: str) -> str | None:
    match = re.search(pattern, output, flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1) if match else None


def validate_local(role: str, baseline: dict[str, object]) -> tuple[list[str], dict[str, str]]:
    errors: list[str] = []
    observations: dict[str, str] = {}
    tools = baseline["tools"]

    actual_os = platform.version()
    observations["windows"] = actual_os
    actual_build = tuple(int(part) for part in re.findall(r"\d+", actual_os)[:3])
    minimum_build = tuple(int(part) for part in baseline["platform"]["minimum_version"].split("."))
    if actual_build < minimum_build:
        errors.append(f"windows: expected >= {minimum_build}, found {actual_build}")

    command_checks = (
        ("powershell", ["pwsh", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"], r"(\d+\.\d+\.\d+)"),
        ("git", ["git", "--version"], r"git version ([^\s]+)"),
        ("git_lfs", ["git", "lfs", "version"], r"git-lfs/([^\s]+)"),
        ("openssh", ["ssh", "-V"], r"OpenSSH_for_Windows_([^,\s]+)"),
        ("python", ["py", "-3.14", "--version"], r"Python ([^\s]+)"),
        ("pip", ["py", "-3.14", "-m", "pip", "--version"], r"pip ([^\s]+)"),
        ("vscode", ["cmd.exe", "/d", "/c", "code", "--version"], r"^(\d+\.\d+\.\d+)"),
    )
    for key, command, pattern in command_checks:
        _, output = run(command)
        add_check(observations, errors, key, first_match(output, pattern), tools[key]["version"])

    add_check(observations, errors, "pytest", package_version("pytest"), tools["pytest"]["version"])

    if role in {"design", "experiment_td_governance"}:
        zotero_paths = (
            pathlib.Path(r"C:\Program Files\Zotero\zotero.exe"),
            pathlib.Path(r"C:\Program Files (x86)\Zotero\zotero.exe"),
        )
        zotero_path = next((path for path in zotero_paths if path.is_file()), None)
        add_check(
            observations,
            errors,
            "zotero",
            file_product_version(zotero_path) if zotero_path else None,
            tools["zotero"]["version"],
        )

    unity_path = pathlib.Path(tools["unity"]["path"])
    product = file_product_version(unity_path)
    normalized = first_match(product or "", r"(6000\.4\.9f1)")
    add_check(observations, errors, "unity", normalized, tools["unity"]["version"])

    td_path = pathlib.Path(tools["touchdesigner"]["path"])
    product = file_product_version(td_path)
    normalized = first_match(product or "", r"(?:0\.99\.)?(2025\.32820)")
    add_check(
        observations,
        errors,
        "touchdesigner",
        normalized,
        tools["touchdesigner"]["version"],
    )

    for name, expected in baseline["python_direct_dependencies"].items():
        add_check(observations, errors, f"python:{name}", package_version(name), expected)

    return errors, observations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-role", choices=sorted(EXPECTED_ROLES))
    args = parser.parse_args()

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8-sig"))
    errors = validate_authority(baseline)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("PASS: shared team tool baseline, role ownership, Python pins and Unity locks")
    if not args.local_role:
        return 0

    local_errors, observations = validate_local(args.local_role, baseline)
    for key in sorted(observations):
        print(f"LOCAL {key}={observations[key]}")
    if local_errors:
        for error in local_errors:
            print(f"LOCAL_GAP: {error}", file=sys.stderr)
        return 2

    print(f"PASS: local role baseline {args.local_role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
