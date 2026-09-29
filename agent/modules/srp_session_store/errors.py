from __future__ import annotations


class StoreError(RuntimeError):
    def __init__(self, code: str, path: str | None = None) -> None:
        self.code = code
        self.path = path
        message = code if not path else f"{code}: {path}"
        super().__init__(message)
