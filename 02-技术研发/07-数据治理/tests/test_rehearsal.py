from __future__ import annotations

import json
from pathlib import Path

from srp_governance.rehearsal import run_synthetic_rehearsal


ROOT = Path(__file__).resolve().parents[1]


def test_fixture_freezes_all_four_cross_stage_inputs() -> None:
    fixture = json.loads(
        (ROOT / "tests" / "fixtures" / "cross_stage_matrix.json").read_text(
            encoding="utf-8"
        )
    )

    assert fixture["stages"] == ["level_b", "level_c", "stage_1", "stage_3"]
    assert fixture["expected_active_reason"] == "ACTIVE_RESERVATION"
    assert fixture["expected_exposed_reason"] == "PRIOR_EXPOSURE"


def test_synthetic_rehearsal_closes_state_concurrency_and_recovery_matrix() -> None:
    report = run_synthetic_rehearsal()
    serialized = json.dumps(report, ensure_ascii=True, sort_keys=True)

    assert report["synthetic_only"] is True
    assert report["active_cross_stage_cases"] == 16
    assert report["active_cross_stage_passed"] is True
    assert report["prior_exposure_cases"] == 16
    assert report["prior_exposure_passed"] is True
    assert report["release_before_exposure_allows_reentry"] is True
    assert report["completed_blocks_reentry"] is True
    assert report["withdrawn_after_exposure_blocks_reentry"] is True
    assert report["concurrent_new_count"] == 1
    assert report["concurrent_active_reservation_count"] == 1
    assert report["backup_restore_valid"] is True
    assert report["audit_chain_valid"] is True
    assert report["cross_stage_audit_valid"] is True
    assert "+86" not in serialized
    assert "139" not in serialized
