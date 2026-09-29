import csv
import hashlib
from itertools import permutations
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
MODULE = ROOT / '02-技术研发/08-随机化'
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(ROOT / 'agent/tasks/X-01/execution'))
from srp_randomization import generate_list, policy_decisions


def current():
    return json.loads((TASK / 'outputs/current-policy.json').read_text(encoding='utf-8'))


def test_real_registry_dependencies_and_unimplemented_status():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'X-02')
    value = current()
    assert value['business_status'] == row['status'] == 'WAIT_DEP'
    assert value['depends_on'] == row['depends_on'].split('|') == ['A-03']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is None
    assert value['model_implemented'] is value['ope_implemented'] is value['policy_frozen'] is False


def test_live_core_route_does_not_require_optional_policy():
    route = json.loads((GOV / 'audit_upgrade/release_routes_v1.2.json').read_text(encoding='utf-8'))
    assert 'X-02' in route['routes']['stage1_only']['not_required_to_mark_done']
    assert current()['required_for_core_paper'] is False


def test_all_split_and_resample_units_are_participants():
    value = current()
    for field in ('independent_unit', 'outer_split_unit', 'inner_split_unit', 'bootstrap_unit'):
        assert value[field] == 'participant'
    assert value['scaler_fit_scope'] == 'TRAINING_PARTICIPANTS_OF_CURRENT_FOLD_ONLY'
    assert value['training_data'] == 'LOCKED_STAGE1'


def test_decision_state_excludes_future_endpoint_identity_and_ecg():
    value = current()
    assert set(value['online_state_fields']).isdisjoint(value['forbidden_online_fields'])
    assert {'panas_post', 'ecg_features', 'stage3_outcomes', 'participant_identity', 'future_module_features'} <= set(value['forbidden_online_fields'])
    assert 'panas_pre' in value['online_state_fields']
    assert value['formal_reward_definition'] is None


def test_actual_native_allocation_and_conditional_probability():
    plan = generate_list('stage_1', ('SYNTHETIC',), 1, b'x02-grouped-input-test')
    records = [r for r in plan.records if r.arm == current()['training_arm']]
    assert len(records) == 24
    assert {r.weather_sequence for r in records} == set(permutations(('storm', 'heat', 'snow', 'fade')))
    for record in records:
        decisions = policy_decisions(session_id='SYNTHETIC-X02', stage='stage_1', sequence=record.weather_sequence, created_monotonic_ns=0)
        product = 1
        for decision in decisions:
            assert decision['behavior_probability'] == 1 / len(decision['candidate_actions'])
            assert decision['target_policy_probability'] is None
            product *= decision['behavior_probability']
        assert abs(product - 1 / 24) < 1e-12
    assert current()['behavior_probability_is_target_probability'] is False


def test_actual_v22_record_is_not_full_target_distribution():
    schema = json.loads((ROOT / '02-技术研发/05-通信协议/contracts/runtime-contract-v2.2.schema.json').read_text(encoding='utf-8'))
    decision = policy_decisions(session_id='SYNTHETIC-X02', stage='stage_1', sequence=('fade', 'heat', 'storm', 'snow'), created_monotonic_ns=0)[0]
    Draft202012Validator(schema).validate(decision)
    assert {'behavior_probability', 'target_policy_probability', 'candidate_actions', 'fallback_applied', 'random_draw', 'state_snapshot_hash'} <= set(schema['$defs']['policy_decision']['required'])
    assert decision['target_policy_probability'] is None
    assert current()['state_hash_is_actual_physiological_state'] is False


def test_freeze_artifacts_and_thresholds_not_filled_from_candidate():
    value = current()
    for field in ('ope_estimator', 'formal_uniform_mixture', 'minimum_support', 'minimum_ess', 'temperature', 'actual_model_artifact', 'actual_ope_report', 'actual_ess_report'):
        assert value[field] is None
    assert value['legacy_uniform_mixture_candidate'] == 0.2
    assert value['fallback_in_deployment_estimand'] is True
    assert {'predecision_state', 'ordered_candidate_actions', 'seed', 'model_version'} <= set(value['replay_identity'])


def test_actual_archive_bytes_and_legacy_consumer_repaired():
    expected = {
        '00_后续研究总设计.md': 'E0388B7482BE1CE03677A4C8EC807D15785F745ECB11BAD27CA484A3E796732A',
        '01_数据与方法储备.md': '74DE0B841CFCB05BFA5C649145B44B8627920FC049F877277A754BC111A6BAA0',
    }
    for name, digest in expected.items():
        assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == digest
    legacy = (PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py').read_text(encoding='utf-8')
    assert 'LEGACY_POLICY = PROJECT_ROOT / "agent/tasks/X-02/archive"' in legacy
    assert 'LEGACY_POLICY / "00_后续研究总设计.md"' in legacy
    assert current()['legacy_gate_order_current'] is False


def test_source_references_and_actual_navigation():
    sources = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))
    for path in sources['paths']:
        assert (ROOT / path).is_file(), path
    for name in ('00_后续研究总设计.md', '01_数据与方法储备.md'):
        path = PLAN / '23_后续可解释序列编排研究' / name
        text = path.read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)', text):
            assert (path.parent / link).resolve().is_file(), link
