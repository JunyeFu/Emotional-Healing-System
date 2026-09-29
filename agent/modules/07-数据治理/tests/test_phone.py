from __future__ import annotations

import pytest

from srp_governance import GovernanceError, normalize_phone
from srp_governance.phone import phone_token


@pytest.mark.parametrize(
    "raw",
    [
        "13800138000",
        "86 138-0013-8000",
        "0086 (138) 0013 8000",
        "+86 138 0013 8000",
    ],
)
def test_mainland_variants_normalize_to_one_e164_value(raw: str) -> None:
    assert normalize_phone(raw) == "+8613800138000"


def test_explicit_international_e164_is_preserved() -> None:
    assert normalize_phone("+1 (415) 555-2671") == "+14155552671"


@pytest.mark.parametrize(
    "raw",
    [None, "", "1234567", "4155552671", "+12", "+1234567890123456", "13800138000x1", "+86.13800138000"],
)
def test_invalid_or_ambiguous_phone_is_rejected_without_echo(raw: object) -> None:
    with pytest.raises(GovernanceError) as error:
        normalize_phone(raw)  # type: ignore[arg-type]

    assert error.value.code == "INVALID_PHONE"
    if raw is not None and str(raw):
        assert str(raw) not in str(error.value)


def test_phone_token_uses_frozen_domain_separation_and_full_digest() -> None:
    token = phone_token("+8613800138000", b"K" * 32)

    assert token.hex() == "8908850faa6718dd5d6381d64645c23fbc5267691ef3d3af449c48bbf8c5e87a"
    assert len(token) == 32


@pytest.mark.parametrize("key", [b"", b"short", b"K" * 31, b"K" * 33])
def test_phone_token_rejects_non_32_byte_keys(key: bytes) -> None:
    with pytest.raises(GovernanceError) as error:
        phone_token("+8613800138000", key)

    assert error.value.code == "KEY_UNAVAILABLE"
