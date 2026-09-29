import csv
from importlib import import_module
import json
from pathlib import Path
import sys
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/S-02'
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
sys.path.insert(0, str(ROOT / 'agent/modules'))
v22 = import_module('05-通信协议.runtime_contract_v22')


def current():
    return json.loads((TASK / 'outputs/current-events.json').read_text(encoding='utf-8'))


def fixture(module):
    path = ROOT / 'agent/modules/05-通信协议/contracts/fixtures-v2.2/valid/telemetry-actual-unavailable.json'
    frame = json.loads(path.read_text(encoding='utf-8'))
    frame['module_id'] = module
    frame['target_step_id'] = 'exhale_1'
    frame['target_phase'] = 'exhale'
    return frame


def test_current_state_and_real_work_not_invented():
    with (PLAN / '24_团队任务与项目治理/05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'S-02')
    value = current()
    assert row['status'] == value['status'] == 'WAIT_DEP'
    assert set(row['depends_on'].split('|')) == set(value['depends_on'])
    assert value['claimant'] is None
    assert not value['real_event_detector_implemented']
    assert not value['online_pf_implemented'] and not value['dual_annotation_verified']
    assert not value['controls_session_clock_or_order']
    assert not value['actual_may_copy_target'] and not value['legacy_calm_index_is_pf']
    assert value['online_offline_pf_tolerance'] is None
    assert value['structure_tolerances'] is None


def test_steps_and_research_roles_align_with_current_authorities():
    value = current()
    assert value['step_phases'] == v22.STEP_PHASES
    assert value['module_weights'] == dict.fromkeys(v22.STEP_PHASES, 0.25)
    assert set(value['opportunity_states']) == {'COMPLIANT', 'NONCOMPLIANT', 'TECH_UNOBSERVABLE'}
    assert not value['missing_module_may_reweight']
    assert not value['unobservable_may_be_noncompliant']
    protocol = json.loads((PLAN / '00_总控/protocol_authority_v1.2.json').read_text(encoding='utf-8-sig'))
    assert value['pf_blocks_affect_reporting'] == protocol['functional_guard']['blocks_affect_reporting'] == False
    assert value['cycle_f1_minimum'] == 0.85 and value['boundary_mae_maximum_seconds'] == 0.50


@pytest.mark.parametrize('module', ['storm', 'heat', 'snow', 'fade'])
def test_unavailable_actual_is_valid_without_target_copy(module):
    frame = fixture(module)
    filtered = v22.validate_and_filter('telemetry_frame', frame)
    assert all(filtered[key] == expected for key, expected in current()['actual_unavailable'].items())
    assert filtered['target_step_id'] is not None


@pytest.mark.parametrize('module', ['storm', 'fade'])
def test_repeated_phase_steps_have_distinct_identity(module):
    frame = fixture(module)
    phase = 'hold' if module == 'storm' else 'inhale'
    pair = ('hold_1', 'hold_2') if module == 'storm' else ('inhale_1', 'inhale_2')
    for step in pair:
        frame.update(actual_phase=phase, actual_progress=0.5, actual_cycle_index=2, actual_step_id=step)
        assert v22.validate_and_filter('telemetry_frame', frame)['actual_step_id'] == step


def test_phase_without_step_instance_is_rejected():
    frame = fixture('fade')
    frame.update(actual_phase='inhale', actual_progress=0.5)
    with pytest.raises(v22.ContractValidationError, match='EMPTY_STEP_STATE_MISMATCH'):
        v22.validate_and_filter('telemetry_frame', frame)


def test_retired_score_not_accepted_as_formal_telemetry():
    frame = fixture('storm')
    frame['calm_index'] = 50
    with pytest.raises(v22.ContractValidationError):
        v22.validate_and_filter('telemetry_frame', frame)


def test_archive_and_frozen_input_are_kept_separate():
    assert not (ROOT / 'agent/modules/02-信号处理/评分模型设计.md').exists()
    assert (TASK / 'archive/评分模型设计.md').is_file()
    frozen = PLAN / '24_团队任务与项目治理/当前解锁独立任务包/A-03/inputs/06_评分模型设计.md'
    assert frozen.is_file()
    assert '2026-09-28归档说明' not in frozen.read_text(encoding='utf-8-sig')
    assert (TASK / 'evidence/consumer-impact.md').is_file()


@pytest.mark.parametrize('status', ['IN_PROGRESS', 'IN_REVIEW'])
def test_frozen_source_relocation_preserves_content_and_identity(status):
    resolver = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['resolve_source']
    validator = runpy.run_path(str(PLAN / '24_团队任务与项目治理/14_validate_ready_task_packages.py'))
    old = 'agent/modules/02-信号处理/评分模型设计.md'
    resolved = resolver(ROOT, 'A-03', status, old)
    assert resolved == TASK / 'archive/评分模型设计.md'
    renderer = runpy.run_path(str(PLAN / '24_团队任务与项目治理/13_render_ready_task_packages.py'))
    assert renderer['safe_source'](old, 'A-03', status) == resolved
    package = PLAN / '24_团队任务与项目治理/当前解锁独立任务包/A-03'
    manifest = json.loads((package / 'package_manifest.json').read_text(encoding='utf-8-sig'))
    historical_path = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['historical_project_path'](ROOT, old)
    item = next(x for x in manifest['source_files'] if x['source_path'] == historical_path)
    assert validator['sha256'](resolved) == item['sha256'] == validator['sha256'](package / item['package_path'])


@pytest.mark.parametrize('task,status,source', [
    ('S-02', 'IN_PROGRESS', 'agent/modules/02-信号处理/评分模型设计.md'),
    ('A-03', 'READY', 'agent/modules/02-信号处理/评分模型设计.md'),
    ('A-03', 'IN_PROGRESS', 'agent/modules/02-信号处理/unknown.md'),
    ('A-03', 'IN_PROGRESS', '../outside.md'),
])
def test_unregistered_or_non_frozen_source_is_not_redirected(task, status, source):
    resolver = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['resolve_source']
    assert resolver(ROOT, task, status, source) == (ROOT / source).resolve()
