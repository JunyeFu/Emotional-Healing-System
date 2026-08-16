from __future__ import annotations

import pytest

import srp_governance.credentials as credentials_module
from srp_governance import GovernanceError
from srp_governance.credentials import (
    CREDENTIAL_TARGET,
    CredentialKeyProvider,
    WindowsCredentialBackend,
)


class FakeCredentialBackend:
    def __init__(self, value: bytes | None = None) -> None:
        self.value = value
        self.read_targets: list[str] = []
        self.writes: list[tuple[str, bytes]] = []

    def read(self, target: str) -> bytes | None:
        self.read_targets.append(target)
        return self.value

    def write(self, target: str, value: bytes) -> None:
        self.writes.append((target, value))
        self.value = value


def test_provider_reads_exact_frozen_target_for_required_account() -> None:
    backend = FakeCredentialBackend(b"K" * 32)
    provider = CredentialKeyProvider(
        backend=backend,
        required_account="SRPDataAdmin",
        account_provider=lambda: "srpdataadmin",
    )

    assert provider() == b"K" * 32
    assert backend.read_targets == [CREDENTIAL_TARGET]


def test_provider_rejects_wrong_windows_account_before_credential_read() -> None:
    backend = FakeCredentialBackend(b"K" * 32)
    provider = CredentialKeyProvider(
        backend=backend,
        required_account="SRPDataAdmin",
        account_provider=lambda: "other-user",
    )

    with pytest.raises(GovernanceError) as error:
        provider()

    assert error.value.code == "UNAUTHORIZED"
    assert backend.read_targets == []


@pytest.mark.parametrize("value", [None, b"", b"short", b"K" * 31, b"K" * 33])
def test_missing_or_malformed_credential_fails_closed(value: bytes | None) -> None:
    provider = CredentialKeyProvider(
        backend=FakeCredentialBackend(value),
        required_account="SRPDataAdmin",
        account_provider=lambda: "SRPDataAdmin",
    )

    with pytest.raises(GovernanceError) as error:
        provider()

    assert error.value.code == "KEY_UNAVAILABLE"


def test_provision_generates_32_byte_key_without_returning_secret() -> None:
    backend = FakeCredentialBackend()
    provider = CredentialKeyProvider(
        backend=backend,
        required_account="SRPDataAdmin",
        account_provider=lambda: "SRPDataAdmin",
    )

    result = provider.provision()

    assert result == CREDENTIAL_TARGET
    assert len(backend.writes) == 1
    assert backend.writes[0][0] == CREDENTIAL_TARGET
    assert len(backend.writes[0][1]) == 32


def test_provision_refuses_to_overwrite_existing_key() -> None:
    original = b"K" * 32
    backend = FakeCredentialBackend(original)
    provider = CredentialKeyProvider(
        backend=backend,
        required_account="SRPDataAdmin",
        account_provider=lambda: "SRPDataAdmin",
    )

    with pytest.raises(GovernanceError) as error:
        provider.provision()

    assert error.value.code == "KEY_ALREADY_PROVISIONED"
    assert backend.value == original
    assert backend.writes == []


def test_windows_backend_wipes_temporary_blob_when_write_fails(monkeypatch) -> None:
    class FailedAdvapi:
        @staticmethod
        def CredWriteW(_credential, _flags):
            return False

    backend = object.__new__(WindowsCredentialBackend)
    backend._advapi = FailedAdvapi()
    wipes: list[int] = []
    original_memset = credentials_module.ctypes.memset

    def recording_memset(buffer, value, size):
        wipes.append(size)
        return original_memset(buffer, value, size)

    monkeypatch.setattr(credentials_module.ctypes, "memset", recording_memset)

    with pytest.raises(GovernanceError) as error:
        backend.write(CREDENTIAL_TARGET, b"K" * 32)

    assert error.value.code == "KEY_UNAVAILABLE"
    assert wipes == [32]
