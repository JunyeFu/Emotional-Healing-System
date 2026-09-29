"""Candidate-only consistency tests; never apply external migration code."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

from build_adaptation import HERE, REPO, SOURCE, read_json, remap, rows, sha, write_json


def graph_errors(tasks, milestones, route):
    graph = {r["task_id"]: set(filter(None, r["depends_on"].split("|"))) for r in tasks}
    graph.update({r["id"]: set(r["depends_on"]) for r in milestones["milestones"]})
    if route == "with_stage3":
        graph["A-06"].update({"A-04", "U12-08"})
    errors = []
    visited, visiting = set(), set()
    def visit(node):
        if node not in graph:
            errors.append("UNKNOWN:" + node)
            return
        if node in visiting:
            errors.append("CYCLE:" + node)
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in graph[node]:
            visit(dep)
        visiting.remove(node)
        visited.add(node)
    for node in graph:
        visit(node)
    return errors


class AdaptationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read_json(HERE / "source_manifest.json")
        cls.tasks = rows(HERE / "candidate/task_registry.csv")
        cls.index = {r["task_id"]: r for r in cls.tasks}
        cls.baseline = rows(HERE / "baseline/05_可领取任务包.csv")
        cls.milestones = read_json(HERE / "candidate/task_milestones.json")
        spec = importlib.util.spec_from_file_location("adaptation_route", HERE / "baseline/route_evaluator.py")
        cls.evaluator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.evaluator)
        cls.evaluator.CONTRACT = HERE / "candidate/release_routes.json"

    def test_original_archive_hashes(self):
        for f in self.manifest["originals"]:
            self.assertEqual(sha((HERE / f["archived_path"]).read_bytes()), f["byte_sha256"])

    def test_all_fifty_source_hashes(self):
        self.assertEqual(len(self.manifest["source_content_files"]), 50)
        for f in self.manifest["source_content_files"]:
            self.assertEqual(sha((SOURCE / f["path"]).read_bytes()), f["byte_sha256"])

    def test_baseline_and_live_authority_unchanged(self):
        for f in self.manifest["baseline_files"]:
            self.assertEqual(sha((HERE / f["snapshot"]).read_bytes()), f["byte_sha256"])
            self.assertEqual(sha((REPO / f["repository_path"]).read_bytes()), f["worktree_byte_sha256"])

    def test_counts_and_namespaces(self):
        self.assertEqual(len(self.tasks), 71)
        self.assertEqual(len(self.index), 71)
        self.assertEqual(sum(r["kind"] == "FIXED" for r in self.tasks), 68)
        self.assertEqual(sum(r["task_id"].startswith("U12-") for r in self.tasks), 12)
        self.assertFalse(any(r["task_id"].startswith("UP-") for r in self.tasks))
        for r in self.tasks:
            self.assertTrue(r["title"].startswith("【" + r["domain"] + "】"))

    def test_chinese_adjacent_task_references(self):
        self.assertEqual(remap("需UP-05；UP-06正式入口"), "需U12-05；U12-06正式入口")
        self.assertEqual(remap("XUP-05 UP-051"), "XUP-05 UP-051")
        changes = read_json(HERE / "candidate/task_changes.json")["changes"]
        for item in changes:
            for field in ("after", "proposed"):
                self.assertNotIn("UP-", str(item.get(field, {})))
        for task in self.tasks:
            if task["task_id"].startswith("U12-"):
                self.assertNotIn("UP-", str(task))

    def test_final_freeze_waits_for_blind_calibration(self):
        self.assertIn("A-03-CAL", self.index["U12-11"]["depends_on"].split("|"))
        self.assertIn("证据哈希", self.index["U12-11"]["acceptance_criteria"])

    def test_extension_keeps_scope_not_ordered_outcome_gates(self):
        task = self.index["A-04"]
        original = next(r for r in self.baseline if r["task_id"] == "A-04")
        for field in ("task_id", "title", "status", "depends_on"):
            self.assertEqual(task[field], original[field])
        self.assertIn("功能护栏或SCCI失败不隐藏预设情绪结果", task["acceptance_criteria"])
        self.assertIn("不以旧联合Gate2或有序门作为结果报告前置", task["acceptance_criteria"])

    def test_signed_and_in_progress_rows_preserved(self):
        protected = [r for r in self.baseline if r["status"] in {"DONE", "IN_PROGRESS", "IN_REVIEW"}]
        self.assertEqual(sum(r["status"] == "DONE" for r in protected), 18)
        for r in protected:
            self.assertEqual(r, self.index[r["task_id"]])
        for r in self.baseline:
            self.assertEqual(r["status"], self.index[r["task_id"]]["status"])

    def test_both_graphs(self):
        for route in ("stage1_only", "with_stage3"):
            self.assertEqual(graph_errors(self.tasks, self.milestones, route), [])

    def test_unknown_dependency_rejected(self):
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["depends_on"] = "MISSING"
        self.assertIn("UNKNOWN:MISSING", graph_errors(tasks, self.milestones, "stage1_only"))

    def test_cycle_rejected(self):
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["depends_on"] = tasks[0]["task_id"]
        self.assertTrue(any(e.startswith("CYCLE:") for e in graph_errors(tasks, self.milestones, "stage1_only")))

    def test_core_ancestry_excludes_stage3(self):
        seen = set()
        def visit(tid):
            if tid in seen:
                return
            seen.add(tid)
            deps = self.index[tid]["depends_on"].split("|") if tid in self.index else next(m["depends_on"] for m in self.milestones["milestones"] if m["id"] == tid)
            for dep in filter(None, deps):
                visit(dep)
        visit("W-03")
        self.assertFalse(seen & {"A-04", "E-06", "B-03", "U12-08"})
        self.assertTrue({"A-06", "U12-10", "U12-07"} <= seen)

    def test_milestone_and_protocol_boundaries(self):
        self.assertEqual(read_json(HERE / "baseline/task_milestone_status_v1.0.json")["statuses"]["A-03-SPEC"], "DONE")
        self.assertIn("U12-04", self.milestones["milestones"][1]["depends_on"])
        self.assertIn("A-03-CAL", self.index["G-03"]["depends_on"])
        p = read_json(HERE / "candidate/protocol_authority_v1.2.json")
        self.assertFalse(p["formal_participant_collection_allowed"])
        self.assertFalse(p["equivalence"]["confirmatory_enabled"])
        self.assertIsNone(p["sample_planning"]["formal_randomized_n"])
        self.assertTrue(p["primary"]["report_even_if_functional_guard_fails"])
        self.assertIn("REQUIRES_CONTROLLED_FREEZE", p["training"]["timing_status"])

    def test_twelve_candidate_packages(self):
        folders = list((HERE / "tasks").iterdir())
        self.assertEqual(len(folders), 12)
        for folder in folders:
            m = read_json(folder / "package_manifest.json")
            self.assertFalse(m["dispatch_allowed"])
            self.assertEqual(m["input_snapshot_id"], sha((folder / "inputs/task_input.json").read_bytes()))
            self.assertTrue({"TASK.md", "FILES.md", "inputs/task_input.json"} <= {f["path"] for f in m["files"]})
            for f in m["files"]:
                self.assertEqual(sha((folder / f["path"]).read_bytes()), f["byte_sha256"])
            self.assertIn("https://", (folder / "TASK.md").read_text(encoding="utf-8"))

    def route_result(self, route, count=0, missing_task=False, tamper=False, boolean_only=False):
        contract = read_json(HERE / "candidate/release_routes.json")
        spec = contract["routes"][route]
        with tempfile.TemporaryDirectory() as directory:
            root, evidence = Path(directory), {}
            for source in contract["stage3_started_evidence_sources"]:
                data = b'{}\n' * count
                (root / (source + ".jsonl")).write_bytes(data)
                evidence[source] = {"path": source + ".jsonl", "byte_sha256": sha(data).upper(), "record_count": count}
            if tamper:
                next(root.iterdir()).write_bytes(b'tampered\n')
            if boolean_only:
                evidence = {"stage3_started": False}
            receipt = {k: "SYNTHETIC_TEST_ONLY" for k in ("record_id", "candidate_identity", "reviewer", "review_method", "signed_ref", "signed_ref_sha256")}
            receipt.update(status="PASS", scope=spec["required_human_receipt_scope"])
            completed = set(spec["required_done"])
            if missing_task:
                completed.remove("U12-10")
            return self.evaluator.evaluate_route(route, completed, evidence, receipt, set(spec.get("required_result_families", [])), root)

    def test_route_success_does_not_authorize_research(self):
        for route, count in (("stage1_only", 0), ("with_stage3", 1)):
            result = self.route_result(route, count)
            self.assertTrue(result["ok"], result)
            self.assertFalse(result["authorization"])

    def test_route_requires_result_review(self):
        self.assertFalse(self.route_result("stage1_only", missing_task=True)["ok"])

    def test_route_cannot_hide_stage3(self):
        self.assertFalse(self.route_result("stage1_only", count=1)["ok"])

    def test_route_rejects_tamper_and_boolean(self):
        self.assertFalse(self.route_result("stage1_only", tamper=True)["ok"])
        self.assertFalse(self.route_result("stage1_only", boolean_only=True)["ok"])


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AdaptationTests))
    write_json(HERE / "evidence/adaptation_validation.json", {"tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "passed": result.wasSuccessful(),
        "scope": "OFFLINE_CANDIDATE_ONLY", "active_protocol_changed": False})
    raise SystemExit(not result.wasSuccessful())
