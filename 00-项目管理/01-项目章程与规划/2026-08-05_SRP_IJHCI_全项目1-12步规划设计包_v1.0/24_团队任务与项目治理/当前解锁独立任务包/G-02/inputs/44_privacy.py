from __future__ import annotations

import re
import unicodedata
from typing import Any

from .errors import GovernanceError
from .phone import normalize_phone


_FORBIDDEN_KEY_PARTS = (
    "name",
    "phone",
    "mobile",
    "email",
    "contact",
    "wechat",
    "qq",
    "deduptoken",
    "姓名",
    "电话",
    "手机",
    "邮箱",
    "联系方式",
)
_EMAIL = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,63}(?![A-Za-z0-9.-])"
)
_PHONE_CANDIDATE = re.compile(
    r"(?<!\d)(?:\+|00)?[0-9][0-9\s().-]{6,}[0-9](?!\d)"
)


def _normalized_key(key: str) -> str:
    key = unicodedata.normalize("NFKC", key)
    return "".join(character.lower() for character in key if character.isalnum())


def _has_confusable_key_script(key: str) -> bool:
    normalized = unicodedata.normalize("NFKC", key)
    return any(
        unicodedata.name(character, "").startswith(("CYRILLIC", "GREEK", "ARMENIAN"))
        for character in normalized
    )


def _normalize_decimal_digits(value: str) -> str:
    result: list[str] = []
    for character in value:
        try:
            result.append(str(unicodedata.decimal(character)))
        except (TypeError, ValueError):
            result.append(character)
    return "".join(result)


def _contact_like_value(value: str) -> bool:
    value = unicodedata.normalize("NFKC", value)
    value = "".join(
        character
        for character in value
        if unicodedata.category(character) != "Cf"
        and not unicodedata.category(character).startswith("M")
    )
    value = _normalize_decimal_digits(value)
    if _EMAIL.search(value):
        return True
    for candidate in _PHONE_CANDIDATE.finditer(value):
        compact = re.sub(r"[\s().-]", "", candidate.group())
        try:
            normalize_phone(compact)
        except GovernanceError:
            continue
        return True
    try:
        normalize_phone(value)
    except GovernanceError:
        return False
    return True


def privacy_lint_manifest(manifest: dict) -> None:
    if not isinstance(manifest, dict):
        raise GovernanceError("INVALID_MANIFEST", path="$")

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str):
                    raise GovernanceError("INVALID_MANIFEST_KEY", path=path)
                child_path = f"{path}.{key}"
                if _has_confusable_key_script(key):
                    raise GovernanceError("FORBIDDEN_MANIFEST_KEY", path=child_path)
                normalized = _normalized_key(key)
                if any(part in normalized for part in _FORBIDDEN_KEY_PARTS):
                    raise GovernanceError("FORBIDDEN_MANIFEST_KEY", path=child_path)
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
        elif isinstance(value, str) and _contact_like_value(value):
            raise GovernanceError("FORBIDDEN_MANIFEST_VALUE", path=path)

    visit(manifest, "$")
