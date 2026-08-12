from __future__ import annotations

import ctypes
from ctypes import wintypes
import getpass
import secrets
from typing import Callable, Protocol

from .errors import GovernanceError


CREDENTIAL_TARGET = "SRP/G02/dedup-hmac/v1"
_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_ERROR_NOT_FOUND = 1168


class CredentialBackend(Protocol):
    def read(self, target: str) -> bytes | None: ...

    def write(self, target: str, value: bytes) -> None: ...


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialBackend:
    def __init__(self) -> None:
        if not hasattr(ctypes, "WinDLL"):
            raise GovernanceError("KEY_UNAVAILABLE")
        self._advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self._advapi.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(_CREDENTIALW)),
        ]
        self._advapi.CredReadW.restype = wintypes.BOOL
        self._advapi.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIALW), wintypes.DWORD]
        self._advapi.CredWriteW.restype = wintypes.BOOL
        self._advapi.CredFree.argtypes = [ctypes.c_void_p]
        self._advapi.CredFree.restype = None

    def read(self, target: str) -> bytes | None:
        pointer = ctypes.POINTER(_CREDENTIALW)()
        if not self._advapi.CredReadW(target, _CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
            error = ctypes.get_last_error()
            if error == _ERROR_NOT_FOUND:
                return None
            raise GovernanceError("KEY_UNAVAILABLE")
        try:
            credential = pointer.contents
            if credential.CredentialBlobSize == 0:
                return b""
            return ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        finally:
            self._advapi.CredFree(pointer)

    def write(self, target: str, value: bytes) -> None:
        blob = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
        try:
            credential = _CREDENTIALW()
            credential.Type = _CRED_TYPE_GENERIC
            credential.TargetName = target
            credential.CredentialBlobSize = len(value)
            credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
            credential.Persist = _CRED_PERSIST_LOCAL_MACHINE
            credential.UserName = "SRP G-02 data administrator"
            if not self._advapi.CredWriteW(ctypes.byref(credential), 0):
                raise GovernanceError("KEY_UNAVAILABLE")
        finally:
            ctypes.memset(blob, 0, len(value))


class CredentialKeyProvider:
    def __init__(
        self,
        *,
        backend: CredentialBackend,
        required_account: str,
        account_provider: Callable[[], str] = getpass.getuser,
    ) -> None:
        self.backend = backend
        self.required_account = required_account
        self.account_provider = account_provider

    def _authorize_account(self) -> None:
        current = self.account_provider()
        if current.casefold() != self.required_account.casefold():
            raise GovernanceError("UNAUTHORIZED")

    def __call__(self) -> bytes:
        self._authorize_account()
        try:
            value = self.backend.read(CREDENTIAL_TARGET)
        except GovernanceError:
            raise
        except Exception as exc:
            raise GovernanceError("KEY_UNAVAILABLE") from exc
        if not isinstance(value, bytes) or len(value) != 32:
            raise GovernanceError("KEY_UNAVAILABLE")
        return value

    def provision(self) -> str:
        self._authorize_account()
        value = bytearray(secrets.token_bytes(32))
        try:
            self.backend.write(CREDENTIAL_TARGET, bytes(value))
        except GovernanceError:
            raise
        except Exception as exc:
            raise GovernanceError("KEY_UNAVAILABLE") from exc
        finally:
            for index in range(len(value)):
                value[index] = 0
        return CREDENTIAL_TARGET
