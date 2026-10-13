from __future__ import annotations

import getpass
import os
from pathlib import Path

from .credentials import CredentialKeyProvider, WindowsCredentialBackend
from .environment import EnvironmentInputs, check_environment
from .errors import GovernanceError
from .identity import IdentityMappingStore
from .registry import DedupRegistry, configure_default_registry
from .windows_checks import encryption_enabled, minimum_acl


DATA_ADMIN_ACTOR_ID = "data-admin"


def _required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise GovernanceError("FORMAL_ENVIRONMENT_UNAVAILABLE")
    return Path(value)


def configure_formal_runtime(repo_root: Path) -> tuple[DedupRegistry, IdentityMappingStore]:
    governance_root = _required_path("SRP_GOVERNANCE_ROOT")
    backup_root = _required_path("SRP_GOVERNANCE_BACKUP_ROOT")
    sealed_evidence = _required_path("SRP_SEALED_KEY_RECOVERY_EVIDENCE")
    required_account = os.environ.get("SRP_DATA_ADMIN_ACCOUNT")
    if not required_account:
        raise GovernanceError("FORMAL_ENVIRONMENT_UNAVAILABLE")
    provider = CredentialKeyProvider(
        backend=WindowsCredentialBackend(),
        required_account=required_account,
    )
    report = check_environment(
        EnvironmentInputs(
            repo_root=Path(repo_root),
            governance_root=governance_root,
            backup_root=backup_root,
            sealed_key_evidence=sealed_evidence,
            required_account=required_account,
            current_account=getpass.getuser(),
            credential_probe=lambda: len(provider()) == 32,
            encryption_probe=encryption_enabled,
            acl_probe=minimum_acl,
            retention_status=os.environ.get(
                "SRP_RETENTION_APPROVAL", "PENDING_INSTITUTIONAL_APPROVAL"
            ),
        )
    )
    if not report.formal_ready:
        raise GovernanceError("FORMAL_ENVIRONMENT_UNAVAILABLE")

    actors = {DATA_ADMIN_ACTOR_ID}
    registry = DedupRegistry(
        database_path=governance_root / "dedup" / "dedup_registry.sqlite",
        key_provider=provider,
        allowed_actors=actors,
    )
    identity = IdentityMappingStore(
        database_path=governance_root / "identity" / "research_id_mapping.sqlite",
        allowed_actors=actors,
    )
    configure_default_registry(registry)
    return registry, identity
