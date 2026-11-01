"""BigRun candidate tests. Synthetic packets are not hardware evidence."""
import asyncio
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from bigrun.protocol import decode_packet


def test_acc_retains_both_signed_xyz_samples():
    packet = bytes.fromhex("0f12061400eb0106ff8b00ee0108ff8ef8260127")
    decoded = decode_packet(packet)
    assert decoded.kind == "acc"
    assert decoded.samples == ((235, 262, -117), (238, 264, -114))


def test_ecg_preserves_adc_counts_and_header_without_claiming_units():
    packet = bytes.fromhex("4160271127132710270726fd26f926fb2702270c")
    decoded = decode_packet(packet)
    assert decoded.samples == (10001, 10003, 10000, 9991, 9981, 9977, 9979, 9986, 9996)
    assert decoded.metadata == {"id": 6, "uid": 0, "units": "adc_counts_unverified"}


def test_rr_and_unknown_notifications_are_not_silently_discarded():
    decoded = decode_packet(bytes.fromhex("1407b3020350035c000000000000000000000000"))
    assert decoded.samples == (848, 860)
    assert decoded.metadata["device_seq"] == 179
    assert decode_packet(b"unexpected").kind == "unparsed"
    malformed = decode_packet(bytes([0x14, 7, 0, 255]) + bytes(16))
    assert malformed.kind == "unparsed"
    assert malformed.metadata["reason"] == "RRI_COUNT_EXCEEDS_PACKET"


def test_project_store_roundtrip_preserves_rr_acc_and_unknown(tmp_path):
    from bigrun.recording import CandidateRecording, open_recording
    raw = [bytes.fromhex("1407b3020350035c000000000000000000000000"),
           bytes.fromhex("0f12061400eb0106ff8b00ee0108ff8ef8260127"), b"unknown"]
    recording = CandidateRecording(tmp_path, "TEST-BIGRUN", "replay", {})
    for i, packet in enumerate(raw):
        recording.record(packet, 1_000_000_000 + i * 100_000_000)
    path = recording.path
    recording.close("COMPLETED")
    reader = open_recording(path)
    assert reader.verify().valid
    packets = list(reader.iter_l0())
    assert [p.payload for p in packets] == raw[:2]
    assert [p.sample_count for p in packets] == [2, 2]
    assert all(p.device_time_ns is None for p in packets)
    unknown = list(reader.iter_l1(record_type="bigrun_notification"))
    assert unknown[0]["payload"]["raw_hex"] == raw[2].hex()
    assert reader.envelope["formal_capable"] is False


def test_driver_reads_back_mode_and_drains_native_project_frames():
    from bigrun.driver import BigRunDriver

    class Recorder:
        def record(self, raw, received_ns):
            return decode_packet(raw)

    class Client:
        def __init__(self, *args, **kwargs):
            self.is_connected = False
            self.params = {0x60: 0, 0x62: 0, 0x61: 0}
        async def connect(self): self.is_connected = True
        async def disconnect(self): self.is_connected = False
        async def start_notify(self, uuid, callback): self.callback = callback
        async def stop_notify(self, uuid): pass
        async def write_gatt_char(self, uuid, data, **kwargs):
            if data[1] == 0x0F and data[2] in self.params:
                if data[3] == 1:
                    self.params[data[2]] = data[4]
                else:
                    self.callback(None, bytes([0x0F, data[2], 0, self.params[data[2]]]) + bytes(16))

    async def run():
        driver = BigRunDriver("synthetic-address", Recorder(), mode="ecg",
                              ecg_hz=125, acc_hz=25, client_factory=Client)
        assert await driver.connect()
        await driver.start_streaming()
        assert driver.mode_readback_verified
        driver._notification(None, bytes.fromhex("4160271127132710270726fd26f926fb2702270c"))
        driver._notification(None, bytes.fromhex("0f12061400eb0106ff8b00ee0108ff8ef8260127"))
        frame = driver.drain_frame()
        assert len(frame.ecg_samples) == 9
        assert frame.signal_validity["resp"] is False
        assert frame.breath_phase == "unknown"
        assert driver.drain_frame().ecg_samples == ()
        await driver.stop()
        assert not driver.is_connected
    asyncio.run(run())


def test_resp_fit_and_independent_validation_use_frozen_causal_coefficients():
    from scipy.signal import butter, sosfilt
    from bigrun.calibration import fit_respiration, validate_respiration, RespirationProxy
    fs = 25
    t = np.arange(150 * fs) / fs
    x = np.column_stack([100 + np.sin(2 * np.pi * .1 * t),
                         np.full(len(t), 300), np.full(len(t), -50)])
    ref = sosfilt(butter(2, [.04, .8], btype="bandpass", fs=fs, output="sos"), x[:, 0] - 100)
    profile = fit_respiration(t, x, t, ref, fs, [.04, .8], 0)
    assert profile["evidence_scope"] == "DEVELOPMENT_UNVERIFIED"
    assert profile["event_recognition"] == "NOT_IMPLEMENTED"
    metrics = validate_respiration(profile, t, x, t, ref)
    assert metrics["waveform_correlation"] > .99
    # Splitting notifications cannot change the causal filter output.
    full = RespirationProxy(profile).feed(x)
    stream = RespirationProxy(profile)
    chunks = np.concatenate([stream.feed(chunk) for chunk in np.array_split(x, 17)])
    assert np.allclose(full, chunks)
    frozen = json.dumps(profile, sort_keys=True)
    bad = validate_respiration(profile, t, x, t, np.cos(2 * np.pi * .1 * t))
    assert bad["normalized_rmse"] > .5
    assert json.dumps(profile, sort_keys=True) == frozen


def test_flat_acc_cannot_be_calibrated_into_a_success():
    from bigrun.calibration import fit_respiration
    t = np.arange(4000) / 25
    with pytest.raises(ValueError, match="NO_ACC_VARIATION"):
        fit_respiration(t, np.ones((len(t), 3)), t, np.sin(t), 25, [.04, .8], 0)


def test_heart_metrics_report_missing_beats_instead_of_filling_them():
    from bigrun.calibration import heart_metrics
    result = heart_metrics(np.array([1., 2., 4., 5.]), np.arange(1., 6.), .1)
    assert result["matched_beats"] == 4
    assert result["missed_reference_beats"] == 1
    assert result["rr_mae_ms_on_consecutive_matches"] == 0


def test_failed_mode_readback_does_not_become_success():
    from bigrun.driver import BigRunDriver

    class Recorder:
        def record(self, raw, received_ns): return decode_packet(raw)

    class Client:
        def __init__(self, *args, **kwargs): self.is_connected = False
        async def connect(self): self.is_connected = True
        async def disconnect(self): self.is_connected = False
        async def start_notify(self, uuid, callback): self.callback = callback
        async def stop_notify(self, uuid): pass
        async def write_gatt_char(self, uuid, data, **kwargs):
            if data[1] == 15 and data[2] in (0x60, 0x61, 0x62) and data[3] == 0:
                self.callback(None, bytes([15, data[2], 0, 0]) + bytes(16))

    async def run():
        driver = BigRunDriver("fake", Recorder(), mode="ecg", client_factory=Client)
        await driver.connect()
        with pytest.raises(RuntimeError, match="MODE_READBACK_MISMATCH"):
            await driver.start_streaming()
        assert not driver.mode_readback_verified
        await driver.stop()
        assert not driver.is_connected
    asyncio.run(run())


def test_recording_failure_and_disconnect_reach_the_owner():
    from bigrun.driver import BigRunDriver

    class Recorder:
        def record(self, raw, received_ns): raise OSError("synthetic disk failure")

    class Client:
        def __init__(self, *args, **kwargs): self.is_connected = True
        async def connect(self): pass
        async def disconnect(self): self.is_connected = False

    async def run():
        driver = BigRunDriver("fake", Recorder(), client_factory=Client)
        await driver.connect()
        driver._notification(None, bytes(20))
        with pytest.raises(OSError, match="disk failure"):
            await driver.failure
        await driver.stop()
        driver = BigRunDriver("fake", Recorder(), client_factory=Client)
        await driver.connect()
        driver._notifying = True
        driver.client.is_connected = False
        driver._disconnected(driver.client)
        with pytest.raises(ConnectionError, match="DISCONNECTED"):
            await driver.failure
        assert driver.drain_frame().ecg_samples == ()
    asyncio.run(run())
