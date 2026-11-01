"""APK-derived connection contracts, tested without Bluetooth hardware."""
import asyncio
from datetime import datetime
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from bigrun.driver import BigRunDriver
from bigrun.protocol import WRITE_UUID, command, date_command, decode_packet


class Recorder:
    def record(self, raw, received_ns):
        return decode_packet(raw)


class Client:
    def __init__(self, *args, **kwargs):
        self.is_connected = False
        self.params = {0x60: 1, 0x62: 0, 0x61: 1}
        self.writes = []
        self.disconnected = kwargs["disconnected_callback"]

    async def connect(self):
        self.is_connected = True

    async def disconnect(self):
        self.is_connected = False

    async def start_notify(self, uuid, callback):
        self.callback = callback

    async def stop_notify(self, uuid):
        pass

    async def write_gatt_char(self, uuid, data, *, response):
        assert uuid == WRITE_UUID and response is True
        assert len(data) == 20
        self.writes.append(data)
        if data[1] == 0x0F and data[2] in self.params:
            if data[3] == 1:
                self.params[data[2]] = data[4]
            else:
                self.callback(None, bytes([0x0F, data[2], 0, self.params[data[2]]]) + bytes(16))


def test_production_connect_uses_scanned_device_and_uncached_winrt(monkeypatch):
    import bleak
    import bigrun.driver as module

    device = object()
    calls = []

    async def find(address):
        calls.append(("scan", address))
        return device

    def make_client(target, **kwargs):
        assert target is device
        assert kwargs["winrt"] == {"use_cached_services": False}
        assert not kwargs.get("pair", False)
        calls.append(("client", target))
        return Client(target, **kwargs)

    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(bleak.BleakScanner, "find_device_by_address", find)
    monkeypatch.setattr(bleak, "BleakClient", make_client)

    async def run():
        driver = BigRunDriver("fake", Recorder())
        await driver.connect()
        assert calls[0] == ("scan", "fake")
        assert driver.connection_phase == "connected_gatt"
        await driver.stop()

    asyncio.run(run())


def test_no_advertisement_does_not_attempt_gatt(monkeypatch):
    import bleak

    async def find(address):
        return None

    def unexpected(*args, **kwargs):
        pytest.fail("GATT must not start without a fresh advertisement")

    monkeypatch.setattr(bleak.BleakScanner, "find_device_by_address", find)
    monkeypatch.setattr(bleak, "BleakClient", unexpected)

    async def run():
        driver = BigRunDriver("fake", Recorder())
        with pytest.raises(ConnectionError, match="BIGRUN_NOT_ADVERTISING"):
            await driver.connect()
        assert driver.connection_phase == "scan"
        await driver.stop()

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["observe", "ecg"])
def test_startup_queries_before_streaming_and_does_not_rewrite_matching_mode(mode):
    async def run():
        driver = BigRunDriver("fake", Recorder(), mode=mode, client_factory=Client)
        await driver.connect()
        await driver.start_streaming()
        writes = driver.client.writes
        assert writes[0][:2] == bytes([0xFC, 0])
        assert writes[1:6] == [command(0x0F, 5), command(0x0F, 6),
                               command(0x42, 6), command(0x42, 1), command(0x42, 0x0B, 0)]
        assert writes[6:9] == [command(0x0F, sub, 0) for sub in (0x60, 0x62, 0x61)]
        assert not any(w[1] == 0x0F and w[2] in (0x60, 0x62, 0x61) and w[3] == 1 for w in writes)
        assert writes[-1] == command(0x14, 4, 0, 1)
        assert driver.mode_readback_verified is (mode == "ecg")
        assert driver.connection_phase == "waiting_for_data"
        driver._notification(None, bytes.fromhex("140600001cdd0000000000000000000000000000"))
        assert driver.connection_phase == "receiving"
        await driver.stop()

    asyncio.run(run())


def test_only_changed_modes_are_written_then_read_back():
    class ChangedClient(Client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.params[0x60] = 0

    async def run():
        driver = BigRunDriver("fake", Recorder(), mode="ecg", client_factory=ChangedClient)
        await driver.connect()
        await driver.start_streaming()
        mode_writes = [w for w in driver.client.writes
                       if w[1] == 0x0F and w[2] in (0x60, 0x62, 0x61) and w[3] == 1]
        assert mode_writes == [command(0x0F, 0x60, 1, 1)]
        assert driver.mode_readback_verified
        await driver.stop()

    asyncio.run(run())


def test_mode_disconnect_aborts_without_stream_start_or_reconnect():
    class RebootClient(Client):
        async def write_gatt_char(self, uuid, data, **kwargs):
            await super().write_gatt_char(uuid, data, **kwargs)
            if data[:4] == bytes([0xFC, 0x0F, 0x60, 1]):
                self.is_connected = False
                self.disconnected(self)

    async def run():
        driver = BigRunDriver("fake", Recorder(), mode="sport", client_factory=RebootClient)
        await driver.connect()
        with pytest.raises(ConnectionError, match="configure_mode.*NO_AUTO_RESUME"):
            await driver.start_streaming()
        assert not driver.mode_readback_verified
        assert command(0x14, 4, 0, 1) not in driver.client.writes
        await driver.stop()

    asyncio.run(run())


def test_write_ack_is_not_a_mode_readback():
    async def run():
        driver = BigRunDriver("fake", Recorder(), client_factory=Client)
        await driver.connect()
        for sub, value in ((0x60, 1), (0x62, 0), (0x61, 1)):
            driver._notification(None, bytes([0x0F, sub, 1, value]) + bytes(16))
        assert not driver._config_event.is_set()
        assert driver.config == {}
        await driver.stop()

    asyncio.run(run())


def test_subscription_failure_cannot_send_initialization_commands():
    class UnreachableClient(Client):
        async def start_notify(self, uuid, callback):
            raise ConnectionError("GATT Unreachable")

    async def run():
        driver = BigRunDriver("fake", Recorder(), client_factory=UnreachableClient)
        await driver.connect()
        with pytest.raises(ConnectionError, match="GATT Unreachable"):
            await driver.start_streaming()
        assert driver.connection_phase == "subscribe"
        assert driver.client.writes == []
        await driver.stop()

    asyncio.run(run())


def test_disconnect_during_readback_is_reported_without_waiting_for_timeout():
    class LostReadbackClient(Client):
        async def write_gatt_char(self, uuid, data, **kwargs):
            if data[:4] == bytes([0xFC, 0x0F, 0x61, 0]):
                asyncio.get_running_loop().call_soon(self.lose_link)
            else:
                await super().write_gatt_char(uuid, data, **kwargs)

        def lose_link(self):
            self.is_connected = False
            self.disconnected(self)

    async def run():
        driver = BigRunDriver("fake", Recorder(), mode="ecg", client_factory=LostReadbackClient)
        await driver.connect()
        with pytest.raises(ConnectionError, match="phase=read_mode"):
            await asyncio.wait_for(driver.start_streaming(), 1)
        assert not driver.mode_readback_verified
        await driver.stop()

    asyncio.run(run())


def test_connection_failure_is_preserved_in_existing_p02_archive(tmp_path):
    from bigrun.recording import CandidateRecording, open_recording

    recording = CandidateRecording(tmp_path, "BLE-SYNTHETIC-FAIL", "replay", {})
    recording.connection_status("subscribe", "ConnectionError: GATT Unreachable")
    recording.close("ABORTED")
    reader = open_recording(recording.path)
    events = list(reader.iter_l1("bigrun_connection"))
    assert events[0]["payload"] == {
        "phase": "subscribe", "error": "ConnectionError: GATT Unreachable", "automatic_resume": False}
    assert reader.verify().valid


def test_capture_cli_keeps_subscription_error_and_closes_archive(tmp_path, monkeypatch, capsys):
    from bigrun import __main__ as cli
    from bigrun.recording import CandidateRecording, open_recording

    class UnreachableClient(Client):
        async def start_notify(self, uuid, callback):
            raise ConnectionError("GATT Unreachable")

    monkeypatch.setattr(cli, "BigRunDriver", lambda *a, **kw:
                        BigRunDriver(*a, **kw, client_factory=UnreachableClient))
    monkeypatch.setattr(cli, "CandidateRecording", lambda root, session_id, policy, settings:
                        CandidateRecording(root, session_id, "replay", settings))
    with pytest.raises(ConnectionError, match="GATT Unreachable"):
        cli.main(["capture", "--address", "fake", "--root", str(tmp_path), "--seconds", "1"])
    assert "phase=subscribe: GATT Unreachable" in capsys.readouterr().out
    reader = open_recording(next((tmp_path / "sessions").iterdir()))
    failures = [e["payload"] for e in reader.iter_l1("bigrun_connection") if e["payload"]["error"]]
    assert len(failures) == 1 and failures[0]["phase"] == "subscribe"
    assert reader.verify().valid


def test_apk_calendar_packet_keeps_sunday_zero_and_has_no_added_crc():
    assert date_command(datetime(2026, 10, 18, 14, 35, 59)) == bytes.fromhex(
        "fc00261018143559005500000000000000000000")
