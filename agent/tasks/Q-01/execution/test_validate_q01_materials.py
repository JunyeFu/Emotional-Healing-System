from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
ROOT = REPO / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/20_产品与场景设计/Q-01_LevelA与独立重建'
SPEC = importlib.util.spec_from_file_location(
    "validate_q01_materials", Path(__file__).resolve().parent / "validate_q01_materials.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Q01MaterialValidationTests(unittest.TestCase):
    def test_material_package_is_consistent(self) -> None:
        self.assertEqual(MODULE.validate_materials(), [])

    def test_blind_task_payload_has_no_identity_tokens(self) -> None:
        tasks = MODULE.load_json("reconstruction_tasks_v1.0.json")["tasks"]
        payload = str(tasks).lower()
        for token in MODULE.FORBIDDEN_BLIND_TOKENS:
            self.assertNotIn(token.lower(), payload)

    def test_distributed_blind_markdown_has_no_identity_tokens(self) -> None:
        payload = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8").lower()
            for relative in MODULE.BLIND_MARKDOWN_FILES
        )
        for token in MODULE.FORBIDDEN_BLIND_TOKENS:
            self.assertNotIn(token.lower(), payload)

    def test_both_tasks_cover_unavailable_input(self) -> None:
        tasks = MODULE.load_json("reconstruction_tasks_v1.0.json")["tasks"]
        for task in tasks:
            self.assertTrue(any(event["response"] is None for event in task["events"]))

    def test_unavailable_periods_freeze_trend(self) -> None:
        tasks = MODULE.load_json("reconstruction_tasks_v1.0.json")["tasks"]
        for task in tasks:
            previous_trend = task["events"][0]["trend"]
            for event in task["events"]:
                if event["availability"] in {"UNUSABLE", "DISCONNECTED"}:
                    self.assertIsNone(event["response"])
                    self.assertEqual(event["trend"], previous_trend)
                else:
                    previous_trend = event["trend"]


if __name__ == "__main__":
    unittest.main()
