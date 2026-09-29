"""Verify the scoped READY refresh against its immutable pre-closeout Git state."""
import json
import subprocess
import unittest

from build_adaptation import GOV, REPO, read_json

PREVIOUS = "15a4c31"
PACKAGES = GOV + "/当前解锁独立任务包"


def old_json(relative):
    return json.loads(subprocess.check_output(["git", "show", PREVIOUS + ":" + relative], cwd=REPO))


class PreupgradeCloseoutTests(unittest.TestCase):
    def test_refresh_has_exactly_two_explained_changes(self):
        relative = PACKAGES + "/T-02/package_manifest.json"
        old, new = old_json(relative), read_json(REPO / relative)
        impact = read_json(REPO / GOV / "audit_upgrade/input_impacts/T-02_395E389B91D3_F4680AC28692.json")
        self.assertEqual(new["status"], "READY")
        self.assertEqual(old["input_snapshot_id"], impact["previous_input_snapshot_id"])
        self.assertEqual(new["input_snapshot_id"], impact["observed_input_snapshot_id"])
        before = {r["source_path"]: r for r in old["source_files"]}
        after = {r["source_path"]: r for r in new["source_files"]}
        self.assertEqual(set(before), set(after))
        changed = {p for p in before if before[p]["sha256"] != after[p]["sha256"]}
        self.assertEqual(changed, {r["source_path"] for r in impact["changes"]})
        self.assertEqual(len(changed), 2)
        for r in impact["changes"]:
            self.assertEqual(before[r["source_path"]]["sha256"], r["previous_sha256"])
            self.assertEqual(after[r["source_path"]]["sha256"], r["current_sha256"])
        self.assertTrue((REPO / PACKAGES / "T-02/INPUT_CHANGE_NOTICE.md").is_file())
        self.assertFalse(impact["research_authorized"])

    def test_other_package_manifests_unchanged(self):
        for task in ("A-03", "U-02"):
            relative = PACKAGES + "/" + task + "/package_manifest.json"
            self.assertEqual(old_json(relative), read_json(REPO / relative))


if __name__ == "__main__":
    unittest.main(verbosity=2)
