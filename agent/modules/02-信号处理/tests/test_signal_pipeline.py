"""Behavior tests for the native-rate signal pipeline."""

import importlib
import math
import os
import sys

import numpy as np


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sp = importlib.import_module("02-信号处理.signal_pipeline")


def native_ecg_batch(frame_index: int, hr_bpm: float = 60.0):
    """Return one 10 Hz coordination interval containing 13 native samples."""
    rate_hz = 130.0
    period = 60.0 / hr_bpm
    start = frame_index * 0.1
    batch = []
    for sample_index in range(13):
        timestamp = start + sample_index / rate_hz
        phase = timestamp % period
        distance = min(phase, period - phase)
        value = math.exp(-((distance / 0.018) ** 2))
        batch.append((timestamp, value))
    return batch


class TestSignalPipeline:
    def test_missing_native_ecg_never_uses_default_hrv(self):
        pipeline = sp.SignalPipeline(buffer_size=300)
        for i in range(120):
            t = i * 0.1
            result = pipeline.feed(
                t,
                math.sin(2 * math.pi * 0.2 * t),
                0.0,
                eda=8.0,
                acc_mag=0.0,
                temp_skin=34.0,
            )
        assert result is None
        assert pipeline.last_status == "invalid"
        assert "ecg_native_missing" in pipeline.last_invalid_reasons
        assert pipeline._last_hr is None
        assert pipeline._last_rmssd is None

    def test_native_ecg_and_periodic_respiration_produce_valid_frame(self):
        pipeline = sp.SignalPipeline(buffer_size=300)
        result = None
        for i in range(140):
            t = i * 0.1
            batch = native_ecg_batch(i)
            result = pipeline.feed(
                t,
                math.sin(2 * math.pi * 0.2 * t),
                batch[-1][1],
                eda=8.0,
                acc_mag=0.0,
                temp_skin=34.0,
                ecg_samples=batch,
            )
        assert result is not None
        assert pipeline.last_status == "valid"
        assert 59.0 <= result.hr <= 61.0
        assert result.rmssd <= 1.0

    def test_hrv_uses_native_timestamps(self):
        pipeline = sp.SignalPipeline()
        beat_times = (0.5, 1.5, 2.4, 3.5)
        timestamps = np.arange(0.0, 4.0, 1 / 130.0)
        values = [
            max(math.exp(-(((timestamp - beat) / 0.012) ** 2)) for beat in beat_times)
            for timestamp in timestamps
        ]
        result = pipeline._extract_hrv(tuple(zip(timestamps, values)))
        assert result is not None
        hr, rmssd = result
        assert 59.0 <= hr <= 61.0
        assert 150.0 <= rmssd <= 165.0

    def test_non_monotonic_native_timestamps_fail_closed(self):
        pipeline = sp.SignalPipeline()
        samples = tuple((i / 130.0, float(i % 2)) for i in range(390))
        malformed = samples[:200] + ((0.5, 1.0),) + samples[201:]
        assert pipeline._extract_hrv(malformed) is None
