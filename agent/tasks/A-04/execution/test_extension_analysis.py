"""Validate extension analysis scope against actual contracts and helpers."""
import csv
import json
from pathlib import Path
import re
import runpy
import sys

import numpy as np
import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(ROOT / '02-技术研发/02-信号处理'))
from a03_gate2_spec import benjamini_hochberg

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def current():
    return read(TASK / 'outputs/current-analysis.json')

def test_registry_scope_and_missing_actual_inputs():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'A-04')
    value = current()
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['depends_on'].split('|') == value['depends_on'] == ['A-05', 'E-06']
    assert row['claimant'] == row['reviewer'] == ''
    assert '不以旧联合Gate2或有序门' in row['acceptance_criteria']
    assert value['formal_stage3_sap_ref'] is value['research_lock_id'] is value['unblind_authorization'] is None
    assert value['real_analysis'] == value['independent_reproduction'] == 'NOT_RUN'
    assert value['actual_instances'] == 0
    assert read(ROOT / 'agent/tasks/B-03/outputs/current-batch.json')['instances'] == []
    assert read(ROOT / 'agent/tasks/E-06/outputs/current-closeout.json')['research_lock_signed'] is False

def test_current_extension_not_stage1_cue_comparison():
    value = current()
    freeze = read(ROOT / 'agent/tasks/G-04/outputs/current-extension.json')
    for key in ('arms', 'cue_mode_both_arms', 'contrast'):
        assert value[key] == freeze[key]
    assert value['candidate_model'] == freeze['candidate_primary_model']
    assert value['candidate_treatment_variable'] == freeze['candidate_treatment_variable']
    assert value['fallback_preserves_assignment'] is freeze['fallback_in_estimand'] is True
    assert value['stage1_parameters_automatically_inherited'] is False
    assert value['sequence_rank_is_causal_effect'] is False

@pytest.mark.parametrize('effect', [-0.4, 0.0, 0.4])
def test_existing_hc3_helper_synthetic_policy_minus_random_direction(effect):
    module = runpy.run_path(str(ROOT / 'agent/tasks/U12-04/execution/power_simulation.py'))
    policy = np.tile([0., 1.], 12)
    pre = np.random.default_rng(604).normal(size=24)
    strata = np.repeat([0., 1.], 12)
    matrix = np.column_stack([np.ones(24), policy, pre, strata])
    outcome = 5. + effect * policy + 0.3 * pre + 0.1 * strata
    fit = module['_ols_hc3'](matrix, outcome)
    assert fit['beta'] == pytest.approx(effect, abs=1e-12)
    assert current()['candidate_policy_code'] == 1 and current()['candidate_random_code'] == 0
    assert current()['lower_is_better'] is True

def test_actual_bh_helper_does_not_create_fdr_pipeline():
    assert benjamini_hochberg({'a': .001, 'b': .02, 'c': .8}) == {'a': True, 'b': True, 'c': False}
    assert current()['bh_helper_is_full_fdr_pipeline'] is False
    report = read(TASK / 'outputs/analysis-report-template.json')
    assert report['secondary_fdr']['family_ref'] is report['secondary_fdr']['method'] is None
    assert report['secondary_fdr']['results'] == []

def test_core_route_optional_extension_partial_activity_required():
    route = read(GOV / 'audit_upgrade/release_routes_v1.2.json')
    assert 'A-04' in route['routes']['stage1_only']['not_required_to_mark_done']
    assert route['routes']['stage1_only']['must_have_no_stage3_activity'] is True
    assert {'A-04', 'U12-08'} <= set(route['routes']['with_stage3']['required_done'])
    assert {'deviations', 'stop_records', 'fallback_exposure'} <= set(route['routes']['with_stage3']['required_result_families'])
    assert current()['optional_stage3_required_for_core_paper'] is False
    assert current()['primary_reporting_blocked_by_guard_or_scci'] is False
    assert current()['stage1_classifier_applies_without_extension_contract'] is False

def test_empty_report_is_not_estimated_or_signed():
    report = read(TASK / 'outputs/analysis-report-template.json')
    assert report['status'] == report['primary']['status'] == report['result_category'] == 'NOT_RUN'
    assert report['primary']['contrast'] == 'policy_minus_random'
    for key in ('estimate', 'ci_lower', 'ci_upper', 'p_value', 'n'):
        assert report['primary'][key] is None
    assert all(value is None for value in report['participant_flow'].values())
    assert all(value is None for value in report['human_review'].values())
    assert report['independent_reproduction_ref'] is None
    assert current()['equivalence_confirmatory_enabled'] is current()['formal_analysis_implemented'] is False

def test_sources_and_active_consumers():
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).is_file(), path
    for relative in ('12_步骤11_离线处理分析与论文写作/00_第11步计划.md',
                     '12_步骤11_离线处理分析与论文写作/01_详细执行方案.md',
                     '22_离线处理与科研分析/06_统计模型与图表计划.md'):
        path = PLAN / relative
        assert 'agent/tasks/A-04/outputs/current-analysis.md' in path.read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            assert (path.parent / link).resolve().exists(), link
    modules = (ROOT / 'PROJECT_MODULES.md').read_text(encoding='utf-8')
    assert '| V4 | 锁库、双分析、三重门' not in modules
    assert 'agent/tasks/A-04/outputs/current-analysis.md' in modules
    for path in (TASK / 'TASK.md', TASK / 'outputs/current-analysis.md'):
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
    assert current()['normalization_is_business_completion'] is current()['root_migration_complete'] is False
