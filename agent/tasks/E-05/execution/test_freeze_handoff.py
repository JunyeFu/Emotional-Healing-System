import csv
from itertools import permutations
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(ROOT / '02-技术研发/08-随机化'))
sys.path.insert(0, str(ROOT / 'agent/tasks/X-01/execution'))
from srp_randomization import generate_list, policy_decisions


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def current():
    return read(TASK / 'outputs/current-freeze.json')


def registry():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        return {r['task_id']: r for r in csv.DictReader(stream)}


def test_registry_actual_dependencies_and_unclaimed_scope():
    value, row = current(), registry()['E-05']
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['depends_on'].split('|') == value['depends_on'] == ['A-05', 'X-02']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is None
    assert read(ROOT / 'agent/tasks/A-05/outputs/current-analysis.json')['real_data_analysis'] == 'NOT_RUN'


def test_selection_criteria_timing_is_not_final_fit_timing():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')['stage_2_3']
    value = current()
    assert protocol['selection_criteria_freeze_before_core_unblinding'] is True
    assert value['selection_criteria_freeze_before_core_unblinding'] is True
    assert value['selection_criteria_receipt'] is None
    assert value['selection_criteria_verified'] is False
    assert value['final_model_freeze'] == 'AFTER_LOCKED_TRAINING_AND_INDEPENDENT_REVIEW'


def test_real_u12_08_is_downstream_analysis_not_freeze_prerequisite():
    row = registry()['U12-08']
    assert row['depends_on'] == 'A-04|E-05'
    assert '分析附录' in row['title']
    assert current()['u12_08_is_freeze_prerequisite'] is False
    for task, name in [('X-02', 'current-policy.md'), ('X-03', 'current-runtime.md')]:
        for path in [ROOT / f'agent/tasks/{task}/TASK.md', ROOT / f'agent/tasks/{task}/outputs/{name}', ROOT / f'agent/tasks/{task}/outputs/summary.json']:
            assert 'E-05/U12-08' not in path.read_text(encoding='utf-8')


def test_optional_core_route_never_waits_for_policy_freeze():
    route = read(GOV / 'audit_upgrade/release_routes_v1.2.json')['routes']['stage1_only']
    assert 'E-05' in route['not_required_to_mark_done']
    assert current()['required_for_core_paper'] is False
    assert current()['fallback_is_stage3_authorization'] is False


def test_actual_native_permutations_and_prefix_probabilities():
    records = generate_list('stage_1', ('SYNTHETIC',), 1, b'e05-probability-audit').records
    records = [r for r in records if r.arm == current()['training_arm']]
    assert {r.weather_sequence for r in records} == set(permutations(('storm', 'heat', 'snow', 'fade')))
    schema = read(ROOT / '02-技术研发/05-通信协议/contracts/runtime-contract-v2.2.schema.json')
    for record in records:
        decisions = policy_decisions(session_id='SYNTHETIC-E05', stage='stage_1', sequence=record.weather_sequence, created_monotonic_ns=0)
        product = 1.0
        for position, decision in enumerate(decisions):
            Draft202012Validator(schema).validate(decision)
            assert set(decision['candidate_actions']) == set(record.weather_sequence[position:])
            assert decision['behavior_probability'] == 1 / (4 - position)
            assert decision['target_policy_probability'] is None
            product *= decision['behavior_probability']
        assert abs(product - 1 / 24) < 1e-12
        assert decisions[-1]['behavior_probability'] == 1
    assert current()['selected_action_probability_is_full_distribution'] is False


def test_candidate_is_not_formal_parameter_or_empirical_report():
    value = current()
    assert value['uniform_mixture_candidate'] == 0.2
    for field in ('formal_reward', 'ope_estimator', 'minimum_support', 'minimum_ess', 'entropy_threshold', 'calibration_threshold', 'stability_threshold', 'formal_uniform_mixture', 'actual_model', 'actual_ope_report', 'actual_ess_report', 'actual_policy_manifest', 'actual_freeze_signature'):
        assert value[field] is None
    assert value['uniform_fallback_is_superiority_evidence'] is False
    assert value['final_model_fit_is_cross_fitted_evaluation'] is False
    assert value['real_freeze'] == 'NOT_RUN'


def test_participant_grouping_and_forbidden_state_match_upstream():
    value = current()
    upstream = read(ROOT / 'agent/tasks/X-02/outputs/current-policy.json')
    assert value['split_unit'] == upstream['outer_split_unit'] == upstream['inner_split_unit'] == 'participant'
    assert value['scaler_scope'] == 'TRAINING_FOLD_ONLY'
    assert set(value['forbidden_online_fields']) == set(upstream['forbidden_online_fields'])
    assert upstream['model_implemented'] is upstream['ope_implemented'] is upstream['policy_frozen'] is False


def test_empty_review_outline_does_not_authorize_or_sign():
    value = read(TASK / 'outputs/policy-review-template.json')
    assert value['status'] == 'NOT_RUN'
    assert value['decision'] == 'NOT_DECIDED'
    assert value['stage3_authorized'] is value['superiority_claim_allowed'] is False
    assert all(v is None for v in value['human_signoff'].values())
    assert all(v is None for v in value['pre_unblinding_selection_criteria'].values())
    assert value['artifact_hashes'] is value['final_refit_model'] is value['cross_fitted_ope_report'] is None


def test_navigation_and_source_paths_are_real():
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).is_file(), path
    for name in ('00_后续研究总设计.md', '01_数据与方法储备.md'):
        path = PLAN / '23_后续可解释序列编排研究' / name
        text = path.read_text(encoding='utf-8')
        assert 'agent/tasks/E-05/outputs/current-freeze.md' in text
        for link in re.findall(r'\]\(([^)]+)\)', text):
            assert (path.parent / link).resolve().is_file(), link
    assert len(list((TASK / 'archive').iterdir())) == 1
    assert current()['root_migration_complete'] is False


def test_current_word_sources_use_compliant_terms():
    text = (TASK / 'outputs/current-freeze.md').read_text(encoding='utf-8')
    assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', text)
    assert '不复制' in (TASK / 'archive/README.md').read_text(encoding='utf-8')
