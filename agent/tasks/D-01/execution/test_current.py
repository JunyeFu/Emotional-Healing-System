import csv
from dataclasses import fields
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/D-01'
sys.path.insert(0, str(ROOT / '02-技术研发'))
from srp_session_store.models import RawPacket
from srp_session_store.archive import SessionArchive
from srp_session_store.errors import StoreError
import pytest


def current():
    return json.loads((TASK / 'outputs/current-acquisition.json').read_text(encoding='utf-8'))


def test_state_and_owner_not_invented():
    registry = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/05_可领取任务包.csv'
    with registry.open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'D-01')
    contract = current()
    assert contract['status'] == row['status'] == 'WAIT_DEP_EXTERNAL'
    assert not contract['formal_driver_implemented'] and not contract['real_hardware_verified']
    assert contract['claimant'] is None and contract['continuous_capture_evidence_seconds'] is None


def test_channels_and_raw_storage():
    contract = current()
    assert contract['ecg']['data_uuid'].startswith('fb005c82-')
    assert contract['ecg']['service_uuid'] != contract['ecg']['data_uuid']
    assert contract['ecg']['type_0_sample_bytes'] == 3
    assert contract['ecg']['nominal_sample_rate_hz'] == 130
    assert not contract['heart_rate_rr']['raw_ecg']
    assert not contract['formal_mock_fallback_allowed']
    assert contract['primary_respiration_source'] == 'D-02_REAL_RESPIRATION_BELT_NOT_EDR'
    assert set(contract['raw_packet_fields']) == {field.name for field in fields(RawPacket)}


def test_archive_and_hardware_obligations():
    for name in ('ble_device.py', '设备方案.md', '真实设备方案.md'):
        assert (TASK / 'archive' / name).is_file()
        assert not (ROOT / '02-技术研发/01-数据采集' / name).exists()
    contract = current()
    assert contract['required_continuous_capture_seconds'] == 1800
    assert not contract['device_time_is_host_time']
    assert 'null' in contract['unknown_time_policy']


@pytest.mark.parametrize('source_id', ['polar_h10_ecg', 'polar_h10_rr'])
def test_real_packet_with_unknown_device_time_is_storable(source_id):
    packet = RawPacket(source_id, 'real', 0, None, 1000, 'device-epoch-1', 1, b'raw-notification')
    SessionArchive._validate_raw_packet(packet)
    assert source_id in current()['raw_source_ids']


def test_device_time_unknown_not_a_missing_payload_reason():
    packet = RawPacket('polar_h10_rr', 'real', 0, None, 1000, 'host-clock', 1,
                       b'raw-notification', 'DEVICE_TIME_UNAVAILABLE')
    with pytest.raises(StoreError, match='RAW_PACKET_INVALID'):
        SessionArchive._validate_raw_packet(packet)
