"""Test normalized sources, frozen inputs and current migration boundaries."""
import csv
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[4]
git_bytes = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['git_source_bytes']
TASK = ROOT / 'agent/tasks/U12-06'
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
LEGACY = ROOT / 'agent/governance/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-06'
DISPATCH = GOV / '当前解锁独立任务包/U12-06'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


@pytest.mark.parametrize('name', ['candidate/TASK.md', 'candidate/FILES.md', 'candidate/package_manifest.json', 'candidate/inputs/task_input.json', 'content-review-before-normalization.md'])
def test_archived_bytes(name):
    assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == read(TASK / 'inputs/sources.json')['archived_bytes'][name]


def test_original_candidate_manifest_preserves_input_identity():
    archive = TASK / 'archive/candidate'
    manifest = read(archive / 'package_manifest.json')
    for item in manifest['files']:
        assert hashlib.sha256((archive / item['path']).read_bytes()).hexdigest() == item['byte_sha256']


def test_all_claimed_package_bytes_and_identity_unchanged():
    sources = read(TASK / 'inputs/sources.json')
    for path in DISPATCH.rglob('*'):
        if path.is_file():
            previous = git_bytes(ROOT, sources['frozen_dispatch_baseline_commit'], path.relative_to(ROOT).as_posix())
            assert path.read_bytes() == previous or path.read_bytes().replace(b'\r\n', b'\n') == previous
    manifest = read(DISPATCH / 'package_manifest.json')
    assert manifest['input_snapshot_id'] == sources['frozen_input_snapshot_id']
    assert manifest['candidate_identity'] == sources['frozen_candidate_identity']


def test_frozen_source_relocation_points_to_original():
    resolve = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['resolve_source']
    old = (LEGACY / 'inputs/task_input.json').relative_to(ROOT).as_posix()
    assert resolve(ROOT, 'U12-06', 'IN_PROGRESS', old) == TASK / 'archive/candidate/inputs/task_input.json'


def test_registration_and_consumer_gaps_remain_current():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(row for row in csv.DictReader(stream) if row['task_id'] == 'U12-06')
    assert row['status'] == 'IN_PROGRESS' and row['claimant'] == '傅钧烨'
    assert row['branch'] == 'codex/u12-06-formal-gate'
    consumers = [item for item in read(GOV / 'u12_upgrade/consumers.json')['entries'] if item['owner'] == 'U12-06']
    assert len(consumers) == 6
    assert all(item['status'] == 'PENDING_RUNTIME_MIGRATION' for item in consumers)
    for item in consumers:
        assert (ROOT / item['path']).is_file()


def test_sources_and_navigation_are_actual():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for path in (LEGACY / 'TASK.md', LEGACY / 'FILES.md', GOV / 'content_reviews/U12-06_内容核验记录.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
            assert (path.parent / target).resolve().exists(), (path, target)


def test_fixture_behavior_does_not_establish_new_research_gate():
    report = read(TASK / 'evidence/runtime-observations.json')
    assert report['default_formal'] == {'result': 'REJECTED', 'code': 'FORMAL_GATE_UNAVAILABLE', 'detail': 'assignment_gate'}
    assert report['synthetic_formal']['status'] == 'PREPARED'
    assert 'formal-fixture:PASS' in report['synthetic_formal']['gate_evidence_ids']
    assert not report['real_approval_read'] and not report['formal_research_gate_delivered']
    assert not report['tcp_udp_sent'] and not report['real_exposure_registered']


def test_unfilled_research_template_and_separate_versions():
    template = read(GOV / 'u12_upgrade/study_manifest_v1.2.template.json')
    assert template['document_type'] == 'UNFILLED_TEMPLATE_NOT_APPROVAL'
    assert template['protocol_version'] == '1.2' and template['runtime_contract_version'] == '2.2'
    assert template['formal_collection_allowed'] is False
    for key in ('final_randomized_n', 'institutional_scope_evidence', 'live_e2e_evidence_hash', 'runtime_gate_integration_evidence_hash', 'preregistration_receipt'):
        assert template[key] is None
