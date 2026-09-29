import csv
import importlib.util
from itertools import permutations
import json
from pathlib import Path
import re
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
TECH = ROOT / 'agent/modules'
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(TECH))
sys.path.insert(0, str(TECH / '08-随机化'))
sys.path.insert(0, str(ROOT / 'agent/tasks/X-01/execution'))
from srp_randomization import generate_list
from srp_session_core import SessionCore, SessionCoreError, SessionStatus


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def current():
    return read(TASK / 'outputs/current-extension.json')


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def factories():
    spec = importlib.util.spec_from_file_location('g04_existing_fixtures', TECH / 'tests/session_core/conftest.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.manifest_factory.__wrapped__(), module.assignment_factory.__wrapped__()


def test_registration_roles_and_optional_core_route():
    row = next(r for r in rows(GOV / '05_可领取任务包.csv') if r['task_id'] == 'G-04')
    value = current()
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['depends_on'].split('|') == value['depends_on'] == ['E-05', 'X-03', 'Z-01']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is None
    route = read(GOV / 'audit_upgrade/release_routes_v1.2.json')['routes']['stage1_only']
    assert 'G-04' in route['not_required_to_mark_done']
    assert value['required_for_core_paper'] is False
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    assert protocol['stage_2_3']['required_for_core_paper'] is False
    assert protocol['formal_participant_collection_allowed'] is False


def test_two_native_arms_require_policy_contrast_not_cue_contrast():
    value = current()
    template = read(GOV / 'u12_upgrade/study_manifest_v1.2.template.json')
    # Inspect the actual candidate rather than assuming where its field lives.
    def models(obj):
        if isinstance(obj, dict):
            for key, val in obj.items():
                if key == 'primary_model':
                    yield val
                yield from models(val)
        elif isinstance(obj, list):
            for val in obj:
                yield from models(val)
    assert any('cue_mode' in model for model in models(template))
    assert value['arms'] == ['frozen_policy', 'balanced_random']
    assert value['cue_mode_both_arms'] == 'scene_native'
    assert value['candidate_treatment_variable'] == 'assigned_policy_arm'
    assert 'assigned_policy_arm' in value['candidate_primary_model']
    assert 'cue_mode' not in value['candidate_primary_model']
    assert value['contrast'] == 'policy_minus_random'
    assert value['fallback_in_estimand'] is True
    assert value['reroute_fallback_to_random_arm'] is False


def test_actual_stage3_allocation_is_not_dynamic_sequence_implementation():
    plan = generate_list('stage_3', ('SYNTHETIC-G04',), 1, b'g04-synthetic-not-formal')
    value = current()
    assert len(plan.records) == plan.block_size == value['randomization_block_size_implemented'] == 48
    random = [r for r in plan.records if r.arm == 'balanced_random']
    policy = [r for r in plan.records if r.arm == 'frozen_policy']
    assert len(random) == len(policy) == value['balanced_random_sequences_per_block'] == 24
    assert {r.weather_sequence for r in random} == set(permutations(('storm', 'heat', 'snow', 'fade')))
    assert all(r.weather_sequence is None for r in policy)
    assert all(r.arm_behavior_probability == 0.5 for r in plan.records)
    assert value['policy_sequence_in_allocation_list'] is None


@pytest.mark.parametrize('mode', ['dev_replay', 'formal_stage_3'])
def test_actual_dynamic_policy_rejected_without_control(mode):
    manifest_factory, assignment_factory = factories()
    manifest = manifest_factory(schema_version='2.2', study_stage='stage_3', runtime_mode=mode, assignment_arm='frozen_policy')
    manifest['strategy_version'] = 'SYNTHETIC-G04-NOT-APPROVED'
    core = SessionCore()
    with pytest.raises(SessionCoreError) as error:
        core.prepare(manifest, assignment_factory(manifest), 0)
    assert error.value.code == 'ADAPTIVE_SEQUENCE_REQUIRES_V2_2'
    assert core.snapshot().status is SessionStatus.CREATED
    assert core.control_log == ()
    assert current()['v22_dynamic_policy_supported'] is False


def test_actual_fixed_random_formal_gate_is_separate_from_protocol_document():
    manifest_factory, assignment_factory = factories()
    manifest = manifest_factory(schema_version='2.2', study_stage='stage_3', runtime_mode='formal_stage_3', assignment_arm='balanced_random')
    core = SessionCore()
    with pytest.raises(SessionCoreError) as error:
        core.prepare(manifest, assignment_factory(manifest), 0)
    assert error.value.code == 'FORMAL_GATE_UNAVAILABLE'
    assert core.control_log == ()
    assert current()['default_formal_adapters_fail_closed'] is True
    assert current()['protocol_flag_is_runtime_interceptor'] is False


def test_actual_activity_scope_has_no_real_receipts():
    matrix = rows(GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv')
    direct = [r for r in matrix if 'G-04' in r['activity'].split('|')]
    assert [r['capability_id'] for r in direct] == current()['required_direct_activity_capabilities']
    assert len(direct) == 3
    assert all(r['status'] == 'PENDING_EXTERNAL' and not r['evidence_ref'] for r in direct)
    assert current()['qualified_direct_activity_capabilities'] == 0
    for name in ['QUESTIONNAIRE_PERMISSION', 'FORMAL_MACHINE']:
        row = next(r for r in matrix if r['capability_id'] == name)
        assert 'G-04' not in row['activity'].split('|')
        assert row['status'] == 'PENDING_EXTERNAL' and not row['evidence_ref']
    assert current()['shared_questionnaire_stage3_scope_verified'] is False
    assert current()['shared_formal_machine_stage3_scope_verified'] is False


def test_unfilled_outline_does_not_approve_real_extension():
    value = current()
    outline = read(TASK / 'outputs/preregistration-review-template.json')
    assert 'UNFILLED' in json.dumps(outline)
    assert value['real_stage3'] == 'NOT_RUN'
    assert value['formal_collection_allowed'] is False
    for name in ['final_randomized_n', 'recruitment_cap', 'formal_gate3_definition', 'formal_pf_margin', 'actual_policy_manifest', 'actual_preregistration_receipt', 'real_responsible_people']:
        assert value[name] is None
    assert value['same_unity_build_verified'] is value['shared_presentation_config_verified'] is False
    assert value['new_unexposed_cohort_required'] is True
    assert value['root_migration_complete'] is False


def test_real_sources_current_consumers_and_wording():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for file in [PLAN / '23_后续可解释序列编排研究/00_后续研究总设计.md', PLAN / '23_后续可解释序列编排研究/01_数据与方法储备.md', PLAN / '00_总控/02_当前状态与不可跨越门禁.md', GOV / '04_可领取树型任务包_v2.0.md']:
        assert 'agent/tasks/G-04/outputs/current-extension.md' in file.read_text(encoding='utf-8')
    for file in [TASK / 'TASK.md', TASK / 'outputs/current-extension.md']:
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', file.read_text(encoding='utf-8'))
