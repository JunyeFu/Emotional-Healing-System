from __future__ import annotations

from enum import StrEnum

from .errors import GovernanceError


DATA_CLASSIFICATIONS = {
    "L0": "RESTRICTED_RAW",
    "L1": "RESTRICTED_PSEUDONYMOUS",
    "L2": "CONTROLLED_PSEUDONYMOUS",
    "L3": "CONTROLLED_PSEUDONYMOUS",
    "L4": "LOCKED_ANALYSIS",
    "L5": "INTERNAL_RELEASE_CANDIDATE",
}


class Role(StrEnum):
    DATA_ADMIN = "data_admin"
    PROJECT_LEAD = "project_lead"
    PRIMARY_OPERATOR = "primary_operator"
    ANALYST = "analyst"
    DESIGN_MEMBER = "design_member"


class Capability(StrEnum):
    RESERVE_CONTACT = "reserve_contact"
    READ_DEDUP_RECORDS = "read_dedup_records"
    READ_DEDUP_AUDIT_SUMMARY = "read_dedup_audit_summary"
    MAINTAIN_IDENTITY_MAPPING = "maintain_identity_mapping"
    READ_L0_L1 = "read_l0_l1"
    READ_L2_L3 = "read_l2_l3"
    APPROVE_L4_L5_DISCLOSURE = "approve_l4_l5_disclosure"


ACCESS_MATRIX = {
    Role.DATA_ADMIN: {
        Capability.RESERVE_CONTACT,
        Capability.READ_DEDUP_RECORDS,
        Capability.MAINTAIN_IDENTITY_MAPPING,
        Capability.READ_L0_L1,
        Capability.READ_L2_L3,
    },
    Role.PROJECT_LEAD: {
        Capability.READ_DEDUP_AUDIT_SUMMARY,
        Capability.READ_L0_L1,
        Capability.READ_L2_L3,
        Capability.APPROVE_L4_L5_DISCLOSURE,
    },
    Role.PRIMARY_OPERATOR: {Capability.READ_L0_L1},
    Role.ANALYST: {Capability.READ_L2_L3},
    Role.DESIGN_MEMBER: set(),
}


def classification_for_level(level: str) -> str:
    try:
        return DATA_CLASSIFICATIONS[level]
    except (KeyError, TypeError) as exc:
        raise GovernanceError("UNKNOWN_DATA_LEVEL") from exc


def authorize(role: Role | str, capability: Capability | str) -> None:
    try:
        normalized_role = Role(role)
        normalized_capability = Capability(capability)
    except (TypeError, ValueError) as exc:
        raise GovernanceError("UNAUTHORIZED") from exc
    if normalized_capability not in ACCESS_MATRIX[normalized_role]:
        raise GovernanceError("UNAUTHORIZED")
