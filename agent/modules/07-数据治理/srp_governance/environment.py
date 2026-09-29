from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class EnvironmentCheck:
    code: str
    passed: bool


@dataclass(frozen=True)
class EnvironmentReport:
    formal_ready: bool
    checks: tuple[EnvironmentCheck, ...]

    def to_dict(self) -> dict:
        return {
            "formal_ready": self.formal_ready,
            "checks": [asdict(item) for item in self.checks],
        }


@dataclass(frozen=True)
class EnvironmentInputs:
    repo_root: Path
    governance_root: Path | None
    backup_root: Path | None
    sealed_key_evidence: Path | None
    required_account: str | None
    current_account: str
    credential_probe: Callable[[], bool]
    encryption_probe: Callable[[Path], bool]
    acl_probe: Callable[[Path, str], bool]
    retention_status: str = "PENDING_INSTITUTIONAL_APPROVAL"


def _inside(candidate: Path, parent: Path) -> bool:
    try:
        candidate.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def check_environment(inputs: EnvironmentInputs) -> EnvironmentReport:
    checks: list[EnvironmentCheck] = []

    governance = inputs.governance_root
    if governance is None:
        checks.append(EnvironmentCheck("GOVERNANCE_ROOT_UNSET", False))
    else:
        checks.append(EnvironmentCheck("GOVERNANCE_ROOT_ABSOLUTE", governance.is_absolute()))
        checks.append(EnvironmentCheck("GOVERNANCE_ROOT_EXISTS", governance.is_dir()))
        checks.append(
            EnvironmentCheck(
                "GOVERNANCE_ROOT_INSIDE_REPOSITORY",
                not _inside(governance, inputs.repo_root),
            )
        )
        checks.append(
            EnvironmentCheck(
                "GOVERNANCE_ROOT_ENCRYPTION_UNCONFIRMED",
                inputs.encryption_probe(governance),
            )
        )

    backup = inputs.backup_root
    if backup is None:
        checks.append(EnvironmentCheck("BACKUP_ROOT_UNSET", False))
    else:
        checks.append(EnvironmentCheck("BACKUP_ROOT_ABSOLUTE", backup.is_absolute()))
        checks.append(EnvironmentCheck("BACKUP_ROOT_EXISTS", backup.is_dir()))
        checks.append(
            EnvironmentCheck(
                "BACKUP_ROOT_SEPARATE",
                governance is not None
                and backup.resolve() != governance.resolve()
                and not _inside(backup, governance)
                and not _inside(governance, backup),
            )
        )
        checks.append(
            EnvironmentCheck("BACKUP_ROOT_ENCRYPTION_UNCONFIRMED", inputs.encryption_probe(backup))
        )

    evidence = inputs.sealed_key_evidence
    if evidence is None:
        checks.append(EnvironmentCheck("SEALED_KEY_EVIDENCE_UNSET", False))
    else:
        checks.append(EnvironmentCheck("SEALED_KEY_EVIDENCE_EXISTS", evidence.is_file()))
        checks.append(
            EnvironmentCheck(
                "SEALED_KEY_EVIDENCE_OUTSIDE_REPOSITORY",
                not _inside(evidence, inputs.repo_root),
            )
        )

    required_account = inputs.required_account
    if not required_account:
        checks.append(EnvironmentCheck("DATA_ADMIN_ACCOUNT_UNSET", False))
    else:
        account_matches = inputs.current_account.casefold() == required_account.casefold()
        checks.append(EnvironmentCheck("DATA_ADMIN_ACCOUNT_MATCH", account_matches))
        if governance is not None:
            checks.append(
                EnvironmentCheck(
                    "GOVERNANCE_ROOT_MINIMUM_ACL",
                    inputs.acl_probe(governance, required_account),
                )
            )
        if backup is not None:
            checks.append(
                EnvironmentCheck(
                    "BACKUP_ROOT_MINIMUM_ACL",
                    inputs.acl_probe(backup, required_account),
                )
            )

    try:
        credential_available = bool(inputs.credential_probe()) if required_account else False
    except Exception:
        credential_available = False
    checks.append(EnvironmentCheck("DEDUP_CREDENTIAL_AVAILABLE", credential_available))
    checks.append(
        EnvironmentCheck(
            "RETENTION_APPROVAL_PENDING",
            isinstance(inputs.retention_status, str)
            and inputs.retention_status.startswith("APPROVED:")
            and len(inputs.retention_status) > len("APPROVED:"),
        )
    )

    return EnvironmentReport(all(item.passed for item in checks), tuple(checks))
