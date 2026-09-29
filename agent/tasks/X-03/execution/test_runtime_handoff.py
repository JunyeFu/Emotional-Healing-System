import csv
from dataclasses import fields, replace
import importlib.util
import json
from pathlib import Path
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
TECH = ROOT / 'agent/modules'
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(TECH))
from srp_session_core import RuntimeDependencies, SessionCore, SessionCoreError, SessionStatus
from srp_session_core.models import SessionSnapshot
from srp_session_core.sequence import FixedSequenceProvider
from srp_session_store import DurableManifestStore, RecordingSessionCore, ReplayReader, SessionReplayer, StoreError


def current():
    return json.loads((TASK / 'outputs/current-runtime.json').read_text(encoding='utf-8'))


def factories():
    spec = importlib.util.spec_from_file_location('x03_existing_core_fixtures', TECH / 'tests/session_core/conftest.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.manifest_factory.__wrapped__(), module.assignment_factory.__wrapped__()


def test_actual_registration_and_missing_implementation():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'X-03')
    value = current()
    assert row['status'] == value['business_status'] == 'WAIT_DEP'
    assert value['depends_on'] == row['depends_on'].split('|')
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is None
    for field in ('loader_implemented', 'dynamic_sequence_implemented', 'policy_replay_implemented', 'same_unity_build_verified'):
        assert value[field] is False
    assert 'E-05' in row['completion_condition']


@pytest.mark.parametrize('runtime_mode', ['dev_replay', 'formal_stage_3'])
def test_actual_v22_frozen_policy_rejected_before_control(runtime_mode):
    manifest_factory, assignment_factory = factories()
    manifest = manifest_factory(schema_version='2.2', study_stage='stage_3', runtime_mode=runtime_mode, assignment_arm='frozen_policy')
    manifest['strategy_version'] = 'SYNTHETIC-X03-POLICY'
    core = SessionCore()
    with pytest.raises(SessionCoreError) as error:
        core.prepare(manifest, assignment_factory(manifest), 0)
    assert error.value.code == current()['v22_frozen_policy_rejection']
    assert core.snapshot().status is SessionStatus.CREATED
    assert core.control_log == ()


def test_existing_prepare_still_declares_fixed_sequence():
    manifest_factory, assignment_factory = factories()
    manifest = manifest_factory(schema_version='2.2')
    core = SessionCore()
    update = core.prepare(manifest, assignment_factory(manifest), 0)
    assert update.control_events[0]['payload']['sequence_mode'] == current()['current_prepare_sequence_mode'] == 'fixed'
    assert len(manifest['weather_sequence']) == 4


def test_fixed_provider_ignores_changed_session_state():
    manifest_factory, assignment_factory = factories()
    manifest = manifest_factory(schema_version='2.2')
    provider = FixedSequenceProvider()
    plan = provider.prepare(manifest, assignment_factory(manifest))
    snapshot = SessionCore().snapshot()
    changed = replace(snapshot, segment_progress=0.9, paused_duration_ns=999)
    assert provider.next(0, snapshot) == provider.next(0, changed)
    assert len(plan.modules) == len(plan.decisions) == 4
    assert {'recent_breathing_pf', 'recent_breathing_sqi', 'panas_pre'}.isdisjoint(f.name for f in fields(SessionSnapshot))
    assert current()['session_snapshot_has_breathing_state'] is False


def test_missing_future_sequence_not_accepted_by_existing_manifest():
    manifest_factory, assignment_factory = factories()
    manifest = manifest_factory(schema_version='2.2')
    assignment = assignment_factory(manifest)
    manifest['weather_sequence'] = None
    with pytest.raises(SessionCoreError):
        SessionCore().prepare(manifest, assignment, 0)
    assert current()['current_manifest_requires_full_sequence'] is True


def test_actual_p02_replay_refuses_custom_policy_core_without_calling_it(tmp_path):
    manifest_factory, assignment_factory = factories()
    manifest = manifest_factory(schema_version='2.2')
    store = DurableManifestStore.development(tmp_path)
    dependencies = RuntimeDependencies.development()
    dependencies.manifest_store = store
    recorder = RecordingSessionCore(SessionCore(dependencies=dependencies), store)
    recorder.prepare(manifest, assignment_factory(manifest), 0)
    summary = recorder.finish('SYNTHETIC_TEST', 1)
    store.archive.seal(summary, 1)
    store.archive.close()
    replayer = SessionReplayer(ReplayReader.open(tmp_path, manifest['session_id']))
    assert replayer.replay_core().valid

    class UnapprovedPolicyCore:
        def __init__(self, **kwargs):
            raise AssertionError('unsafe factory must never be called')

    with pytest.raises(StoreError, match='REPLAY_CORE_UNSAFE'):
        replayer.replay_core(core_factory=UnapprovedPolicyCore)
    assert current()['p02_custom_core_factory_allowed'] is False


def test_optional_route_fallback_arm_and_unsigned_model():
    route = json.loads((GOV / 'audit_upgrade/release_routes_v1.2.json').read_text(encoding='utf-8'))
    assert 'X-03' in route['routes']['stage1_only']['not_required_to_mark_done']
    value = current()
    assert value['required_for_core_paper'] is False
    assert value['fallback_preserves_assignment_arm'] is True
    for field in ('strategy_contract_version', 'actual_policy_manifest', 'fallback_thresholds', 'actual_replay_report', 'actual_readonly_evidence', 'actual_build_identity_evidence'):
        assert value[field] is None


def test_current_sources_and_activity_correction():
    for path in json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))['paths']:
        assert (ROOT / path).is_file(), path
    text = (PLAN / '21_真实设备与在线运行系统/02_Python模块设计.md').read_text(encoding='utf-8')
    assert 'F-05步骤合同不提供动态顺序接口' in text
    assert 'v2.1及v2.2均只支持' in text
