import csv
import hashlib
import json
import runpy
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def test_archive_actual_bytes_and_original_acceptance():
    current = read(TASK / 'outputs/current-governance.json')
    for name, expected in current['archive_byte_sha256'].items():
        assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == expected
    assert hashlib.sha256((GOV / 'u12_upgrade/acceptance/U12-01.json').read_bytes()).hexdigest().upper() == current['unchanged_acceptance_byte_sha256']
    assert not (GOV / 'u12_upgrade/record_u12_01_signoff.py').exists()

def test_scoped_acceptance_not_formal_authorization():
    consumers = read(GOV / 'u12_upgrade/consumers.json')
    assert consumers['formal_collection_allowed'] is False
    assert len(consumers['entries']) == 15
    for entry in consumers['entries']:
        root = GOV.parent if entry['root'] == 'plan' else ROOT
        assert (root / entry['path']).is_file()
        if entry['owner'] in ('U12-02', 'U12-04'):
            assert entry['status'] == 'SCOPED_CANDIDATE_ACCEPTED_NOT_LIVE'
            evidence = read(ROOT / entry['acceptance_path'])
            assert evidence['human_review']['reviewer'] == '傅钧烨'
            assert evidence['human_review']['status'] == 'PASS'
            assert entry['limit']
    pending = [e for e in consumers['entries'] if e['owner'] == 'U12-06']
    assert len(pending) == 6
    assert all(e['status'] == 'PENDING_RUNTIME_MIGRATION' for e in pending)

def test_registry_and_historical_scope_preserved():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U12-01')
    assert row['status'] == 'DONE' and row['reviewer'] == '傅钧烨'
    original = read(GOV / 'u12_upgrade/acceptance/U12-01.json')
    assert original['candidate_commit'] == '47c81744884ae380e047cafb722aeb332c8cda29'
    assert original['independent_review']['reviewer'] == 'Pascal'
    binding = read(GOV / 'u12_upgrade/legacy_evidence_binding.json')
    unresolved = [e for group in binding['entries'].values() for e in group if e['original_byte_identity'] == 'UNRESOLVED_WORKTREE_BYTES']
    assert len(unresolved) == 6

def test_navigation_and_scope_sources_exist():
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).is_file()
    assert 'agent/tasks/U12-01/outputs/current-governance.md' in (GOV / 'u12_upgrade/README.md').read_text(encoding='utf-8')
    current = read(TASK / 'outputs/current-governance.json')
    assert current['current_independent_review'] == 'NOT_RUN'
    assert current['current_human_acceptance'] == 'NOT_SIGNED'
    assert current['root_migration_complete'] is False

def test_frozen_and_current_consumer_resolution_are_separate():
    resolve = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['resolve_source']
    relative = (GOV / 'u12_upgrade/consumers.json').relative_to(ROOT).as_posix()
    assert resolve(ROOT, 'U12-03', 'IN_REVIEW', relative) == TASK / 'archive/consumers.json'
    assert resolve(ROOT, 'U12-06', 'IN_PROGRESS', relative) == TASK / 'archive/consumers.json'
    assert resolve(ROOT, 'U12-01', 'DONE', relative) == ROOT / relative
    assert resolve(ROOT, 'U12-06', 'READY', relative) == ROOT / relative
    old = read(TASK / 'archive/consumers.json')
    assert all(e['status'] == 'PENDING_SCOPE_REVIEW' for e in old['entries'] if e['owner'] in ('U12-02', 'U12-04'))
