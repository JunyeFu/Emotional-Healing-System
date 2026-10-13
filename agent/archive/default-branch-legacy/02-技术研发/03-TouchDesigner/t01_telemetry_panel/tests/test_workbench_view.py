from copy import deepcopy
import ast
import json
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from t01_telemetry import T01TelemetryAdapter
from workbench_view import COUNTERS, MISSING, compact, display, view_model


def frame():
    path = BASE.parents[1] / '05-通信协议/contracts/consumer-fixtures/v2.2/touchdesigner/phase-instance-stream.jsonl'
    return json.loads(path.read_text(encoding='utf-8').splitlines()[0])


def test_waiting_preserves_unknown_and_local_zero():
    model = view_model(T01TelemetryAdapter().read_snapshot(0))
    assert model['values']['status'] == '等待遥测'
    assert model['values']['resp_state'] == '未知'
    assert model['values']['resp_sqi'] == MISSING
    assert model['values']['recovery_locked'] == MISSING
    assert all(model['values'][key] == '0' for key, _ in COUNTERS)


def test_real_contract_fields_and_source_snapshot_remain_unchanged():
    data = frame()
    adapter = T01TelemetryAdapter()
    assert adapter.ingest_datagram(json.dumps(data), 0).accepted
    snapshot = adapter.read_snapshot(0)
    before = deepcopy(data)
    model = view_model(snapshot)
    assert model['values']['target_cycle_index'] == str(data['target_cycle_index'])
    assert model['values']['cue_mode'].endswith('(' + data['cue_mode'] + ')')
    assert model['values']['actual_confidence'] == display(data['actual_confidence'], percent=True)
    assert model['values']['recovery_value'] == str(data['recovery_value'])
    assert dict(snapshot.telemetry) == before


def test_disconnect_retains_explicit_historical_marker():
    adapter = T01TelemetryAdapter()
    assert adapter.ingest_datagram(json.dumps(frame()), 0).accepted
    model = view_model(adapter.read_snapshot(2_000_000_000))
    assert '断流' in model['values']['status']
    assert '末帧历史值' in model['values']['status']
    assert '帧序号' in model['values']['footer']


def test_rejected_packet_surfaces_receiver_error():
    adapter = T01TelemetryAdapter()
    adapter.ingest_datagram('{', 0)
    model = view_model(adapter.read_snapshot(0))
    assert model['values']['invalid_frames'] == '1'
    assert model['values']['last_error'] == 'INVALID_JSON'


def test_long_identifiers_retained_in_details():
    data = frame()
    data['session_id'] = 'session-' + 'x' * 200
    adapter = T01TelemetryAdapter()
    assert adapter.ingest_datagram(json.dumps(data), 0).accepted
    model = view_model(adapter.read_snapshot(0))
    assert model['details']['telemetry.session_id'] == data['session_id']
    assert len(compact(model['values']['session_id'])) == 42


@pytest.mark.parametrize('value,expected', [(None, MISSING), (0, '0.0%'), (1, '100.0%'), (.123, '12.3%')])
def test_percent_missing_and_zero_are_distinct(value, expected):
    assert display(value, percent=True) == expected


def test_candidate_builder_callbacks_compile_without_running_td():
    tree = ast.parse((BASE / 'build_workbench_a.py').read_text(encoding='utf-8'))
    runtime = next(n.value.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'RUNTIME' for t in n.targets))
    compile(runtime, '<TD frame callback>', 'exec')
    assert '50_000_000' in runtime
    assert 'ingest_datagram' not in runtime
    assert 'sendto' not in runtime
    assert 'save(' not in runtime
