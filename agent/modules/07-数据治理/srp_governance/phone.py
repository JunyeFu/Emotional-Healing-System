from __future__ import annotations

import hashlib
import hmac
import re

from .errors import GovernanceError


DOMAIN_PREFIX = b"srp:g02:phone:v1\0"
_ALLOWED_INPUT = re.compile(r"^[0-9+ ()-]+$")
_SEPARATORS = str.maketrans("", "", " -()")


def normalize_phone(raw: str) -> str:
    if not isinstance(raw, str) or not raw or not _ALLOWED_INPUT.fullmatch(raw):
        raise GovernanceError("INVALID_PHONE")

    compact = raw.translate(_SEPARATORS)
    if compact.startswith("+86"):
        national = compact[3:]
        if len(national) == 11 and national.startswith("1") and national.isdigit():
            return f"+86{national}"
        raise GovernanceError("INVALID_PHONE")

    for prefix in ("0086", "86"):
        if compact.startswith(prefix):
            national = compact[len(prefix):]
            if len(national) == 11 and national.startswith("1") and national.isdigit():
                return f"+86{national}"
            raise GovernanceError("INVALID_PHONE")

    if len(compact) == 11 and compact.startswith("1") and compact.isdigit():
        return f"+86{compact}"

    if compact.startswith("+"):
        digits = compact[1:]
        if 8 <= len(digits) <= 15 and digits.isdigit() and not digits.startswith("0"):
            return compact

    raise GovernanceError("INVALID_PHONE")


def phone_token(canonical_e164: str, key: bytes) -> bytes:
    if not isinstance(key, bytes) or len(key) != 32:
        raise GovernanceError("KEY_UNAVAILABLE")
    canonical = normalize_phone(canonical_e164)
    return hmac.new(key, DOMAIN_PREFIX + canonical.encode("utf-8"), hashlib.sha256).digest()
