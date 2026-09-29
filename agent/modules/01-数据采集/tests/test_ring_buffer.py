"""Tests for RingBuffer — thread-safe sensor sample buffer."""

import threading
import time
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
from ring_buffer import RingBuffer


def test_push_and_read():
    buf = RingBuffer(10)
    assert buf.is_empty
    assert buf.read_latest() is None

    buf.push(1.0, 3.14)
    buf.push(2.0, 2.71)
    assert len(buf) == 2
    assert buf.read_latest() == 2.71


def test_capacity():
    buf = RingBuffer(3)
    for i in range(5):
        buf.push(i * 0.1, float(i))
    assert len(buf) == 3  # wraps around
    assert buf.read_latest() == 4.0


def test_read_window():
    buf = RingBuffer(10)
    for i in range(5):
        buf.push(i * 0.1, float(i))
    window = buf.read_window(3)
    assert window == [2.0, 3.0, 4.0]


def test_read_window_larger_than_buffer():
    buf = RingBuffer(10)
    buf.push(0.0, 1.0)
    buf.push(0.1, 2.0)
    window = buf.read_window(10)
    assert window == [1.0, 2.0]


def test_read_latest_ts():
    buf = RingBuffer(10)
    assert buf.read_latest_ts() is None

    buf.push(1.5, 42.0)
    assert buf.read_latest_ts() == (1.5, 42.0)


def test_read_after_preserves_native_timestamps():
    buf = RingBuffer(10)
    buf.push(1.0, 10.0)
    buf.push(1.1, 11.0)
    buf.push(1.2, 12.0)
    assert buf.read_after(1.0) == [(1.1, 11.0), (1.2, 12.0)]


def test_clear():
    buf = RingBuffer(10)
    buf.push(1.0, 1.0)
    buf.push(2.0, 2.0)
    buf.clear()
    assert buf.is_empty
    assert len(buf) == 0


def test_thread_safety():
    buf = RingBuffer(1000)
    errors = []

    def writer():
        try:
            for i in range(500):
                buf.push(time.time(), float(i))
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for _ in range(500):
                _ = buf.read_latest()
                _ = buf.read_window(10)
                _ = len(buf)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=writer),
        threading.Thread(target=reader),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Thread safety errors: {errors}"


if __name__ == "__main__":
    test_push_and_read()
    test_capacity()
    test_read_window()
    test_read_window_larger_than_buffer()
    test_read_latest_ts()
    test_clear()
    test_thread_safety()
    print("All RingBuffer tests passed.")
