from __future__ import annotations

from pathlib import Path
import hashlib
import json
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2] / "08-随机化"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verify_x01 import verify


def test_checked_in_x01_evidence_is_self_consistent() -> None:
    assert verify() == []


def test_verifier_rejects_probability_and_empty_balance_false_pass(tmp_path) -> None:
    copied = tmp_path / "x01"
    shutil.copytree(ROOT, copied)
    probability_path = copied / "evidence/probability_report_v1.json"
    probability = json.loads(probability_path.read_text(encoding="utf-8"))
    probability["unique_probability_vectors"] = [[0.5, 0.5, 0.5, 0.5]]
    probability_path.write_text(json.dumps(probability), encoding="utf-8")
    balance_path = copied / "evidence/balance_report_v1.json"
    balance = json.loads(balance_path.read_text(encoding="utf-8"))
    balance["strata"] = []
    balance_path.write_text(json.dumps(balance), encoding="utf-8")
    summary_path = copied / "evidence/x01_validation_report_v1.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["stage_1"]["record_count"] = 0
    summary["stage_1"]["complete_blocks"] = 0
    summary["stage_1"]["arm_counts"] = {}
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    errors = verify(copied)
    assert "PROBABILITY_REPORT" in errors
    assert "BALANCE_REPORT" in errors
    assert "SUMMARY_REPORT" in errors


def test_verifier_binds_balance_strata_to_the_actual_list(tmp_path) -> None:
    copied = tmp_path / "x01"
    shutil.copytree(ROOT, copied)
    list_path = copied / "fixtures/synthetic/stage_1_list_v1.json"
    plan = json.loads(list_path.read_text(encoding="utf-8"))
    for record in plan["records"]:
        record["stratum"] = f"renamed_{record['stratum']}"
    unsigned = {key: value for key, value in plan.items() if key != "list_hash"}
    encoded = json.dumps(
        unsigned, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    plan["list_hash"] = f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    list_path.write_text(json.dumps(plan), encoding="utf-8")

    summary_path = copied / "evidence/x01_validation_report_v1.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["stage_1"]["list_hash"] = plan["list_hash"]
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    assert "BALANCE_REPORT" in verify(copied)
