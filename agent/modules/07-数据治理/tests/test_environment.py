from __future__ import annotations

from pathlib import Path

from srp_governance.environment import EnvironmentInputs, check_environment


def test_missing_machine_configuration_keeps_formal_gate_closed(tmp_path) -> None:
    report = check_environment(
        EnvironmentInputs(
            repo_root=tmp_path / "repo",
            governance_root=None,
            backup_root=None,
            sealed_key_evidence=None,
            required_account=None,
            current_account="developer",
            credential_probe=lambda: False,
            encryption_probe=lambda _: False,
            acl_probe=lambda _, __: False,
        )
    )

    assert report.formal_ready is False
    assert {item.code for item in report.checks if not item.passed} >= {
        "GOVERNANCE_ROOT_UNSET",
        "BACKUP_ROOT_UNSET",
        "SEALED_KEY_EVIDENCE_UNSET",
        "DATA_ADMIN_ACCOUNT_UNSET",
        "RETENTION_APPROVAL_PENDING",
    }


def test_complete_separated_encrypted_configuration_passes(tmp_path) -> None:
    repo = tmp_path / "repo"
    governance = tmp_path / "governance"
    backup = tmp_path / "backup"
    evidence = tmp_path / "sealed-key-evidence.md"
    for directory in (repo, governance, backup):
        directory.mkdir()
    evidence.write_text("fixture", encoding="ascii")

    report = check_environment(
        EnvironmentInputs(
            repo_root=repo,
            governance_root=governance,
            backup_root=backup,
            sealed_key_evidence=evidence,
            required_account="SRPDataAdmin",
            current_account="srpdataadmin",
            credential_probe=lambda: True,
            encryption_probe=lambda _: True,
            acl_probe=lambda _, __: True,
            retention_status="APPROVED:fixture-policy-v1",
        )
    )

    assert report.formal_ready is True
    assert all(item.passed for item in report.checks)


def test_repo_nested_or_unencrypted_roots_fail(tmp_path) -> None:
    repo = tmp_path / "repo"
    governance = repo / "governance"
    backup = tmp_path / "backup"
    evidence = tmp_path / "evidence"
    for directory in (governance, backup):
        directory.mkdir(parents=True)
    evidence.write_text("fixture", encoding="ascii")

    report = check_environment(
        EnvironmentInputs(
            repo_root=repo,
            governance_root=governance,
            backup_root=backup,
            sealed_key_evidence=evidence,
            required_account="SRPDataAdmin",
            current_account="SRPDataAdmin",
            credential_probe=lambda: True,
            encryption_probe=lambda _: False,
            acl_probe=lambda _, __: True,
            retention_status="APPROVED:fixture-policy-v1",
        )
    )

    failures = {item.code for item in report.checks if not item.passed}
    assert "GOVERNANCE_ROOT_INSIDE_REPOSITORY" in failures
    assert "GOVERNANCE_ROOT_ENCRYPTION_UNCONFIRMED" in failures


def test_backup_root_cannot_contain_governance_root(tmp_path) -> None:
    backup = tmp_path / "backup"
    governance = backup / "governance"
    repo = tmp_path / "repo"
    evidence = tmp_path / "sealed-key-evidence.md"
    for directory in (governance, repo):
        directory.mkdir(parents=True)
    evidence.write_text("fixture", encoding="ascii")

    report = check_environment(
        EnvironmentInputs(
            repo_root=repo,
            governance_root=governance,
            backup_root=backup,
            sealed_key_evidence=evidence,
            required_account="SRPDataAdmin",
            current_account="SRPDataAdmin",
            credential_probe=lambda: True,
            encryption_probe=lambda _: True,
            acl_probe=lambda _, __: True,
            retention_status="APPROVED:fixture-policy-v1",
        )
    )

    failures = {item.code for item in report.checks if not item.passed}
    assert "BACKUP_ROOT_SEPARATE" in failures


def test_sealed_key_evidence_must_remain_outside_repository(tmp_path) -> None:
    repo = tmp_path / "repo"
    governance = tmp_path / "governance"
    backup = tmp_path / "backup"
    evidence = repo / "sealed-key-evidence.md"
    for directory in (repo, governance, backup):
        directory.mkdir()
    evidence.write_text("fixture", encoding="ascii")

    report = check_environment(
        EnvironmentInputs(
            repo_root=repo,
            governance_root=governance,
            backup_root=backup,
            sealed_key_evidence=evidence,
            required_account="SRPDataAdmin",
            current_account="SRPDataAdmin",
            credential_probe=lambda: True,
            encryption_probe=lambda _: True,
            acl_probe=lambda _, __: True,
            retention_status="APPROVED:fixture-policy-v1",
        )
    )

    failures = {item.code for item in report.checks if not item.passed}
    assert "SEALED_KEY_EVIDENCE_OUTSIDE_REPOSITORY" in failures
