from __future__ import annotations

import pytest

from srp_governance import GovernanceError
from srp_governance.access import Capability, Role, authorize, classification_for_level


@pytest.mark.parametrize(
    ("level", "classification"),
    [
        ("L0", "RESTRICTED_RAW"),
        ("L1", "RESTRICTED_PSEUDONYMOUS"),
        ("L2", "CONTROLLED_PSEUDONYMOUS"),
        ("L3", "CONTROLLED_PSEUDONYMOUS"),
        ("L4", "LOCKED_ANALYSIS"),
        ("L5", "INTERNAL_RELEASE_CANDIDATE"),
    ],
)
def test_l0_to_l5_classification_is_frozen(level: str, classification: str) -> None:
    assert classification_for_level(level) == classification


@pytest.mark.parametrize(
    ("role", "capability"),
    [
        (Role.DATA_ADMIN, Capability.RESERVE_CONTACT),
        (Role.DATA_ADMIN, Capability.MAINTAIN_IDENTITY_MAPPING),
        (Role.PROJECT_LEAD, Capability.READ_DEDUP_AUDIT_SUMMARY),
        (Role.ANALYST, Capability.READ_L2_L3),
        (Role.PROJECT_LEAD, Capability.APPROVE_L4_L5_DISCLOSURE),
    ],
)
def test_frozen_access_matrix_allows_expected_capabilities(role, capability) -> None:
    authorize(role, capability)


@pytest.mark.parametrize(
    ("role", "capability"),
    [
        (Role.PROJECT_LEAD, Capability.RESERVE_CONTACT),
        (Role.PRIMARY_OPERATOR, Capability.READ_DEDUP_RECORDS),
        (Role.ANALYST, Capability.MAINTAIN_IDENTITY_MAPPING),
        (Role.DESIGN_MEMBER, Capability.READ_L0_L1),
        (Role.DATA_ADMIN, Capability.APPROVE_L4_L5_DISCLOSURE),
    ],
)
def test_minimum_access_negative_matrix_fails_closed(role, capability) -> None:
    with pytest.raises(GovernanceError) as error:
        authorize(role, capability)

    assert error.value.code == "UNAUTHORIZED"
