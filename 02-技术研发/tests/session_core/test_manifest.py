from __future__ import annotations

from copy import deepcopy

import pytest

from srp_session_core import SessionCore, SessionCoreError, SessionStatus

from .helpers import formal_dependencies


def test_valid_manifest_runs_contract_privacy_and_ordered_gates(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()

    update = core.prepare(manifest, assignment_factory(manifest), 0)

    assert update.snapshot.status is SessionStatus.PREPARED
    assert [receipt.gate for receipt in update.gate_receipts] == [
        "privacy",
        "assignment",
        "manifest_store",
        "formal_readiness",
    ]
    assert update.control_events[0]["event_type"] == "prepare"
    assert update.control_events[0]["payload"]["sequence_mode"] == "fixed"


def test_privacy_lint_sees_unknown_contact_field_before_contract_filter(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    manifest["phone_hash"] = "not-a-phone"

    with pytest.raises(SessionCoreError) as error:
        SessionCore().prepare(manifest, assignment_factory(manifest), 0)

    assert error.value.code == "PRIVACY_FORBIDDEN_MANIFEST_KEY"
    assert error.value.detail == "$.phone_hash"
    assert "not-a-phone" not in str(error.value)


@pytest.mark.parametrize(
    ("segment", "value"),
    [
        ("demo", 23.999),
        ("demo", 30.001),
        ("closed_loop", 139.999),
        ("closed_loop", 160.001),
        ("lock_transition", 19.999),
        ("lock_transition", 30.001),
    ],
)
def test_duration_outside_candidate_range_fails_closed(
    manifest_factory, assignment_factory, segment, value
) -> None:
    manifest = manifest_factory()
    manifest["module_durations"][segment] = value

    with pytest.raises(SessionCoreError) as error:
        SessionCore().prepare(manifest, assignment_factory(manifest), 0)

    assert error.value.code == "DURATION_OUT_OF_RANGE"
    assert error.value.detail == segment


def test_assignment_must_match_manifest(manifest_factory, assignment_factory) -> None:
    manifest = manifest_factory()
    assignment = assignment_factory(manifest)
    wrong = deepcopy(assignment)
    object.__setattr__(wrong, "allocation_index", 8)

    with pytest.raises(SessionCoreError) as error:
        SessionCore().prepare(manifest, wrong, 0)

    assert error.value.code == "ASSIGNMENT_INDEX_MISMATCH"


def test_formal_default_dependencies_fail_closed(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory(runtime_mode="formal_stage_1")

    with pytest.raises(SessionCoreError) as error:
        SessionCore().prepare(manifest, assignment_factory(manifest), 0)

    assert error.value.code == "FORMAL_GATE_UNAVAILABLE"
    assert error.value.detail == "assignment_gate"


def test_formal_fixture_can_reach_prepared_with_all_real_gates(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory(runtime_mode="formal_stage_1")
    core = SessionCore(dependencies=formal_dependencies())

    update = core.prepare(manifest, assignment_factory(manifest), 0)

    assert update.snapshot.status is SessionStatus.PREPARED
    assert all(receipt.formal_capable for receipt in update.gate_receipts)


def test_stage_three_frozen_policy_requires_contract_v22(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory(
        study_stage="stage_3",
        runtime_mode="formal_stage_3",
        cue_mode="scene_native",
        assignment_arm="frozen_policy",
    )
    manifest["strategy_version"] = "policy-1"

    with pytest.raises(SessionCoreError) as error:
        SessionCore(dependencies=formal_dependencies()).prepare(
            manifest, assignment_factory(manifest), 0
        )

    assert error.value.code == "ADAPTIVE_SEQUENCE_REQUIRES_V2_2"


def test_policy_decisions_must_match_each_position(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    assignment = assignment_factory(manifest)
    decisions = [dict(item) for item in assignment.policy_decisions]
    decisions[1]["selected_action"] = "fade"
    object.__setattr__(assignment, "policy_decisions", tuple(decisions))

    with pytest.raises(SessionCoreError) as error:
        SessionCore().prepare(manifest, assignment, 0)

    assert error.value.code in {"CONTRACT_ILLEGAL_SELECTED_ACTION", "POLICY_ACTION_MISMATCH"}
