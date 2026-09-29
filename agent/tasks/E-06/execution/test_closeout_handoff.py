import csv
import json
from pathlib import Path
import re
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(ROOT / '02-技术研发/08-随机化'))
sys.path.insert(0, str(ROOT / 'agent/tasks/X-01/execution'))
from srp_randomization import (AllocationRequest, GateEvidence, RandomizationStore,
                               SnapshotGateEvidenceVerifier, generate_list)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def current():
    return read(TASK / 'outputs/current-closeout.json')


def test_registry_and_real_missing_lock_are_not_business_done():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'E-06')
    value = current()
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['kind'] == 'FIXED'
    assert row['depends_on'].split('|') == value['depends_on'] == ['G-04', 'B-03']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is value['historical_acceptance'] is None
    assert value['actual_instances'] == [] and value['actual_batch_count'] == 0
    assert value['real_activity'] == 'NOT_RUN'
    for key in ['research_lock_id', 'research_lock_hash', 'unblind_authorization', 'real_responsible_people']:
        assert value[key] is None
    assert value['research_lock_signed'] is value['unblinding_authorized'] is False


@pytest.mark.parametrize('assigned,completed,balanced', [(12, 8, False), (48, 36, True)])
def test_actual_stage3_balance_does_not_mean_completion_or_policy_audit(tmp_path, assigned, completed, balanced):
    store = RandomizationStore(tmp_path / 'synthetic.sqlite', evidence_verifier=SnapshotGateEvidenceVerifier())
    store.import_list(generate_list('stage_3', ('all',), 1, b'e06-synthetic-balance-only'), actor_role='custodian')
    for index in range(1, assigned + 1):
        reservation = f'RES-E06-SYN-{index}'
        request = AllocationRequest(request_id=f'REQ-E06-SYN-{index}', stage='stage_3', stratum='all',
                                    reservation_id=reservation, expected_randomization_version='1.0')
        evidence = tuple(GateEvidence(gate=gate, reservation_id=reservation, evidence_id=f'SYN-{gate}', passed=True)
                         for gate in ('eligibility', 'device_readiness', 'dedup_reservation'))
        receipt = store.allocate_and_reveal(request, evidence, actor_role='allocator')
        store.record_outcome(receipt.randomization_list_hash, receipt.allocation_index,
                             'COMPLETE' if index <= completed else 'ABORTED', actor_role='auditor')
    report = store.audit_balance('stage_3', 'all', actor_role='auditor')
    assert report.assigned_count == assigned and report.complete_count == completed
    assert report.incomplete_count == assigned - completed
    assert sum(report.arm_counts.values()) == assigned
    assert report.balanced_by_assignment is balanced
    assert report.reason_code == ('BALANCED_BY_ASSIGNMENT' if balanced else 'PARTIAL_BLOCK')
    if balanced:
        assert report.arm_counts == {'frozen_policy': 24, 'balanced_random': 24}
    assert store.verify_audit_chain(actor_role='auditor').valid
    assert store.formal_capable is False
    assert current()['x01_balance_covers_sequence_policy_and_analysis_eligibility'] is False
    assert current()['partial_block_is_automatic_protocol_failure'] is False


def test_empty_lock_review_has_no_signed_identity_or_reveal_permission():
    outline = read(TASK / 'outputs/lock-review-template.json')
    assert outline['status'] == 'NOT_RUN' and outline['study_stage'] == 'stage_3'
    assert all(v is None for v in outline['counts'].values())
    assert all(v is None for v in outline['research_lock'].values())
    assert all(v is None for v in outline['unblind_authorization'].values())
    assert outline['unblinding_authorized'] is False
    assert outline['policy_audit']['status'] == 'NOT_RUN'
    assert all(v is None for key, v in outline['policy_audit'].items() if key != 'status')
    schema = read(ROOT / '02-技术研发/srp_session_store/contracts/raw-evidence-bundle-v1.schema.json')
    assert set(outline['raw_evidence']['required_families']) == set(schema['properties']['families']['items']['enum'])
    assert outline['raw_evidence']['status'] == 'NOT_CHECKED'


def test_real_stage3_permissions_batches_and_runtime_are_still_missing():
    freeze = read(ROOT / 'agent/tasks/G-04/outputs/current-extension.json')
    batch = read(ROOT / 'agent/tasks/B-03/outputs/current-batch.json')
    runtime = read(ROOT / 'agent/tasks/X-03/outputs/current-runtime.json')
    assert freeze['actual_preregistration_receipt'] is freeze['final_randomized_n'] is None
    assert batch['instances'] == []
    assert runtime['policy_replay_implemented'] is False
    assert current()['actual_policy_artifact_identity_report'] is current()['real_dynamic_replay_report'] is None
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['capability_id'] == 'INSTITUTION_STAGE3')
    assert 'E-06' in row['activity'].split('|')
    assert row['status'] == 'PENDING_EXTERNAL' and not row['evidence_ref']


def test_no_go_partial_activity_and_core_route_are_not_conflated():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    route = read(GOV / 'audit_upgrade/release_routes_v1.2.json')
    assert protocol['stage_2_3']['partial_runs_must_be_disclosed'] is True
    assert protocol['primary']['report_even_if_functional_guard_fails'] is True
    assert 'E-06' in route['routes']['stage1_only']['not_required_to_mark_done']
    assert route['routes']['stage1_only']['must_have_no_stage3_activity'] is True
    assert 'A-04' in route['routes']['with_stage3']['required_done']
    assert {'deviations', 'stop_records', 'fallback_exposure'} <= set(route['routes']['with_stage3']['required_result_families'])
    assert current()['no_go_means_no_activity'] is False
    assert current()['fallback_preserves_assignment_arm'] is True
    assert current()['optional_stage3_required_for_core_paper'] is current()['primary_affect_reporting_blocked_by_pf_or_scci'] is False


def test_sealing_blinding_and_hashes_do_not_replace_real_evidence():
    value = current()
    for key in ['session_seal_is_research_lock', 'single_model_hash_proves_no_online_update',
                'restricted_bundle_reference_is_authorized_original_review', 'both_native_arms_are_automatically_blinded',
                'all_batches_qc_complete', 'blind_reconstruction_delivered', 'formal_stage3_sap_frozen',
                'first_condition_training_exposure_integrated', 'normalization_is_business_completion', 'root_migration_complete']:
        assert value[key] is False
    assert value['completion_based_refilling_forbidden'] is value['outcome_based_optional_stopping_forbidden'] is True
    assert value['formal_tail_block_rule'] is value['stop_receipt'] is None
    text = (TASK / 'outputs/current-closeout.md').read_text(encoding='utf-8')
    for fact in ['原始manifest含assignment_arm', 'explicit_none即缺必需原件', '会话seal哈希不是研究锁库哈希',
                 '锁库签收不等于揭盲授权', 'NO_GO不等于无活动', '零分母不填0', '原始证据及二进制/制品按字节SHA-256']:
        assert fact in text


def test_actual_sources_and_consumer_navigation():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for name in ['00_第11步计划.md', '01_详细执行方案.md']:
        file = PLAN / '12_步骤11_离线处理分析与论文写作' / name
        text = file.read_text(encoding='utf-8')
        assert 'agent/tasks/E-06/outputs/current-closeout.md' in text
        for link in re.findall(r'\]\(([^)]+)\)', text):
            assert (file.parent / link).resolve().exists(), link
    outline = read(TASK / 'outputs/lock-review-template.json')
    assert not {'phone', 'hmac', 'password', 'subject_mapping'} & set(outline)
    assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', (TASK / 'outputs/current-closeout.md').read_text(encoding='utf-8'))
