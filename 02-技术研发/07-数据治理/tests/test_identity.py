from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from srp_governance import GovernanceError
from srp_governance.identity import IdentityMappingStore


def test_identity_mapping_generates_stable_random_research_id(tmp_path) -> None:
    store = IdentityMappingStore(
        database_path=tmp_path / "identity" / "research_id_mapping.sqlite",
        allowed_actors={"data-admin"},
    )

    first = store.create_or_get("REC-SYNTHETIC-0001", "data-admin")
    second = store.create_or_get("REC-SYNTHETIC-0001", "data-admin")

    assert first == second
    assert first.startswith("SRP-R-")
    assert len(first) == len("SRP-R-") + 32


@pytest.mark.parametrize("opaque_reference", ["13800138000", "+8613800138000", "short", ""])
def test_mapping_rejects_non_opaque_recruitment_references(
    tmp_path, opaque_reference: str
) -> None:
    store = IdentityMappingStore(
        database_path=tmp_path / "identity.sqlite",
        allowed_actors={"data-admin"},
    )

    with pytest.raises(GovernanceError) as error:
        store.create_or_get(opaque_reference, "data-admin")

    assert error.value.code == "INVALID_OPAQUE_REFERENCE"
    assert not store.database_path.exists()


def test_mapping_store_has_no_contact_or_dedup_columns(tmp_path) -> None:
    store = IdentityMappingStore(
        database_path=tmp_path / "identity.sqlite",
        allowed_actors={"data-admin"},
    )
    store.create_or_get("REC-SYNTHETIC-0002", "data-admin")

    with sqlite3.connect(store.database_path) as connection:
        columns = {
            row[1].lower()
            for row in connection.execute("PRAGMA table_info(research_mappings)")
        }

    assert not {"phone", "contact", "subject_token", "hmac", "key"} & columns


def test_unauthorized_mapping_request_fails_before_database_creation(tmp_path) -> None:
    store = IdentityMappingStore(
        database_path=tmp_path / "identity.sqlite",
        allowed_actors={"data-admin"},
    )

    with pytest.raises(GovernanceError) as error:
        store.create_or_get("REC-SYNTHETIC-0003", "observer")

    assert error.value.code == "UNAUTHORIZED"
    assert not store.database_path.exists()


def test_concurrent_create_or_get_returns_one_stable_research_id(tmp_path) -> None:
    store = IdentityMappingStore(
        database_path=tmp_path / "identity" / "mapping.sqlite",
        allowed_actors={"data-admin"},
    )

    with ThreadPoolExecutor(max_workers=8) as executor:
        identifiers = list(
            executor.map(
                lambda _: store.create_or_get("REC-CONCURRENT_01", "data-admin"),
                range(16),
            )
        )

    assert len(set(identifiers)) == 1
