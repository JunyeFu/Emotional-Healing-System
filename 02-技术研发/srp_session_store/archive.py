from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, BinaryIO, Iterator, Mapping

from .canonical import canonical_bytes, domain_hash, file_sha256
from .config import load_store_config
from .errors import StoreError
from .models import (
    AppendReceipt,
    CheckpointReceipt,
    IntegrityReport,
    RawPacket,
    SessionSeal,
    StoreConfig,
    mapping,
)
from .privacy import privacy_lint


_SESSION_DOMAIN = b"srp:p02:session-path:v1\0"
_ENVELOPE_DOMAIN = b"srp:p02:archive-envelope:v1\0"
_TAIL_STATE_DOMAIN = b"srp:p02:tail-state:v1\0"
_MANIFEST_DOMAIN = b"srp:p02:manifest:v1\0"
_RECORD_DOMAIN = b"srp:p02:record:v1\0"
_CHECKPOINT_DOMAIN = b"srp:p02:checkpoint:v1\0"
_SEAL_DOMAIN = b"srp:p02:seal:v1\0"
_ZERO_HASH = "sha256:" + "0" * 64
_RAW_SOURCE_IDS = {"plux_respiban", "polar_h10_ecg", "polar_h10_rr"}
_FORMAL_ARCHIVE_TOKEN = object()
_HASH_VALUE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SESSION_KEY_VALUE = re.compile(r"^[0-9a-f]{64}$")
_ENVELOPE_KEYS = {
    "archive_schema_version",
    "envelope_hash",
    "formal_capable",
    "manifest",
    "manifest_hash",
    "protocol_config_hash",
    "session_key",
    "store_config_hash",
}


def session_key(session_id: str) -> str:
    import hashlib

    return hashlib.sha256(_SESSION_DOMAIN + session_id.encode("utf-8")).hexdigest()


def _exclusive_json(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = canonical_bytes(dict(payload)) + b"\n"
    try:
        with path.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise StoreError("IMMUTABLE_TARGET_EXISTS") from error
    except OSError as error:
        raise StoreError("STORAGE_APPEND_FAILED") from error


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    encoded = canonical_bytes(dict(payload)) + b"\n"
    try:
        with temporary.open("wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise StoreError("STORAGE_SYNC_FAILED") from error


def _envelope_is_valid(envelope: Mapping[str, Any]) -> bool:
    return (
        set(envelope) == _ENVELOPE_KEYS
        and envelope.get("archive_schema_version") == "1.0"
        and isinstance(envelope.get("formal_capable"), bool)
        and isinstance(envelope.get("manifest"), dict)
        and isinstance(envelope.get("protocol_config_hash"), str)
        and bool(envelope.get("protocol_config_hash"))
        and isinstance(envelope.get("manifest_hash"), str)
        and _HASH_VALUE.fullmatch(str(envelope.get("manifest_hash"))) is not None
        and isinstance(envelope.get("store_config_hash"), str)
        and _HASH_VALUE.fullmatch(str(envelope.get("store_config_hash"))) is not None
        and isinstance(envelope.get("envelope_hash"), str)
        and _HASH_VALUE.fullmatch(str(envelope.get("envelope_hash"))) is not None
        and isinstance(envelope.get("session_key"), str)
        and _SESSION_KEY_VALUE.fullmatch(str(envelope.get("session_key"))) is not None
    )


class _WriterLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle: BinaryIO | None = None

    def acquire(self) -> None:
        self.handle = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            self.handle.write(b"\0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, IOError) as error:
            self.handle.close()
            self.handle = None
            raise StoreError("SESSION_WRITER_LOCKED") from error

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


@dataclass
class _Stream:
    name: str
    segment_index: int
    handle: BinaryIO
    seq: int = 0
    tail_hash: str = _ZERO_HASH
    unsynced_bytes: int = 0
    last_sync_ns: int = 0
    anchored_seq: int = 0


class SessionArchive:
    def __init__(
        self,
        path: Path,
        envelope: dict[str, Any],
        store_config: StoreConfig,
        lock: _WriterLock,
        streams: dict[str, _Stream],
        *,
        acknowledged_unclean_segments: tuple[str, ...] = (),
    ) -> None:
        self.path = path
        self.envelope = envelope
        self.store_config = store_config
        self._lock = lock
        self._streams = streams
        self._sealed = (path / "seal.json").exists()
        self._checkpoint_seq = len(list((path / "checkpoints").glob("checkpoint-*.json")))
        self._last_checkpoint_ns = 0
        self._acknowledged_unclean_segments = acknowledged_unclean_segments
        self._raw_seq_by_source: dict[str, int] = {}

    @classmethod
    def create(
        cls,
        root: Path,
        manifest: Mapping[str, Any],
        *,
        protocol_config_hash: str,
        store_config: StoreConfig | None = None,
        _formal_token: object | None = None,
    ) -> "SessionArchive":
        if not isinstance(manifest, Mapping) or not isinstance(manifest.get("session_id"), str):
            raise StoreError("MANIFEST_REJECTED", "$.session_id")
        privacy_lint(dict(manifest))
        config = store_config or load_store_config()
        root = Path(root)
        sessions = root / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        key = session_key(str(manifest["session_id"]))
        path = sessions / key
        try:
            path.mkdir()
        except FileExistsError as error:
            raise StoreError("SESSION_ALREADY_EXISTS") from error
        for name in ("l0", "l1", "checkpoints", "tails"):
            (path / name).mkdir()
        lock = _WriterLock(path / "writer.lock")
        lock.acquire()
        manifest_payload = dict(manifest)
        envelope_body = {
            "archive_schema_version": "1.0",
            "formal_capable": _formal_token is _FORMAL_ARCHIVE_TOKEN,
            "manifest": manifest_payload,
            "manifest_hash": domain_hash(_MANIFEST_DOMAIN, manifest_payload),
            "protocol_config_hash": protocol_config_hash,
            "session_key": key,
            "store_config_hash": config.config_hash,
        }
        envelope = dict(
            envelope_body,
            envelope_hash=domain_hash(_ENVELOPE_DOMAIN, envelope_body),
        )
        try:
            _exclusive_json(path / "archive.json", envelope)
            for name in ("l0", "l1"):
                body = {
                    "session_key": key,
                    "stream": name,
                    "stream_seq": 0,
                    "tail_hash": _ZERO_HASH,
                }
                _exclusive_json(
                    path / "tails" / f"{name}.json",
                    dict(body, tail_state_hash=domain_hash(_TAIL_STATE_DOMAIN, body)),
                )
            streams = {
                name: cls._create_stream(path, name, 1)
                for name in ("l0", "l1")
            }
        except Exception:
            lock.release()
            raise
        return cls(path, envelope, config, lock, streams)

    @staticmethod
    def _create_stream(path: Path, name: str, segment_index: int) -> _Stream:
        segment = path / name / f"segment-{segment_index:06d}.jsonl"
        try:
            handle = segment.open("xb")
        except FileExistsError as error:
            raise StoreError("IMMUTABLE_TARGET_EXISTS") from error
        return _Stream(name, segment_index, handle)

    @property
    def manifest_hash(self) -> str:
        return str(self.envelope["manifest_hash"])

    @property
    def formal_capable(self) -> bool:
        return bool(self.envelope["formal_capable"])

    def append_raw_packet(self, packet: RawPacket) -> AppendReceipt:
        self._require_open()
        self._validate_raw_packet(packet)
        previous_packet_seq = self._raw_seq_by_source.get(packet.source_id, -1)
        if packet.packet_seq <= previous_packet_seq:
            raise StoreError("NON_MONOTONIC_PACKET_SEQUENCE")
        if packet.source_policy != self.envelope["manifest"]["source_policy"]:
            raise StoreError("SOURCE_POLICY_MISMATCH")
        payload = {
            "clock_domain_id": packet.clock_domain_id,
            "device_time_ns": packet.device_time_ns,
            "host_received_monotonic_ns": packet.host_received_monotonic_ns,
            "missing_reason_code": packet.missing_reason_code,
            "packet_seq": packet.packet_seq,
            "payload_base64": (
                None if packet.payload is None else base64.b64encode(packet.payload).decode("ascii")
            ),
            "sample_count": packet.sample_count,
            "source_id": packet.source_id,
            "source_policy": packet.source_policy,
        }
        privacy_lint(payload)
        receipt = self._append("l0", "raw_packet", payload, packet.host_received_monotonic_ns)
        self._raw_seq_by_source[packet.source_id] = packet.packet_seq
        stream = self._streams["l0"]
        elapsed = packet.host_received_monotonic_ns - stream.last_sync_ns
        if (
            stream.unsynced_bytes >= self.store_config.l0_flush_bytes
            or elapsed >= self.store_config.l0_flush_interval_ms * 1_000_000
        ):
            self._sync(stream)
        self._rollover_if_needed(stream)
        self._maybe_checkpoint(packet.host_received_monotonic_ns)
        return AppendReceipt(
            receipt.stream,
            receipt.record_id,
            receipt.stream_seq,
            receipt.record_hash,
            stream.unsynced_bytes == 0,
        )

    def append_l1(
        self, record_type: str, payload: Mapping[str, Any], now_ns: int
    ) -> AppendReceipt:
        self._require_open()
        if not isinstance(record_type, str) or not record_type:
            raise StoreError("L1_RECORD_INVALID", "$.record_type")
        privacy_lint(dict(payload))
        receipt = self._append("l1", record_type, dict(payload), now_ns)
        self._sync(self._streams["l1"])
        self._rollover_if_needed(self._streams["l1"])
        self._maybe_checkpoint(now_ns)
        return AppendReceipt(
            receipt.stream,
            receipt.record_id,
            receipt.stream_seq,
            receipt.record_hash,
            True,
        )

    def _append(
        self, stream_name: str, record_type: str, payload: Mapping[str, Any], now_ns: int
    ) -> AppendReceipt:
        if isinstance(now_ns, bool) or not isinstance(now_ns, int) or now_ns < 0:
            raise StoreError("INVALID_MONOTONIC_TIME")
        stream = self._streams[stream_name]
        sequence = stream.seq + 1
        body = {
            "previous_hash": stream.tail_hash,
            "record_id": f"{stream_name}:{sequence:012d}",
            "record_type": record_type,
            "recorded_monotonic_ns": now_ns,
            "segment_index": stream.segment_index,
            "session_key": self.envelope["session_key"],
            "storage_schema_version": self.store_config.storage_schema_version,
            "stream": stream_name,
            "stream_seq": sequence,
            "payload": dict(payload),
        }
        record_hash = domain_hash(_RECORD_DOMAIN, body)
        record = dict(body, record_hash=record_hash)
        encoded = canonical_bytes(record) + b"\n"
        if len(encoded) > self.store_config.max_record_bytes:
            raise StoreError("RECORD_TOO_LARGE")
        try:
            stream.handle.write(encoded)
        except OSError as error:
            raise StoreError("STORAGE_APPEND_FAILED") from error
        stream.seq = sequence
        stream.tail_hash = record_hash
        stream.unsynced_bytes += len(encoded)
        return AppendReceipt(stream_name, body["record_id"], sequence, record_hash, False)

    def checkpoint(self, now_ns: int) -> CheckpointReceipt:
        self._require_open()
        for stream in self._streams.values():
            self._sync(stream)
        self._checkpoint_seq += 1
        body = {
            "checkpoint_id": f"checkpoint-{self._checkpoint_seq:06d}",
            "created_monotonic_ns": now_ns,
            "l0_seq": self._streams["l0"].seq,
            "l0_tail_hash": self._streams["l0"].tail_hash,
            "l1_seq": self._streams["l1"].seq,
            "l1_tail_hash": self._streams["l1"].tail_hash,
            "storage_schema_version": self.store_config.storage_schema_version,
        }
        checkpoint_hash = domain_hash(_CHECKPOINT_DOMAIN, body)
        payload = dict(body, checkpoint_hash=checkpoint_hash)
        path = self.path / "checkpoints" / f"checkpoint-{self._checkpoint_seq:06d}.json"
        _exclusive_json(path, payload)
        self._last_checkpoint_ns = now_ns
        return CheckpointReceipt(body["checkpoint_id"], path, checkpoint_hash)

    def seal(self, summary: Mapping[str, Any] | Any, now_ns: int) -> SessionSeal:
        self._require_open()
        summary_payload = mapping(summary)
        reason_code = str(
            summary_payload.get("reason_code")
            or summary_payload.get("status")
            or "SEALED"
        )
        existing_l1, existing_reasons = ReplayReader(
            self.path, self.envelope
        )._scan_stream(
            "l1",
            mode="recover" if reason_code == "PROCESS_INTERRUPTED" else "strict",
            acknowledged_segments=self._acknowledged_unclean_segments,
        )
        if "INTEGRITY_MISMATCH" in existing_reasons:
            raise StoreError("INTEGRITY_MISMATCH")
        finish_outputs = [
            record["payload"].get("output", {})
            for record in existing_l1
            if record.get("record_type") == "operation_commit"
            and record["payload"].get("method") == "finish"
        ]
        if reason_code == "PROCESS_INTERRUPTED":
            interruption_events = [
                record
                for record in existing_l1
                if record.get("record_type") == "storage_event"
                and record["payload"].get("event_type") == "PROCESS_INTERRUPTED"
            ]
            if finish_outputs or not interruption_events:
                raise StoreError("INTERRUPTION_EVIDENCE_INVALID")
            evidence_scope = "INTERRUPTION_RECOVERY"
        elif finish_outputs:
            if (
                len(finish_outputs) != 1
                or finish_outputs[0].get("output_type") != "SessionSummary"
                or finish_outputs[0].get("value") != summary_payload
            ):
                raise StoreError("SESSION_SUMMARY_MISMATCH")
            evidence_scope = "SESSION_REPLAY"
        elif self.formal_capable:
            raise StoreError("FINISH_COMMIT_REQUIRED")
        else:
            evidence_scope = "DEVELOPMENT_STORAGE_ONLY"
        self.append_l1("session_summary", summary_payload, now_ns)
        self.checkpoint(now_ns)
        for stream in self._streams.values():
            self._sync(stream)
        files = []
        for name, pattern in (
            ("l0", "segment-*.jsonl"),
            ("l1", "segment-*.jsonl"),
            ("checkpoints", "checkpoint-*.json"),
            ("tails", "*.json"),
        ):
            for path in sorted((self.path / name).glob(pattern)):
                files.append(
                    {
                        "path": path.relative_to(self.path).as_posix(),
                        "sha256": file_sha256(path),
                        "size_bytes": path.stat().st_size,
                    }
                )
        body = {
            "acknowledged_unclean_segments": list(self._acknowledged_unclean_segments),
            "archive_hash": file_sha256(self.path / "archive.json"),
            "created_monotonic_ns": now_ns,
            "evidence_scope": evidence_scope,
            "files": files,
            "final_state_hash": domain_hash(b"srp:p02:final-state:v1\0", summary_payload),
            "l0_count": self._streams["l0"].seq,
            "l0_tail_hash": self._streams["l0"].tail_hash,
            "l1_count": self._streams["l1"].seq,
            "l1_tail_hash": self._streams["l1"].tail_hash,
            "manifest_hash": self.manifest_hash,
            "reason_code": reason_code,
            "store_config_hash": self.store_config.config_hash,
        }
        seal_hash = domain_hash(_SEAL_DOMAIN, body)
        path = self.path / "seal.json"
        _exclusive_json(path, dict(body, seal_hash=seal_hash))
        self._sealed = True
        return SessionSeal(path, seal_hash, body["final_state_hash"], reason_code)

    @classmethod
    def recover_interrupted(
        cls,
        root: Path,
        session_id: str,
        *,
        now_ns: int,
        store_config: StoreConfig | None = None,
    ) -> SessionSeal:
        path = Path(root) / "sessions" / session_key(session_id)
        config = store_config or load_store_config()
        lock = _WriterLock(path / "writer.lock")
        if not (path / "archive.json").is_file():
            raise StoreError("ARCHIVE_UNAVAILABLE")
        lock.acquire()
        baseline_files = {
            item.relative_to(path).as_posix(): item.read_bytes()
            for item in path.rglob("*")
            if item.is_file() and item.name != "writer.lock"
        }
        recovered = False
        try:
            reader = ReplayReader.open(root, session_id)
            report = reader.verify(mode="recover")
            if "INTEGRITY_MISMATCH" in report.reason_codes:
                raise StoreError("INTEGRITY_MISMATCH")
            if not report.recoverable or report.sealed:
                raise StoreError("RECOVERY_NOT_AVAILABLE")
            envelope = reader.envelope
            if envelope.get("store_config_hash") != config.config_hash:
                raise StoreError("STORE_CONFIG_MISMATCH")
            states = reader.stream_states(mode="recover")
            streams = {}
            for name in ("l0", "l1"):
                next_segment = len(list((path / name).glob("segment-*.jsonl"))) + 1
                stream = cls._create_stream(path, name, next_segment)
                stream.seq = states[name]["seq"]
                stream.tail_hash = states[name]["tail_hash"]
                stream.anchored_seq = states[name]["anchored_seq"]
                stream.last_sync_ns = now_ns
                streams[name] = stream
            archive = cls(
                path,
                envelope,
                config,
                lock,
                streams,
                acknowledged_unclean_segments=tuple(reader.unclean_segments),
            )
            archive.append_l1(
                "storage_event",
                {"event_type": "PROCESS_INTERRUPTED", "reason_code": "PROCESS_INTERRUPTED"},
                now_ns,
            )
            result = archive.seal(
                {"status": "ABORTED", "reason_code": "PROCESS_INTERRUPTED"},
                now_ns,
            )
            recovered = True
            return result
        finally:
            if "archive" in locals():
                archive.close()
            else:
                lock.release()
            if not recovered:
                current_files = {
                    item.relative_to(path).as_posix(): item
                    for item in path.rglob("*")
                    if item.is_file() and item.name != "writer.lock"
                }
                for relative, item in current_files.items():
                    if relative not in baseline_files:
                        item.unlink(missing_ok=True)
                for relative, content in baseline_files.items():
                    target = path / relative
                    if not target.is_file() or target.read_bytes() != content:
                        target.write_bytes(content)

    def _maybe_checkpoint(self, now_ns: int) -> None:
        if now_ns - self._last_checkpoint_ns >= self.store_config.checkpoint_interval_ms * 1_000_000:
            self.checkpoint(now_ns)

    @staticmethod
    def _validate_raw_packet(packet: RawPacket) -> None:
        if (
            not isinstance(packet.source_id, str)
            or packet.source_id not in _RAW_SOURCE_IDS
            or packet.source_policy not in {"real", "replay", "mock"}
            or isinstance(packet.packet_seq, bool)
            or not isinstance(packet.packet_seq, int)
            or packet.packet_seq < 0
            or isinstance(packet.host_received_monotonic_ns, bool)
            or not isinstance(packet.host_received_monotonic_ns, int)
            or packet.host_received_monotonic_ns < 0
            or not isinstance(packet.clock_domain_id, str)
            or not packet.clock_domain_id
            or isinstance(packet.sample_count, bool)
            or not isinstance(packet.sample_count, int)
            or packet.sample_count < 0
        ):
            raise StoreError("RAW_PACKET_INVALID")
        if packet.device_time_ns is not None and (
            isinstance(packet.device_time_ns, bool)
            or not isinstance(packet.device_time_ns, int)
            or packet.device_time_ns < 0
        ):
            raise StoreError("RAW_PACKET_INVALID")
        if packet.payload is None:
            if packet.sample_count != 0 or not packet.missing_reason_code:
                raise StoreError("RAW_PACKET_INVALID")
        elif (
            not isinstance(packet.payload, bytes)
            or packet.sample_count <= 0
            or packet.missing_reason_code is not None
        ):
            raise StoreError("RAW_PACKET_INVALID")

    def _sync(self, stream: _Stream) -> None:
        try:
            stream.handle.flush()
            os.fsync(stream.handle.fileno())
        except OSError as error:
            raise StoreError("STORAGE_SYNC_FAILED") from error
        stream.unsynced_bytes = 0
        if stream.seq != stream.anchored_seq:
            body = {
                "session_key": self.envelope["session_key"],
                "stream": stream.name,
                "stream_seq": stream.seq,
                "tail_hash": stream.tail_hash,
            }
            _atomic_json(
                self.path / "tails" / f"{stream.name}.json",
                dict(body, tail_state_hash=domain_hash(_TAIL_STATE_DOMAIN, body)),
            )
            stream.anchored_seq = stream.seq

    def _rollover_if_needed(self, stream: _Stream) -> None:
        if stream.handle.tell() < self.store_config.segment_max_bytes:
            return
        if stream.unsynced_bytes:
            self._sync(stream)
        stream.handle.close()
        replacement = self._create_stream(
            self.path, stream.name, stream.segment_index + 1
        )
        replacement.seq = stream.seq
        replacement.tail_hash = stream.tail_hash
        replacement.last_sync_ns = stream.last_sync_ns
        replacement.anchored_seq = stream.anchored_seq
        self._streams[stream.name] = replacement

    def _require_open(self) -> None:
        if self._sealed:
            raise StoreError("SESSION_SEALED")

    def close(self) -> None:
        for stream in self._streams.values():
            if not stream.handle.closed:
                try:
                    self._sync(stream)
                finally:
                    stream.handle.close()
        self._lock.release()


class ReplayReader:
    def __init__(self, path: Path, envelope: dict[str, Any]) -> None:
        self.path = path
        self.envelope = envelope
        self.unclean_segments: list[str] = []

    @classmethod
    def open(cls, root: Path, session_id: str) -> "ReplayReader":
        path = Path(root) / "sessions" / session_key(session_id)
        try:
            envelope = json.loads((path / "archive.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise StoreError("ARCHIVE_UNAVAILABLE") from error
        if envelope.get("session_key") != session_key(session_id):
            raise StoreError("ARCHIVE_SESSION_MISMATCH")
        return cls(path, envelope)

    def _seal(self) -> dict[str, Any] | None:
        path = self.path / "seal.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"invalid": True}

    def _scan_stream(
        self,
        name: str,
        *,
        mode: str,
        acknowledged_segments: tuple[str, ...] = (),
    ) -> tuple[list[dict[str, Any]], list[str]]:
        records: list[dict[str, Any]] = []
        reasons: list[str] = []
        expected_seq = 1
        previous_hash = _ZERO_HASH
        seal = self._seal() or {}
        acknowledged = set(seal.get("acknowledged_unclean_segments", []))
        acknowledged.update(acknowledged_segments)
        segments = sorted((self.path / name).glob("segment-*.jsonl"))
        for segment_position, segment in enumerate(segments):
            relative = segment.relative_to(self.path).as_posix()
            try:
                expected_segment_index = int(segment.stem.removeprefix("segment-"))
            except ValueError:
                reasons.append("INTEGRITY_MISMATCH")
                continue
            raw = segment.read_bytes()
            lines = raw.splitlines(keepends=True)
            for index, line in enumerate(lines):
                if not line.endswith(b"\n"):
                    self.unclean_segments.append(relative)
                    is_final_segment = segment_position == len(segments) - 1
                    if relative in acknowledged or (is_final_segment and mode == "recover"):
                        reasons.append("UNCLEAN_TAIL")
                        break
                    reasons.append("INTEGRITY_MISMATCH")
                    break
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    reasons.append("INTEGRITY_MISMATCH")
                    break
                if not isinstance(record, dict):
                    reasons.append("INTEGRITY_MISMATCH")
                    break
                actual_hash = record.get("record_hash")
                body = {key: value for key, value in record.items() if key != "record_hash"}
                if (
                    record.get("stream") != name
                    or record.get("stream_seq") != expected_seq
                    or record.get("segment_index") != expected_segment_index
                    or record.get("session_key") != self.envelope.get("session_key")
                    or record.get("storage_schema_version") != "1.0"
                    or record.get("previous_hash") != previous_hash
                    or actual_hash != domain_hash(_RECORD_DOMAIN, body)
                ):
                    reasons.append("INTEGRITY_MISMATCH")
                    break
                records.append(record)
                expected_seq += 1
                previous_hash = str(actual_hash)
        return records, reasons

    def _tail_state(self, name: str) -> dict[str, Any] | None:
        path = self.path / "tails" / f"{name}.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        expected_keys = {
            "session_key",
            "stream",
            "stream_seq",
            "tail_hash",
            "tail_state_hash",
        }
        if not isinstance(value, dict) or set(value) != expected_keys:
            return None
        body = {key: item for key, item in value.items() if key != "tail_state_hash"}
        if (
            value.get("session_key") != self.envelope.get("session_key")
            or value.get("stream") != name
            or isinstance(value.get("stream_seq"), bool)
            or not isinstance(value.get("stream_seq"), int)
            or value["stream_seq"] < 0
            or _HASH_VALUE.fullmatch(str(value.get("tail_hash"))) is None
            or value.get("tail_state_hash") != domain_hash(_TAIL_STATE_DOMAIN, body)
        ):
            return None
        return value

    def stream_states(self, *, mode: str = "strict") -> dict[str, dict[str, Any]]:
        states = {}
        for name in ("l0", "l1"):
            records, reasons = self._scan_stream(name, mode=mode)
            if "INTEGRITY_MISMATCH" in reasons:
                raise StoreError("INTEGRITY_MISMATCH")
            tail_state = self._tail_state(name)
            if tail_state is None or tail_state["stream_seq"] > len(records):
                raise StoreError("INTEGRITY_MISMATCH")
            anchored_seq = tail_state["stream_seq"]
            anchored_hash = (
                _ZERO_HASH if anchored_seq == 0 else records[anchored_seq - 1]["record_hash"]
            )
            if tail_state["tail_hash"] != anchored_hash:
                raise StoreError("INTEGRITY_MISMATCH")
            states[name] = {
                "seq": len(records),
                "tail_hash": records[-1]["record_hash"] if records else _ZERO_HASH,
                "anchored_seq": anchored_seq,
            }
        return states

    def verify(self, mode: str = "strict") -> IntegrityReport:
        if mode not in {"strict", "recover"}:
            raise StoreError("VERIFY_MODE_INVALID")
        self.unclean_segments = []
        reasons: list[str] = []
        streams: dict[str, list[dict[str, Any]]] = {}
        for name in ("l0", "l1"):
            records, stream_reasons = self._scan_stream(name, mode=mode)
            streams[name] = records
            reasons.extend(stream_reasons)
        seal = self._seal()
        sealed = seal is not None
        if not _envelope_is_valid(self.envelope):
            reasons.append("INTEGRITY_MISMATCH")
        expected_manifest_hash = domain_hash(
            _MANIFEST_DOMAIN, self.envelope.get("manifest")
        )
        if self.envelope.get("manifest_hash") != expected_manifest_hash:
            reasons.append("INTEGRITY_MISMATCH")
        envelope_body = {
            key: value for key, value in self.envelope.items() if key != "envelope_hash"
        }
        if self.envelope.get("envelope_hash") != domain_hash(
            _ENVELOPE_DOMAIN, envelope_body
        ):
            reasons.append("INTEGRITY_MISMATCH")
        if seal is not None:
            if seal.get("invalid"):
                reasons.append("INTEGRITY_MISMATCH")
            else:
                seal_hash = seal.get("seal_hash")
                body = {key: value for key, value in seal.items() if key != "seal_hash"}
                if seal_hash != domain_hash(_SEAL_DOMAIN, body):
                    reasons.append("INTEGRITY_MISMATCH")
                if seal.get("archive_hash") != file_sha256(self.path / "archive.json"):
                    reasons.append("INTEGRITY_MISMATCH")
                for item in seal.get("files", []):
                    file_path = self.path / str(item.get("path", ""))
                    if (
                        not file_path.is_file()
                        or file_sha256(file_path) != item.get("sha256")
                        or file_path.stat().st_size != item.get("size_bytes")
                    ):
                        reasons.append("INTEGRITY_MISMATCH")
                expected_paths = {str(item.get("path", "")) for item in seal.get("files", [])}
                actual_paths = {
                    path.relative_to(self.path).as_posix()
                    for directory, pattern in (
                        ("l0", "segment-*.jsonl"),
                        ("l1", "segment-*.jsonl"),
                        ("checkpoints", "checkpoint-*.json"),
                        ("tails", "*.json"),
                    )
                    for path in (self.path / directory).glob(pattern)
                }
                if actual_paths != expected_paths:
                    reasons.append("INTEGRITY_MISMATCH")
                if (
                    seal.get("l0_count") != len(streams["l0"])
                    or seal.get("l1_count") != len(streams["l1"])
                    or seal.get("l0_tail_hash")
                    != (streams["l0"][-1]["record_hash"] if streams["l0"] else _ZERO_HASH)
                    or seal.get("l1_tail_hash")
                    != (streams["l1"][-1]["record_hash"] if streams["l1"] else _ZERO_HASH)
                    or seal.get("manifest_hash") != self.envelope.get("manifest_hash")
                    or seal.get("store_config_hash")
                    != self.envelope.get("store_config_hash")
                ):
                    reasons.append("INTEGRITY_MISMATCH")
                summaries = [
                    record["payload"]
                    for record in streams["l1"]
                    if record.get("record_type") == "session_summary"
                ]
                if (
                    len(summaries) != 1
                    or not streams["l1"]
                    or streams["l1"][-1].get("record_type") != "session_summary"
                    or seal.get("final_state_hash")
                    != domain_hash(b"srp:p02:final-state:v1\0", summaries[-1] if summaries else {})
                ):
                    reasons.append("INTEGRITY_MISMATCH")
                finish_outputs = [
                    record["payload"].get("output", {})
                    for record in streams["l1"]
                    if record.get("record_type") == "operation_commit"
                    and record["payload"].get("method") == "finish"
                ]
                if finish_outputs and (
                    finish_outputs[-1].get("output_type") != "SessionSummary"
                    or finish_outputs[-1].get("value") != (summaries[-1] if summaries else None)
                ):
                    reasons.append("INTEGRITY_MISMATCH")
                summary = summaries[-1] if summaries else {}
                expected_reason = str(
                    summary.get("reason_code") or summary.get("status") or "SEALED"
                )
                if seal.get("reason_code") != expected_reason:
                    reasons.append("INTEGRITY_MISMATCH")
                evidence_scope = seal.get("evidence_scope")
                interruption_events = [
                    record
                    for record in streams["l1"]
                    if record.get("record_type") == "storage_event"
                    and record["payload"].get("event_type") == "PROCESS_INTERRUPTED"
                ]
                if evidence_scope == "SESSION_REPLAY":
                    if len(finish_outputs) != 1:
                        reasons.append("INTEGRITY_MISMATCH")
                elif evidence_scope == "INTERRUPTION_RECOVERY":
                    if (
                        expected_reason != "PROCESS_INTERRUPTED"
                        or finish_outputs
                        or not interruption_events
                    ):
                        reasons.append("INTEGRITY_MISMATCH")
                elif evidence_scope == "DEVELOPMENT_STORAGE_ONLY":
                    if self.envelope.get("formal_capable") or finish_outputs:
                        reasons.append("INTEGRITY_MISMATCH")
                else:
                    reasons.append("INTEGRITY_MISMATCH")
        else:
            reasons.append("UNSEALED_ARCHIVE")
        for name in ("l0", "l1"):
            tail_state = self._tail_state(name)
            if tail_state is None or tail_state["stream_seq"] > len(streams[name]):
                reasons.append("INTEGRITY_MISMATCH")
                continue
            anchored_seq = tail_state["stream_seq"]
            expected_tail = (
                _ZERO_HASH
                if anchored_seq == 0
                else streams[name][anchored_seq - 1]["record_hash"]
            )
            if tail_state["tail_hash"] != expected_tail:
                reasons.append("INTEGRITY_MISMATCH")
            if sealed and anchored_seq != len(streams[name]):
                reasons.append("INTEGRITY_MISMATCH")
        checkpoints = sorted((self.path / "checkpoints").glob("checkpoint-*.json"))
        for checkpoint_index, checkpoint in enumerate(checkpoints, start=1):
            expected_id = f"checkpoint-{checkpoint_index:06d}"
            if checkpoint.name != f"{expected_id}.json":
                reasons.append("INTEGRITY_MISMATCH")
            try:
                value = json.loads(checkpoint.read_text(encoding="utf-8"))
                checkpoint_hash = value.pop("checkpoint_hash")
            except (OSError, json.JSONDecodeError, KeyError, AttributeError):
                reasons.append("INTEGRITY_MISMATCH")
                continue
            if value.get("checkpoint_id") != expected_id:
                reasons.append("INTEGRITY_MISMATCH")
            if checkpoint_hash != domain_hash(_CHECKPOINT_DOMAIN, value):
                reasons.append("INTEGRITY_MISMATCH")
            for stream_name in ("l0", "l1"):
                sequence = value.get(f"{stream_name}_seq")
                if not isinstance(sequence, int) or sequence < 0 or sequence > len(streams[stream_name]):
                    reasons.append("INTEGRITY_MISMATCH")
                    continue
                expected_tail = (
                    _ZERO_HASH
                    if sequence == 0
                    else streams[stream_name][sequence - 1]["record_hash"]
                )
                if value.get(f"{stream_name}_tail_hash") != expected_tail:
                    reasons.append("INTEGRITY_MISMATCH")
        integrity_failure = "INTEGRITY_MISMATCH" in reasons
        valid = not integrity_failure and (sealed or mode == "recover")
        recoverable = not integrity_failure and not sealed
        return IntegrityReport(
            valid=valid,
            sealed=sealed,
            recoverable=recoverable,
            reason_codes=tuple(dict.fromkeys(reasons)),
            l0_count=len(streams["l0"]),
            l1_count=len(streams["l1"]),
            final_state_hash=None if seal is None else seal.get("final_state_hash"),
        )

    def _iter_records(self, name: str) -> Iterator[dict[str, Any]]:
        records, reasons = self._scan_stream(name, mode="strict")
        if "INTEGRITY_MISMATCH" in reasons:
            raise StoreError("INTEGRITY_MISMATCH")
        yield from records

    def iter_l0(self, source_id: str | None = None) -> Iterator[RawPacket]:
        for record in self._iter_records("l0"):
            if record["record_type"] != "raw_packet":
                continue
            payload = record["payload"]
            if source_id is not None and payload["source_id"] != source_id:
                continue
            encoded = payload["payload_base64"]
            yield RawPacket(
                source_id=payload["source_id"],
                source_policy=payload["source_policy"],
                packet_seq=payload["packet_seq"],
                device_time_ns=payload["device_time_ns"],
                host_received_monotonic_ns=payload["host_received_monotonic_ns"],
                clock_domain_id=payload["clock_domain_id"],
                sample_count=payload["sample_count"],
                payload=None if encoded is None else base64.b64decode(encoded, validate=True),
                missing_reason_code=payload["missing_reason_code"],
            )

    def iter_l1(self, record_type: str | None = None) -> Iterator[dict[str, Any]]:
        for record in self._iter_records("l1"):
            if record_type is None or record["record_type"] == record_type:
                yield record
