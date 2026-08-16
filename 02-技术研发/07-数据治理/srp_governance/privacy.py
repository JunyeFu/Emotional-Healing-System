from __future__ import annotations

import re
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
    r"(?<!\d)(?:\+|00)?[0-9][0-9 ()-]{6,}[0-9](?!\d)"
)


def _normalized_key(key: str) -> str:
    return "".join(character.lower() for character in key if character.isalnum())


def _contact_like_value(value: str) -> bool:
    if _EMAIL.search(value):
        return True
    for candidate in _PHONE_CANDIDATE.finditer(value):
        try:
            normalize_phone(candidate.group())
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
