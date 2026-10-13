"""Tests for FrameClock — 10 Hz frame assembler."""

import time
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
from ring_buffer import RingBuffer
from frame_clock import FrameClock, RawFrame


def test_frame_clock_output():
    """Frame clock produces RawFrames at ~10 Hz from ring buffers."""
    ecg = RingBuffer(2000)
    resp = RingBuffer(500)
    eda = RingBuffer(200)

    # Pre-fill buffers with sample data
    for i in range(20):
        ecg.push(time.time(), float(i) * 0.1)
        resp.push(time.time(), float(i) * 0.05)
        eda.push(time.time(), 5.0 + float(i) * 0.01)

    clock = FrameClock(
        ecg_buf=ecg, resp_buf=resp, eda_buf=eda, rate_hz=10.0
    )
    clock.ecg_connected = True
    clock.resp_connected = True
    clock.eda_connected = True

    clock.start()
    time.sleep(0.5)  # collect ~5 frames
    clock.stop()
    clock.join(timeout=1.0)

    frames = []
    while not clock.output_queue.empty():
        frames.append(clock.output_queue.get_nowait())

    assert len(frames) >= 3, f"Expected >=3 frames, got {len(frames)}"
    print(f"Collected {len(frames)} frames in 0.5s (~{len(frames)*2:.0f} Hz effective)")

    # Each frame should be a RawFrame with expected fields
    for f in frames:
        assert isinstance(f, RawFrame)
        assert f.timestamp > 0
        assert isinstance(f.respiration_raw, float)
        if f.ecg_samples:
            assert f.ecg_raw == f.ecg_samples[-1][1]
        assert isinstance(f.eda_raw, float)


def test_missing_device():
    """Missing channels are explicit and never neutral-looking values."""
    clock = FrameClock(rate_hz=10.0)
    clock.start()
    time.sleep(0.3)
    clock.stop()
    clock.join(timeout=1.0)

    frame = clock.output_queue.get_nowait()
    assert frame.ecg_raw is None
    assert frame.ecg_samples == ()
    assert frame.respiration_raw is None
    assert frame.eda_raw is None
    assert frame.temp_skin is None
    assert not any(frame.signal_validity.values())


def test_native_ecg_batch_is_preserved():
    """A coordination frame preserves native ECG values and timestamps."""
    ecg = RingBuffer(2000)
    for i in range(13):
        ecg.push(time.time(), float(i + 1))  # 1..13

    clock = FrameClock(ecg_buf=ecg, rate_hz=10.0)
    clock.ecg_connected = True
    frame = clock._assemble(time.time())
    assert frame.ecg_raw == 13.0
    assert [value for _, value in frame.ecg_samples] == list(map(float, range(1, 14)))
    assert frame.signal_validity["ecg"] is True

    # A second tick without new samples must be missing, not a repeated value.
    second = clock._assemble(time.time())
    assert second.ecg_raw is None
    assert second.ecg_samples == ()


if __name__ == "__main__":
    test_frame_clock_output()
    test_missing_device()
    test_native_ecg_batch_is_preserved()
    print("All FrameClock tests passed.")
