"""Synthetic packets test the frontend, not physical BigRun performance."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest

PANEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PANEL))
from bigrun_preview import BigRunPreview
from device_preview import raster_waveform


def packet(seq=1, kind='ecg', samples=None, **kwargs):
    return dict(message_type='bigrun_preview', version='1.0', device='BigRun Team',
                source_mode='real', evidence_scope='DEVELOPMENT_UNVERIFIED', formal_capable=False,
                stream_id='SYNTHETIC-CANDIDATE', packet_seq=seq, received_monotonic_ns=seq*100_000_000,
                sent_monotonic_ns=seq*100_000_000+1000, kind=kind,
                samples=[100, -400, 500] if samples is None else samples, **kwargs)


def ingest(model, p, now=1_000_000_000):
    return model.ingest(json.dumps(p), now)


def connected(model, seq=1, now=1_000_000_000, **kw):
    assert ingest(model, packet(seq, 'status', [], connected=True, **kw), now)


def test_only_bigrun_real_candidate_messages_and_monotonic_batches():
    model = BigRunPreview()
    for changes in ({'source_mode':'dev_mock'}, {'message_type':'device_preview'},
                    {'formal_capable':True}, {'device':'Polar H10'}, {'evidence_scope':'FORMAL'}):
        assert not ingest(model, {**packet(), **changes})
    connected(model)
    assert ingest(model, packet(2, sample_rate_hz_nominal=100))
    assert not ingest(model, packet(2))
    assert len(model.data['ecg']) == 3
    assert model.fields(1_000_000_000)['heart_rate'] == '—'
    assert model.fields(1_000_000_000)['gate'] == '实验桥未接入'
    assert model.rejected == 6


def test_two_xyz_samples_raw_rr_units_and_no_gyro():
    model = BigRunPreview()
    connected(model)
    assert ingest(model, packet(2, 'acc', [[1, 2, 3], [-4, -5, -6]], sample_rate_hz_nominal=None))
    assert [v for _, v in model.data['z']] == [3, -6]
    assert ingest(model, packet(3, 'rr', [918, 919]))
    assert model.fields(1_000_000_000)['rr_interval'] == '919'
    from bigrun_preview import VIEWS, UNITS
    assert 'angular_velocity' not in VIEWS['resp']
    assert UNITS['ecg'] == 'ADC' and UNITS['rr'] == '原始整数'
    assert model.series('acceleration', 1_000_000_000)[2]['unit'] == '原始整数'
    assert 'resp' not in model.data


def test_calibration_profile_is_not_validation_and_warmup_not_measurement():
    model = BigRunPreview()
    connected(model, resp_profile_loaded=True, resp_warmed_up=False, heart_profile_loaded=True)
    assert model.fields(1_000_000_000)['resp_state'] == '预热中'
    assert model.fields(1_000_000_000)['heart_calibration'] == '已加载待验'
    for seq, warm in ((2, False), (3, True)):
        assert ingest(model, packet(seq, 'acc', [[1, 2, 3], [2, 3, 4]],
                                   respiration_proxy=[.3, .6], resp_warmed_up=warm))
    assert [v for _, v in model.data['resp']] == [.3, .6]
    connected(model, seq=4, resp_profile_loaded=True, resp_warmed_up=True)
    fields = model.fields(1_000_000_000)
    assert fields['resp_state'] == '代理待验'
    assert fields['actual_step_id'] == '未识别'
    assert not model.action_allowed('submit') and not model.action_allowed('start')


def test_disconnect_timeout_reconnect_and_loss_never_keep_live_values():
    model = BigRunPreview()
    connected(model)
    assert ingest(model, packet(2, 'hr', [75]))
    assert model.fields(1_000_000_000)['heart_rate'] == '75.0'
    assert model.fields(4_000_000_000)['heart_rate'] == '—'
    assert ingest(model, packet(4, 'ecg', [5, 6]))
    assert model.lost == 1 and any(v is None for _, v in model.data['hr'])
    assert ingest(model, packet(5, 'status', [], connected=False))
    assert model.fields(1_000_000_000)['heart_rate'] == '—'
    assert ingest(model, {**packet(1, 'status', [], connected=True), 'stream_id':'NEW-SYNTHETIC'})
    assert not model.data and model.fields(1_000_000_000)['rr_interval'] == '—'


@pytest.mark.parametrize('bad', [float('nan'), '7', True])
def test_bad_numeric_packets_do_not_mutate_frontend(bad):
    model = BigRunPreview()
    assert not ingest(model, packet(samples=[bad]))
    assert not model.data


def test_all_five_wave_views_render_pixels_without_physical_unit_invention():
    model = BigRunPreview()
    connected(model)
    seq = 2
    for kind, samples in [('ecg', [0, 1000, -1000, 500]), ('rr', [920, 850, 950]),
                           ('hr', [65, 80, 70]), ('acc', [[0, 2, 5], [5, 1, -1], [2, 3, 0]])]:
        extra = {'respiration_proxy':[.1, .8, -.5], 'resp_warmed_up':True} if kind == 'acc' else {}
        assert ingest(model, packet(seq, kind, samples, sample_rate_hz_nominal=1, **extra))
        seq += 1
    for key in ('ecg', 'rr', 'hr', 'acceleration', 'resp'):
        for s in model.series(key, 1_000_000_000):
            image = raster_waveform(s, 400, 100)
            assert image.shape == (100, 400, 4)
            assert (np.abs(image[:, :, :3] - np.array(s['color'])).max(axis=2) < .01).any()


def test_nominal_timing_and_host_clock_are_explicit():
    model = BigRunPreview()
    connected(model, ecg_hz_nominal=125)
    assert '名义' in model.fields(1_000_000_000)['ecg_rate']
    assert ingest(model, packet(2, samples=[1, 2], sample_rate_hz_nominal=125))
    points = list(model.data['ecg'])
    assert points[-1][0] - points[-2][0] == 8_000_000
    assert model.fields(1_000_000_000)['ecg_sqi'] == '未验证'
