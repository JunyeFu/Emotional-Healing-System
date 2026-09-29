from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import sys
import tempfile

from srp_governance.assets import build_asset_inventory, scan_unity_assets
from srp_governance.credentials import CredentialKeyProvider, WindowsCredentialBackend
from srp_governance.environment import EnvironmentInputs, check_environment
from srp_governance.rehearsal import run_synthetic_rehearsal
from srp_governance.windows_checks import encryption_enabled, minimum_acl


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    temporary.replace(path)


def _path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _credential_probe(required_account: str | None) -> bool:
    if not required_account:
        return False
    try:
        provider = CredentialKeyProvider(
            backend=WindowsCredentialBackend(),
            required_account=required_account,
        )
        return len(provider()) == 32
    except Exception:
        return False


def command_inventory(arguments: argparse.Namespace) -> int:
    inventory = build_asset_inventory(
        arguments.repo_root, arguments.unity_root, arguments.ledger
    )
    _write_json(arguments.output, inventory)
    print(f"G02_ASSET_INVENTORY_WRITTEN items={len(inventory['items'])}")
    return 0


def command_scan(arguments: argparse.Namespace) -> int:
    report = scan_unity_assets(
        arguments.repo_root,
        arguments.unity_root,
        arguments.ledger,
        arguments.baseline,
    )
    _write_json(arguments.output, report.to_dict())
    print(
        "G02_ASSET_GATE_"
        f"{'PASS' if report.release_allowed else 'BLOCKED'} "
        f"items={len(report.inventory['items'])} blockers={len(report.blockers)}"
    )
    return 0 if report.release_allowed else 2


def command_environment(arguments: argparse.Namespace) -> int:
    required_account = os.environ.get("SRP_DATA_ADMIN_ACCOUNT")
    report = check_environment(
        EnvironmentInputs(
            repo_root=arguments.repo_root,
            governance_root=_path(os.environ.get("SRP_GOVERNANCE_ROOT")),
            backup_root=_path(os.environ.get("SRP_GOVERNANCE_BACKUP_ROOT")),
            sealed_key_evidence=_path(os.environ.get("SRP_SEALED_KEY_RECOVERY_EVIDENCE")),
            required_account=required_account,
            current_account=getpass.getuser(),
            credential_probe=lambda: _credential_probe(required_account),
            encryption_probe=encryption_enabled,
            acl_probe=minimum_acl,
            retention_status=os.environ.get(
                "SRP_RETENTION_APPROVAL", "PENDING_INSTITUTIONAL_APPROVAL"
            ),
        )
    )
    _write_json(arguments.output, report.to_dict())
    failures = sum(not item.passed for item in report.checks)
    print(
        "G02_FORMAL_ENV_"
        f"{'PASS' if report.formal_ready else 'BLOCKED'} failures={failures}"
    )
    return 0 if report.formal_ready else 2


def command_provision_credential(arguments: argparse.Namespace) -> int:
    required_account = os.environ.get("SRP_DATA_ADMIN_ACCOUNT")
    if arguments.confirm_target != "SRP/G02/dedup-hmac/v1" or not required_account:
        print("G02_CREDENTIAL_PROVISION_REFUSED", file=sys.stderr)
        return 3
    provider = CredentialKeyProvider(
        backend=WindowsCredentialBackend(),
        required_account=required_account,
    )
    target = provider.provision()
    print(f"G02_CREDENTIAL_PROVISIONED target={target}")
    return 0


def command_rehearsal(arguments: argparse.Namespace) -> int:
    report = run_synthetic_rehearsal()
    _write_json(arguments.output, report)
    passed = all(
        (
            report["active_cross_stage_passed"],
            report["prior_exposure_passed"],
            report["release_before_exposure_allows_reentry"],
            report["completed_blocks_reentry"],
            report["withdrawn_after_exposure_blocks_reentry"],
            report["concurrent_new_count"] == 1,
            report["concurrent_active_reservation_count"] == 1,
            report["backup_restore_valid"],
            report["audit_chain_valid"],
            report["cross_stage_audit_valid"],
        )
    )
    print(f"G02_SYNTHETIC_REHEARSAL_{'PASS' if passed else 'FAIL'}")
    return 0 if passed else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SRP G-02 governance gates")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("generate-asset-inventory")
    inventory.add_argument("--repo-root", type=Path, required=True)
    inventory.add_argument("--unity-root", type=Path, required=True)
    inventory.add_argument("--ledger", type=Path, required=True)
    inventory.add_argument("--output", type=Path, required=True)
    inventory.set_defaults(handler=command_inventory)

    scan = subparsers.add_parser("scan-assets")
    scan.add_argument("--repo-root", type=Path, required=True)
    scan.add_argument("--unity-root", type=Path, required=True)
    scan.add_argument("--ledger", type=Path, required=True)
    scan.add_argument("--baseline", type=Path, required=True)
    scan.add_argument("--output", type=Path, required=True)
    scan.set_defaults(handler=command_scan)

    environment = subparsers.add_parser("check-environment")
    environment.add_argument("--repo-root", type=Path, required=True)
    environment.add_argument("--output", type=Path, required=True)
    environment.set_defaults(handler=command_environment)

    provision = subparsers.add_parser("provision-credential")
    provision.add_argument("--confirm-target", required=True)
    provision.set_defaults(handler=command_provision_credential)

    rehearsal = subparsers.add_parser("synthetic-rehearsal")
    rehearsal.add_argument("--output", type=Path, required=True)
    rehearsal.set_defaults(handler=command_rehearsal)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        return arguments.handler(arguments)
    except Exception as error:
        code = getattr(error, "code", "G02_COMMAND_FAILED")
        print(code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
