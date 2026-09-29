from __future__ import annotations

from typing import Any, Mapping

from .errors import RandomizationError
from .store import RandomizationStore


class X01AssignmentGate:
    def __init__(self, store: RandomizationStore) -> None:
        self.store = store
        self.formal_capable = store.formal_capable

    def check(
        self,
        manifest: Mapping[str, Any],
        assignment: Any,
        config_hash: str,
    ) -> Any:
        del config_hash
        try:
            evidence_id = self.store.validate_assignment(dict(manifest), assignment)
        except RandomizationError as error:
            from srp_session_core.errors import SessionCoreError

            raise SessionCoreError(error.code, error.detail) from error
        from srp_session_core.models import GateReceipt

        return GateReceipt("assignment", evidence_id, self.formal_capable)
