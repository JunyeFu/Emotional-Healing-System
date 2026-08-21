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
