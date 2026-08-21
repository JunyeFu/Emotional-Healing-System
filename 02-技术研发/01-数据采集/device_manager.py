"""
SRP Device Manager — orchestrates multiple BLE biosignal devices.

Manages a single asyncio event loop running in a daemon thread for all
BLE devices, plus a FrameClock thread that assembles RawFrames at 10 Hz.

Usage:
    manager = DeviceManager()
    manager.register("ecg", PolarH10Driver(), RingBuffer(2000))
    manager.register("resp", RespirationBeltDriver(), RingBuffer(500))
    manager.register("eda", EDAWristbandDriver(), RingBuffer(200))
    manager.start()
    # Main loop: frame = manager.read_frame()
    manager.stop()
"""

import asyncio
import threading
import time
import logging
from typing import Optional

from ring_buffer import RingBuffer
from device_driver import DeviceDriver
from frame_clock import FrameClock, RawFrame

logger = logging.getLogger(__name__)

# Reconnection backoff schedule (seconds)
RECONNECT_BACKOFF = [1, 2, 4, 8, 15]


class DeviceManager:
    """Start/stop/monitor all BLE devices. Single asyncio loop for all."""

    def __init__(self, rate_hz: float = 10.0):
        self._drivers: dict[str, DeviceDriver] = {}
        self._buffers: dict[str, RingBuffer] = {}
        self._connected: dict[str, bool] = {}

        self.frame_clock: Optional[FrameClock] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._rate_hz = rate_hz
        self._started = False

        # Signal quality tracking
        self.signal_quality: dict[str, str] = {}

    # ── Registration ────────────────────────────────────────────────────────

    def register(self, name: str, driver: DeviceDriver, buffer: RingBuffer) -> None:
        """Register a device driver and its ring buffer."""
        self._drivers[name] = driver
        self._buffers[name] = buffer
        self._connected[name] = False
        self.signal_quality[name] = "no_signal"
        logger.info(f"Registered device: {name} ({driver.device_name})")

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start BLE event loop in daemon thread, connect all devices."""
        if self._started:
            logger.warning("DeviceManager already started")
            return False

        # Create frame clock with registered buffers
        self.frame_clock = FrameClock(
            ecg_buf=self._buffers.get("ecg"),
            resp_buf=self._buffers.get("resp"),
            eda_buf=self._buffers.get("eda"),
            acc_buf=self._buffers.get("acc"),
            temp_buf=self._buffers.get("temp"),
            rate_hz=self._rate_hz,
        )

        # Start BLE event loop in daemon thread
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="BLE-Loop"
        )
        self._thread.start()

        # Wait for connections to establish (with generous timeout)
        timeout = 15.0
        start = time.time()
        while time.time() - start < timeout:
            if any(self._connected.values()):
                break
            time.sleep(0.2)

        connected_count = sum(1 for v in self._connected.values() if v)
        if connected_count == 0:
            logger.warning("No devices connected within timeout, starting frame clock anyway")

        # Update frame clock connection flags
        self.frame_clock.ecg_connected = self._connected.get("ecg", False)
        self.frame_clock.resp_connected = self._connected.get("resp", False)
        self.frame_clock.eda_connected = self._connected.get("eda", False)
        self.frame_clock.acc_connected = self._connected.get("acc", False)
        self.frame_clock.temp_connected = self._connected.get("temp", False)

        # Start frame clock
        self.frame_clock.start()
        self._started = True

        logger.info(
            f"DeviceManager started: {connected_count}/{len(self._drivers)} devices, "
            f"frame clock @ {self._rate_hz} Hz"
        )
        return True

    def stop(self) -> None:
        """Stop frame clock, disconnect all devices, stop event loop."""
        if not self._started:
            return

        logger.info("DeviceManager stopping...")

        if self.frame_clock:
            self.frame_clock.stop()
            if self.frame_clock.is_alive():
                self.frame_clock.join(timeout=2.0)

        stop_error: Optional[BaseException] = None
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._stop_all(), self._loop)
            try:
                future.result(timeout=5.0)
            except BaseException as exc:
                future.cancel()
                stop_error = exc
                logger.error("Device shutdown did not complete cleanly: %s", exc)
            finally:
                self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self._started = False
        logger.info("DeviceManager stopped")
        if stop_error is not None:
            raise RuntimeError("DEVICE_SHUTDOWN_FAILED") from stop_error

    # ── Frame Access ────────────────────────────────────────────────────────

    def read_frame(self, timeout: float = 1.0) -> Optional[RawFrame]:
        """Read next assembled RawFrame (blocking, with timeout).

        Returns None if no frame available within timeout.
        """
        if not self.frame_clock:
            return None
        try:
            return self.frame_clock.output_queue.get(timeout=timeout)
        except Exception:
            return None

    @property
    def is_running(self) -> bool:
        return self._started

    @property
    def connected_devices(self) -> list[str]:
        return [name for name, ok in self._connected.items() if ok]

    @property
    def queue_backlog(self) -> int:
        if self.frame_clock:
            return self.frame_clock.queue_backlog
        return 0

    # ── Internal ────────────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        """Create event loop, connect all devices, run forever."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_all())
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"BLE event loop error: {e}")
        finally:
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            if pending:
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            self._loop.close()

    async def _stop_all(self) -> None:
        """Await every registered driver shutdown before the loop is stopped."""
        if not self._drivers:
            return
        results = await asyncio.gather(
            *(driver.stop() for driver in self._drivers.values()),
            return_exceptions=True,
        )
        failures = [result for result in results if isinstance(result, BaseException)]
        if failures:
            raise RuntimeError(
                "driver stop failures: " + ", ".join(str(item) for item in failures)
            )

    async def _connect_all(self) -> None:
        """Connect all registered devices concurrently."""
        tasks = []
        for name, driver in self._drivers.items():
            tasks.append(self._connect_device(name, driver))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for name, result in zip(self._drivers.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Device '{name}' connection failed: {result}")
                elif result:
                    logger.info(f"Device '{name}' connected successfully")

    async def _connect_device(self, name: str, driver: DeviceDriver) -> bool:
        """Connect a single device with retry backoff."""
        for attempt, delay in enumerate(RECONNECT_BACKOFF):
            try:
                ok = await driver.connect()
                if ok:
                    self._connected[name] = True
                    self.signal_quality[name] = "good"
                    await driver.start_streaming()
                    return True
            except Exception as e:
                logger.warning(
                    f"Device '{name}' connect attempt {attempt + 1} failed: {e}"
                )

            if attempt < len(RECONNECT_BACKOFF) - 1:
                logger.info(f"Retrying '{name}' in {delay}s...")
                await asyncio.sleep(delay)

        logger.error(f"Device '{name}': all {len(RECONNECT_BACKOFF)} connect attempts failed")
        self._connected[name] = False
        self.signal_quality[name] = "no_signal"
        return False
