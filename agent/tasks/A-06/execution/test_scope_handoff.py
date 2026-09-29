"""Use current route evaluator with explicitly synthetic temporary ledgers."""
import csv
import hashlib
import json
from pathlib import Path
import re
import runpy

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
UPGRADE = GOV / 'audit_upgrade'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def current():
    return read(TASK / 'outputs/current-scope.json')

def evaluate():
    namespace = runpy.run_path(str(UPGRADE / 'route_evaluator.py'))
    assert namespace['CONTRACT'].name == 'release_routes_v1.2.json'
    return namespace['evaluate_route']

def activity(tmp_path, active=None):
    result = {}
    for source in current()['stage3_started_sources']:
        content = b'{"synthetic":true,"event":"partial_activity"}\n' if source == active else b''
        path = tmp_path / (source + '.jsonl')
        path.write_bytes(content)
        result[source] = {'path': path.name, 'byte_sha256': hashlib.sha256(content).hexdigest().upper(),
                          'record_count': 1 if content else 0}
    return result

def receipt(scope):
    return {'record_id': 'SYNTHETIC_ONLY', 'candidate_identity': 'synthetic-not-git',
            'reviewer': 'synthetic-not-person', 'review_method': 'record_review',
            'signed_ref': 'synthetic-file-not-present', 'signed_ref_sha256': '0' * 64,
            'status': 'PASS', 'scope': scope}

def test_registry_and_actual_closure_not_done():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'A-06')
    assert row['status'] == current()['business_status'] == 'WAIT_DEP'
    assert row['depends_on'].split('|') == current()['depends_on'] == ['A-05', 'U12-10']
    assert row['claimant'] == row['reviewer'] == ''
    assert '双人签收' in row['evidence_required']
    assert not (UPGRADE / 'a06_route_closure_v1.json').exists()
    assert read(ROOT / 'agent/tasks/A-05/outputs/current-analysis.json')['real_data_analysis'] == 'NOT_RUN'
    assert current()['real_scope_closure'] == 'NOT_RUN'
    assert current()['real_activity_ledgers_verified'] is False
    assert current()['scope_receipt'] is current()['selected_route'] is None

def test_core_route_actual_v12_metadata_only(tmp_path):
    result = evaluate()('stage1_only', set(current()['core_required_done']), activity(tmp_path),
                        receipt('NO_STAGE3'), evidence_root=tmp_path)
    assert result['ok'] is True and result['authorization'] is False
    assert result['scope'] == current()['inner_evaluator_scope'] == 'A06_ROUTE_METADATA_ONLY'
    # Current inner function does not read the signed report. Outer validator must.
    errors = runpy.run_path(str(GOV / '15_validate_audit_upgrade.py'))['validate_a06_receipt'](receipt('NO_STAGE3'))
    assert 'A06_SIGNED_REPORT_MISSING' in errors
    assert 'A06_RECEIPT_CANDIDATE_NOT_A_COMMIT' in errors
    assert current()['inner_ok_proves_signed_report'] is False

@pytest.mark.parametrize('source', ['stage3_assignment_ledger', 'stage3_exposure_ledger', 'B-03_instance_registry'])
def test_any_partial_activity_cannot_hide_in_core_route(tmp_path, source):
    data = activity(tmp_path, source)
    result = evaluate()('stage1_only', set(current()['core_required_done']), data,
                        receipt('NO_STAGE3'), evidence_root=tmp_path)
    assert result['ok'] is False and 'CANNOT_HIDE_STAGE3_ACTIVITY' in result['errors']
    assert result['stage3_activity_count'] == 1
    extension = evaluate()('with_stage3', set(current()['extension_required_done']), data,
                           receipt('INCLUDE_STAGE3'), set(current()['extension_required_result_families']),
                           evidence_root=tmp_path)
    assert extension['ok'] is True and extension['authorization'] is False

@pytest.mark.parametrize('missing', ['A-05', 'W-01', 'U12-10'])
def test_missing_core_result_or_review_blocks(tmp_path, missing):
    result = evaluate()('stage1_only', set(current()['core_required_done']) - {missing}, activity(tmp_path),
                        receipt('NO_STAGE3'), evidence_root=tmp_path)
    assert 'MISSING_TASKS:' + missing in result['errors']

@pytest.mark.parametrize('missing', ['A-04', 'U12-08'])
def test_extension_missing_analysis_blocks(tmp_path, missing):
    result = evaluate()('with_stage3', set(current()['extension_required_done']) - {missing},
                        activity(tmp_path, 'stage3_exposure_ledger'), receipt('INCLUDE_STAGE3'),
                        set(current()['extension_required_result_families']), evidence_root=tmp_path)
    assert 'MISSING_TASKS:' + missing in result['errors']

@pytest.mark.parametrize('family', ['stage3_results', 'deviations', 'stop_records', 'fallback_exposure'])
def test_extension_missing_result_family_blocks(tmp_path, family):
    result = evaluate()('with_stage3', set(current()['extension_required_done']),
                        activity(tmp_path, 'B-03_instance_registry'), receipt('INCLUDE_STAGE3'),
                        set(current()['extension_required_result_families']) - {family}, evidence_root=tmp_path)
    assert 'MISSING_RESULT_FAMILIES:' + family in result['errors']

@pytest.mark.parametrize('change', ['missing_file', 'tampered_file', 'wrong_count', 'boolean_only'])
def test_invalid_actual_ledger_identity_blocks(tmp_path, change):
    data = activity(tmp_path)
    source = 'stage3_assignment_ledger'
    path = tmp_path / data[source]['path']
    if change == 'missing_file':
        path.unlink()
    elif change == 'tampered_file':
        path.write_bytes(b'{"synthetic":true}\n')
    elif change == 'wrong_count':
        data[source]['record_count'] = 1
    else:
        data = {'stage3_started': False}
    result = evaluate()('stage1_only', set(current()['core_required_done']), data,
                        receipt('NO_STAGE3'), evidence_root=tmp_path)
    assert 'INVALID_STAGE3_ACTIVITY_EVIDENCE' in result['errors']
    assert not result['ok']

def test_unreviewed_template_is_not_production_signed_closure(tmp_path):
    draft = read(TASK / 'outputs/scope-review-template.json')
    assert draft['status'] == 'NOT_RUN' and draft['is_production_route_closure'] is False
    assert draft['production_receipt_ref'] is draft['unique_participant_count'] is None
    assert all(value is None for row in draft['signature_reviews'].values() for value in row.values())
    result = evaluate()('stage1_only', set(current()['core_required_done']), activity(tmp_path),
                        {}, evidence_root=tmp_path)
    assert 'ROUTE_NOT_SIGNED_PASS' in result['errors']
    assert current()['activity_count_is_unique_participant_count'] is False
    assert current()['empty_package_instance_list_proves_no_stage3'] is False
    assert current()['ordinary_governance_pass_executes_a06_done_branch'] is False

def test_sources_and_current_consumer_paths():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for relative in ('12_步骤11_离线处理分析与论文写作/00_第11步计划.md',
                     '12_步骤11_离线处理分析与论文写作/01_详细执行方案.md'):
        path = PLAN / relative
        assert 'agent/tasks/A-06/outputs/current-scope.md' in path.read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            assert (path.parent / link).resolve().exists(), link
    progress = (ROOT / 'agent/normalization.md').read_text(encoding='utf-8')
    assert '共44/71包；下一包B-01' not in progress
    assert 'normalization-progress.json' in progress
    for path in (TASK / 'TASK.md', TASK / 'outputs/current-scope.md'):
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
    assert current()['normalization_is_business_completion'] is current()['root_migration_complete'] is False
