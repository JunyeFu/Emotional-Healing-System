from __future__ import annotations

from collections.abc import Callable, Mapping

from .errors import RandomizationError
from .models import AllocationRequest, GateEvidence


class SnapshotGateEvidenceVerifier:
    """Development-only verifier for synthetic, already-materialized evidence."""

    formal_capable = False

    def verify_current(
        self, request: AllocationRequest, evidence: tuple[GateEvidence, ...]
    ) -> None:
        del request, evidence


class CurrentGateEvidenceVerifier:
    """Rechecks each opaque gate receipt immediately before a new reveal."""

    def __init__(
        self,
        validators: Mapping[
            str, Callable[[AllocationRequest, GateEvidence], bool]
        ],
        *,
        formal_capable: bool = False,
    ) -> None:
        self._validators = dict(validators)
        self.formal_capable = formal_capable is True

    def verify_current(
        self, request: AllocationRequest, evidence: tuple[GateEvidence, ...]
    ) -> None:
        for item in evidence:
            validator = self._validators.get(item.gate)
            if validator is None:
                raise RandomizationError("GATE_CURRENT_VERIFIER_MISSING", item.gate)
            try:
                valid = validator(request, item)
            except RandomizationError:
                raise
            except Exception as error:
                raise RandomizationError("GATE_CURRENT_CHECK_FAILED", item.gate) from error
            if valid is not True:
                raise RandomizationError("GATE_NO_LONGER_VALID", item.gate)


def gate_evidence_from_dedup(decision: object) -> GateEvidence:
    if getattr(decision, "allowed", None) is not True:
        raise RandomizationError("DEDUP_RESERVATION_REJECTED")
    reservation_id = getattr(decision, "reservation_id", None)
    audit_event_id = getattr(decision, "audit_event_id", None)
    if not reservation_id or not audit_event_id:
        raise RandomizationError("DEDUP_RECEIPT_INVALID")
    return GateEvidence(
        gate="dedup_reservation",
        reservation_id=reservation_id,
        evidence_id=audit_event_id,
        passed=True,
    )
