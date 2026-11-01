"""One BLE connection -> P-02 raw evidence + candidate project RawFrames."""
import asyncio
from datetime import datetime
import sys
import time

from device_driver import DeviceDriver
from frame_clock import RawFrame
from ring_buffer import RingBuffer
from .protocol import MODES, NOTIFY_UUID, WRITE_UUID, command, date_command


class BigRunDriver(DeviceDriver):
    def __init__(self, address, recording, *, mode="observe", ecg_hz=None,
                 acc_hz=None, resp_profile=None, client_factory=None, packet_observer=None):
        if mode not in {"observe", *MODES}:
            raise ValueError("UNKNOWN_MODE")
        for rate in (ecg_hz, acc_hz):
            if rate is not None and (not 0 < rate <= 10000):
                raise ValueError("INVALID_NOMINAL_RATE")
        self.address, self.recording, self.mode = address, recording, mode
        self.ecg_hz, self.acc_hz = ecg_hz, acc_hz
        self.client_factory = client_factory
        self.packet_observer = packet_observer
        self.client = None
        self.failure = None
        self.config = {}
        self.mode_readback_verified = False
        self.connection_phase = "idle"
        self._data_received = False
        self._config_event = None
        self._notifying = False
        self._ecg_anchor = None
        self._acc_anchor = None
        self._ecg_index = self._acc_index = 0
        self._ecg_cursor = self._resp_cursor = float("-inf")
        self.ecg_buffer = RingBuffer(max(1, int((ecg_hz or 1) * 10)))
        self.resp_buffer = RingBuffer(max(1, int((acc_hz or 1) * 10)))
        self.hr_bpm = None
        self.hr_received_ns = None
        self.latest_acc = None
        self._acc_unread = False
        self.resp_estimator = None
        if resp_profile is not None:
            from .calibration import RespirationProxy
            if acc_hz != resp_profile["acc_hz"]:
                raise ValueError("PROFILE_ACC_RATE_MISMATCH")
            self.resp_estimator = RespirationProxy(resp_profile)

    @property
    def device_name(self):
        return "BigRun Team (DEVELOPMENT_UNVERIFIED)"

    @property
    def is_connected(self):
        return bool(self.client and self.client.is_connected)

    async def connect(self):
        factory = self.client_factory
        target = self.address
        options = {}
        self.failure = asyncio.get_running_loop().create_future()
        self._config_event = asyncio.Event()
        if factory is None:
            from bleak import BleakClient, BleakScanner
            self.connection_phase = "scan"
            target = await BleakScanner.find_device_by_address(self.address)
            if target is None:
                raise ConnectionError("BIGRUN_NOT_ADVERTISING")
            factory = BleakClient
            if sys.platform == "win32":
                options["winrt"] = {"use_cached_services": False}
        self.connection_phase = "connect_gatt"
        self.client = factory(target, disconnected_callback=self._disconnected, **options)
        await self.client.connect()
        self.connection_phase = "connected_gatt"
        return self.is_connected

    def _disconnected(self, client):
        if self._notifying and not self.failure.done():
            self.failure.set_exception(ConnectionError(
                f"BIGRUN_DISCONNECTED phase={self.connection_phase} NO_AUTO_RESUME"))

    def _notification(self, sender, data):
        if self.failure.done():
            return
        try:
            received_ns = time.monotonic_ns()
            packet = self.recording.record(bytes(data), received_ns)
            proxy = None
            if packet.kind == "config":
                # Mode en=1 acknowledges a write; only en=0 is a readback.
                if data[0] != 0x0F or data[2] == 0:
                    self.config.update(packet.metadata)
                    if all(k in self.config for k in ("ecg", "sr", "xo")):
                        self._config_event.set()
            elif packet.kind == "hr":
                self.hr_bpm = packet.samples[0]
                self.hr_received_ns = received_ns
            elif packet.kind == "ecg" and self.ecg_hz:
                if self._ecg_anchor is None:
                    self._ecg_anchor = received_ns / 1e9 - (len(packet.samples) - 1) / self.ecg_hz
                for value in packet.samples:
                    ts = self._ecg_anchor + self._ecg_index / self.ecg_hz
                    self.ecg_buffer.push(ts, value)
                    self._ecg_index += 1
            elif packet.kind == "acc":
                self.latest_acc = packet.samples[-1]
                self._acc_unread = True
                if self.acc_hz and self.resp_estimator:
                    if self._acc_anchor is None:
                        self._acc_anchor = received_ns / 1e9 - (len(packet.samples) - 1) / self.acc_hz
                    values = self.resp_estimator.feed(packet.samples)
                    proxy = values
                    for value in values:
                        ts = self._acc_anchor + self._acc_index / self.acc_hz
                        self.resp_buffer.push(ts, float(value))
                        self._acc_index += 1
            if packet.kind in {"ecg", "acc", "rr", "hr"} and packet.samples:
                self._data_received = True
                if self.connection_phase == "waiting_for_data":
                    self.connection_phase = "receiving"
            if self.packet_observer is not None:
                self.packet_observer(packet, received_ns, self, proxy)
        except Exception as error:
            # Bleak callbacks must propagate recording/processing failures to the owner.
            self.failure.set_exception(error)

    async def _write(self, data):
        if self.failure.done():
            await self.failure
        await self.client.write_gatt_char(WRITE_UUID, data, response=True)
        if self.failure.done():
            await self.failure

    async def _read_mode(self):
        for key in ("ecg", "sr", "xo"):
            self.config.pop(key, None)
        self._config_event.clear()
        for sub in (0x60, 0x62, 0x61):
            await self._write(command(0x0F, sub, 0))
        if self.mode != "observe":
            readback = asyncio.create_task(self._config_event.wait())
            try:
                done, _ = await asyncio.wait({readback, self.failure}, timeout=5,
                                             return_when=asyncio.FIRST_COMPLETED)
                if self.failure in done:
                    await self.failure
                if readback not in done:
                    raise TimeoutError("MODE_READBACK_TIMEOUT")
            finally:
                readback.cancel()
                await asyncio.gather(readback, return_exceptions=True)

    async def start_streaming(self):
        self._data_received = False
        self.connection_phase = "subscribe"
        await self.client.start_notify(NOTIFY_UUID, self._notification)
        self._notifying = True
        self.connection_phase = "initialize"
        # ECTRI ManDevice startup: calendar, device info, battery, ECG settings.
        # Calendar time is NOT a sample clock; offline history/settings are untouched.
        await self._write(date_command(datetime.now()))
        for data in (command(0x0F, 5), command(0x0F, 6), command(0x42, 6),
                     command(0x42, 1), command(0x42, 0x0B, 0)):
            await self._write(data)
        self.connection_phase = "read_mode"
        await self._read_mode()
        if self.mode != "observe":
            actual = tuple(self.config[k] for k in ("ecg", "sr", "xo"))
            if actual != MODES[self.mode]:
                self.connection_phase = "configure_mode"
                # Mode changes can reboot the belt. Do not rewrite matching values.
                for key, sub, value in zip(("ecg", "sr", "xo"), (0x60, 0x62, 0x61), MODES[self.mode]):
                    if self.config[key] != value:
                        await self._write(command(0x0F, sub, 1, value))
                        await asyncio.sleep(0.2)
                self.connection_phase = "verify_mode"
                await self._read_mode()
                actual = tuple(self.config[k] for k in ("ecg", "sr", "xo"))
            if actual != MODES[self.mode]:
                raise RuntimeError(f"MODE_READBACK_MISMATCH: {actual}")
            self.mode_readback_verified = True
        self.connection_phase = "start_acquisition"
        await self._write(command(0x14, 4, 0, 1))
        self.connection_phase = "receiving" if self._data_received else "waiting_for_data"

    def drain_frame(self):
        ecg = tuple(self.ecg_buffer.read_after(self._ecg_cursor)) if self.is_connected else ()
        resp = tuple(self.resp_buffer.read_after(self._resp_cursor)) if self.is_connected else ()
        if ecg:
            self._ecg_cursor = ecg[-1][0]
        if resp:
            self._resp_cursor = resp[-1][0]
        acc_new, self._acc_unread = self._acc_unread and self.is_connected, False
        return RawFrame(
            timestamp=time.monotonic(), ecg_samples=ecg, resp_samples=resp,
            ecg_raw=ecg[-1][1] if ecg else None,
            respiration_raw=resp[-1][1] if resp else None,
            breath_phase="unknown", respiration_depth=None,
            weather_type="",
            # The proxy is displayable, not admitted as an actual respiratory measurement.
            signal_validity={"ecg": bool(ecg), "resp": False, "acc": acc_new},
        )

    async def stop(self):
        notifying, self._notifying = self._notifying, False
        try:
            if self.is_connected and notifying:
                await self.client.stop_notify(NOTIFY_UUID)
        finally:
            if self.is_connected:
                await self.client.disconnect()
