from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class StoreConfig:
    storage_schema_version: str
    max_record_bytes: int
    l0_flush_interval_ms: int
    l0_flush_bytes: int
    checkpoint_interval_ms: int
    segment_max_bytes: int
    config_hash: str


@dataclass(frozen=True)
class RawPacket:
    source_id: str
    source_policy: str
    packet_seq: int
    device_time_ns: int | None
    host_received_monotonic_ns: int
    clock_domain_id: str
    sample_count: int
    payload: bytes | None
    missing_reason_code: str | None = None


@dataclass(frozen=True)
class AppendReceipt:
    stream: str
    record_id: str
    stream_seq: int
    record_hash: str
    durable: bool


@dataclass(frozen=True)
class CheckpointReceipt:
    checkpoint_id: str
    path: Path
    checkpoint_hash: str


@dataclass(frozen=True)
class SessionSeal:
    path: Path
    seal_hash: str
    final_state_hash: str
    reason_code: str


@dataclass(frozen=True)
class IntegrityReport:
    valid: bool
    sealed: bool
    recoverable: bool
    reason_codes: tuple[str, ...]
    l0_count: int
    l1_count: int
    final_state_hash: str | None


@dataclass(frozen=True)
class ReplayReport:
    valid: bool
    operation_count: int
    expected_final_hash: str
    actual_final_hash: str
    mismatch_operation_ids: tuple[str, ...] = ()


def mapping(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return dict(value)
