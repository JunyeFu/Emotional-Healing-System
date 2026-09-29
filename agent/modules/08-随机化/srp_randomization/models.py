from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AllocationRecord:
    allocation_index: int
    stage: str
    stratum: str
    block: int
    arm: str
    weather_sequence: tuple[str, ...] | None
    arm_behavior_probability: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "allocation_index": self.allocation_index,
            "stage": self.stage,
            "stratum": self.stratum,
            "block": self.block,
            "arm": self.arm,
            "weather_sequence": (
                list(self.weather_sequence) if self.weather_sequence is not None else None
            ),
            "arm_behavior_probability": self.arm_behavior_probability,
        }


@dataclass(frozen=True)
class RandomizationPlan:
    schema_version: str
    randomization_version: str
    stage: str
    block_size: int
    seed_commitment: str
    records: tuple[AllocationRecord, ...]
    list_hash: str

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "randomization_version": self.randomization_version,
            "stage": self.stage,
            "block_size": self.block_size,
            "seed_commitment": self.seed_commitment,
            "records": [record.to_dict() for record in self.records],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_dict(), "list_hash": self.list_hash}


@dataclass(frozen=True)
class GateEvidence:
    gate: str
    reservation_id: str
    evidence_id: str
    passed: bool


@dataclass(frozen=True)
class AllocationRequest:
    request_id: str
    stage: str
    stratum: str
    reservation_id: str
    expected_randomization_version: str


@dataclass(frozen=True)
class AllocationReceipt:
    allocation_index: int
    stage: str
    stratum: str
    block: int
    arm: str
    weather_sequence: tuple[str, ...] | None
    arm_behavior_probability: float
    randomization_list_hash: str
    randomization_version: str
    permit_id: str
    reservation_id: str
    evidence_id: str

    def policy_decisions(
        self, session_id: str, created_monotonic_ns: int
    ) -> tuple[dict[str, Any], ...]:
        if self.weather_sequence is None:
            return ()
        from .generator import policy_decisions

        return policy_decisions(
            session_id=session_id,
            stage=self.stage,
            sequence=self.weather_sequence,
            created_monotonic_ns=created_monotonic_ns,
        )

    def to_assignment_bundle(self, session_id: str, created_monotonic_ns: int) -> Any:
        if self.weather_sequence is None:
            raise RuntimeError("FROZEN_POLICY_SEQUENCE_REQUIRES_X03")
        from srp_session_core.models import AssignmentBundle

        return AssignmentBundle(
            allocation_index=self.allocation_index,
            randomization_list_hash=self.randomization_list_hash,
            weather_sequence=self.weather_sequence,
            policy_decisions=self.policy_decisions(session_id, created_monotonic_ns),
            permit_id=self.permit_id,
            reservation_id=self.reservation_id,
        )


@dataclass(frozen=True)
class BalanceAudit:
    stage: str
    stratum: str
    assigned_count: int
    complete_count: int
    incomplete_count: int
    arm_counts: dict[str, int]
    balanced_by_assignment: bool
    reason_code: str


@dataclass(frozen=True)
class AuditIntegrity:
    valid: bool
    checked_events: int
    reason_code: str
