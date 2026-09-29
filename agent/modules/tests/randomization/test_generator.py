from __future__ import annotations

from collections import Counter
from dataclasses import replace
import hashlib
from itertools import permutations
import json

from srp_randomization import generate_list, policy_decisions, verify_plan
from srp_randomization.errors import RandomizationError
import pytest


WEATHERS = ("storm", "heat", "snow", "fade")


def test_stage_1_complete_block_contains_every_sequence_once_per_condition() -> None:
    plan = generate_list(
        stage="stage_1",
        strata=("na_pre_low",),
        block_count=2,
        seed=b"stage-1-test-seed",
    )

    assert len(plan.records) == 96
    expected = set(permutations(WEATHERS))
    for block in (1, 2):
        records = [record for record in plan.records if record.block == block]
        assert len(records) == 48
        by_arm = {
            arm: {record.weather_sequence for record in records if record.arm == arm}
            for arm in ("scene_native", "abstract_pacer")
        }
        assert by_arm == {"scene_native": expected, "abstract_pacer": expected}


def test_lists_are_deterministic_and_stage_independent() -> None:
    first = generate_list("stage_1", ("all",), 1, b"same-held-seed-01")
    repeated = generate_list("stage_1", ("all",), 1, b"same-held-seed-01")
    other_stage = generate_list("stage_3", ("all",), 1, b"same-held-seed-01")

    assert first.to_dict() == repeated.to_dict()
    assert first.list_hash == repeated.list_hash
    assert first.list_hash != other_stage.list_hash
    assert first.seed_commitment != other_stage.seed_commitment
    assert "same-held-seed-01" not in str(first.to_dict())


def test_stage_3_has_independent_balanced_random_and_frozen_policy_arms() -> None:
    plan = generate_list("stage_3", ("all",), 1, b"stage-3-test-seed")
    counts = Counter(record.arm for record in plan.records)

    assert counts == {"balanced_random": 24, "frozen_policy": 24}
    random_sequences = {
        record.weather_sequence
        for record in plan.records
        if record.arm == "balanced_random"
    }
    assert random_sequences == set(permutations(WEATHERS))
    assert all(
        record.weather_sequence is None
        for record in plan.records
        if record.arm == "frozen_policy"
    )


def test_policy_decisions_reconstruct_uniform_without_replacement_probability() -> None:
    sequence = ("fade", "storm", "snow", "heat")
    decisions = policy_decisions(
        session_id="S-X01-0001",
        stage="stage_1",
        sequence=sequence,
        created_monotonic_ns=100,
    )

    assert [item["selected_action"] for item in decisions] == list(sequence)
    assert [item["behavior_probability"] for item in decisions] == [0.25, 1 / 3, 0.5, 1.0]
    assert [len(item["candidate_actions"]) for item in decisions] == [4, 3, 2, 1]
    assert all(0 <= item["random_draw"] <= 1 for item in decisions)


def test_stage_3_frozen_policy_assignment_waits_for_x03_sequence() -> None:
    plan = generate_list("stage_3", ("all",), 1, b"frozen-policy-seed-01")
    frozen = next(record for record in plan.records if record.arm == "frozen_policy")
    from srp_randomization.models import AllocationReceipt

    receipt = AllocationReceipt(
        allocation_index=frozen.allocation_index,
        stage=frozen.stage,
        stratum=frozen.stratum,
        block=frozen.block,
        arm=frozen.arm,
        weather_sequence=frozen.weather_sequence,
        arm_behavior_probability=frozen.arm_behavior_probability,
        randomization_list_hash=plan.list_hash,
        randomization_version=plan.randomization_version,
        permit_id="PERMIT-X03",
        reservation_id="RES-X03",
        evidence_id="X01E-X03",
    )
    with pytest.raises(RuntimeError, match="FROZEN_POLICY_SEQUENCE_REQUIRES_X03"):
        receipt.to_assignment_bundle("S-X03", 0)


def test_complete_blocks_must_be_contiguous_in_allocation_order() -> None:
    plan = generate_list("stage_1", ("all",), 2, b"block-order-seed-01")
    reordered = tuple(
        replace(record, allocation_index=index)
        for index, record in enumerate(
            sorted(plan.records, key=lambda item: (item.arm, item.block)), start=1
        )
    )
    candidate = replace(plan, records=reordered)
    encoded = json.dumps(
        candidate.unsigned_dict(),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    candidate = replace(
        candidate, list_hash=f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    )
    with pytest.raises(RandomizationError, match="BLOCK_SEQUENCE_INVALID"):
        verify_plan(candidate)
