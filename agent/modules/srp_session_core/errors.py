from __future__ import annotations


class SessionCoreError(RuntimeError):
    """Fail-closed error with a stable reason code and non-sensitive detail."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        message = code if not detail else f"{code}: {detail}"
        super().__init__(message)


class TransportError(SessionCoreError):
    """Local transport failure that must be routed back to SessionCore."""
