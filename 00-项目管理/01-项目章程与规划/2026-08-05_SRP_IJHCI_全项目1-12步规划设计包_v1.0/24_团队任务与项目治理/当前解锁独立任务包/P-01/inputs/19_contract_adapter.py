from __future__ import annotations

from importlib import import_module
from typing import Any, Mapping

from .errors import SessionCoreError


_contract = import_module("05-通信协议.runtime_contract")

SCHEMA_VERSION: str = _contract.SCHEMA_VERSION


def validate_message(message_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return _contract.validate_and_filter(message_type, payload)
    except _contract.ContractValidationError as error:
        raise SessionCoreError(f"CONTRACT_{error.code}", error.detail) from error
