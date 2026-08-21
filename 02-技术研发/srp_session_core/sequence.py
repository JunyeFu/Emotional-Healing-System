from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .contract_adapter import validate_message
from .errors import SessionCoreError
from .models import AssignmentBundle, SessionSnapshot


@dataclass(frozen=True)
class ModuleDecision:
    position: int
    module_id: str
    policy_decision: Mapping[str, Any] | None


@dataclass(frozen=True)
class SequencePlan:
    modules: tuple[str, ...]
    decisions: tuple[Mapping[str, Any] | None, ...]


class SequenceProvider(Protocol):
    def prepare(
        self, manifest: Mapping[str, Any], assignment: AssignmentBundle
    ) -> SequencePlan: ...

    def next(self, position: int, state_snapshot: SessionSnapshot) -> ModuleDecision: ...


class FixedSequenceProvider:
    def __init__(self) -> None:
        self._plan: SequencePlan | None = None

    def prepare(
        self, manifest: Mapping[str, Any], assignment: AssignmentBundle
    ) -> SequencePlan:
        sequence = tuple(manifest["weather_sequence"])
        if assignment.allocation_index != int(manifest["allocation_index"]):
            raise SessionCoreError("ASSIGNMENT_INDEX_MISMATCH")
        if assignment.randomization_list_hash != manifest["randomization_list_hash"]:
            raise SessionCoreError("ASSIGNMENT_LIST_HASH_MISMATCH")
        if assignment.weather_sequence != sequence:
            raise SessionCoreError("ASSIGNMENT_SEQUENCE_MISMATCH")

        stage = str(manifest["study_stage"])
        raw_decisions = assignment.policy_decisions
        if stage in {"stage_1", "stage_3"} and len(raw_decisions) != 4:
            raise SessionCoreError("POLICY_DECISIONS_REQUIRED", stage)
        if stage == "level_c" and raw_decisions:
            raise SessionCoreError("POLICY_DECISIONS_FORBIDDEN", stage)

        decisions: list[Mapping[str, Any] | None] = []
        remaining = list(sequence)
        for position in range(4):
            if not raw_decisions:
                decisions.append(None)
                continue
            decision = validate_message("policy_decision", raw_decisions[position])
            if decision["session_id"] != manifest["session_id"]:
                raise SessionCoreError("POLICY_SESSION_MISMATCH", str(position))
            if int(decision["position"]) != position:
                raise SessionCoreError("POLICY_POSITION_MISMATCH", str(position))
            if decision["stage"] != stage:
                raise SessionCoreError("POLICY_STAGE_MISMATCH", str(position))
            if decision["selected_action"] != sequence[position]:
                raise SessionCoreError("POLICY_ACTION_MISMATCH", str(position))
            if set(decision["candidate_actions"]) != set(remaining):
                raise SessionCoreError("POLICY_CANDIDATES_MISMATCH", str(position))
            remaining.remove(sequence[position])
            decisions.append(decision)

        self._plan = SequencePlan(sequence, tuple(decisions))
        return self._plan

    def next(self, position: int, state_snapshot: SessionSnapshot) -> ModuleDecision:
        del state_snapshot
        if self._plan is None:
            raise SessionCoreError("SEQUENCE_NOT_PREPARED")
        if position < 0 or position >= len(self._plan.modules):
            raise SessionCoreError("SEQUENCE_POSITION_OUT_OF_RANGE", str(position))
        return ModuleDecision(
            position=position,
            module_id=self._plan.modules[position],
            policy_decision=self._plan.decisions[position],
        )
