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
    tree = ast.parse((BASE.parents[3] / 'agent/tasks/T-01/execution/build_workbench_a.py').read_text(encoding='utf-8'))
    runtime = next(n.value.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'RUNTIME' for t in n.targets))
    compile(runtime, '<TD frame callback>', 'exec')
    assert '50_000_000' in runtime
    assert 'ingest_datagram' not in runtime
    assert 'sendto' not in runtime
    assert 'save(' not in runtime


def test_overview_uses_chinese_without_changing_legacy_values_or_details():
    data = frame()
    data['runtime_mode'] = 'dev_replay'
    adapter = T01TelemetryAdapter()
    assert adapter.ingest_datagram(json.dumps(data), 0).accepted
    model = view_model(adapter.read_snapshot(0))
    assert model['overview_values']['runtime_mode'] == '开发回放'
    assert model['values']['runtime_mode'] == 'dev_replay'
    assert model['details']['telemetry.runtime_mode'] == 'dev_replay'
    assert model['overview_values']['cue_mode'] in ('场景原生提示', '抽象呼吸提示')
    assert model['values']['cue_mode'].endswith('(' + data['cue_mode'] + ')')
    assert model['overview_values']['target_phase'] == '保持'
    assert '(' not in model['overview_values']['resp_state']
    assert '(' not in model['overview_values']['fallback_state']


def test_overview_waiting_and_disconnect_keep_missing_and_history():
    adapter = T01TelemetryAdapter()
    waiting = view_model(adapter.read_snapshot(0))['overview_values']
    assert waiting['resp_state'] == '未知'
    assert waiting['resp_sqi'] == MISSING
    assert waiting['actual_confidence'] == MISSING
    assert adapter.ingest_datagram(json.dumps(frame()), 0).accepted
    disconnected = view_model(adapter.read_snapshot(2_000_000_000))
    assert '末帧历史值' in disconnected['overview_values']['status']
    assert disconnected['details']['telemetry.target_step_id'] == frame()['target_step_id']
    assert disconnected['overview_values']['resp_state'].startswith('末帧：')
    assert disconnected['overview_values']['resp_sqi'].startswith('历史 ')


@pytest.mark.parametrize('value', ['bad', 1.4, -.2, True, float('nan')])
def test_invalid_sqi_is_rejected_without_crashing_view(value):
    data = frame()
    data['signal_quality']['resp'] = value
    adapter = T01TelemetryAdapter()
    assert not adapter.ingest_datagram(json.dumps(data), 0).accepted
    assert view_model(adapter.read_snapshot(0))['values']['resp_sqi'] == MISSING


def test_readable_palette_text_contrast():
    namespace = {}
    source = (BASE.parents[3] / 'agent/tasks/T-01/execution/build_workbench_a.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    assignments = {target.id: node.value for node in tree.body if isinstance(node, ast.Assign)
                   for target in node.targets if isinstance(target, ast.Name)}
    palette = ast.literal_eval(assignments['PALETTE'])
    statuses = ast.literal_eval(assignments['STATUS_COLORS'])

    def luminance(code):
        values = [int(code[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))

    pairs = list(statuses.values()) + [(palette['text'], palette['body']),
        (palette['muted'], palette['canvas']), (palette['teal_text'], palette['teal']),
        (palette['blue_text'], palette['blue'])]
    for foreground, background in pairs:
        low, high = sorted((luminance(foreground), luminance(background)))
        assert (high + .05) / (low + .05) >= 4.5
    low, high = sorted((luminance(palette['selected']), luminance(palette['canvas'])))
    assert (high + .05) / (low + .05) >= 3
