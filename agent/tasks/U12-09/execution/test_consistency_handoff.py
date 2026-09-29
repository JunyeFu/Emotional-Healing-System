"""Check actual indices, old identities and current candidate scope."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import re
import runpy

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def test_current_registered_state_and_no_business_acceptance():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U12-09')
    assert row['status'] == 'WAIT_DEP'
    assert row['depends_on'].split('|') == ['U12-02', 'U12-03', 'U12-04', 'U12-06']
    assert row['claimant'] == row['reviewer'] == '' and row['effort_person_days'] == '2'
    report = read(TASK / 'outputs/current-consistency.json')
    assert report['new_human_acceptance'] == 'NOT_SIGNED'
    assert report['new_independent_review'] == 'NOT_RUN'
    assert report['formal_gate_proved'] is report['formal_authorization'] is False


@pytest.mark.parametrize('index', [0, 1, 2])
def test_actual_original_candidate_byte_identities(index):
    archive = TASK / 'archive/task-input'
    manifest = read(archive / 'package_manifest.json')
    entry = manifest['files'][index]
    assert hashlib.sha256((archive / entry['path']).read_bytes()).hexdigest() == entry['byte_sha256']
    assert manifest['input_snapshot_id'] == 'c8b0da9637cd58c685869e6a3d9b7f70c47d587567d0feb3cdc1ec26fad19cb2'
    assert manifest['dispatch_allowed'] is False


def test_output_matrices_rebuild_from_actual_inputs():
    artifacts = runpy.run_path(str(TASK / 'execution/inspect_consistency.py'))['artifacts']()
    for name, value in artifacts.items():
        assert (TASK / 'outputs' / name).read_bytes() == value, name
    report = read(TASK / 'outputs/current-consistency.json')
    assert report['consumer_count'] == 15 and report['registered_done_count'] == 24
    assert report['consumer_status_counts'] == {'GOVERNANCE_IMPLEMENTED': 4, 'PENDING_RUNTIME_MIGRATION': 7,
        'SCOPED_CANDIDATE_ACCEPTED_NOT_LIVE': 2, 'PENDING_SCOPE_REVIEW': 1, 'PENDING_EXTERNAL': 1}
    with (TASK / 'outputs/consumer-matrix.csv').open(encoding='utf-8-sig', newline='') as stream:
        consumers = list(csv.DictReader(stream))
    assert len(consumers) == 15
    runtime = [row for row in consumers if row['owner_task'] == 'U12-06']
    assert len(runtime) == 6 and all(row['owner_claimant'] == '傅钧烨' for row in runtime)
    assert all(row['declared_consumer_status'] == 'PENDING_RUNTIME_MIGRATION' for row in runtime)


def test_old_done_impact_is_index_not_new_signed_scope():
    with (TASK / 'outputs/old-done-impact.csv').open(encoding='utf-8-sig', newline='') as stream:
        impact = list(csv.DictReader(stream))
    assert len(impact) == 24
    assert all(row['new_scope_acceptance_inferred'] == 'False' for row in impact)
    for row in impact:
        summary = read(ROOT / row['source'])
        assert row['current_scope_and_pending'] == summary['conclusion']
        assert row['reported_historical_reviewer'] == summary['historical_acceptance']['reviewer']


def test_formal_blanks_and_three_different_versions_preserved():
    report = read(TASK / 'outputs/current-consistency.json')
    assert len(report['formal_blank_fields']) == 5
    runtime = read(ROOT / 'agent/tasks/U12-06/outputs/current-runtime.json')
    assert (runtime['study_protocol_version'], runtime['runtime_contract_version'], runtime['transport_config_version']) == ('1.2', '2.2', '1.1')
    observation = read(ROOT / 'agent/tasks/U12-06/evidence/runtime-observations.json')
    assert observation['default_formal']['result'] == 'REJECTED'
    assert observation['synthetic_formal']['status'] == 'PREPARED'
    assert observation['formal_research_gate_delivered'] is observation['real_approval_read'] is False
    assert report['all_consumer_paths_exist'] is True and report['formal_gate_proved'] is False


def test_current_governance_rejects_unapproved_formal_change():
    checker = runpy.run_path(str(GOV / 'u12_upgrade/validate_u12_governance.py'))['semantic_errors']
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    protocol = read(GOV.parent / '00_总控/protocol_authority_v1.2.json')
    milestones = read(GOV / 'audit_upgrade/task_milestones_v1.2.json')
    changed = copy.deepcopy(protocol)
    changed['formal_participant_collection_allowed'] = True
    assert 'FORMAL_COLLECTION_NOT_BLOCKED' in checker(rows, changed, milestones)
    changed = copy.deepcopy(protocol)
    changed['sample_planning']['formal_randomized_n'] = 48
    assert 'UNAPPROVED_NUMERIC_FREEZE' in checker(rows, changed, milestones)


def test_six_original_claims_still_unresolved_in_checked_sources():
    report = read(TASK / 'outputs/legacy-byte-observations.json')
    assert len(report['references']) == 6
    assert len({row['repository_path'] for row in report['references']}) == 4
    assert all(row['historical_git_identity_matches'] for row in report['references'])
    assert all(not row['matching_candidate_sources'] for row in report['references'])
    assert runpy.run_path(str(GOV / 'u12_upgrade/freeze_legacy_evidence.py'))['validate']() == []
    assert report['scope'] == 'BOUNDED_ACCESSIBLE_SOURCE_CHECK_NOT_EXHAUSTIVE_RECOVERY'


def test_current_navigation_sources_and_language():
    for relative in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / relative).is_file(), relative
    old = ROOT / 'agent/governance/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-09/README.md'
    for path in (old, TASK / 'TASK.md', TASK / 'outputs/current-consistency.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if not link.startswith('https://'):
                assert (path.parent / link).resolve().exists(), (path, link)
    assert not (old.parent / 'TASK.md').exists()
    for path in (TASK / 'TASK.md', TASK / 'outputs/current-consistency.md'):
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
    assert '../../U12-09/outputs/current-consistency.md' in (ROOT / 'agent/tasks/U12-06/outputs/current-runtime.md').read_text(encoding='utf-8')
