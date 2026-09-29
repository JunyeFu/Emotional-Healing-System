"""Verify the concrete normalization and existing research/runtime boundaries."""
import csv
import hashlib
import json
from pathlib import Path
import re

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def registry():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        return {row['task_id']: row for row in csv.DictReader(stream)}


def test_business_state_and_real_receipts_are_not_invented():
    row = registry()['G-03']
    value = read(TASK / 'outputs/current-freeze.json')
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['claimant'] == row['reviewer'] == ''
    assert value['depends_on'] == row['depends_on'].split('|')
    for key in ('claimant', 'reviewer', 'historical_acceptance', 'real_preregistration_receipt',
                'final_randomized_n', 'formal_recruitment_cap', 'minimum_important_affect_difference',
                'formal_training_seconds', 'calibration_receipt', 'u12_11_research_freeze',
                'runtime_integration_evidence', 'real_responsible_people'):
        assert value[key] is None
    assert value['formal_collection_allowed'] is value['normalization_is_business_completion'] is False


def test_existing_dependency_path_requires_runtime_migration_without_duplicate_edge():
    rows = registry()
    path = read(TASK / 'outputs/current-freeze.json')['runtime_dependency_path']
    for task, dependency in zip(path, path[1:]):
        assert dependency in rows[task]['depends_on'].split('|')
    assert rows['U12-06']['status'] == 'IN_PROGRESS'
    frozen = read(GOV / '当前解锁独立任务包/U12-06/package_manifest.json')
    assert frozen['input_snapshot_id'] == '3D3852D6A8F68C093B6963F03D1A7524BAD429C56D20D34B458AA6610C29F95B'


def test_empty_index_matches_all_fifteen_authoritative_freezes():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    value = read(TASK / 'outputs/freeze-template.json')
    assert value['status'] == 'NOT_RUN'
    assert value['formal_collection_allowed'] is value['downstream']['release_allowed'] is False
    assert list(value['required_freezes']) == protocol['required_freezes']
    assert len(value['required_freezes']) == 15
    assert all(v == {'status': 'PENDING', 'evidence_ref': None} for v in value['required_freezes'].values())
    assert all(v is None for v in value['review'].values())
    assert value['preregistration_receipt_ref'] is value['preregistration_timestamp'] is None
    assert value['frozen_study_manifest_ref'] is value['calibration_receipt_ref'] is None


def test_primary_guardrail_and_candidate_numbers_remain_separate():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    sap = read(ROOT / 'agent/tasks/U12-04/outputs/contract.json')
    assert sap['formal_collection_allowed'] is protocol['formal_participant_collection_allowed'] is False
    assert sap['primary']['outcome'] == protocol['primary']['outcome'] == 'panas_negative_affect_post_adjusted_for_pre'
    assert sap['primary']['report_even_if_functional_guard_fails'] is True
    assert protocol['functional_guard']['blocks_affect_reporting'] is False
    assert protocol['manipulation_check']['role'] == 'manipulation_only'
    assert protocol['equivalence']['confirmatory_enabled'] is False
    assert protocol['sample_planning']['formal_randomized_n'] is None
    assert protocol['missingness']['model_and_mnar_grid'] is None
    assert protocol['training']['budget_seconds'] is None
    assert protocol['functional_guard']['margin_status'] == 'INHERITED_REQUIRES_JUSTIFICATION'


def test_real_calibration_and_optional_route_are_not_reversed():
    milestones = read(GOV / 'audit_upgrade/task_milestones_v1.2.json')
    cal = next(m for m in milestones['milestones'] if m['id'] == 'A-03-CAL')
    assert cal['depends_on'] == ['A-03-REAL', 'E-03']
    assert {'G-03', 'U12-11'} <= set(cal['consumers'])
    current = read(ROOT / 'agent/tasks/A-03/outputs/current-statistics.json')
    assert current['milestones']['CAL'] == 'NOT_DELIVERED'
    routes = read(GOV / 'audit_upgrade/release_routes_v1.2.json')
    assert 'A-04' not in routes['routes']['stage1_only']['required_done']
    assert read(TASK / 'outputs/current-freeze.json')['optional_stage3_required_for_core_paper'] is False


def test_activity_scope_is_consumed_not_fabricated():
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    scoped = [row for row in rows if 'G-03' in row['activity'].split('|')]
    assert [r['capability_id'] for r in scoped] == read(TASK / 'outputs/current-freeze.json')['required_activity_capabilities']
    assert all(r['status'] == 'PENDING_EXTERNAL' and r['evidence_ref'] == '' for r in scoped)
    assert read(ROOT / 'agent/tasks/G-05/outputs/current-admission.json')['qualified_capabilities'] == 0


def test_archive_bytes_and_both_validator_consumers():
    original = TASK / 'archive/02_当前状态与不可跨越门禁.md'
    assert hashlib.sha256(original.read_bytes()).hexdigest().upper() == '1E6053643994115BB477D6F53C97F25141204B7FEE372F1319181DB8466C7F01'
    validator = (PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py').read_text(encoding='utf-8')
    assert 'LEGACY_LOCK / "02_当前状态与不可跨越门禁.md"' in validator
    assert 'PACKAGE / "00_总控" / "02_当前状态与不可跨越门禁.md"' in validator
    current = PLAN / '00_总控/02_当前状态与不可跨越门禁.md'
    text = current.read_text(encoding='utf-8')
    assert 'protocol_authority_v1.2.json' in text and '有效预设情绪比较不因功能门失败隐去' in text
    for link in re.findall(r'\]\(([^)]+)\)', text):
        assert (current.parent / link).resolve().exists(), link


def test_runtime_adapters_are_real_but_not_new_v12_approval():
    consumers = read(GOV / 'u12_upgrade/consumers.json')['entries']
    required = ['session_prepare_start', 'formal_readiness_gate', 'tcp_prepare', 'allocation_reveal',
                'durable_recording', 'unity_formal_build']
    assert all(e['status'] == 'PENDING_RUNTIME_MIGRATION' for e in consumers if e['id'] in required)
    assert len([e for e in consumers if e['id'] in required]) == 6
    source = (ROOT / '02-技术研发/srp_session_core/gates.py').read_text(encoding='utf-8')
    assert 'FORMAL_GATE_UNAVAILABLE' in source and '_require_capability' in source
    value = read(TASK / 'outputs/current-freeze.json')
    assert value['default_formal_adapters_fail_closed'] is True
    assert value['generic_formal_capable_receipt_is_institutional_approval'] is False
    assert value['protocol_false_intercepts_legacy_runtime'] is value['first_condition_training_exposure_integrated'] is False


def test_current_handoff_and_all_source_paths():
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).is_file(), path
    text = (TASK / 'outputs/current-freeze.md').read_text(encoding='utf-8')
    for point in ('未领取未签收', 'P-01当前仅首次核心start登记', '100次插补仍候选',
                  '受限原件/隐藏分配不公开上传', '最多12人一实例', '不要求未开展阶段三伪DONE'):
        assert point in text
    assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', text)
