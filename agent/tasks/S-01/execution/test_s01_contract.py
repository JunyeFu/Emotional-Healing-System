import csv
from importlib import import_module
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/S-01'
sys.path.insert(0, str(ROOT / '02-技术研发'))
v21 = import_module('05-通信协议.runtime_contract')
v22 = import_module('05-通信协议.runtime_contract_v22')


def current():
    return json.loads((TASK / 'outputs/current-quality.json').read_text(encoding='utf-8'))


def fixture():
    path = ROOT / '02-技术研发/05-通信协议/contracts/fixtures-v2.2/valid/telemetry-actual-unavailable.json'
    return json.loads(path.read_text(encoding='utf-8'))


def test_state_and_real_evidence_not_invented():
    registry = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/05_可领取任务包.csv'
    with registry.open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'S-01')
    value = current()
    assert row['status'] == value['status'] == 'WAIT_DEP'
    assert set(row['depends_on'].split('|')) == set(value['depends_on'])
    assert value['claimant'] is None
    assert not value['clock_mapping_implemented'] and not value['measured_sqi_implemented']
    assert not value['real_dual_device_verified']
    assert value['quality_thresholds'] is None and value['clock_error_acceptance_ns'] is None


def test_quality_and_clock_fields_align_with_authority():
    value = current()
    assert set(value['quality_states']) == v21.FALLBACK_STATES
    assert set(value['device_states']) == v21.DEVICE_STATES
    assert set(value['clock_fields']) <= set(v22.KNOWN_FIELDS['telemetry_frame'])
    assert set(value['time_fields']) <= set(v22.KNOWN_FIELDS['telemetry_frame'])
    assert not value['connection_implies_good_quality']
    assert not value['unknown_clock_may_be_zero_filled']
    assert not value['controls_session_clock_or_order']
    assert not value['degraded_visibility_cap_is_sqi_threshold']


@pytest.mark.parametrize('state', ['GOOD', 'DEGRADED', 'UNUSABLE', 'DISCONNECTED'])
def test_all_four_states_are_legal_protocol_inputs(state):
    frame = fixture()
    frame['fallback_state'] = state
    frame['fallback_reason'] = None if state == 'GOOD' else 'SYNTHETIC_QUALITY_REASON'
    assert v22.validate_and_filter('telemetry_frame', frame)['fallback_state'] == state


@pytest.mark.parametrize('unknown', [None, float('nan'), float('inf')])
def test_unknown_clock_does_not_form_valid_telemetry(unknown):
    frame = fixture()
    frame['sync_uncertainty_ns'] = unknown
    with pytest.raises(v22.ContractValidationError):
        v22.validate_and_filter('telemetry_frame', frame)


def test_non_good_quality_requires_reason():
    frame = fixture()
    frame['fallback_state'] = 'UNUSABLE'
    with pytest.raises(v22.ContractValidationError, match='MISSING_FALLBACK_REASON'):
        v22.validate_and_filter('telemetry_frame', frame)
