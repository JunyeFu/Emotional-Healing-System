"""Regression checks for scope updates and frozen-claim review boundaries."""
import csv
import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / 'agent/governance/planning/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
RENDER = runpy.run_path(str(GOV/'13_render_ready_task_packages.py'))
HANDBOOK = runpy.run_path(str(GOV/'10_render_task_handbook.py'))

class ScopeUpdateTests(unittest.TestCase):
    def test_active_claim_input_cannot_be_replaced(self):
        for status in ['IN_PROGRESS','IN_REVIEW']:
            with self.assertRaises(ValueError):
                RENDER['enforce_snapshot_freeze'](status,'old','new')
            RENDER['enforce_snapshot_freeze'](status,'same','same')

    def test_ready_scope_can_refresh_input(self):
        RENDER['enforce_snapshot_freeze']('READY','old','new')

    def test_new_scope_does_not_inherit_passed_review(self):
        with (GOV/'05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
            row = next(r for r in csv.DictReader(stream) if r['task_id']=='U12-03')
        task_map = {'source_files':[], 'acceptance_results':['PASS']*3,
                    'evidence_results':['PASS']*3, 'human_review_status':'PASS',
                    'human_review_commit':'historical', 'model_review_status':'PASS',
                    'implementation_commit':'historical', 'execution_update_path':'agent/tasks/U12-03/TASK.md'}
        text = RENDER['task_markdown'](row,HANDBOOK['parse_resources'](),HANDBOOK['PROCESS_PROFILES'],task_map)
        for ac in row['current_acceptance_criteria'].split('；'):
            self.assertIn('- [ ] '+ac,text)
        self.assertNotIn('- [x]',text)
        self.assertIn('新设计范围尚未取得业务验收',text)
        self.assertIn('真实团队第二人复核：`PENDING`',text)
        self.assertIn('design_updates/',text)
        self.assertEqual(task_map['human_review_status'],'PASS')

if __name__=='__main__':
    unittest.main()
