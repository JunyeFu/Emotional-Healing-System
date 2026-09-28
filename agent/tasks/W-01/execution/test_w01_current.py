from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
CHECK = runpy.run_path(str(TASK / 'execution/validate_candidate.py'))


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def context():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = {row['task_id']: row for row in csv.DictReader(stream)}
    active = read(GOV / 'active_governance.json')
    return read(TASK / 'outputs/current-paper.json'), read(GOV / active['research_authority']), rows


def test_current_paper_matches_actual_authority_and_registry():
    assert CHECK['current_errors'](*context()) == []


@pytest.mark.parametrize('field,value', [
    ('primary_outcome', 'gate2_joint_pass'),
    ('report_affect_when_guard_fails', False),
    ('scci_role', 'primary_result'),
    ('confirmatory_equivalence_enabled', True),
    ('core_requires_stage_3', True),
    ('formal_randomized_n', 192),
    ('w02_dependencies', ['W-01', 'A-04']),
    ('acceptance_scope', 'FORMAL_RESEARCH_DONE'),
    ('current_search_update', 'COMPLETE'),
    ('human_dual_source_review', 'DONE'),
])
def test_rejects_old_gates_expanded_scope_or_unperformed_work(field, value):
    current, protocol, rows = context()
    current[field] = value
    assert CHECK['current_errors'](current, protocol, rows)


def test_claims_require_counterexample_and_keep_results_unobserved():
    current, protocol, rows = context()
    altered = deepcopy(current)
    altered['claims'][2]['counterexample'] = ''
    assert CHECK['current_errors'](altered, protocol, rows)
    current['claims'][2]['status'] = 'PROVEN'
    assert CHECK['current_errors'](current, protocol, rows)


def test_raw_report_bytes_preserved_and_original_acceptance_unchanged():
    expected = read(TASK / 'inputs/sources.json')['archived_report_sha256_bytes']
    report = next((TASK / 'archive').glob('W-01_2015-2026*.md'))
    assert hashlib.sha256(report.read_bytes()).hexdigest().upper() == expected
    path = PLAN / '25_论文投稿与成果交付/W-01_最近工作与论文骨架/W-01_验收记录.md'
    delta = subprocess.run(['git', 'diff', 'HEAD', '--name-only', '--', str(path)],
                           cwd=ROOT, capture_output=True, text=True, check=True)
    assert not delta.stdout.strip()
    assert 'Codex独立AC审查' in path.read_text(encoding='utf-8-sig')


def test_moved_entry_is_recorded_as_exact_scope_equivalence():
    previous = subprocess.run(['git', 'show', f'6fa45af:{(GOV / "05_可领取任务包.csv").relative_to(ROOT).as_posix()}'],
                              cwd=ROOT, capture_output=True, encoding='utf-8', check=True).stdout
    before = next(row for row in csv.DictReader(previous.splitlines()) if row['task_id'] == 'W-01')
    current, _, rows = context()
    scope_check = runpy.run_path(str(GOV / 'u12_upgrade/validate_u12_governance.py'))['scope_field_matches']
    assert scope_check('W-01', 'evidence_required', before['evidence_required'], rows['W-01']['evidence_required'])
    assert not scope_check('W-01', 'evidence_required', before['evidence_required'], rows['W-01']['evidence_required'] + ';unregistered.py')
    assert not (PLAN / '99_验证与清单/validate_w01_package.py').exists()
    assert current['business_status'] == rows['W-01']['status'] == 'DONE'


def test_active_links_and_sources_resolve():
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).exists(), path
    nav = PLAN / '25_论文投稿与成果交付/W-01_最近工作与论文骨架/W-01_2015-2026最近工作击穿与单篇IJHCI论文骨架_v0.9-candidate.md'
    for path in (nav, TASK / 'outputs/current-paper.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if link == '../evidence/verification.json':
                continue  # The runner writes this artifact after these tests finish.
            assert (path.parent / link).resolve().exists(), link


def test_dispatch_only_refreshes_registry_reference_not_inputs():
    validator = runpy.run_path(str(GOV / '14_validate_ready_task_packages.py'))
    expected = validator['sha256'](GOV / '05_可领取任务包.csv')
    for task_id in ('A-03', 'T-02', 'U12-03', 'U12-06', 'V-05'):
        path = GOV / '当前解锁独立任务包' / task_id / 'package_manifest.json'
        prior = subprocess.run(['git', 'show', f'6fa45af:{path.relative_to(ROOT).as_posix()}'],
                               cwd=ROOT, capture_output=True, encoding='utf-8', check=True)
        original = json.loads(prior.stdout)
        current = read(path)
        assert current.pop('registry_sha256') == expected
        original.pop('registry_sha256')
        assert current == original
    changes = subprocess.run(['git', 'diff', '6fa45af', '--name-only', '--', str(GOV / '当前解锁独立任务包')],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    assert len(changes) == 5 and all(line.endswith('/package_manifest.json"') or line.endswith('/package_manifest.json') for line in changes)
