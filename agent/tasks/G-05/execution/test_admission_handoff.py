"""Check current external scope and missing receipts without authorization."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/G-05'
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
LEGACY = GOV / '第58号任务包_G-05_外部准入闭环'
CAPABILITIES = ('INSTITUTION_LEVEL_A', 'INSTITUTION_LEVEL_B', 'INSTITUTION_LEVEL_C',
                'INSTITUTION_STAGE1', 'INSTITUTION_STAGE3', 'QUESTIONNAIRE_PERMISSION',
                'RETENTION_AND_PRIVACY', 'FORMAL_MACHINE', 'ASSET_EXPERIMENT_USE',
                'ASSET_PUBLICATION_USE', 'ASSET_REDISTRIBUTION',
                'STATION_CAPACITY_STAGE1', 'STATION_CAPACITY_STAGE3')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def test_actual_capabilities_are_pending():
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert {r['capability_id'] for r in rows} == set(CAPABILITIES)
    assert len(rows) == 13
    assert all(r['status'] == 'PENDING_EXTERNAL' and not r['evidence_ref'] for r in rows)


@pytest.mark.parametrize('capability', CAPABILITIES)
def test_missing_external_record_fails_closed(capability):
    path = GOV / '15_validate_audit_upgrade.py'
    spec = importlib.util.spec_from_file_location('g05_existing_validator', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.validate_external_capability_record(capability, '') == [f'{capability}:EVIDENCE_RECORD_MISSING']


@pytest.mark.parametrize('path,sha', [
    ('legacy-package/TASK.md', '5366c7c2f7c88371da47b7634607b638e2935e767752ed047a325875136e8f21'),
    ('legacy-package/FILES.md', 'ff6a1c3f09b199f733bbe79e0fe8a3fc7c1ff265fe54e3bb938c8488372fd571'),
    ('legacy-package/package_manifest.json', 'c9bd414fcf7fa011c0dc2b29ca8bf858a54ab7e2c1026ade78810821900b32dc'),
    ('formal-machine-setup-before-g05.md', '28f2f36e6a9cc25a6cd657c33fa212002080b1d5eeaa4f29455e0862e51bf38f'),
    ('formal-environment-runbook-before-g05.md', '29015582df46fa840bf55237ecb6d1d4040159a32f00768023c46f62abd4b33f'),
])
def test_archives_preserve_original_bytes(path, sha):
    assert hashlib.sha256((TASK / 'archive' / path).read_bytes()).hexdigest() == sha


def test_registry_and_null_real_results():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(row for row in csv.DictReader(stream) if row['task_id'] == 'G-05')
    state = read(TASK / 'outputs/current-admission.json')
    assert row['status'] == state['status'] == 'WAIT_DEP_EXTERNAL'
    assert row['depends_on'].split('|') == state['dependencies']
    assert row['claimant'] == '未领取' and row['reviewer'] == '未指定'
    assert state['real_institution_receipt'] is None and state['approved_retention'] is None
    assert state['u8_real_rehearsal'] is None and state['u8_result'] is None
    assert state['qualified_capabilities'] == 0


def test_current_navigation_links_resolve():
    docs = ROOT / 'agent/modules/07-数据治理/docs'
    for path in (LEGACY / 'TASK.md', LEGACY / 'FILES.md', docs / 'formal_machine_setup.md', docs / 'formal_environment_closure_runbook.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
            assert (path.parent / target).resolve().exists(), (path, target)
    manifest = read(LEGACY / 'package_manifest.json')
    assert manifest['package_role'] == 'LEGACY_NAVIGATION_ONLY'
    assert (LEGACY / manifest['current_task']).resolve() == TASK / 'TASK.md'


def test_sources_and_unchanged_dispatch_inputs():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).exists(), source
    mapping = (GOV / '12_独立任务包文件映射_v1.0.json').read_text(encoding='utf-8-sig')
    for manifest in (GOV / '当前解锁独立任务包').glob('*/package_manifest.json'):
        mapping += manifest.read_text(encoding='utf-8-sig')
    assert 'formal_machine_setup.md' not in mapping
    assert 'formal_environment_closure_runbook.md' not in mapping
    assert '第58号任务包_G-05_外部准入闭环' not in mapping


def test_scope_and_actual_asset_gate_are_not_approvals():
    text = (TASK / 'outputs/current-admission.md').read_text(encoding='utf-8-sig')
    assert 'U12-05' in text
    assert '所有适用checks均通过' in text
    assert '十三项均QUALIFIED' in text and '不能伪造' in text
    report = read(ROOT / 'agent/tasks/Z-01/evidence/asset-scan.json')
    assert report['release_allowed'] is False
    assert len(report['blockers']) == 269
