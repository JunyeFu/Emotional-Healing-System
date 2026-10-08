import json
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE.parents[3] / 'agent/tasks/T-01/execution'))
from device_preview import DevicePreview, raster_waveform
from simulate_device_preview import batch


def packet(seq=1, stamp=1_000_000_000):
    return batch('plux_respiban', seq, stamp, 'demo')


def test_batches_preserve_all_samples_and_only_matching_session_visible():
    p = DevicePreview()
    assert p.ingest(json.dumps(packet()), 1_000_000_000)
    stream = p.snapshot(1_000_000_000, 'demo')['resp']
    assert len(stream['points']) == 40
    assert [v for _, v in stream['points']] == packet()['samples']
    assert p.snapshot(1_000_000_000, 'other')['resp']['points'] == ()


@pytest.mark.parametrize('key,value', [('sample_rate_hz', 0), ('unit', 'mL'), ('samples', [float('nan')]),
    ('samples', []), ('samples', [True]), ('preview_version', '2'), ('source_mode', 'mock'),
    ('hr_bpm', -1), ('packet_seq', True), ('motion_state', 'invented')])
def test_bad_external_batches_rejected(key, value):
    p = DevicePreview()
    data = packet()
    data[key] = value
    assert not p.ingest(json.dumps(data), 1_000_000_000)
    assert p.accepted == 0 and p.rejected == 1


def test_duplicate_reorder_overlap_and_future_rejected_without_buffer_change():
    p = DevicePreview()
    assert p.ingest(json.dumps(packet()), 1_000_000_000)
    assert not p.ingest(json.dumps(packet()), 1_000_000_000)
    assert not p.ingest(json.dumps(packet(2)), 1_000_000_000)
    future = packet(2, 2_000_000_000)
    future['sent_monotonic_ns'] = 1_000_000_000
    assert not p.ingest(json.dumps(future), 1_000_000_000)
    assert len(p.snapshot(1_000_000_000, 'demo')['resp']['points']) == 40


def test_new_epoch_resets_buffer_missing_preserved_and_timeout_freezes():
    p = DevicePreview()
    data = packet()
    data['samples'][10] = None
    assert p.ingest(json.dumps(data), 1_000_000_000)
    assert p.snapshot(3_000_000_000, 'demo')['resp']['state'] == 'STALE'
    assert p.snapshot(3_000_000_000, 'demo')['resp']['end_ns'] == 1_000_000_000
    data['session_id'] = 'new'
    assert p.ingest(json.dumps(data), 1_000_000_000)
    assert len(p.snapshot(1_000_000_000, 'new')['resp']['points']) == 40
    assert p.snapshot(1_000_000_000, 'new')['resp']['points'][10][1] is None


def test_source_and_receiver_clock_origins_are_not_assumed_equal():
    p = DevicePreview()
    assert p.ingest(json.dumps(packet()), 100_000_000)
    stream = p.snapshot(120_000_000, 'demo')['resp']
    assert stream['age_ms'] == 25
    assert stream['end_ns'] == 1_025_000_000


def test_800_seconds_buffer_bounded():
    p = DevicePreview()
    for seq in range(1, 8001):
        stamp = seq * 100_000_000
        assert p.ingest(json.dumps(packet(seq, stamp)), stamp)
    assert 12000 <= len(p.streams['plux_respiban']['points']) <= 12001


def test_plot_has_wave_pixels_and_missing_batch_is_only_grid():
    np = pytest.importorskip('numpy')
    p = DevicePreview()
    assert p.ingest(json.dumps(packet()), 1_000_000_000)
    stream = p.snapshot(1_000_000_000, 'demo')['resp']
    image = raster_waveform(stream, 640, 160)
    assert np.any(image[:, :, 0] < .2)
    stream['points'] = tuple((stamp, None) for stamp, _ in stream['points'])
    assert not np.any(raster_waveform(stream, 640, 160)[:, :, 0] < .2)
