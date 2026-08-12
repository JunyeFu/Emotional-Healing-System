from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from srp_governance import GovernanceError
from srp_governance.registry import (
    DedupRegistry,
    Stage,
    check_and_reserve,
    mark_exposed,
    release_before_exposure,
)


SYNTHETIC_PHONE = "+8613800138000"


@pytest.fixture
def registry(tmp_path):
    return DedupRegistry(
        database_path=tmp_path / "dedup" / "dedup_registry.sqlite",
        key_provider=lambda: b"K" * 32,
        allowed_actors={"data-admin"},
    )


def test_new_reservation_exposes_only_opaque_public_fields(registry) -> None:
    decision = check_and_reserve(
        SYNTHETIC_PHONE, Stage.LEVEL_B, "data-admin", registry=registry
    )

    assert decision.allowed is True
    assert decision.reason_code == "NEW"
    assert decision.reservation_id.startswith("RSV-")
    assert decision.audit_event_id.startswith("AUD-")
    assert decision.token_version == 1
    assert set(decision.__dict__) == {
        "allowed", "reason_code", "reservation_id", "audit_event_id", "token_version"
    }
    assert SYNTHETIC_PHONE not in repr(decision)


@pytest.mark.parametrize(
    ("first_stage", "next_stage"),
    [
        (Stage.LEVEL_B, Stage.STAGE_3),
        (Stage.LEVEL_C, Stage.STAGE_1),
        (Stage.STAGE_1, Stage.STAGE_1),
        (Stage.STAGE_3, Stage.LEVEL_B),
    ],
)
def test_active_reservation_blocks_any_stage(registry, first_stage, next_stage) -> None:
    check_and_reserve(SYNTHETIC_PHONE, first_stage, "data-admin", registry=registry)

    blocked = check_and_reserve(
        SYNTHETIC_PHONE, next_stage, "data-admin", registry=registry
    )

    assert blocked.allowed is False
    assert blocked.reason_code == "ACTIVE_RESERVATION"
    assert blocked.reservation_id is None


def test_release_before_exposure_allows_a_new_stage_reservation(registry) -> None:
    first = check_and_reserve(
        SYNTHETIC_PHONE, Stage.LEVEL_B, "data-admin", registry=registry
    )
    release_before_exposure(
        first.reservation_id, "SYNTHETIC_CANCEL", "data-admin", registry=registry
    )

    second = check_and_reserve(
        SYNTHETIC_PHONE, Stage.STAGE_1, "data-admin", registry=registry
    )

    assert second.allowed is True
    assert second.reason_code == "NEW"
    assert second.reservation_id != first.reservation_id


@pytest.mark.parametrize(
    "reason",
    ["cancelled", "CALL_+8613912345678", "HAS SPACE", "A" * 65],
)
def test_release_reason_rejects_free_text_before_writing_audit(registry, reason) -> None:
    first = check_and_reserve(
        SYNTHETIC_PHONE, Stage.LEVEL_B, "data-admin", registry=registry
    )
    audit_before = registry.verify_audit_chain().checked_events

    with pytest.raises(GovernanceError) as error:
        release_before_exposure(
            first.reservation_id, reason, "data-admin", registry=registry
        )

    assert error.value.code == "INVALID_RELEASE_REASON"
    assert registry.verify_audit_chain().checked_events == audit_before
    assert "+8613912345678" not in registry.database_path.read_bytes().decode(
        "utf-8", errors="ignore"
    )


def test_exposure_permanently_blocks_other_stages(registry) -> None:
    first = check_and_reserve(
        SYNTHETIC_PHONE, Stage.LEVEL_C, "data-admin", registry=registry
    )
    mark_exposed(first.reservation_id, "data-admin", registry=registry)

    blocked = check_and_reserve(
        SYNTHETIC_PHONE, Stage.STAGE_3, "data-admin", registry=registry
    )

    assert blocked.allowed is False
    assert blocked.reason_code == "PRIOR_EXPOSURE"


def test_unauthorized_actor_fails_without_creating_registry(registry) -> None:
    with pytest.raises(GovernanceError) as error:
        check_and_reserve(SYNTHETIC_PHONE, Stage.LEVEL_B, "observer", registry=registry)

    assert error.value.code == "UNAUTHORIZED"
    assert not registry.database_path.exists()


@pytest.mark.parametrize("actor", ["+8613912345678", "person@example.invalid", "has space"])
def test_contact_like_actor_id_is_rejected_without_database_creation(tmp_path, actor) -> None:
    registry = DedupRegistry(
        database_path=tmp_path / "dedup.sqlite",
        key_provider=lambda: b"K" * 32,
        allowed_actors={actor},
    )

    with pytest.raises(GovernanceError) as error:
        check_and_reserve(SYNTHETIC_PHONE, Stage.LEVEL_B, actor, registry=registry)

    assert error.value.code == "UNAUTHORIZED"
    assert not registry.database_path.exists()


def test_missing_key_fails_closed_without_creating_registry(tmp_path) -> None:
    registry = DedupRegistry(
        database_path=tmp_path / "dedup.sqlite",
        key_provider=lambda: (_ for _ in ()).throw(GovernanceError("KEY_UNAVAILABLE")),
        allowed_actors={"data-admin"},
    )

    with pytest.raises(GovernanceError) as error:
        check_and_reserve(SYNTHETIC_PHONE, Stage.LEVEL_B, "data-admin", registry=registry)

    assert error.value.code == "KEY_UNAVAILABLE"
    assert not registry.database_path.exists()


def test_two_concurrent_reservations_have_exactly_one_new(registry) -> None:
    def reserve():
        return check_and_reserve(
            SYNTHETIC_PHONE, Stage.STAGE_1, "data-admin", registry=registry
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        decisions = list(pool.map(lambda _: reserve(), range(2)))

    assert [item.reason_code for item in decisions].count("NEW") == 1
    assert [item.reason_code for item in decisions].count("ACTIVE_RESERVATION") == 1


def test_database_has_no_contact_or_research_identifier_columns(registry) -> None:
    check_and_reserve(SYNTHETIC_PHONE, Stage.LEVEL_B, "data-admin", registry=registry)

    with sqlite3.connect(registry.database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        columns = {
            row[1].lower()
            for table in tables
            for row in connection.execute(f"PRAGMA table_info({table})")
        }
        raw_bytes = registry.database_path.read_bytes()

    assert not {"phone", "mobile", "contact", "research_id"} & columns
    assert SYNTHETIC_PHONE.encode("utf-8") not in raw_bytes
    assert b"13800138000" not in raw_bytes


def test_tampering_with_an_audit_event_breaks_chain_verification(registry) -> None:
    check_and_reserve(SYNTHETIC_PHONE, Stage.LEVEL_B, "data-admin", registry=registry)
    assert registry.verify_audit_chain().valid is True

    with sqlite3.connect(registry.database_path) as connection:
        connection.execute("UPDATE audit_events SET result = 'tampered' WHERE sequence = 1")
        connection.commit()

    report = registry.verify_audit_chain()
    assert report.valid is False
    assert report.reason_code == "AUDIT_CHAIN_INVALID"
