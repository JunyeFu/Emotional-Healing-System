"""Tests of current facts, not acceptance tests for an implemented T-02."""
import asyncio
from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
TECH = ROOT / 'agent/modules'
sys.path.insert(0, str(TECH))
from srp_session_core import OperatorRequest, RuntimeDependencies, SessionCore
from srp_session_core.transport import ControlServer
from srp_session_store import DurableManifestStore, RecordingSessionCore, ReplayReader, SessionReplayer

GOLDEN = runpy.run_path(str(ROOT / 'agent/tasks/P-01/execution/generate_golden_trace.py'))
CONTRACT = json.loads((TASK / 'outputs/current-operator-contract.json').read_text(encoding='utf-8'))
ARCHIVE = json.loads((TASK / 'inputs/legacy-relocations.json').read_text(encoding='utf-8'))


def prepared_inputs():
    manifest = GOLDEN['_manifest']()
    manifest.update(schema_version='2.2', breath_protocol_config_version='2.2',
                    breath_protocol_config_hash=SessionCore().breath_config.config_hash)
    assignment = GOLDEN['_assignment'](manifest)
    for decision in assignment.policy_decisions:
        decision['schema_version'] = '2.2'
    return manifest, assignment


@pytest.mark.parametrize('item', ARCHIVE['files'], ids=lambda item: item['original_path'])
def test_archive_keeps_checkout_bytes(item):
    data = (ROOT / item['archive_path']).read_bytes()
    assert len(data) == item['bytes']
    assert sha256(data).hexdigest().upper() == item['sha256']
    original = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['resolve_project_path'](ROOT, item['original_path'])
    if original.suffix == '.md' and original.name in ('TD原型规划.md', 'step-3-breath-animation.md'):
        assert '当前' in original.read_text(encoding='utf-8')
        assert 'tasks/T-02' in original.read_text(encoding='utf-8')
    else:
        assert not original.exists()


def test_current_contract_does_not_claim_implemented_requests():
    assert CONTRACT['business_status'] == 'READY'
    assert CONTRACT['claimant'] is None and CONTRACT['reviewer'] is None
    assert CONTRACT['request_protocol_status'] == 'NOT_IMPLEMENTED'
    assert CONTRACT['request_schema'] is None and CONTRACT['request_ack_schema'] is None
    assert CONTRACT['manual_mark_core_action'] is False
    assert CONTRACT['operator_ack_is_unity_ack'] is False
    assert CONTRACT['alarm_ack_changes_quality_or_session'] is False
    assert CONTRACT['required_evidence_status'] == 'NOT_DELIVERED'


@pytest.mark.parametrize('action', ['manual_mark', 'set_threshold', 'set_weather', 'end', 'resume'])
def test_unknown_internal_actions_do_not_control_or_change_session(action):
    manifest, assignment = prepared_inputs()
    core = SessionCore()
    core.prepare(manifest, assignment, 0)
    before = core.snapshot()
    update = core.apply_operator_request(OperatorRequest('request-' + action, action), 1)
    assert update.snapshot == before
    assert not update.control_events and not update.session_events
    assert update.audit_records[0].result == 'rejected'
    assert update.audit_records[0].reason_code == 'UNKNOWN_OPERATOR_ACTION'


def test_abort_recording_replays_without_td_or_network(tmp_path):
    manifest, assignment = prepared_inputs()
    store = DurableManifestStore.development(tmp_path)
    dependencies = RuntimeDependencies.development()
    dependencies.manifest_store = store
    core = RecordingSessionCore(SessionCore(dependencies=dependencies), store)
    try:
        core.prepare(manifest, assignment, 0)
        request = OperatorRequest('test-abort', 'abort', 'OPERATOR_REQUEST')
        update = core.apply_operator_request(request, 1)
        assert update.snapshot.status.value == 'ABORTED'
        assert len(update.control_events) == 1
        duplicate = core.apply_operator_request(request, 2)
        assert not duplicate.control_events
        assert duplicate.audit_records[0].reason_code == 'DUPLICATE_OPERATOR_REQUEST'
        summary = core.finish('OPERATOR_REQUEST', 3)
        store.archive.seal(summary, 3)
    finally:
        if store.archive is not None:
            store.archive.close()
    reader = ReplayReader.open(tmp_path, manifest['session_id'])
    assert reader.verify().valid
    assert list(reader.iter_l1(record_type='audit_record'))
    assert SessionReplayer(reader).replay_core().valid


@pytest.mark.parametrize('action', ['manual_mark', 'abort', 'set_threshold', 'set_weather'])
def test_real_loopback_td_handshake_is_not_a_request_handler(action):
    async def scenario():
        manifest, assignment = prepared_inputs()
        core = SessionCore()
        core.prepare(manifest, assignment, 0)
        before = core.snapshot()
        server = ControlServer(core, port=0)
        await server.start()
        writer = None
        try:
            reader, writer = await asyncio.open_connection('127.0.0.1', server.bound_port)
            hello = dict(transport_type='hello', transport_version='1.0', role='td',
                         schema_version='2.2', client_instance_id='t02-boundary-test')
            writer.write(json.dumps(hello).encode() + b'\n')
            await writer.drain()
            assert json.loads(await asyncio.wait_for(reader.readline(), 2))['accepted'] is True
            writer.write(json.dumps({'action': action, 'request_id': 'test-request'}).encode() + b'\n')
            await writer.drain()
            response = json.loads(await asyncio.wait_for(reader.readline(), 2))
            assert response['error_code'] == 'TD_STATE_CHANGE_NOT_AVAILABLE'
            assert response['transport_type'] == 'error'
            assert core.snapshot() == before
            assert not server.unity_connected
        finally:
            if writer is not None:
                writer.close()
                await writer.wait_closed()
            await server.close()
    asyncio.run(scenario())


def test_current_sources_and_handoff_are_accessible():
    for path in json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))['paths']:
        assert (ROOT / path).exists(), path
    assert CONTRACT['core_workbench_features'] == ['UI13', 'UI14', 'UI15', 'UI16']
    assert CONTRACT['requested_extensions_not_implemented'] == ['UI17', 'UI18', 'UI19', 'UI20']
