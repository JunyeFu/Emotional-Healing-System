"""Synthetic tests only. Disposable Git fixtures are NOT the user's repository."""
from __future__ import annotations
import csv
import io
import json
import math
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from result_classifier import Evidence, classify
from planning_checks import planning_results, rounded
from apply_upgrade import (PACKAGE, NEW_PREFIX, MigrationError, ancestors,validate_graph,
                           transform_csv, safe_target, git_blob,prepare_changes,apply_changes,restore)

CFG=PACKAGE/'02_仓库升级'
ROUTE=json.loads((CFG/'overlay'/NEW_PREFIX/'route_contract_v1.2.json').read_text())
BASE=json.loads((PACKAGE/'04_来源与历史/base_task_graph_derived.json').read_text())['tasks']
MUT=json.loads((CFG/'task_mutations_v1.2.json').read_text())
DONE={r['historical_task'] for r in csv.DictReader((CFG/'历史DONE影响与复核.csv').open(encoding='utf-8-sig',newline=''))}

def source_fixture() -> bytes:
    with (CFG/'new_tasks_v1.2.csv').open(encoding='utf-8-sig',newline='') as f:fields=csv.DictReader(f).fieldnames
    s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fields,lineterminator='\n');w.writeheader()
    for task,deps in BASE.items():
        row={k:'' for k in fields}
        row.update(task_id=task,parent_id='SRP-ROOT',wave='W0',title='SYNTHETIC_TEST_ONLY '+task,
                   depends_on='|'.join(deps),status='DONE' if task in DONE else 'WAIT_DEP',kind='FIXED',
                   effort_person_days='1',deliverables='SYNTHETIC_NOT_REPOSITORY_SOURCE')
        w.writerow(row)
    return s.getvalue().encode()

def parse(b: bytes) -> dict:
    return {r['task_id']:r for r in csv.DictReader(io.StringIO(b.decode('utf-8-sig')))}

class ClassifierTests(unittest.TestCase):
    def test_native_important(self):
        r=classify(Evidence(-3,-4,-2,1));self.assertEqual(r['direction_evidence'],'NATIVE_LOWER');self.assertEqual(r['practical_scale'],'NATIVE_IMPORTANT_BENEFIT_SUPPORTED')
    def test_abstract_important(self):
        r=classify(Evidence(3,2,4,1));self.assertEqual(r['direction_evidence'],'ABSTRACT_LOWER');self.assertEqual(r['practical_scale'],'ABSTRACT_IMPORTANT_BENEFIT_SUPPORTED')
    def test_wide_null_not_equivalent(self):
        r=classify(Evidence(0,-4,4,1));self.assertEqual(r['direction_evidence'],'NO_DIRECTION_ESTABLISHED');self.assertEqual(r['practical_scale'],'IMPORTANT_EFFECT_NOT_EXCLUDED');self.assertFalse(r['formal_equivalence_claim_allowed'])
    def test_narrow_not_formal_equivalence(self):
        r=classify(Evidence(0,-.2,.2,1));self.assertEqual(r['practical_scale'],'WITHIN_PRESPECIFIED_PRACTICAL_BOUNDS');self.assertFalse(r['formal_equivalence_claim_allowed'])
    def test_small_significant_and_practical_bounds_can_coexist(self):
        r=classify(Evidence(.2,.1,.3,1));self.assertEqual(r['direction_evidence'],'ABSTRACT_LOWER');self.assertEqual(r['practical_scale'],'WITHIN_PRESPECIFIED_PRACTICAL_BOUNDS')
    def test_no_threshold_no_importance(self):
        self.assertEqual(classify(Evidence(-2,-3,-1))['practical_scale'],'THRESHOLD_NOT_FROZEN')
    def test_functional_failure_does_not_hide_affect(self):
        r=classify(Evidence(2,1,3,1,functional_guard='FAIL'));self.assertTrue(r['prespecified_affect_result_must_be_reported']);self.assertEqual(r['direction_evidence'],'ABSTRACT_LOWER')
    def test_delivery_problem_limits_concept_not_numbers(self):
        r=classify(Evidence(2,1,3,delivery_valid=False));self.assertEqual(r['direction_evidence'],'ABSTRACT_LOWER');self.assertEqual(r['interpretation_scope'],'DELIVERY_VALIDITY_LIMITED');self.assertFalse(r['automatic_deployment_recommendation'])
    def test_not_assessable(self):
        self.assertEqual(classify(Evidence(0,-1,1,affect_assessable=False))['direction_evidence'],'NOT_ASSESSABLE')
    def test_zero_boundary_no_superiority(self):
        self.assertEqual(classify(Evidence(-.5,-1,0))['direction_evidence'],'NO_DIRECTION_ESTABLISHED')
    def test_practical_boundary_no_important_claim(self):
        self.assertEqual(classify(Evidence(-2,-3,-1,1))['practical_scale'],'IMPORTANT_EFFECT_NOT_EXCLUDED')
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):classify(Evidence(math.nan,-1,1))
    def test_inf_rejected(self):
        with self.assertRaises(ValueError):classify(Evidence(0,-1,math.inf))
    def test_reversed_ci_rejected(self):
        with self.assertRaises(ValueError):classify(Evidence(0,1,-1))
    def test_estimate_outside_ci_rejected(self):
        with self.assertRaises(ValueError):classify(Evidence(2,-1,1))
    def test_wrong_ci_level_rejected(self):
        with self.assertRaises(ValueError):classify(Evidence(0,-1,1,ci_level=.90))
    def test_boolean_numeric_rejected(self):
        with self.assertRaises(ValueError):classify(Evidence(True,-1,2))
    def test_zero_delta_rejected(self):
        with self.assertRaises(ValueError):classify(Evidence(0,-1,1,0))
    def test_invalid_guard_rejected(self):
        with self.assertRaises(ValueError):classify(Evidence(0,-1,1,functional_guard='APPROVED_BY_AI'))
    def test_sensitivity_caveat_retained(self):
        self.assertEqual(classify(Evidence(-2,-3,-1,sensitivity='SENSITIVE'))['sensitivity'],'SENSITIVE')
    def test_no_automatic_universal_claim(self):
        r=classify(Evidence(-3,-4,-2,1));self.assertFalse(r['mechanism_or_all_explicit_vs_native_claim_allowed']);self.assertFalse(r['long_term_or_treatment_efficacy_claim_allowed'])

class GraphAndCSVTests(unittest.TestCase):
    def test_target_graph_70(self):self.assertEqual(len(ROUTE['tasks']),70)
    def test_source_graph_58(self):self.assertEqual(len(BASE),58)
    def test_core_reachable_without_extension(self):
        validate_graph(ROUTE['tasks'],ROUTE);self.assertTrue('A-04' in ancestors(ROUTE['tasks'],'W-03'));self.assertFalse(set(ROUTE['core_must_not_depend_on']) & ancestors(ROUTE['tasks'],'W-03'))
    def test_extension_requires_e06(self):self.assertIn('E-06',ancestors(ROUTE['tasks'],'UP-08'))
    def test_cycle_rejected(self):
        with self.assertRaises(MigrationError):ancestors({'a':['b'],'b':['a']},'a')
    def test_unknown_dependency_rejected(self):
        with self.assertRaises(MigrationError):ancestors({'a':['missing']},'a')
    def test_transform_preserves_done(self):
        before=parse(source_fixture());after=parse(transform_csv(source_fixture(),MUT,CFG/'new_tasks_v1.2.csv',ROUTE))
        for i in DONE:self.assertEqual(before[i],after[i])
        self.assertEqual(len(after),70)
    def test_dep_drift_rejected(self):
        b=source_fixture().replace(b'A-05|E-06',b'A-05|E-05')
        with self.assertRaises(MigrationError):transform_csv(b,MUT,CFG/'new_tasks_v1.2.csv',ROUTE)
    def test_bom_preserved(self):
        b=transform_csv(b'\xef\xbb\xbf'+source_fixture(),MUT,CFG/'new_tasks_v1.2.csv',ROUTE);self.assertTrue(b.startswith(b'\xef\xbb\xbf'))
    def test_windows_crlf_preserved(self):
        b=transform_csv(source_fixture().replace(b'\n',b'\r\n'),MUT,CFG/'new_tasks_v1.2.csv',ROUTE);self.assertEqual(b.count(b'\n'),b.count(b'\r\n'))
    def test_no_generated_task_done(self):
        out=parse(transform_csv(source_fixture(),MUT,CFG/'new_tasks_v1.2.csv',ROUTE))
        self.assertTrue(all(out[i]['status']!='DONE' for i in out if i.startswith('UP-')))

class PlanningAndPathTests(unittest.TestCase):
    def test_proposed_pretreatment_baseline_timing_explicit(self):
        p=json.loads((CFG/'overlay'/NEW_PREFIX/'protocol_authority_v1.2.json').read_text())
        self.assertTrue(p['primary']['pretreatment_baseline_required']);self.assertTrue(p['training']['condition_specific_training_after_panas_pre']);self.assertTrue(p['training']['primary_estimand_includes_condition_specific_training']);self.assertEqual(p['training']['timing_status'],'EXPLICIT_PROPOSED_CORRECTION_REQUIRES_CONTROLLED_FREEZE')

    def test_capacity_exact(self):
        c=planning_results()['capacity'];self.assertEqual(c['core_station_hours'],[264.0,336.0]);self.assertEqual(c['full_station_hours'],[484.0,616.0]);self.assertEqual(c['full_collection_weeks'],16.5)
    def test_new_n_not_old_anchor(self):
        rows=planning_results()['affect_sensitivity'];self.assertTrue(rows[0]['ideal_n_per_arm']>rows[-1]['ideal_n_per_arm']);self.assertTrue(all(r['illustrative_recruitment_with_20pct_unavailable']%48==0 for r in rows))
    def test_pf_counterexample(self):self.assertAlmostEqual(sum(planning_results()['pf_counterexample']['module_differences'])/4,-.06)
    def test_bad_round_input(self):
        with self.assertRaises(ValueError):rounded(-1,48)
    def test_parent_escape_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(MigrationError):safe_target(Path(t),'../x')
    def test_windows_drive_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(MigrationError):safe_target(Path(t),'C:/x')
    def test_git_write_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(MigrationError):safe_target(Path(t),'.git/config')
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'real').mkdir()
            try:(root/'link').symlink_to(root/'real',target_is_directory=True)
            except OSError:self.skipTest('Symlink creation not permitted in this environment.')
            with self.assertRaises(MigrationError):safe_target(root,'link/x')

class SyntheticGitMigrationTests(unittest.TestCase):
    def setUp(self):
        if not shutil.which('git'):self.skipTest('Git unavailable; no actual source migration tested.')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.repo=self.root/'repo';self.repo.mkdir();self.pkg=self.root/'package'
        shutil.copytree(CFG,self.pkg/'02_仓库升级')
        self.cfg=json.loads((self.pkg/'02_仓库升级/migration_manifest.json').read_text())
        for p in self.cfg['expected_source_blobs']:
            target=self.repo/p;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(source_fixture() if p.endswith('.csv') else b'SYNTHETIC_TEST_ONLY\n')
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        self.run_git('config','core.autocrlf','false')
        hooks=self.root/'empty_hooks';hooks.mkdir();self.run_git('config','core.hooksPath',str(hooks))
        self.run_git('add','.');self.run_git('-c','user.name=Synthetic Test','-c','user.email=synthetic@example.invalid','commit','-qm','SYNTHETIC TEST FIXTURE ONLY')
        self.cfg['expected_commit']=self.run_git('rev-parse','HEAD').decode().strip()
        self.cfg['expected_source_blobs']={p:git_blob((self.repo/p).read_bytes()) for p in self.cfg['expected_source_blobs']}
        (self.pkg/'02_仓库升级/migration_manifest.json').write_text(json.dumps(self.cfg))
    def run_git(self,*args):return subprocess.run(['git','-C',str(self.repo),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    def prep(self):return prepare_changes(self.repo,self.pkg,check_integrity=False)
    def test_synthetic_preflight_read_only(self):
        changes,report=self.prep();self.assertEqual(report['status'],'CHECK_PASS_NOT_APPLIED');self.assertEqual(self.run_git('status','--porcelain'),b'');self.assertFalse((self.repo/'SRP_UPGRADE_v1.2.md').exists())
    def test_synthetic_apply_and_restore(self):
        before={p:(self.repo/p).read_bytes() for p in self.cfg['expected_source_blobs']}
        changes,report=self.prep();backup=self.root/'backup';result=apply_changes(self.repo,changes,backup,report)
        self.assertEqual(result['status'],'APPLIED_DOCUMENTS_AND_TASKS_ONLY');self.assertTrue((self.repo/'SRP_UPGRADE_v1.2.md').exists())
        self.assertEqual(len(parse((self.repo/MUT['target_csv']).read_bytes())),70)
        restore(self.repo,backup)
        for p,b in before.items():self.assertEqual((self.repo/p).read_bytes(),b)
        self.assertEqual(self.run_git('status','--porcelain'),b'')
    def test_dirty_worktree_rejected(self):
        (self.repo/'README.md').write_text('user change')
        with self.assertRaises(MigrationError):self.prep()
    def test_wrong_head_rejected(self):
        self.cfg['expected_commit']='0'*40;(self.pkg/'02_仓库升级/migration_manifest.json').write_text(json.dumps(self.cfg))
        with self.assertRaises(MigrationError):self.prep()
    def test_wrong_blob_rejected(self):
        self.cfg['expected_source_blobs']['README.md']='0'*40;(self.pkg/'02_仓库升级/migration_manifest.json').write_text(json.dumps(self.cfg))
        with self.assertRaises(MigrationError):self.prep()
    def test_unsafe_backup_rejected(self):
        changes,report=self.prep()
        with self.assertRaises(MigrationError):apply_changes(self.repo,changes,self.repo/'backup',report)
    def test_restore_refuses_subsequent_edit(self):
        changes,report=self.prep();backup=self.root/'backup';apply_changes(self.repo,changes,backup,report)
        (self.repo/'README.md').write_text('later user edit')
        with self.assertRaises(MigrationError):restore(self.repo,backup)
        self.assertEqual((self.repo/'README.md').read_text(),'later user edit')

if __name__=='__main__':unittest.main(verbosity=2)
