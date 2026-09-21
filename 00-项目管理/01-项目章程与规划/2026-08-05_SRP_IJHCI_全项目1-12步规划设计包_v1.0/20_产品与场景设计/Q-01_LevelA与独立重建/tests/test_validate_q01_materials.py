from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_q01_materials", ROOT / "tools" / "validate_q01_materials.py"
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
