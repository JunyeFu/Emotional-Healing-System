"""DeviceManager lifecycle tests."""

import asyncio
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from device_driver import DeviceDriver
from device_manager import DeviceManager
from ring_buffer import RingBuffer


class DelayedDriver(DeviceDriver):
    def __init__(self, stop_delay: float = 0.05):
        self.stop_delay = stop_delay
        self.stopped = False
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def start_streaming(self) -> None:
        return None

    async def stop(self) -> None:
        await asyncio.sleep(self.stop_delay)
        self.stopped = True
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def device_name(self) -> str:
        return "delayed-test-driver"


def test_stop_waits_for_driver_and_closes_threads():
    driver = DelayedDriver()
    manager = DeviceManager(rate_hz=20.0)
    manager.register("ecg", driver, RingBuffer(100))
    assert manager.start()

    manager.stop()

    assert driver.stopped is True
    assert manager.is_running is False
    assert manager._thread is not None and not manager._thread.is_alive()
    assert manager.frame_clock is not None and not manager.frame_clock.is_alive()


def test_connection_does_not_claim_measured_signal_quality():
    manager = DeviceManager()

    class InspectingDriver(DelayedDriver):
        async def start_streaming(self):
            assert manager._connected['resp'] is False
            assert manager.signal_quality['resp'] != 'good'

    driver = InspectingDriver()
    manager.register('resp', driver, RingBuffer(100))
    assert asyncio.run(manager._connect_device('resp', driver))
    assert manager._connected['resp'] is True
    assert manager.signal_quality['resp'] == 'unknown'


def test_stream_start_failure_never_claims_connection(monkeypatch):
    import device_manager
    monkeypatch.setattr(device_manager, 'RECONNECT_BACKOFF', [0])

    class FailingStreamDriver(DelayedDriver):
        async def start_streaming(self):
            raise RuntimeError('synthetic stream start failure')

    manager = DeviceManager()
    manager.register('resp', FailingStreamDriver(), RingBuffer(100))
    assert asyncio.run(manager._connect_device('resp', manager._drivers['resp'])) is False
    assert manager._connected['resp'] is False
    assert manager.signal_quality['resp'] == 'no_signal'
