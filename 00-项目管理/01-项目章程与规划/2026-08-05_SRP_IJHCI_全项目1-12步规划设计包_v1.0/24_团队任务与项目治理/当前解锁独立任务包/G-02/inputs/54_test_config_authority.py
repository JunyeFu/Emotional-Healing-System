from __future__ import annotations

import json
from pathlib import Path

from srp_governance.access import ACCESS_MATRIX, DATA_CLASSIFICATIONS


ROOT = Path(__file__).resolve().parents[1]


def test_machine_readable_classification_matches_runtime_authority() -> None:
    config = json.loads(
        (ROOT / "config" / "data_classification_v1.json").read_text(encoding="utf-8")
    )

    assert config["schema_version"] == 1
    assert config["levels"] == DATA_CLASSIFICATIONS
    assert {
        item["retention"] for item in config["isolated_stores"].values()
    } == {"PENDING_INSTITUTIONAL_APPROVAL"}


def test_machine_readable_access_matrix_matches_runtime_authority() -> None:
    config = json.loads(
        (ROOT / "config" / "access_matrix_v1.json").read_text(encoding="utf-8")
    )
    runtime = {
        role.value: sorted(capability.value for capability in capabilities)
        for role, capabilities in ACCESS_MATRIX.items()
    }

    assert config == {"schema_version": 1, "capabilities": runtime}
