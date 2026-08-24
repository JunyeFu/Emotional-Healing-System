from __future__ import annotations

import subprocess

import srp_governance.windows_checks as windows_checks


def _result(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")


def test_minimum_acl_accepts_domain_account_with_modify_and_system(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(
        windows_checks,
        "_powershell",
        lambda _: _result(
            '[{"identity":"LAB\\\\SRPDataAdmin","rights":"Modify, Synchronize",'
            '"type":"Allow","inherited":false},'
            '{"identity":"NT AUTHORITY\\\\SYSTEM","rights":"FullControl",'
            '"type":"Allow","inherited":true}]'
        ),
    )

    assert windows_checks.minimum_acl(tmp_path, "LAB\\SRPDataAdmin") is True


def test_minimum_acl_rejects_unknown_allowed_identity(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        windows_checks,
        "_powershell",
        lambda _: _result(
            '[{"identity":"SRPDataAdmin","rights":"FullControl",'
            '"type":"Allow","inherited":false},'
            '{"identity":"BUILTIN\\\\Users","rights":"ReadAndExecute",'
            '"type":"Allow","inherited":true}]'
        ),
    )

    assert windows_checks.minimum_acl(tmp_path, "SRPDataAdmin") is False


def test_minimum_acl_requires_modify_for_data_admin(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        windows_checks,
        "_powershell",
        lambda _: _result(
            '[{"identity":"SRPDataAdmin","rights":"ReadAndExecute",'
            '"type":"Allow","inherited":false}]'
        ),
    )

    assert windows_checks.minimum_acl(tmp_path, "SRPDataAdmin") is False
