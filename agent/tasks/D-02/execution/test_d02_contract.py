import csv
from dataclasses import fields
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/D-02'
sys.path.insert(0, str(ROOT / 'agent/modules'))
from srp_session_store.models import RawPacket
from srp_session_store.archive import SessionArchive
from srp_session_store.errors import StoreError


def current():
    return json.loads((TASK / 'outputs/current-acquisition.json').read_text(encoding='utf-8'))


def test_state_and_real_deliveries_remain_open():
    registry = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/05_可领取任务包.csv'
    with registry.open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'D-02')
    value = current()
    assert value['status'] == row['status'] == 'WAIT_DEP_EXTERNAL'
    assert value['claimant'] is None
    assert not value['formal_driver_implemented'] and not value['real_hardware_verified']
    assert value['required_continuous_capture_seconds'] == 1800
    assert value['continuous_capture_evidence_seconds'] is None


def test_specification_does_not_invent_wire_protocol():
    value = current()
    assert value['nominal_sample_rate_hz'] == 400
    assert [(c['count'], c['resolution_bits']) for c in value['channels']] == [(1, 28), (3, 16), (3, 16)]
    assert not value['wire_layout_verified'] and not value['vendor_sdk_received']
    assert not value['windows_sdk_compatibility_verified']
    assert not value['formal_mock_fallback_allowed'] and not value['edr_primary_substitution_allowed']
    assert not value['decoded_sdk_values_are_wire_bytes']
    assert set(value['raw_packet_fields']) == {field.name for field in fields(RawPacket)}


@pytest.mark.parametrize('missing', [False, True])
def test_p02_consumer_accepts_present_and_missing_notification(missing):
    value = current()
    packet = RawPacket(value['raw_source_id'], 'real', 0, None, 1000, 'plux-epoch-1',
                       0 if missing else 40, None if missing else b'synthetic-notification',
                       'PACKET_MISSING' if missing else None)
    SessionArchive._validate_raw_packet(packet)


def test_p02_rejects_time_reason_as_missing_payload():
    packet = RawPacket('plux_respiban', 'real', 0, None, 1000, 'plux-epoch-1',
                       40, b'synthetic-notification', 'DEVICE_TIME_UNAVAILABLE')
    with pytest.raises(StoreError, match='RAW_PACKET_INVALID'):
        SessionArchive._validate_raw_packet(packet)
