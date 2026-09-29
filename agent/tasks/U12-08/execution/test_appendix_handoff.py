"""Verify current appendix responsibilities and actual preserved inputs."""
import csv
import hashlib
import json
from pathlib import Path
import re

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def current():
    return read(TASK / 'outputs/current-extension.json')


def test_registered_scope_not_completed():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U12-08')
    assert row['status'] == current()['business_status'] == 'WAIT_DEP'
    assert row['depends_on'].split('|') == current()['depends_on'] == ['A-04', 'E-05']
    assert row['claimant'] == row['reviewer'] == ''
    assert row['effort_person_days'] == '4'
    assert current()['claimant'] is current()['reviewer'] is None
    assert current()['real_analysis'] == current()['independent_reproduction'] == 'NOT_RUN'
    assert current()['real_appendix'] == 'NOT_DELIVERED'
    assert current()['human_acceptance'] == 'NOT_SIGNED'
    assert all(ref is None for ref in current()['result_family_refs'].values())


@pytest.mark.parametrize('index', [0, 1, 2])
def test_original_candidate_bytes_preserved(index):
    archive = TASK / 'archive/task-input'
    manifest = read(archive / 'package_manifest.json')
    item = manifest['files'][index]
    assert hashlib.sha256((archive / item['path']).read_bytes()).hexdigest() == item['byte_sha256']
    assert manifest['dispatch_allowed'] is False
    assert manifest['input_snapshot_id'] == 'aadd131e20a1e74ff35491aaceece00fb8f7f1b52aa8c0ebcf2e36e27a16d28b'
    assert read(archive / 'inputs/task_input.json')['authority'] == 'CANDIDATE_NOT_DISPATCHABLE'


def test_appendix_matches_analysis_and_closure_not_freeze():
    analysis = read(ROOT / 'agent/tasks/A-04/outputs/current-analysis.json')
    scope = read(ROOT / 'agent/tasks/A-06/outputs/current-scope.json')
    value = current()
    for key in ('arms', 'cue_mode_both_arms', 'contrast', 'fallback_preserves_assignment',
                'stage1_parameters_automatically_inherited', 'sequence_rank_is_causal_effect',
                'primary_reporting_blocked_by_guard_or_scci', 'stage1_classifier_applies_without_extension_contract'):
        assert value[key] == analysis[key]
    assert value['stage3_started_sources'] == scope['stage3_started_sources']
    assert value['required_result_families'] == scope['extension_required_result_families']
    assert value['responsible_for_policy_freeze'] is False
    assert value['actual_activity_ledgers_verified'] is False
    assert value['formal_stage3_sap_ref'] is value['research_lock_id'] is value['unblind_authorization'] is None


def test_two_routes_and_all_result_families_preserved():
    routes = read(GOV / 'audit_upgrade/release_routes_v1.2.json')['routes']
    assert 'U12-08' not in routes['stage1_only']['required_done']
    assert 'U12-08' in routes['stage1_only']['not_required_to_mark_done']
    assert 'U12-08' in routes['with_stage3']['required_done']
    assert current()['required_result_families'] == routes['with_stage3']['required_result_families']
    assert routes['stage1_only']['must_have_no_stage3_activity'] is True
    assert routes['with_stage3']['required_human_receipt_scope'] == 'INCLUDE_STAGE3'
    assert current()['optional_stage3_required_for_core_paper'] is False
    assert current()['empty_instance_list_proves_no_stage3'] is False


def test_sources_navigation_and_actual_consumers():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    navigation = ROOT / '00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-08/README.md'
    for path in (navigation, TASK / 'TASK.md', TASK / 'outputs/current-extension.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if not link.startswith('https://'):
                assert (path.parent / link).resolve().exists(), (path, link)
    assert not (navigation.parent / 'TASK.md').exists()
    assert not (navigation.parent / 'package_manifest.json').exists()
    for task_id, filename in (('A-04', 'current-analysis.md'), ('A-06', 'current-scope.md')):
        body = (ROOT / f'agent/tasks/{task_id}/outputs/{filename}').read_text(encoding='utf-8')
        assert '../../U12-08/outputs/current-extension.md' in body
    for task_id in ('X-02', 'X-03'):
        body = (ROOT / f'agent/tasks/{task_id}/evidence/consumer-impact.md').read_text(encoding='utf-8')
        assert 'E-05/U12-08' not in body
    for path in (TASK / 'TASK.md', TASK / 'outputs/current-extension.md', TASK / 'outputs/appendix-spec.md'):
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
    assert current()['normalization_is_business_completion'] is current()['root_migration_complete'] is False
