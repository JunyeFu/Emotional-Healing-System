from __future__ import annotations


class GovernanceError(RuntimeError):
    """Fail-closed error that never carries rejected source values."""

    def __init__(self, code: str, *, path: str | None = None) -> None:
        self.code = code
        self.path = path
        detail = f" at {path}" if path else ""
        super().__init__(f"{code}{detail}")
