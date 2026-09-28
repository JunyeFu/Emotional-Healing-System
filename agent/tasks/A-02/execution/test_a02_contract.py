"""Inspect existing specifications; these are not A-02 model acceptance tests."""
import hashlib
import json
from pathlib import Path
import re
import runpy

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/A-02'
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
SAP = PLAN / '24_团队任务与项目治理/u12_upgrade/U12-04_panas_sap'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def test_archive_bytes():
    for item in read(TASK / 'inputs/legacy-relocations.json')['files']:
        assert hashlib.sha256((TASK / 'archive' / item['name']).read_bytes()).hexdigest().upper() == item['sha256']


def test_current_navigation():
    path = PLAN / '22_离线处理与科研分析/06_统计模型与图表计划.md'
    for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        assert (path.parent / link).resolve().is_file(), link
    assert 'Gate 1通过后' not in path.read_text(encoding='utf-8')


def test_current_opportunity_definitions_match_S02():
    candidate = read(TASK / 'outputs/current-statistics.json')
    source = read(ROOT / 'agent/tasks/S-02/outputs/current-events.json')
    for key in ('opportunity_states', 'opportunity_completion_rate', 'pf_observable',
                'pf_conservative', 'module_weights', 'missing_module_may_reweight'):
        assert candidate[key] == source[key]
    assert candidate['zero_denominator_value'] is None


def test_current_freeze_and_missingness_match_authority():
    candidate = read(TASK / 'outputs/current-statistics.json')
    authority = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    guard = candidate['functional_guard']
    assert guard['margin_candidate'] == authority['functional_guard']['noninferiority_margin_candidate']
    assert guard['blocks_affect_reporting'] is False
    assert guard['all_modules_noninferior_from_mean'] is False
    for key in ('affect_and_sensor_separated', 'sensor_failure_does_not_drop_valid_panas',
                'candidate_imputations', 'model_and_mnar_grid', 'status'):
        assert candidate['missingness'][key] == authority['missingness'][key]
    assert candidate['missingness']['pooling_rules'] is None
    assert candidate['formal_n'] is None
    assert not candidate['equivalence_enabled']
    assert candidate['business_status'] == 'WAIT_DEP'
    assert candidate['owner'] is None
    assert candidate['implementation'] == 'ANALYSIS_SET_MI_AND_SENSITIVITY_PIPELINE_NOT_DELIVERED'


def test_signed_candidate_is_not_research_freeze():
    contract = read(SAP / 'contract.json')
    acceptance = read(SAP.parent / 'acceptance/U12-04.json')
    assert acceptance['human_review']['status'] == 'PASS'
    assert acceptance['human_review']['reviewer'] == '傅钧烨'
    assert contract['status'] == 'CANDIDATE_NOT_RESEARCH_FROZEN'
    assert contract['missingness']['model_and_mnar_grid'] is None
    assert contract['formal_collection_allowed'] is False


def test_actual_power_missingness_is_carried_forward_not_MI(monkeypatch):
    module = runpy.run_path(str(SAP / 'power_simulation.py'))
    replicate = module['_replicate']
    data = {
        'cue': np.array([0., 0., 1., 1., 0., 0., 1., 1.]),
        'strata': np.array([0., 1., 0., 1., 0., 1., 0., 1.]),
        'pre': np.arange(8.) + 20.,
        'post': np.arange(8.) + 30.,
        'observed': np.array([True, False, True, True, True, False, True, True]),
    }
    calls = []
    def capture_fit(X, y):
        calls.append((X.copy(), y.copy()))
        return {'beta': 0., 'se': 1.}
    monkeypatch.setitem(replicate.__globals__, '_generate_participants', lambda *args: data)
    monkeypatch.setitem(replicate.__globals__, '_ols_hc3', capture_fit)
    result = replicate(np.random.default_rng(1), 8, 0.)
    assert set(result) == {'PRIMARY_CONSERVATIVE', 'OBSERVED_CASE'}
    assert len(calls) == 2
    np.testing.assert_array_equal(calls[0][1], data['post'][data['observed']])
    np.testing.assert_array_equal(calls[1][1], np.where(data['observed'], data['post'], data['pre']))
    assert calls[0][0].shape[0] == 6
    assert calls[1][0].shape[0] == 8


@pytest.mark.parametrize('effect', [-0.3, 0., 0.3])
def test_existing_synthetic_grid_is_deterministic_not_MI(effect):
    module = runpy.run_path(str(SAP / 'power_simulation.py'))
    args = dict(seed=20260929, replications=100, n_grid=(48,), effect_grid=(effect,))
    first = module['run_power_grid'](**args)
    assert first == module['run_power_grid'](**args)
    assert first['evidence_class'] == 'DESIGN_AND_SYNTHETIC_ONLY'
    assert first['frozen'] == {'n_frozen': False, 'effect_frozen': False}
    assert first['test'] == 'two_sided'
    assert 'MISSINGNESS_POLICY_PRE_FREEZE' in first['limitations']


def test_legacy_statistics_validator_consumes_archive():
    module = runpy.run_path(str(PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py'))
    archive = TASK / 'archive/06_统计模型与图表计划.md'
    assert archive in module['ACTIVE_FILES']
    assert archive in module['REQUIRED_MARKERS']
    assert module['main']() == 0


def test_sources_exist():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
