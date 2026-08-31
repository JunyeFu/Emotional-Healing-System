from __future__ import annotations

from importlib import import_module
from typing import Any, Mapping

from .errors import SessionCoreError


_contract_v21 = import_module("05-通信协议.runtime_contract")
_contract_v22 = import_module("05-通信协议.runtime_contract_v22")

SCHEMA_VERSION: str = _contract_v21.SCHEMA_VERSION
SUPPORTED_SCHEMA_VERSIONS = frozenset(
    {_contract_v21.SCHEMA_VERSION, _contract_v22.SCHEMA_VERSION}
)


def validate_message(message_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    version = payload.get("schema_version") if isinstance(payload, Mapping) else None
    contract = _contract_v22 if version == _contract_v22.SCHEMA_VERSION else _contract_v21
    try:
        return contract.validate_and_filter(message_type, payload)
    except (
        _contract_v21.ContractValidationError,
        _contract_v22.ContractValidationError,
    ) as error:
        raise SessionCoreError(f"CONTRACT_{error.code}", error.detail) from error
