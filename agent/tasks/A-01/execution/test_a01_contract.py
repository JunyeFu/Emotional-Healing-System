"""Consumer evidence for A-01; synthetic data is not an event pipeline."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import runpy
import socket
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/A-01'
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
sys.path.insert(0, str(ROOT / '02-技术研发'))
from srp_session_store import ReplayReader, SessionReplayer
from srp_session_store.evidence_bundle import validate_bundle

make_bundle = runpy.run_path(str(ROOT / '02-技术研发/tests/session_store/test_evidence_bundle.py'))['bundle']


def test_archive_original_bytes():
    for item in json.loads((TASK / 'inputs/legacy-relocations.json').read_text(encoding='utf-8'))['files']:
        assert hashlib.sha256((TASK / 'archive' / item['name']).read_bytes()).hexdigest().upper() == item['sha256']


def test_current_navigation_links_exist():
    for name in ('02_QC与分析集规则.md', '03_呼吸事件与Protocol_Fidelity.md'):
        source = PLAN / '22_离线处理与科研分析' / name
        for target in re.findall(r'\]\(([^)]+)\)', source.read_text(encoding='utf-8')):
            assert (source.parent / target).resolve().is_file(), target
        assert '当前' in source.read_text(encoding='utf-8')


def test_current_scope_and_independent_emotion():
    contract = json.loads((TASK / 'outputs/current-rebuild.json').read_text(encoding='utf-8'))
    assert contract['business_status'] == 'WAIT_DEP'
    assert contract['owner'] is None
    assert contract['implementation'] == 'OFFLINE_PIPELINE_NOT_DELIVERED'
    assert contract['primary_emotion_independent_of_pf_gate']
    assert not contract['frozen_A03_input_refresh']
    assert contract['event_tolerances'] is None
    assert contract['online_offline_difference_limits'] is None


@pytest.mark.parametrize('family', ['runtime_facts', 'questionnaires', 'allocations', 'annotations', 'configuration_build'])
def test_non_wave_changes_input_identity(family, tmp_path):
    candidate = make_bundle(tmp_path)
    before = validate_bundle(candidate, tmp_path)
    artifact = next(item for item in candidate['artifacts'] if item['family'] == family)
    path = tmp_path / artifact['location']
    path.write_text('changed synthetic ' + family, encoding='utf-8')
    artifact['content_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    after = validate_bundle(candidate, tmp_path)
    assert before['ok'] and after['ok']
    assert before['input_identity'] != after['input_identity']


def test_restricted_metadata_not_original_access(tmp_path):
    candidate = make_bundle(tmp_path)
    for artifact in candidate['artifacts']:
        (tmp_path / artifact['location']).unlink()
        artifact.update(location_type='restricted_ref', location='restricted://' + artifact['artifact_id'])
    result = validate_bundle(candidate, tmp_path)
    assert result['ok']
    assert result['authorization'] is False
    assert not list(tmp_path.iterdir())


def test_required_explicit_none_is_still_missing(tmp_path):
    candidate = make_bundle(tmp_path)
    candidate['artifacts'][0].update(location_type='explicit_none', location='none://not-collected',
                                    hash_strategy=None, content_sha256=None, reason_code='NOT_COLLECTED')
    result = validate_bundle(candidate, tmp_path)
    assert not result['ok']
    assert any('REQUIRED_ARTIFACT_MISSING' in item for item in result['errors'])


def test_golden_core_replay_is_read_only_without_network(monkeypatch):
    fixture = ROOT / 'agent/tasks/P-02/evidence/runtime/session-archive-v1'
    before = {str(p.relative_to(fixture)): p.read_bytes() for p in fixture.rglob('*') if p.is_file()}
    def reject_socket(*args, **kwargs):
        raise AssertionError('Offline replay must not open network transport')
    monkeypatch.setattr(socket, 'socket', reject_socket)
    reader = ReplayReader.open(fixture, 'S-P01-GOLDEN-0001')
    integrity = reader.verify(mode='strict')
    assert integrity.valid and integrity.sealed
    facts = list(reader.iter_l1())
    assert sum(item['record_type'] == 'control_event' for item in facts) == 19
    assert sum(item['record_type'] == 'render_receipt' for item in facts) == 12
    first = SessionReplayer(reader).replay_core()
    second = SessionReplayer(reader).replay_core()
    assert first.valid and second.valid
    assert first.operation_count == 46
    assert first.actual_final_hash == second.actual_final_hash
    after = {str(p.relative_to(fixture)): p.read_bytes() for p in fixture.rglob('*') if p.is_file()}
    assert before == after


def test_legacy_checker_negative_marker_reports_without_path_exception(tmp_path, capsys):
    path = PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py'
    spec = importlib.util.spec_from_file_location('legacy_a01', path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    sample = tmp_path / 'missing.md'
    sample.write_text('historical text', encoding='utf-8')
    checker.PROJECT_ROOT = tmp_path
    checker.ACTIVE_FILES = []
    checker.REQUIRED_MARKERS = {sample: ('expected_cycle_opportunity',)}
    checker.HISTORICAL_FILES = []
    assert checker.main() == 1
    assert 'missing.md missing v1.1 marker' in capsys.readouterr().out


def test_A03_frozen_total_design_is_unchanged():
    path = PLAN / '22_离线处理与科研分析/00_离线处理总设计.md'
    renderer = runpy.run_path(str(PLAN / '24_团队任务与项目治理/13_render_ready_task_packages.py'))
    manifest = json.loads((PLAN / '24_团队任务与项目治理/当前解锁独立任务包/A-03/package_manifest.json').read_text(encoding='utf-8-sig'))
    frozen = next(item for item in manifest['source_files'] if item['source_path'].endswith('/00_离线处理总设计.md'))
    assert renderer['sha256'](path) == frozen['sha256']
