"""Verify actual allocation interfaces, archived sources and blank handoff."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(ROOT / '02-技术研发/08-随机化'))
from srp_randomization import generate_list


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def current():
    return read(TASK / 'outputs/current-batch.json')


def test_current_template_state_and_empty_actual_instances():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'B-02')
    value = current()
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['kind'] == value['task_kind'] == 'TEMPLATE'
    assert row['depends_on'].split('|') == value['depends_on'] == ['G-03']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['instances'] == [] and value['actual_batch_count'] == 0
    assert value['real_activity'] == 'NOT_RUN'
    assert value['historical_acceptance'] is value['real_roles'] is None
    assert value['formal_collection_allowed'] is value['normalization_is_business_completion'] is False


def test_real_generator_stage_one_full_block_and_batch_are_different_units():
    plan = generate_list('stage_1', ('all',), 1, b'b02-synthetic-test-only')
    assert len(plan.records) == 48
    assert Counter(r.arm for r in plan.records) == {'scene_native': 24, 'abstract_pacer': 24}
    for arm in ('scene_native', 'abstract_pacer'):
        assert len({r.weather_sequence for r in plan.records if r.arm == arm}) == 24
    assert current()['max_batch'] == 12
    assert current()['x01_variable_blocks_supported'] is False
    assert current()['fixed_batch_count_required'] is current()['per_batch_equal_arm_counts_required'] is False
    assert current()['partial_block_is_automatic_protocol_failure'] is False


def test_final_n_and_formal_training_still_require_real_freeze():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    freeze = read(ROOT / 'agent/tasks/G-03/outputs/current-freeze.json')
    assert protocol['sample_planning']['formal_randomized_n'] is current()['formal_randomized_n'] is None
    assert current()['formal_recruitment_cap'] is None
    assert freeze['formal_collection_allowed'] is current()['formal_timing_frozen'] is False
    assert protocol['training']['condition_specific_training_after_panas_pre'] is True
    assert protocol['stage_2_3']['required_for_core_paper'] is False


def test_empty_register_and_qc_have_real_source_families_not_approvals():
    with (TASK / 'outputs/batch-register-template.csv').open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        assert list(reader) == []
        assert {'frozen_study_ref', 'preregistration_receipt_ref', 'assigned', 'exposed', 'completed',
                'stopped_after_exposure', 'cancelled_before_exposure', 'pending', 'qc_ref'} <= set(reader.fieldnames)
        assert not {'phone', 'name', 'hmac', 'password'} & set(reader.fieldnames)
    qc = read(TASK / 'outputs/batch-qc-template.json')
    assert qc['study_stage'] == 'stage_1' and qc['status'] == 'NOT_RUN'
    assert all(v is None for v in qc['counts'].values())
    assert qc['lock_and_unblind_authorized'] is False
    assert all(v is None for v in qc['review'].values())
    assert qc['archive_integrity']['status'] == qc['raw_evidence_bundle']['status'] == 'NOT_CHECKED'
    schema = read(ROOT / '02-技术研发/srp_session_store/contracts/raw-evidence-bundle-v1.schema.json')
    assert set(qc['raw_evidence_bundle']['required_sources']) == set(schema['properties']['families']['items']['enum'])


def test_stopping_exposure_missingness_and_reporting_are_not_redefined():
    value = current()
    assert value['balance_unit'] == 'assigned_not_complete'
    assert value['completion_based_refilling_forbidden'] is value['outcome_based_optional_stopping_forbidden'] is True
    for key in ('x01_outcome_is_analysis_set_eligibility', 'first_condition_training_exposure_integrated',
                'post_exposure_repeat_allowed', 'interruption_resumes_experience',
                'primary_affect_reporting_blocked_by_functional_or_scci_failure',
                'restricted_bundle_reference_is_authorized_original_review', 'batch_completion_authorizes_unblinding'):
        assert value[key] is False
    text = (TASK / 'outputs/current-batch.md').read_text(encoding='utf-8')
    for point in ('不强制每批6比6', '操作记录的完成状态不是完整分析集', '新session_id不恢复参与资格',
                  '传感器失败不删有效PANAS', '未知值null加原因', '当前P-01仅首次核心start调用mark_exposed',
                  '已揭示分配的处理需冻结规则'):
        assert point in text


def test_stage_one_activity_receipt_is_still_pending():
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['capability_id'] == 'INSTITUTION_STAGE1')
    assert row['activity'].split('|') == ['G-03', 'B-02', 'E-04']
    assert row['status'] == 'PENDING_EXTERNAL' and row['evidence_ref'] == ''


def test_archives_and_current_consumers_are_real():
    expected = {'00_第10步计划.md': 'A3E80D0380397993FB8652AB2A7FB3C9057AB303B1E64E282B2D2F912F062860',
                '01_详细执行方案.md': '4E84807D9CC53F8A5484C688FB4AE650B509BAAFD089FA9033454126140E9518'}
    validator = (PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py').read_text(encoding='utf-8')
    for name, digest in expected.items():
        assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == digest
        assert f'LEGACY_EXECUTION / "{name}"' in validator
        path = PLAN / '11_步骤10_正式研究执行' / name
        text = path.read_text(encoding='utf-8')
        assert 'agent/tasks/B-02/outputs/current-batch.md' in text
        for link in re.findall(r'\]\(([^)]+)\)', text):
            assert (path.parent / link).resolve().exists(), link


def test_current_inputs_and_language():
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).is_file(), path
    text = (TASK / 'outputs/current-batch.md').read_text(encoding='utf-8')
    assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', text)
    assert not list((TASK / 'outputs').glob('*manifest*.json'))
