from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from .errors import StoreError


_P02_FORBIDDEN_KEY_PARTS = (
    "subjecttoken",
    "hmac",
    "hmactoken",
    "apikey",
    "accesskey",
    "privatekey",
    "credential",
    "secret",
    "recruitmentreference",
    "recruitmentref",
    "identitymapping",
    "identitymap",
    "researchidmapping",
    "researchmap",
    "contacthash",
)


def _normalized_key(key: str) -> str:
    return "".join(character.lower() for character in key if character.isalnum())


def _safe_path(path: str) -> str:
    if not path.startswith("$"):
        return "$"
    result = "$"
    index = 1
    while index < len(path):
        if path[index] == "[":
            end = path.find("]", index)
            if end == -1:
                return result
            result += path[index : end + 1]
            index = end + 1
        elif path[index] == ".":
            result += ".*"
            index += 1
            while index < len(path) and path[index] not in ".[":
                index += 1
        else:
            index += 1
    return result


def _lint_p02_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise StoreError("PRIVACY_FORBIDDEN", path)
            child_path = f"{path}.*"
            normalized = _normalized_key(key)
            if any(part in normalized for part in _P02_FORBIDDEN_KEY_PARTS):
                raise StoreError("PRIVACY_FORBIDDEN", child_path)
            _lint_p02_keys(child, child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _lint_p02_keys(child, f"{path}[{index}]")


def _load_linter():
    module_root = Path(__file__).resolve().parents[1] / "07-数据治理"
    module_path = str(module_root)
    if module_path not in sys.path:
        sys.path.insert(0, module_path)
    try:
        from srp_governance import privacy_lint_manifest
    except ImportError as error:
        raise StoreError("G02_PRIVACY_GATE_UNAVAILABLE") from error
    return privacy_lint_manifest


def privacy_lint(value: Any) -> None:
    _lint_p02_keys(value)
    try:
        _load_linter()({"payload": value})
    except StoreError:
        raise
    except Exception as error:
        path = _safe_path(str(getattr(error, "path", "$")))
        raise StoreError("PRIVACY_FORBIDDEN", path) from error
