"""Check actual balance behavior and honest closeout inputs and status."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(ROOT / '02-技术研发/08-随机化'))
from srp_randomization import (AllocationRequest, GateEvidence, RandomizationStore,
                               SnapshotGateEvidenceVerifier, generate_list)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def current():
    return read(TASK / 'outputs/current-closeout.json')


def test_real_registry_and_missing_closeout_are_not_done():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'E-04')
    value = current()
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['kind'] == 'FIXED' and row['depends_on'].split('|') == value['depends_on'] == ['G-03', 'B-02']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['actual_instances'] == [] and value['actual_batch_count'] == 0
    assert value['claimant'] is value['reviewer'] is value['historical_acceptance'] is None
    assert value['real_activity'] == 'NOT_RUN'
    for field in ('research_lock_id', 'research_lock_hash', 'unblind_authorization', 'real_responsible_people'):
        assert value[field] is None
    assert value['research_lock_signed'] is value['unblinding_authorized'] is False


def test_real_partial_block_audit_does_not_claim_sequence_or_lock(tmp_path):
    store = RandomizationStore(tmp_path / 'synthetic.sqlite', evidence_verifier=SnapshotGateEvidenceVerifier())
    store.import_list(generate_list('stage_1', ('all',), 1, b'e04-synthetic-balance-only'), actor_role='custodian')
    for index in range(1, 13):
        reservation = f'RES-E04-SYN-{index}'
        request = AllocationRequest(request_id=f'REQ-E04-SYN-{index}', stage='stage_1', stratum='all',
                                    reservation_id=reservation, expected_randomization_version='1.0')
        evidence = tuple(GateEvidence(gate=gate, reservation_id=reservation, evidence_id=f'SYN-{gate}', passed=True)
                         for gate in ('eligibility', 'device_readiness', 'dedup_reservation'))
        receipt = store.allocate_and_reveal(request, evidence, actor_role='allocator')
        store.record_outcome(receipt.randomization_list_hash, receipt.allocation_index,
                             'COMPLETE' if index <= 8 else 'ABORTED', actor_role='auditor')
    report = store.audit_balance('stage_1', 'all', actor_role='auditor')
    assert report.assigned_count == 12 and report.complete_count == 8 and report.incomplete_count == 4
    assert sum(report.arm_counts.values()) == 12
    assert report.reason_code == 'PARTIAL_BLOCK' and report.balanced_by_assignment is False
    assert store.verify_audit_chain(actor_role='auditor').valid is True
    assert store.formal_capable is False
    assert current()['x01_balance_covers_sequence_and_analysis_eligibility'] is False
    assert current()['partial_block_is_automatic_protocol_failure'] is False


def test_blank_review_is_not_a_signature_or_lock():
    template = read(TASK / 'outputs/lock-review-template.json')
    assert template['status'] == 'NOT_RUN' and template['study_stage'] == 'stage_1'
    assert all(v is None for v in template['counts'].values())
    assert all(v is None for v in template['research_lock'].values())
    assert all(v is None for v in template['unblind_authorization'].values())
    assert template['unblinding_authorized'] is False
    schema = read(ROOT / '02-技术研发/srp_session_store/contracts/raw-evidence-bundle-v1.schema.json')
    assert set(template['raw_evidence']['required_families']) == set(schema['properties']['families']['items']['enum'])
    assert template['raw_evidence']['status'] == 'NOT_CHECKED'


def test_research_and_activity_freezes_are_still_missing():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    assert protocol['sample_planning']['formal_randomized_n'] is current()['final_randomized_n'] is None
    assert protocol['formal_participant_collection_allowed'] is False
    assert read(ROOT / 'agent/tasks/G-03/outputs/current-freeze.json')['real_preregistration_receipt'] is None
    assert read(ROOT / 'agent/tasks/B-02/outputs/current-batch.json')['instances'] == []
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        activity = next(r for r in csv.DictReader(stream) if r['capability_id'] == 'INSTITUTION_STAGE1')
    assert 'E-04' in activity['activity'].split('|')
    assert activity['status'] == 'PENDING_EXTERNAL' and activity['evidence_ref'] == ''


def test_core_route_and_affect_reporting_do_not_wait_for_optional_stage3():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    routes = read(GOV / 'audit_upgrade/release_routes_v1.2.json')
    assert protocol['primary']['report_even_if_functional_guard_fails'] is True
    assert current()['primary_affect_reporting_blocked_by_pf_or_scci'] is False
    assert current()['optional_stage3_required_for_core_paper'] is False
    assert 'A-05' in routes['routes']['stage1_only']['required_done']
    assert 'A-04' in routes['routes']['stage1_only']['not_required_to_mark_done']


def test_blinding_sealing_and_missingness_boundaries():
    value = current()
    for field in ('session_seal_is_research_lock', 'restricted_bundle_reference_is_authorized_original_review',
                  'condition_alias_is_blinding', 'blind_reconstruction_delivered', 'formal_sap_frozen',
                  'first_condition_training_exposure_integrated', 'all_batches_qc_complete',
                  'normalization_is_business_completion', 'root_migration_complete'):
        assert value[field] is False
    assert value['balance_unit'] == 'assigned_not_complete'
    assert value['completion_based_refilling_forbidden'] is value['outcome_based_optional_stopping_forbidden'] is True
    text = (TASK / 'outputs/current-closeout.md').read_text(encoding='utf-8')
    for fact in ('manifest含cue_mode', '零分母不填0', 'explicit_none即缺必需原件',
                 '锁库签收不等于揭盲授权', '不能把X-01的COMPLETE当作完整四模块分析集',
                 '传感器缺失不删除有效PANAS', '原始证据/二进制/制品使用字节SHA-256'):
        assert fact in text


def test_archives_and_both_consumers_exist():
    digests = {'00_第11步计划.md': 'B41E78C466BDB4A47844D9710EC102136B0BFD51F3CE80F757DFD9CD9634540C',
               '01_详细执行方案.md': 'A25AADCBF6FED0CC5E72A882B2316C21DDB21FB133B3E17F7E298253E5AA4338'}
    validator = (PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py').read_text(encoding='utf-8')
    for name, digest in digests.items():
        assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == digest
        assert f'LEGACY_CLOSEOUT / "{name}"' in validator
        path = PLAN / '12_步骤11_离线处理分析与论文写作' / name
        text = path.read_text(encoding='utf-8')
        assert 'agent/tasks/E-04/outputs/current-closeout.md' in text
        for link in re.findall(r'\]\(([^)]+)\)', text):
            assert (path.parent / link).resolve().exists(), link


def test_actual_sources_and_no_restricted_identity_in_empty_form():
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).is_file(), path
    template = read(TASK / 'outputs/lock-review-template.json')
    assert not {'phone', 'hmac', 'password', 'subject_mapping'} & set(template)
    assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', (TASK / 'outputs/current-closeout.md').read_text(encoding='utf-8'))
