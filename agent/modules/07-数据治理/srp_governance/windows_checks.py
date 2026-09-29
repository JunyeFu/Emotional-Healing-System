from __future__ import annotations

import json
from pathlib import Path
import subprocess


def _powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )


def encryption_enabled(path: Path) -> bool:
    drive = path.resolve().drive
    if not drive:
        return False
    safe_drive = drive.replace("'", "''")
    result = _powershell(
        f"$v = Get-BitLockerVolume -MountPoint '{safe_drive}' -ErrorAction Stop; "
        "$v.ProtectionStatus.ToString()"
    )
    return result.returncode == 0 and result.stdout.strip().casefold() in {
        "on",
        "1",
    }


def minimum_acl(path: Path, required_account: str) -> bool:
    safe_path = str(path.resolve()).replace("'", "''")
    result = _powershell(
        f"$a = Get-Acl -LiteralPath '{safe_path}' -ErrorAction Stop; "
        "$a.Access | ForEach-Object { [pscustomobject]@{ "
        "identity=$_.IdentityReference.Value; "
        "rights=$_.FileSystemRights.ToString(); "
        "type=$_.AccessControlType.ToString(); "
        "inherited=[bool]$_.IsInherited } } | ConvertTo-Json -Compress"
    )
    if result.returncode != 0 or not result.stdout.strip():
        return False
    try:
        entries = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        return False

    required = required_account.casefold()
    required_short = required.split("\\")[-1]
    allowed_accounts = {
        required,
        "nt authority\\system",
        "builtin\\administrators",
        "nt service\\trustedinstaller",
    }
    required_seen = False
    for entry in entries:
        if not isinstance(entry, dict) or str(entry.get("type", "")).casefold() != "allow":
            continue
        identity = str(entry.get("identity", "")).casefold()
        identity_short = identity.split("\\")[-1]
        is_required = identity == required or (
            "\\" not in required and identity_short == required_short
        )
        if is_required:
            rights = str(entry.get("rights", "")).casefold()
            if not any(value in rights for value in ("modify", "fullcontrol", "write")):
                return False
            required_seen = True
        elif identity not in allowed_accounts:
            return False
    return required_seen
