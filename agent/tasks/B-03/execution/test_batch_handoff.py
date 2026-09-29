from collections import Counter
import csv
import importlib.util
from itertools import permutations
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
TECH = ROOT / '02-技术研发'
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(TECH))
sys.path.insert(0, str(TECH / '08-随机化'))
sys.path.insert(0, str(ROOT / 'agent/tasks/X-01/execution'))
from srp_randomization import generate_list, policy_decisions
from srp_session_core import RuntimeDependencies, SessionCore
from srp_session_store import DurableManifestStore, RecordingSessionCore, ReplayReader, SessionReplayer


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def current():
    return read(TASK / 'outputs/current-batch.json')


def factories():
    spec = importlib.util.spec_from_file_location('b03_existing_core_fixtures', TECH / 'tests/session_core/conftest.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.manifest_factory.__wrapped__(), module.assignment_factory.__wrapped__()


def test_actual_template_is_unexecuted_and_unclaimed():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'B-03')
    value = current()
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['kind'] == value['task_kind'] == 'TEMPLATE'
    assert row['depends_on'].split('|') == value['depends_on'] == ['G-04']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is value['real_roles'] is value['historical_acceptance'] is None
    assert value['real_activity'] == 'NOT_RUN'
    assert value['instances'] == [] and value['actual_batch_count'] == 0


def test_actual_stage3_block_and_twelve_person_batch_are_distinct():
    plan = generate_list('stage_3', ('SYNTHETIC-B03',), 1, b'b03-synthetic-not-formal')
    value = current()
    assert len(plan.records) == plan.block_size == value['x01_block_size'] == 48
    assert Counter(r.arm for r in plan.records) == {'balanced_random': 24, 'frozen_policy': 24}
    assert {r.weather_sequence for r in plan.records if r.arm == 'balanced_random'} == set(permutations(('storm', 'heat', 'snow', 'fade')))
    assert all(r.weather_sequence is None for r in plan.records if r.arm == 'frozen_policy')
    assert value['max_batch'] == 12
    assert value['per_batch_equal_arm_counts_required'] is False
    assert value['policy_actual_sequences_must_cover_24_permutations'] is False


def test_actual_random_policy_messages_are_not_full_state_or_probability_vector():
    schema = read(TECH / '05-通信协议/contracts/runtime-contract-v2.2.schema.json')
    fields = schema['$defs']['policy_decision']['properties']
    assert 'behavior_probability' in fields and 'state_snapshot_hash' in fields
    assert not {'candidate_probabilities', 'state_snapshot', 'full_distribution'} & set(fields)
    plan = generate_list('stage_3', ('SYNTHETIC-B03',), 1, b'b03-probability-not-policy')
    for row in plan.records:
        if row.arm != 'balanced_random':
            continue
        decisions = policy_decisions(session_id='SYNTHETIC-B03', stage='stage_3', sequence=row.weather_sequence, created_monotonic_ns=0)
        for position, message in enumerate(decisions):
            Draft202012Validator(schema).validate(message)
            assert message['behavior_probability'] == 1 / (4 - position)
            assert message['target_policy_probability'] is None
            assert set(message['candidate_actions']) == set(row.weather_sequence[position:])
            selected = message['candidate_actions'].index(message['selected_action'])
            assert message['random_draw'] == (selected + 0.5) / len(message['candidate_actions'])
    assert current()['policy_message_contains_full_distribution'] is False
    assert current()['uniform_helper_is_actual_policy_rng'] is False


def test_actual_fixed_stage3_recording_is_replayable_but_not_policy_deployment(tmp_path):
    manifest_factory, assignment_factory = factories()
    manifest = manifest_factory(schema_version='2.2', study_stage='stage_3', assignment_arm='balanced_random')
    assignment = assignment_factory(manifest)
    store = DurableManifestStore.development(tmp_path)
    dependencies = RuntimeDependencies.development()
    dependencies.manifest_store = store
    recorder = RecordingSessionCore(SessionCore(dependencies=dependencies), store)
    recorder.prepare(manifest, assignment, 0)
    summary = recorder.finish('SYNTHETIC_TEST', 1)
    store.archive.seal(summary, 1)
    store.archive.close()
    reader = ReplayReader.open(tmp_path, manifest['session_id'])
    assert reader.verify().valid
    report = SessionReplayer(reader).replay_core()
    assert report.valid and report.operation_count == 2
    assert report.expected_final_hash == report.actual_final_hash
    assert len(assignment.policy_decisions) == 4
    assert current()['v22_dynamic_policy_supported'] is False
    assert current()['real_dynamic_replay'] == 'NOT_RUN'


def test_empty_register_and_qc_do_not_create_instances_or_authority():
    with (TASK / 'outputs/batch-register-template.csv').open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        assert list(reader) == []
        assert {'frozen_stage3_ref', 'assigned_arm_counts_ref', 'policy_decision_index_ref', 'fallback_exposure_ref', 'qc_ref'} <= set(reader.fieldnames)
        assert not {'phone', 'name', 'hmac', 'password'} & set(reader.fieldnames)
    qc = read(TASK / 'outputs/batch-qc-template.json')
    assert qc['study_stage'] == 'stage_3' and qc['status'] == 'NOT_RUN'
    assert all(v is None for v in qc['counts'].values())
    assert all(v is None for v in qc['review'].values())
    assert qc['policy_audit']['status'] == 'NOT_RUN'
    assert all(v is None for k, v in qc['policy_audit'].items() if k != 'status')
    assert qc['lock_and_unblind_authorized'] is False
    schema = read(TECH / 'srp_session_store/contracts/raw-evidence-bundle-v1.schema.json')
    assert set(qc['raw_evidence_bundle']['required_sources']) == set(schema['properties']['families']['items']['enum'])


def test_partial_runs_fallback_and_route_use_actual_facts():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    assert protocol['stage_2_3']['partial_runs_must_be_disclosed'] is current()['partial_runs_must_be_disclosed'] is True
    assert current()['fallback_preserves_assignment_arm'] is True
    assert current()['completion_based_refilling_forbidden'] is current()['outcome_based_optional_stopping_forbidden'] is True
    assert current()['balance_unit'] == 'assigned_not_complete'
    route = read(GOV / 'audit_upgrade/release_routes_v1.2.json')
    assert 'B-03' in route['routes']['stage1_only']['not_required_to_mark_done']
    assert 'B-03_instance_registry' in route['stage3_started_evidence_sources']
    assert route['routes']['stage1_only']['must_have_no_stage3_activity'] is True
    assert {'deviations', 'stop_records', 'fallback_exposure'} <= set(route['routes']['with_stage3']['required_result_families'])
    assert current()['batch_completion_authorizes_unblinding'] is False


def test_real_admission_and_timing_have_not_been_filled():
    freeze = read(ROOT / 'agent/tasks/G-04/outputs/current-extension.json')
    assert freeze['formal_collection_allowed'] is current()['formal_collection_allowed'] is False
    assert freeze['actual_preregistration_receipt'] is None
    for key in ['formal_randomized_n', 'formal_recruitment_cap', 'formal_stopping_rule', 'formal_tail_block_rule']:
        assert current()[key] is None
    for key in ['first_condition_training_exposure_integrated', 'post_exposure_repeat_allowed', 'interruption_resumes_experience', 'same_build_and_shared_config_verified', 'sensor_failure_drops_valid_panas']:
        assert current()[key] is False
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['capability_id'] == 'INSTITUTION_STAGE3')
    assert 'B-03' in row['activity'].split('|')
    assert row['status'] == 'PENDING_EXTERNAL' and not row['evidence_ref']


def test_sources_current_navigation_and_language():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for name in ['00_第10步计划.md', '01_详细执行方案.md']:
        file = PLAN / '11_步骤10_正式研究执行' / name
        text = file.read_text(encoding='utf-8')
        assert 'agent/tasks/B-03/outputs/current-batch.md' in text
        for link in re.findall(r'\]\(([^)]+)\)', text):
            assert (file.parent / link).resolve().exists(), link
    text = (TASK / 'outputs/current-batch.md').read_text(encoding='utf-8')
    assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', text)
    assert '注册完成条件仍写' in text
    assert not list((TASK / 'outputs').glob('*manifest*.json'))
