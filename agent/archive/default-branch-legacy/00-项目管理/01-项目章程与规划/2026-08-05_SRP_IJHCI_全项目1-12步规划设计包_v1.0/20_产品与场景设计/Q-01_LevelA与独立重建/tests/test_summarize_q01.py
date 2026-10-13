from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from summarize_q01 import evaluate, read_csv  # noqa: E402


CONTRACT = json.loads((ROOT / "framework_contract_v1.0.json").read_text(encoding="utf-8"))


def roster_rows() -> list[dict[str, str]]:
    rows = []
    for index, group in enumerate(["construct_method"] * 3 + ["hci_visual"] * 3 + ["runtime_system"] * 2, 1):
        rows.append({"person_code": f"E{index:02}", "role": "expert", "role_group": group,
                     "framework_author": "0", "eligible": "1", "conflict_note": ""})
    for index, group in enumerate(["hci_visual"] * 2 + ["realtime_game"] * 2, 1):
        rows.append({"person_code": f"D{index:02}", "role": "designer", "role_group": group,
                     "framework_author": "0", "eligible": "1", "conflict_note": ""})
    for index in range(1, 3):
        rows.append({"person_code": f"R{index:02}", "role": "rater", "role_group": "blind_visual",
                     "framework_author": "0", "eligible": "1", "conflict_note": ""})
    rows.append({"person_code": "A01", "role": "adjudicator", "role_group": "research_lead",
                 "framework_author": "0", "eligible": "1", "conflict_note": ""})
    return rows


def expert_rows() -> list[dict[str, str]]:
    return [
        {"reviewer_code": f"E{reviewer:02}", "item_id": f"E{item:02}",
         "relevance": "4", "comprehensiveness": "4", "clarity": "4",
         "construct_purity": "4", "critical_blocker": "0", "comment": ""}
        for reviewer in range(1, 9)
        for item in range(1, 11)
    ]


def reconstruction_rows(failing_designers: set[str] | None = None) -> list[dict[str, str]]:
    failing_designers = failing_designers or set()
    rows = []
    for designer in [f"D{i:02}" for i in range(1, 5)]:
        for task in ["R-UNSEEN-RHYTHM", "R-NON-WEATHER"]:
            for rater in ["R01", "R02"]:
                failed = designer in failing_designers
                rows.append({
                    "designer_code": designer, "task_id": task, "rater_code": rater,
                    "target_correct": "0" if failed else "1", "actual_correct": "1",
                    "cumulative_correct": "1", "fallback_correct": "1",
                    "forbidden_coupling": "0", "identity_leak": "0", "color_only": "0",
                    "evidence_location": "frame-01" if failed else "",
                    "comment": "Target object missing" if failed else "",
                })
    return rows


class Q01FrameworkTests(unittest.TestCase):
    def test_all_gates_pass(self) -> None:
        result = evaluate(roster_rows(), expert_rows(), reconstruction_rows(), CONTRACT)
        self.assertEqual("PASS", result["decision"])

    def test_expert_item_below_threshold_requires_revision(self) -> None:
        reviews = expert_rows()
        for row in reviews:
            if row["item_id"] == "E01" and row["reviewer_code"] in {"E01", "E02"}:
                row["relevance"] = "2"
        result = evaluate(roster_rows(), reviews, reconstruction_rows(), CONTRACT)
        self.assertEqual("REVISE", result["decision"])

    def test_each_expert_dimension_is_gated(self) -> None:
        for dimension in ("comprehensiveness", "clarity", "construct_purity"):
            reviews = expert_rows()
            for row in reviews:
                if row["item_id"] == "E01" and row["reviewer_code"] in {"E01", "E02"}:
                    row[dimension] = "2"
            with self.subTest(dimension=dimension):
                result = evaluate(roster_rows(), reviews, reconstruction_rows(), CONTRACT)
                self.assertEqual("REVISE", result["decision"])

    def test_unstable_reconstruction_downgrades_claim(self) -> None:
        scores = reconstruction_rows({"D01", "D02"})
        result = evaluate(roster_rows(), expert_rows(), scores, CONTRACT)
        self.assertEqual("DOWNGRADE_TO_FOUR_SCENE_DESIGN_PATTERN", result["decision"])

    def test_rater_disagreement_requires_revision(self) -> None:
        scores = reconstruction_rows()
        scores[0]["target_correct"] = "0"
        scores[0]["evidence_location"] = "frame-01"
        scores[0]["comment"] = "Target object missing"
        result = evaluate(roster_rows(), expert_rows(), scores, CONTRACT)
        self.assertEqual("REVISE", result["decision"])

    def test_adjudication_resolves_disagreement_without_rewriting_scores(self) -> None:
        scores = reconstruction_rows()
        scores[0]["target_correct"] = "0"
        scores[0]["evidence_location"] = "frame-01"
        scores[0]["comment"] = "Target object missing"
        adjudications = [{
            "designer_code": "D01", "task_id": "R-UNSEEN-RHYTHM",
            "field": "target_correct", "adjudicator_code": "A01",
            "final_value": "1", "rationale": "Reviewed both coded observations",
        }]
        result = evaluate(
            roster_rows(), expert_rows(), scores, CONTRACT, adjudications
        )
        self.assertEqual("PASS", result["decision"])
        self.assertEqual([], result["reconstruction_gate"]["unresolved_disagreements"])

    def test_unknown_adjudicator_is_incomplete(self) -> None:
        scores = reconstruction_rows()
        scores[0]["target_correct"] = "0"
        scores[0]["evidence_location"] = "frame-01"
        scores[0]["comment"] = "Target object missing"
        adjudications = [{
            "designer_code": "D01", "task_id": "R-UNSEEN-RHYTHM",
            "field": "target_correct", "adjudicator_code": "UNKNOWN",
            "final_value": "1", "rationale": "Invalid identity",
        }]
        result = evaluate(
            roster_rows(), expert_rows(), scores, CONTRACT, adjudications
        )
        self.assertEqual("INCOMPLETE", result["decision"])
        self.assertIn(
            "ADJUDICATOR_UNKNOWN:UNKNOWN",
            result["reconstruction_gate"]["adjudication_errors"],
        )

    def test_failed_rating_without_evidence_is_incomplete(self) -> None:
        scores = reconstruction_rows()
        scores[0]["target_correct"] = "0"
        scores[0]["evidence_location"] = ""
        scores[0]["comment"] = ""
        result = evaluate(roster_rows(), expert_rows(), scores, CONTRACT, [])
        self.assertEqual("INCOMPLETE", result["decision"])
        self.assertIn(
            "RATING_EVIDENCE_MISSING:D01:R-UNSEEN-RHYTHM:R01",
            result["reconstruction_gate"]["rating_errors"],
        )

    def test_incomplete_roster_is_incomplete(self) -> None:
        roster = [row for row in roster_rows() if row["person_code"] != "R02"]
        result = evaluate(roster, expert_rows(), reconstruction_rows(), CONTRACT)
        self.assertEqual("INCOMPLETE", result["decision"])

    def test_empty_templates_are_incomplete_without_crashing(self) -> None:
        result = evaluate([], [], [], CONTRACT, [])
        self.assertEqual("INCOMPLETE", result["decision"])

    def test_csv_templates_are_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rows.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=roster_rows()[0].keys())
                writer.writeheader()
                writer.writerows(roster_rows())
            self.assertEqual(15, len(read_csv(path)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
