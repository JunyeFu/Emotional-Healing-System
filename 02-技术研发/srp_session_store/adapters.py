from __future__ import annotations

import getpass
import os
from pathlib import Path
import sys
from typing import Any, Mapping

from srp_session_core import GateReceipt, OperatorRequest
from srp_session_core.contract_adapter import validate_message
from srp_session_core.errors import TransportError

from .archive import SessionArchive, _FORMAL_ARCHIVE_TOKEN
from .canonical import domain_hash
from .config import load_store_config
from .errors import StoreError
from .models import StoreConfig
from .privacy import privacy_lint
from .serialization import json_value, serialize_core_output


_FORMAL_CAPABILITY_TOKEN = object()


def _governance_root() -> Path:
    root = Path(__file__).resolve().parents[1] / "07-数据治理"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def _system_account() -> str:
    return getpass.getuser()


def _formal_environment_checks(root: Path, account: str, actor_role: str) -> bool:
    _governance_root()
    from srp_governance.access import Capability, authorize
    from srp_governance.windows_checks import encryption_enabled, minimum_acl

    authorize(actor_role, Capability.READ_L0_L1)
    return encryption_enabled(root) and minimum_acl(root, account)


class DurableManifestStore:
    def __init__(
        self,
        root: Path,
        *,
        store_config: StoreConfig | None = None,
        _formal_token: object | None = None,
    ) -> None:
        self.root = Path(root)
        self.formal_capable = _formal_token is _FORMAL_CAPABILITY_TOKEN
        self.store_config = store_config or load_store_config()
        self.archive: SessionArchive | None = None
        self._assignment: Any = None
        self._prepare_now_ns: int | None = None

    @classmethod
    def development(cls, root: Path) -> "DurableManifestStore":
        return cls(root)

    @classmethod
    def from_formal_environment(
        cls,
        repo_root: Path,
    ) -> "DurableManifestStore":
        root_value = os.environ.get("SRP_SESSION_DATA_ROOT")
        required_account = os.environ.get("SRP_SESSION_WRITER_ACCOUNT")
        actor_role = os.environ.get("SRP_SESSION_WRITER_ROLE")
        if not root_value or not required_account or not actor_role:
            raise StoreError("FORMAL_STORAGE_UNAVAILABLE")
        root = Path(root_value)
        repo_root = Path(repo_root).resolve()
        try:
            root_resolved = root.resolve()
            root_resolved.relative_to(repo_root)
            inside_repo = True
        except (OSError, ValueError):
            root_resolved = root.resolve()
            inside_repo = False
        if not root.is_absolute() or not root.is_dir() or inside_repo:
            raise StoreError("FORMAL_STORAGE_UNAVAILABLE")
        account = _system_account()
        if account.casefold() != required_account.casefold():
            raise StoreError("FORMAL_STORAGE_UNAVAILABLE")
        try:
            environment_ok = _formal_environment_checks(
                root_resolved, required_account, actor_role
            )
        except Exception as error:
            raise StoreError("FORMAL_STORAGE_UNAVAILABLE") from error
        if not environment_ok:
            raise StoreError("FORMAL_STORAGE_UNAVAILABLE")
        return cls(root_resolved, _formal_token=_FORMAL_CAPABILITY_TOKEN)

    def arm_prepare(
        self,
        assignment: Any,
        now_ns: int,
        operation_id: str,
        operation_arguments: Mapping[str, Any],
    ) -> None:
        if self.archive is not None:
            raise StoreError("SESSION_ALREADY_EXISTS")
        self._assignment = assignment
        self._prepare_now_ns = now_ns
        self._prepare_operation_id = operation_id
        self._prepare_operation_arguments = dict(operation_arguments)

    def append_manifest(
        self, manifest: Mapping[str, Any], config_hash: str
    ) -> GateReceipt:
        if self.archive is not None:
            raise StoreError("SESSION_ALREADY_EXISTS")
        validated = validate_message("session_manifest", manifest)
        privacy_lint(validated)
        if self._assignment is None or self._prepare_now_ns is None:
            raise StoreError("PREPARE_CONTEXT_REQUIRED")
        archive = SessionArchive.create(
            self.root,
            validated,
            protocol_config_hash=config_hash,
            store_config=self.store_config,
            _formal_token=(
                _FORMAL_ARCHIVE_TOKEN if self.formal_capable else None
            ),
        )
        try:
            archive.append_l1(
                "manifest_context",
                {
                    "assignment": json_value(self._assignment),
                    "manifest_hash": archive.manifest_hash,
                    "protocol_config_hash": config_hash,
                    "store_config_hash": self.store_config.config_hash,
                },
                self._prepare_now_ns,
            )
            archive.append_l1(
                "operation_begin",
                {
                    "arguments": json_value(self._prepare_operation_arguments),
                    "method": "prepare",
                    "operation_id": self._prepare_operation_id,
                },
                self._prepare_now_ns,
            )
        except Exception:
            archive.close()
            raise
        self.archive = archive
        evidence = "p02:manifest:" + domain_hash(
            b"srp:p02:gate-receipt:v1\0",
            {
                "manifest_hash": archive.manifest_hash,
                "store_config_hash": self.store_config.config_hash,
            },
        ).removeprefix("sha256:")
        return GateReceipt("manifest_store", evidence, self.formal_capable)


class RecordingSessionCore:
    """Persist calls and outputs while leaving all state transitions in SessionCore."""

    def __init__(self, core: Any, manifest_store: DurableManifestStore) -> None:
        self.core = core
        self.manifest_store = manifest_store
        self._operation_seq = 0

    def prepare(self, manifest: Mapping[str, Any], assignment: Any, now_ns: int):
        arguments = {
            "manifest": dict(manifest),
            "assignment": json_value(assignment),
            "now_ns": now_ns,
        }
        operation_id = self._next_operation_id()
        self.manifest_store.arm_prepare(
            assignment, now_ns, operation_id, arguments
        )
        try:
            result = self.core.prepare(manifest, assignment, now_ns)
        except Exception as error:
            if self.manifest_store.archive is not None:
                try:
                    self._failed(operation_id, "prepare", error, now_ns)
                except StoreError:
                    pass
            raise
        try:
            self._commit(operation_id, "prepare", result, now_ns)
        except StoreError:
            return self._storage_failure(now_ns, prior_result=result)
        return result

    def apply_operator_request(self, request: OperatorRequest, now_ns: int):
        return self._invoke(
            "apply_operator_request",
            {"request": json_value(request), "now_ns": now_ns},
            lambda: self.core.apply_operator_request(request, now_ns),
            now_ns,
        )

    def advance(self, now_ns: int):
        return self._invoke(
            "advance", {"now_ns": now_ns}, lambda: self.core.advance(now_ns), now_ns
        )

    def confirm_delivery(self, message: Mapping[str, Any], now_ns: int):
        message_type = str(message.get("message_type", ""))
        validated = validate_message(message_type, message)
        self._archive().append_l1(message_type, validated, now_ns)
        return self._invoke(
            "confirm_delivery",
            {"message": validated, "now_ns": now_ns},
            lambda: self.core.confirm_delivery(validated, now_ns),
            now_ns,
        )

    def transport_failure(self, reason_code: str, now_ns: int):
        return self._invoke(
            "transport_failure",
            {"reason_code": reason_code, "now_ns": now_ns},
            lambda: self.core.transport_failure(reason_code, now_ns),
            now_ns,
        )

    def finish(self, reason_code: str, now_ns: int):
        return self._invoke(
            "finish",
            {"reason_code": reason_code, "now_ns": now_ns},
            lambda: self.core.finish(reason_code, now_ns),
            now_ns,
        )

    def snapshot(self):
        return self.core.snapshot()

    def _invoke(
        self,
        method: str,
        arguments: Mapping[str, Any],
        call: Callable[[], Any],
        now_ns: int,
    ) -> Any:
        try:
            operation_id = self._begin(method, arguments, now_ns)
        except StoreError:
            if method == "finish":
                raise
            return self._storage_failure(now_ns)
        try:
            result = call()
        except Exception as error:
            try:
                self._failed(operation_id, method, error, now_ns)
            except StoreError:
                pass
            raise error
        try:
            self._commit(operation_id, method, result, now_ns)
        except StoreError:
            if method == "finish":
                raise
            return self._storage_failure(now_ns, prior_result=result)
        return result

    def _record_completed(
        self, method: str, arguments: Mapping[str, Any], result: Any, now_ns: int
    ) -> None:
        operation_id = self._begin(method, arguments, now_ns)
        self._commit(operation_id, method, result, now_ns)

    def _record_failed(
        self, method: str, arguments: Mapping[str, Any], error: Exception, now_ns: int
    ) -> None:
        operation_id = self._begin(method, arguments, now_ns)
        self._failed(operation_id, method, error, now_ns)

    def _begin(self, method: str, arguments: Mapping[str, Any], now_ns: int) -> str:
        archive = self._archive()
        operation_id = self._next_operation_id()
        archive.append_l1(
            "operation_begin",
            {
                "arguments": json_value(arguments),
                "method": method,
                "operation_id": operation_id,
            },
            now_ns,
        )
        return operation_id

    def _next_operation_id(self) -> str:
        self._operation_seq += 1
        return f"operation-{self._operation_seq:06d}"

    def _commit(self, operation_id: str, method: str, result: Any, now_ns: int) -> None:
        output = serialize_core_output(result)
        archive = self._archive()
        if output.get("output_type") == "CoreUpdate":
            for record_type, key in (
                ("control_event", "control_events"),
                ("session_event", "session_events"),
                ("policy_decision", "policy_decisions"),
                ("audit_record", "audit_records"),
                ("gate_receipt", "gate_receipts"),
            ):
                for item in output[key]:
                    archive.append_l1(record_type, item, now_ns)
        archive.append_l1(
            "operation_commit",
            {
                "method": method,
                "operation_id": operation_id,
                "output": output,
                "output_hash": domain_hash(b"srp:p02:core-output:v1\0", output),
            },
            now_ns,
        )

    def _failed(self, operation_id: str, method: str, error: Exception, now_ns: int) -> None:
        code = str(getattr(error, "code", type(error).__name__))
        self._archive().append_l1(
            "operation_failed",
            {"method": method, "operation_id": operation_id, "reason_code": code},
            now_ns,
        )

    def _storage_failure(self, now_ns: int, prior_result: Any | None = None):
        if prior_result is not None and any(
            event.get("event_type") == "abort"
            for event in getattr(prior_result, "control_events", ())
        ):
            return prior_result
        try:
            return self.core.transport_failure("STORAGE_APPEND_FAILED", now_ns)
        except Exception as error:
            raise StoreError("STORAGE_APPEND_FAILED") from error

    def _archive(self) -> SessionArchive:
        if self.manifest_store.archive is None:
            raise StoreError("MANIFEST_NOT_STORED")
        return self.manifest_store.archive


class RecordingTelemetryPublisher:
    def __init__(self, publisher: Any, manifest_store: DurableManifestStore) -> None:
        self.publisher = publisher
        self.manifest_store = manifest_store
        self._last_frame_seq = -1

    def publish(self, frame: Mapping[str, Any]) -> bool:
        validated = validate_message("telemetry_frame", frame)
        snapshot = self.publisher.core.snapshot()
        expected = {
            "session_id": snapshot.session_id,
            "module_id": snapshot.module_id,
            "module_position": snapshot.module_position,
            "segment": snapshot.segment,
            "cue_mode": snapshot.cue_mode,
            "runtime_mode": snapshot.runtime_mode,
        }
        mismatches = [key for key, value in expected.items() if validated[key] != value]
        if mismatches:
            raise TransportError("TELEMETRY_SNAPSHOT_MISMATCH", ",".join(mismatches))
        frame_seq = int(validated["frame_seq"])
        if frame_seq <= self._last_frame_seq:
            raise TransportError("STALE_TELEMETRY_SEQUENCE", str(frame_seq))
        archive = self.manifest_store.archive
        if archive is None:
            raise StoreError("MANIFEST_NOT_STORED")
        now_ns = int(validated["sent_monotonic_ns"])
        archive.append_l1("telemetry_frame", validated, now_ns)
        self._last_frame_seq = frame_seq
        try:
            sent = bool(self.publisher.publish(validated))
        except Exception as error:
            archive.append_l1(
                "udp_delivery_result",
                {"frame_seq": frame_seq, "reason_code": str(getattr(error, "code", "UDP_SEND_FAILED")), "sent": False},
                now_ns,
            )
            raise
        archive.append_l1(
            "udp_delivery_result",
            {"frame_seq": frame_seq, "reason_code": None, "sent": sent},
            now_ns,
        )
        return sent

    def close(self) -> None:
        self.publisher.close()
