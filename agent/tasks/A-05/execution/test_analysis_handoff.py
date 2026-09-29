"""Inspect candidate helpers and actual input gaps without fitting real data."""
import csv
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys

import numpy as np
import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
SAP = ROOT / 'agent/tasks/U12-04/execution'
sys.path.insert(0, str(ROOT / 'agent/modules/02-信号处理'))
from a03_gate2_spec import ItemResponse, ResponseStatus, benjamini_hochberg, score_panas


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def current():
    return read(TASK / 'outputs/current-analysis.json')


def test_registry_and_actual_input_gaps():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'A-05')
    value = current()
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['depends_on'].split('|') == value['depends_on'] == ['A-02', 'A-03', 'E-04']
    assert row['kind'] == 'FIXED' and row['claimant'] == row['reviewer'] == ''
    assert value['real_data_analysis'] == 'NOT_RUN'
    assert value['research_lock_id'] is value['unblind_authorization'] is value['formal_sap_ref'] is None
    assert read(ROOT / 'agent/tasks/E-04/outputs/current-closeout.json')['research_lock_signed'] is False
    assert read(ROOT / 'agent/tasks/A-03/outputs/current-statistics.json')['milestones']['REAL'] == 'NOT_DELIVERED'


def test_primary_and_guard_match_current_authority():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    for key, value in current()['primary'].items():
        assert value == protocol['primary'][key], key
    assert current()['functional_guard']['analysis_sets'] == protocol['functional_guard']['analysis_sets']
    assert current()['functional_guard']['margin_candidate'] == protocol['functional_guard']['noninferiority_margin_candidate']
    assert current()['functional_guard']['blocks_affect_reporting'] is False
    assert current()['scci_role'] == 'MANIPULATION_CHECK_ONLY'
    assert current()['equivalence_confirmatory_enabled'] is current()['sensor_failure_drops_valid_panas'] is False


@pytest.mark.parametrize('effect', [-0.4, 0., 0.4])
def test_actual_candidate_hc3_preserves_native_minus_abstract_direction(effect):
    module = runpy.run_path(str(SAP / 'power_simulation.py'))
    cue = np.tile([0., 1.], 12)
    pre = np.random.default_rng(529).normal(size=24)
    strata = np.repeat([0., 1.], 12)
    X = np.column_stack([np.ones(24), cue, pre, strata])
    y = 5. + effect * cue + 0.5 * pre + 0.1 * strata
    fit = module['_ols_hc3'](X, y)
    assert fit['beta'] == pytest.approx(effect, abs=1e-12)
    assert current()['primary']['lower_is_better'] is True


def test_actual_bh_helper_is_not_an_analysis_family_or_real_result():
    assert benjamini_hochberg({'a': 0.001, 'b': 0.02, 'c': 0.8}) == {'a': True, 'b': True, 'c': False}
    assert current()['bh_helper_is_full_fdr_pipeline'] is False
    rows = [ItemResponse('p', ResponseStatus.RESPONDED, 3), ItemResponse('n', ResponseStatus.RESPONDED, 2)]
    with pytest.raises(ValueError, match='PANAS_FORMAL_SCORING_REQUIRES_A03_CAL'):
        score_panas(rows, positive_item_ids=['p'], negative_item_ids=['n'])


def test_empty_report_and_training_release_do_not_invent_results():
    report = read(TASK / 'outputs/analysis-report-template.json')
    assert report['status'] == report['primary']['status'] == report['result_category'] == 'NOT_RUN'
    for key in ('beta', 'ci_lower', 'ci_upper', 'p_value', 'n'):
        assert report['primary'][key] is None
    assert all(value is None for value in report['human_review'].values())
    assert all(value is None for value in report['optional_training'].values())
    assert current()['approved_training_release'] is None
    assert current()['online_state_may_include_post_panas'] is False
    assert current()['observed_case_is_complete_four_module'] is current()['power_script_is_formal_mi_analysis'] is False
    assert current()['result_classifier'] == 'U12-10_CANDIDATE_ONLY_FORMAL_NOT_DELIVERED'


def test_candidate_signature_preserved_and_differences_recorded():
    assert read(SAP.parent / 'outputs/contract.json')['status'] == 'CANDIDATE_NOT_RESEARCH_FROZEN'
    signature = read(GOV / 'u12_upgrade/acceptance/U12-04.json')
    assert signature['human_review']['status'] == 'PASS' and signature['human_review']['reviewer'] == '傅钧烨'
    impact = (TASK / 'evidence/consumer-impact.md').read_text(encoding='utf-8')
    assert 'OBSERVED_CASE只筛后测可观察' in impact
    assert '48为总块、每臂24顺序' in impact
    assert 'FIXED_ACTIVE_SAP_WORDING_REVIEW_PENDING' in impact


def test_archived_questionnaire_and_current_navigation():
    name = '05_问卷与访谈处理.md'
    assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == '58BDB7DCDD1708F164FA233C258689AD5E18F67C299195E8F48F4B57BC501CE7'
    validator = runpy.run_path(str(PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py'))
    assert TASK / 'archive' / name in validator['ACTIVE_FILES']
    assert TASK / 'archive' / name in validator['REQUIRED_MARKERS']
    for relative in ('22_离线处理与科研分析/05_问卷与访谈处理.md',
                     '22_离线处理与科研分析/06_统计模型与图表计划.md',
                     '12_步骤11_离线处理分析与论文写作/00_第11步计划.md',
                     '12_步骤11_离线处理分析与论文写作/01_详细执行方案.md'):
        path = PLAN / relative
        assert 'agent/tasks/A-05/outputs/current-analysis.md' in path.read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            assert (path.parent / link).resolve().exists(), link


def test_sources_and_reporting_boundaries():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    text = (TASK / 'outputs/current-analysis.md').read_text(encoding='utf-8')
    assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', text)
    assert current()['optional_stage3_required_for_core_paper'] is current()['normalization_is_business_completion'] is False
    assert '原生优效' not in read(TASK / 'outputs/analysis-report-template.json')['result_category']
