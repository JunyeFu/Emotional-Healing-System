from __future__ import annotations

import hashlib
import hmac
from itertools import permutations
import json
import re
from typing import Iterable

from .errors import RandomizationError
from .models import AllocationRecord, RandomizationPlan


WEATHERS = ("storm", "heat", "snow", "fade")
SCHEMA_VERSION = "1.0"
RANDOMIZATION_VERSION = "1.0"
BLOCK_SIZE = 48
_SEED_DOMAIN = b"srp:x01:randomization-seed:v1\0"
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _stage_key(stage: str, seed: bytes) -> tuple[bytes, str]:
    context = _SEED_DOMAIN + stage.encode("ascii")
    key = hmac.new(seed, context, hashlib.sha256).digest()
    return key, _sha256(context + b"\0" + key)


def _shuffle_cells(
    cells: list[tuple[str, tuple[str, ...] | None]],
    *,
    key: bytes,
    stage: str,
    stratum: str,
    block: int,
) -> list[tuple[str, tuple[str, ...] | None]]:
    tagged = []
    for index, cell in enumerate(cells):
        arm, sequence = cell
        payload = _canonical_bytes(
            {
                "stage": stage,
                "stratum": stratum,
                "block": block,
                "cell_index": index,
                "arm": arm,
                "sequence": sequence,
            }
        )
        tagged.append((hmac.new(key, payload, hashlib.sha256).digest(), cell))
    tagged.sort(key=lambda item: item[0])
    return [cell for _, cell in tagged]


def _cells(stage: str) -> list[tuple[str, tuple[str, ...] | None]]:
    sequences = list(permutations(WEATHERS))
    if stage == "stage_1":
        return [
            (arm, sequence)
            for arm in ("scene_native", "abstract_pacer")
            for sequence in sequences
        ]
    if stage == "stage_3":
        return [*(('balanced_random', sequence) for sequence in sequences), *(
            ("frozen_policy", None) for _ in range(24)
        )]
    raise RandomizationError("STAGE_UNSUPPORTED", stage)


def generate_list(
    stage: str,
    strata: Iterable[str],
    block_count: int,
    seed: bytes,
) -> RandomizationPlan:
    strata_tuple = tuple(strata)
    if not strata_tuple or any(not item for item in strata_tuple):
        raise RandomizationError("STRATA_REQUIRED")
    if len(set(strata_tuple)) != len(strata_tuple):
        raise RandomizationError("STRATA_DUPLICATED")
    if not isinstance(block_count, int) or block_count < 1:
        raise RandomizationError("BLOCK_COUNT_INVALID")
    if not isinstance(seed, bytes) or len(seed) < 16:
        raise RandomizationError("SEED_TOO_SHORT")

    key, seed_commitment = _stage_key(stage, seed)
    records: list[AllocationRecord] = []
    allocation_index = 1
    for stratum in strata_tuple:
        for block in range(1, block_count + 1):
            cells = _shuffle_cells(
                _cells(stage),
                key=key,
                stage=stage,
                stratum=stratum,
                block=block,
            )
            for arm, sequence in cells:
                records.append(
                    AllocationRecord(
                        allocation_index=allocation_index,
                        stage=stage,
                        stratum=stratum,
                        block=block,
                        arm=arm,
                        weather_sequence=sequence,
                        arm_behavior_probability=0.5,
                    )
                )
                allocation_index += 1

    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "randomization_version": RANDOMIZATION_VERSION,
        "stage": stage,
        "block_size": BLOCK_SIZE,
        "seed_commitment": seed_commitment,
        "records": [record.to_dict() for record in records],
    }
    return RandomizationPlan(
        schema_version=SCHEMA_VERSION,
        randomization_version=RANDOMIZATION_VERSION,
        stage=stage,
        block_size=BLOCK_SIZE,
        seed_commitment=seed_commitment,
        records=tuple(records),
        list_hash=_sha256(_canonical_bytes(unsigned)),
    )


def verify_plan(plan: RandomizationPlan) -> None:
    if plan.schema_version != SCHEMA_VERSION:
        raise RandomizationError("SCHEMA_VERSION_UNSUPPORTED")
    if plan.randomization_version != RANDOMIZATION_VERSION:
        raise RandomizationError("RANDOMIZATION_VERSION_UNSUPPORTED")
    if plan.block_size != BLOCK_SIZE:
        raise RandomizationError("BLOCK_SIZE_MISMATCH")
    if not plan.records:
        raise RandomizationError("RECORDS_REQUIRED")
    if not _HASH.fullmatch(plan.seed_commitment):
        raise RandomizationError("SEED_COMMITMENT_INVALID")
    if _sha256(_canonical_bytes(plan.unsigned_dict())) != plan.list_hash:
        raise RandomizationError("LIST_HASH_MISMATCH")
    if [record.allocation_index for record in plan.records] != list(
        range(1, len(plan.records) + 1)
    ):
        raise RandomizationError("ALLOCATION_INDEX_INVALID")

    grouped: dict[tuple[str, int], list[AllocationRecord]] = {}
    for record in plan.records:
        if record.stage != plan.stage:
            raise RandomizationError("RECORD_STAGE_MISMATCH")
        if record.arm_behavior_probability != 0.5:
            raise RandomizationError("ARM_PROBABILITY_INVALID")
        grouped.setdefault((record.stratum, record.block), []).append(record)
    expected_sequences = set(permutations(WEATHERS))
    for stratum in dict.fromkeys(record.stratum for record in plan.records):
        ordered = [record for record in plan.records if record.stratum == stratum]
        blocks = sorted({record.block for record in ordered})
        if blocks != list(range(1, len(blocks) + 1)) or [
            record.block for record in ordered
        ] != [block for block in blocks for _ in range(BLOCK_SIZE)]:
            raise RandomizationError("BLOCK_SEQUENCE_INVALID")
    for records in grouped.values():
        if len(records) != BLOCK_SIZE:
            raise RandomizationError("INCOMPLETE_BLOCK")
        if plan.stage == "stage_1":
            for arm in ("scene_native", "abstract_pacer"):
                actual = {
                    record.weather_sequence for record in records if record.arm == arm
                }
                if actual != expected_sequences:
                    raise RandomizationError("STAGE_1_BLOCK_UNBALANCED")
        elif plan.stage == "stage_3":
            random_sequences = {
                record.weather_sequence
                for record in records
                if record.arm == "balanced_random"
            }
            frozen = [record for record in records if record.arm == "frozen_policy"]
            if (
                random_sequences != expected_sequences
                or len(frozen) != 24
                or any(record.weather_sequence is not None for record in frozen)
            ):
                raise RandomizationError("STAGE_3_BLOCK_UNBALANCED")


def policy_decisions(
    *,
    session_id: str,
    stage: str,
    sequence: tuple[str, ...],
    created_monotonic_ns: int,
) -> tuple[dict[str, object], ...]:
    if stage not in {"stage_1", "stage_3"}:
        raise RandomizationError("STAGE_UNSUPPORTED", stage)
    if len(sequence) != 4 or set(sequence) != set(WEATHERS):
        raise RandomizationError("SEQUENCE_INVALID")
    remaining = list(WEATHERS)
    decisions: list[dict[str, object]] = []
    for position, selected in enumerate(sequence):
        selected_index = remaining.index(selected)
        probability = 1 / len(remaining)
        identity = _sha256(
            _canonical_bytes(
                {
                    "session_id": session_id,
                    "stage": stage,
                    "position": position,
                    "candidate_actions": remaining,
                    "selected_action": selected,
                }
            )
        )
        decisions.append(
            {
                "schema_version": "2.2",
                "message_type": "policy_decision",
                "decision_id": f"PD-{identity.removeprefix('sha256:')[:24]}",
                "session_id": session_id,
                "stage": stage,
                "position": position,
                "candidate_actions": list(remaining),
                "selected_action": selected,
                "behavior_probability": probability,
                "target_policy_probability": None,
                "state_snapshot_hash": identity,
                "random_draw": (selected_index + 0.5) / len(remaining),
                "reason_code": "BALANCED_LIST_UNIFORM_WITHOUT_REPLACEMENT",
                "fallback_applied": False,
                "fallback_reason": None,
                "policy_version": None,
                "created_monotonic_ns": created_monotonic_ns,
            }
        )
        remaining.remove(selected)
    return tuple(decisions)
