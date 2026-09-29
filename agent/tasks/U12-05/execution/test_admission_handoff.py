"""Check historical bytes and the existing capability consumer, not approval."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/U12-05'
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
LEGACY = ROOT / 'agent/governance/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-05'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def validator():
    spec = importlib.util.spec_from_file_location('u1205_existing_capability', GOV / '15_validate_audit_upgrade.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name', ['TASK.md', 'FILES.md', 'package_manifest.json', 'inputs/task_input.json'])
def test_original_bytes_are_preserved(name):
    source = read(TASK / 'inputs/sources.json')
    assert hashlib.sha256((TASK / 'archive/candidate' / name).read_bytes()).hexdigest().upper() == source['archived_bytes'][name]


def test_original_manifest_still_resolves_original_inputs():
    archive = TASK / 'archive/candidate'
    manifest = read(archive / 'package_manifest.json')
    for entry in manifest['files']:
        assert hashlib.sha256((archive / entry['path']).read_bytes()).hexdigest() == entry['byte_sha256']
    assert manifest['input_snapshot_id'] == read(TASK / 'inputs/sources.json')['historical_input_snapshot_id']
    assert manifest['dispatch_allowed'] is False


def test_current_registry_and_roles_are_not_fabricated():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = {row['task_id']: row for row in csv.DictReader(stream)}
    state = read(TASK / 'outputs/current-admission.json')
    assert rows['U12-05']['status'] == state['status'] == 'WAIT_DEP_EXTERNAL'
    assert rows['U12-05']['depends_on'].split('|') == state['dependencies']
    assert not rows['U12-05']['claimant'] and not rows['U12-05']['reviewer']
    for field in ('claimant', 'reviewer', 'real_approval', 'real_roles', 'real_consent_and_permissions', 'real_second_person_acceptance'):
        assert state[field] is None
    assert state['formal_collection_allowed'] is False
    assert state['static_approval_implies_device_permission'] is False
    assert state['whole_g05_done_required_for_approved_static_activity'] is False
    assert rows['E-01']['status'] == rows['E-02']['status'] == 'BLOCKED_EXTERNAL'


def test_current_sources_and_navigation_resolve():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for name in ('TASK.md', 'FILES.md'):
        for target in re.findall(r'\]\(([^)]+)\)', (LEGACY / name).read_text(encoding='utf-8-sig')):
            assert (LEGACY / target).resolve().exists(), target
    manifest = read(LEGACY / 'package_manifest.json')
    assert manifest['package_role'] == 'LEGACY_NAVIGATION_ONLY'
    assert (LEGACY / manifest['current_task']).resolve() == TASK / 'TASK.md'
    assert (LEGACY / manifest['historical_manifest']).resolve().is_file()


@pytest.mark.parametrize('activity,capability', [('E-01', 'INSTITUTION_LEVEL_A'), ('E-02', 'INSTITUTION_LEVEL_B')])
def test_actual_activity_capability_is_pending(activity, capability):
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(row for row in csv.DictReader(stream) if row['capability_id'] == capability)
    assert row['activity'] == activity
    assert row['status'] == 'PENDING_EXTERNAL' and not row['evidence_ref']
    assert validator().validate_external_capability_record(capability, row['evidence_ref']) == [f'{capability}:EVIDENCE_RECORD_MISSING']


@pytest.fixture
def synthetic_capability(tmp_path, monkeypatch):
    module = validator()
    monkeypatch.setattr(module, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(module, 'git_tracks', lambda _: True)
    signed = tmp_path / 'synthetic.txt'
    signed.write_text('SYNTHETIC SOFTWARE FIXTURE ONLY NOT INSTITUTIONAL APPROVAL', encoding='utf-8')
    identity = hashlib.sha256(f'synthetic.txt:{hashlib.sha256(signed.read_bytes()).hexdigest().upper()}'.encode()).hexdigest().upper()
    record = {'record_id': 'SYNTHETIC_ONLY', 'record_type': 'external_capability', 'scope': 'INSTITUTION_LEVEL_A',
              'candidate_identity': identity, 'source_commit': None, 'input_snapshot_id': None,
              'evidence_refs': ['synthetic.txt'], 'review': {'status': 'PASS', 'reviewer': 'SYNTHETIC_REVIEWER',
              'role': 'TEST_ONLY', 'method': 'external_receipt', 'signed_ref': 'synthetic.txt'}}
    return module, tmp_path, record


def save_fixture(root, record):
    (root / 'synthetic.json').write_text(json.dumps(record), encoding='utf-8')


def test_scoped_interface_does_not_require_whole_g05(synthetic_capability):
    module, root, record = synthetic_capability
    save_fixture(root, record)
    assert module.validate_external_capability_record('INSTITUTION_LEVEL_A', 'synthetic.json') == []


def test_static_record_does_not_match_another_activity(synthetic_capability):
    module, root, record = synthetic_capability
    save_fixture(root, record)
    assert 'INSTITUTION_LEVEL_B:EVIDENCE_SCOPE_MISMATCH' in module.validate_external_capability_record('INSTITUTION_LEVEL_B', 'synthetic.json')


def test_changed_public_receipt_identity_is_rejected(synthetic_capability):
    module, root, record = synthetic_capability
    save_fixture(root, record)
    (root / 'synthetic.txt').write_text('CHANGED SOFTWARE FIXTURE', encoding='utf-8')
    assert 'INSTITUTION_LEVEL_A:EVIDENCE_IDENTITY_MISMATCH' in module.validate_external_capability_record('INSTITUTION_LEVEL_A', 'synthetic.json')


def test_unsigned_receipt_is_rejected(synthetic_capability):
    module, root, record = synthetic_capability
    record['review']['status'] = 'PENDING'
    save_fixture(root, record)
    assert 'INSTITUTION_LEVEL_A:EXTERNAL_REVIEW_NOT_PASS' in module.validate_external_capability_record('INSTITUTION_LEVEL_A', 'synthetic.json')


def test_consumer_navigation_and_scope_explanations():
    for consumer, name in [('G-05', 'current-admission.md'), ('E-01', 'current-execution.md'), ('E-02', 'current-execution.md')]:
        path = ROOT / 'agent/tasks' / consumer / 'outputs' / name
        text = path.read_text(encoding='utf-8-sig')
        assert '../../U12-05/outputs/current-admission.md' in text
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if 'U12-05' in target:
                assert (path.parent / target).resolve().is_file()
    text = (TASK / 'outputs/current-admission.md').read_text(encoding='utf-8-sig')
    for phrase in ('不要求G-05十三项整体DONE', '不能识别机构真实性', '未领取', '首次看到核心材料'):
        assert phrase in text
