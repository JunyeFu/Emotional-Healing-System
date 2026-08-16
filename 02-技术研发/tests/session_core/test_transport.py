from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import socket

import pytest

from srp_session_core import OperatorRequest, SessionCore, TransportError
from srp_session_core.transport import (
    ControlServer,
    SessionRuntimeHost,
    TelemetryPublisher,
)

from .helpers import ack_for, fast_transport_config, formal_dependencies, telemetry_for


def _hello(**changes):
    payload = {
        "transport_type": "hello",
        "transport_version": "1.0",
        "role": "unity",
        "schema_version": "2.1",
        "client_instance_id": "unity-test-1",
    }
    payload.update(changes)
    return payload


async def _write(writer, payload):
    writer.write(json.dumps(payload, separators=(",", ":")).encode() + b"\n")
    await writer.drain()


async def _read(reader):
    return json.loads((await reader.readline()).decode())


def test_tcp_handshake_control_ack_and_same_id_retry(
    manifest_factory, assignment_factory
) -> None:
    async def scenario():
        manifest = manifest_factory()
        core = SessionCore()
        prepared = core.prepare(manifest, assignment_factory(manifest), 0)
        config = fast_transport_config(ack_timeout_ms=20, max_send_attempts=3)
        server = ControlServer(core, config=config, port=0, now_ns=lambda: 100)
        await server.start()
        reader, writer = await asyncio.open_connection("127.0.0.1", server.bound_port)
        await _write(writer, _hello())
        welcome = await _read(reader)

        async def client():
            first = await _read(reader)
            second = await _read(reader)
            assert first["event_id"] == second["event_id"]
            assert first["control_seq"] == second["control_seq"]
            await _write(writer, ack_for(second, now_ns=100))

        client_task = asyncio.create_task(client())
        ack = await server.publish_control(prepared.control_events[0])
        await client_task
        assert welcome["accepted"] is True
        assert ack["result"] == "applied"
        assert prepared.control_events[0]["event_id"] in {
            item.event_id for item in core.audit_log if item.result == "applied"
        }
        writer.close()
        await writer.wait_closed()
        await server.close()

    asyncio.run(scenario())


def test_tcp_reconnect_resends_pending_event_with_same_identity(
    manifest_factory, assignment_factory
) -> None:
    async def scenario():
        manifest = manifest_factory()
        core = SessionCore()
        prepared = core.prepare(manifest, assignment_factory(manifest), 0)
        config = fast_transport_config(ack_timeout_ms=20, reconnect_grace_ms=100)
        server = ControlServer(core, config=config, port=0, now_ns=lambda: 100)
        await server.start()

        first_reader, first_writer = await asyncio.open_connection(
            "127.0.0.1", server.bound_port
        )
        await _write(first_writer, _hello())
        await _read(first_reader)

        async def clients():
            first = await _read(first_reader)
            first_writer.close()
            await first_writer.wait_closed()
            await asyncio.sleep(0.01)
            second_reader, second_writer = await asyncio.open_connection(
                "127.0.0.1", server.bound_port
            )
            await _write(second_writer, _hello())
            await _read(second_reader)
            resent = await _read(second_reader)
            assert resent["event_id"] == first["event_id"]
            assert resent["control_seq"] == first["control_seq"]
            await _write(second_writer, ack_for(resent, now_ns=100))
            second_writer.close()
            await second_writer.wait_closed()

        client_task = asyncio.create_task(clients())
        ack = await server.publish_control(prepared.control_events[0])
        await client_task
        assert ack["result"] == "applied"
        await server.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("change", "value", "expected"),
    [
        ("transport_version", "9.9", "TRANSPORT_VERSION_MISMATCH"),
        ("schema_version", "9.9", "SCHEMA_VERSION_MISMATCH"),
        ("role", "operator", "TRANSPORT_ROLE_INVALID"),
    ],
)
def test_tcp_rejects_invalid_handshake(change, value, expected) -> None:
    async def scenario():
        core = SessionCore()
        server = ControlServer(core, config=fast_transport_config(), port=0)
        await server.start()
        reader, writer = await asyncio.open_connection("127.0.0.1", server.bound_port)
        await _write(writer, _hello(**{change: value}))
        response = await _read(reader)
        assert response["error_code"] == expected
        writer.close()
        await writer.wait_closed()
        await server.close()

    asyncio.run(scenario())


def test_td_connection_cannot_change_authoritative_state() -> None:
    async def scenario():
        core = SessionCore()
        server = ControlServer(core, config=fast_transport_config(), port=0)
        await server.start()
        reader, writer = await asyncio.open_connection("127.0.0.1", server.bound_port)
        await _write(writer, _hello(role="td", client_instance_id="td-test"))
        assert (await _read(reader))["accepted"] is True
        await _write(writer, {"message_type": "control_event", "event_type": "abort"})
        response = await _read(reader)
        assert response["error_code"] == "TD_STATE_CHANGE_NOT_AVAILABLE"
        assert core.snapshot().status.value == "CREATED"
        writer.close()
        await writer.wait_closed()
        await server.close()

    asyncio.run(scenario())


def test_tcp_rejects_malformed_json() -> None:
    async def scenario():
        server = ControlServer(SessionCore(), config=fast_transport_config(), port=0)
        await server.start()
        reader, writer = await asyncio.open_connection("127.0.0.1", server.bound_port)
        writer.write(b"{invalid-json\n")
        await writer.drain()
        response = await _read(reader)
        assert response["error_code"] == "TRANSPORT_FRAME_INVALID"
        writer.close()
        await writer.wait_closed()
        await server.close()

    asyncio.run(scenario())


def test_tcp_reports_semantically_invalid_ack_without_waiting_for_timeout(
    manifest_factory, assignment_factory
) -> None:
    async def scenario():
        manifest = manifest_factory()
        core = SessionCore()
        prepared = core.prepare(manifest, assignment_factory(manifest), 0)
        server = ControlServer(
            core,
            config=fast_transport_config(ack_timeout_ms=500),
            port=0,
            now_ns=lambda: 100,
        )
        await server.start()
        reader, writer = await asyncio.open_connection("127.0.0.1", server.bound_port)
        await _write(writer, _hello())
        await _read(reader)

        publish_task = asyncio.create_task(
            server.publish_control(prepared.control_events[0])
        )
        event = await _read(reader)
        invalid = ack_for(event, now_ns=100)
        invalid["session_id"] = "S-P01-OTHER"
        await _write(writer, invalid)

        response = await _read(reader)
        assert response["error_code"] == "SESSION_ID_MISMATCH"
        with pytest.raises(TransportError) as error:
            await asyncio.wait_for(publish_task, 0.1)
        assert error.value.code == "SESSION_ID_MISMATCH"
        writer.close()
        await writer.wait_closed()
        await server.close()

    asyncio.run(scenario())


def test_tcp_rejects_ack_for_control_that_has_not_been_sent(
    manifest_factory, assignment_factory
) -> None:
    async def scenario():
        manifest = manifest_factory()
        core = SessionCore()
        prepared = core.prepare(manifest, assignment_factory(manifest), 0)
        core.confirm_delivery(ack_for(prepared.control_events[0], now_ns=0), 0)
        started = core.apply_operator_request(OperatorRequest("REQ-START", "start"), 1)
        server = ControlServer(core, config=fast_transport_config(), port=0)
        early_ack = ack_for(started.control_events[1], now_ns=2)

        with pytest.raises(TransportError) as error:
            await server._handle_unity_message(early_ack)

        assert error.value.code == "CONTROL_ACK_NOT_PENDING"
        assert started.control_events[1]["event_id"] not in {
            item.event_id for item in core.audit_log if item.result == "applied"
        }

    asyncio.run(scenario())


def test_tcp_port_conflict_fails_closed() -> None:
    async def scenario():
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", 0))
        blocker.listen()
        port = blocker.getsockname()[1]
        server = ControlServer(SessionCore(), config=fast_transport_config(), port=port)
        try:
            with pytest.raises(TransportError) as error:
                await server.start()
            assert error.value.code == "PORT_BIND_FAILED"
        finally:
            blocker.close()

    asyncio.run(scenario())


def test_udp_publishes_identical_frame_to_both_ports_and_throttles(
    manifest_factory, assignment_factory
) -> None:
    receivers = []
    targets = []
    for _ in range(2):
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(1)
        receivers.append(receiver)
        targets.append(("127.0.0.1", receiver.getsockname()[1]))
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
    publish_clock = iter((1_000_000_000, 1_025_000_000))
    publisher = TelemetryPublisher(
        core, targets=tuple(targets), now_ns=lambda: next(publish_clock)
    )
    first = telemetry_for(core.snapshot(), frame_seq=1, sent_ns=50_000_000)
    second = telemetry_for(core.snapshot(), frame_seq=2, sent_ns=75_000_000)
    try:
        assert publisher.publish(first) is True
        payloads = [receiver.recvfrom(65535)[0] for receiver in receivers]
        assert payloads[0] == payloads[1]
        assert json.loads(payloads[0])["frame_seq"] == 1
        assert publisher.publish(second) is False
    finally:
        publisher.close()
        for receiver in receivers:
            receiver.close()


def test_udp_uses_local_publish_clock_instead_of_frame_timestamp(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
    publish_clock = iter((1_000_000_000, 1_010_000_000))
    publisher = TelemetryPublisher(
        core,
        targets=(("127.0.0.1", 50991),),
        now_ns=lambda: next(publish_clock),
    )
    first = telemetry_for(core.snapshot(), frame_seq=1, sent_ns=50_000_000)
    future_dated = telemetry_for(
        core.snapshot(), frame_seq=2, sent_ns=50_000_000_000
    )
    try:
        assert publisher.publish(first) is True
        assert publisher.publish(future_dated) is False
    finally:
        publisher.close()


def test_udp_rejects_stale_or_snapshot_mismatch(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
    publisher = TelemetryPublisher(core, targets=(("127.0.0.1", 50991),))
    frame = telemetry_for(core.snapshot(), frame_seq=1, sent_ns=50_000_000)
    try:
        assert publisher.publish(frame) is True
        stale = telemetry_for(core.snapshot(), frame_seq=1, sent_ns=100_000_000)
        with pytest.raises(TransportError) as stale_error:
            publisher.publish(stale)
        assert stale_error.value.code == "STALE_TELEMETRY_SEQUENCE"
        mismatch = telemetry_for(core.snapshot(), frame_seq=2, sent_ns=100_000_000)
        mismatch["module_id"] = "heat"
        with pytest.raises(TransportError) as mismatch_error:
            publisher.publish(mismatch)
        assert mismatch_error.value.code == "TELEMETRY_SNAPSHOT_MISMATCH"
    finally:
        publisher.close()


def test_runtime_host_delivers_abort_best_effort_and_disconnects_after_formal_failure(
    manifest_factory, assignment_factory
) -> None:
    class FailingControlServer:
        def __init__(self):
            self.events = []
            self.disconnected = False
            self.now_ns = lambda: 2

        async def publish_control(self, event):
            self.events.append(event)
            if len(self.events) == 1:
                raise TransportError("CONTROL_ACK_TIMEOUT")
            return ack_for(event, now_ns=2)

        def pop_delivery_update(self, event_id):
            del event_id
            return None

        async def disconnect_unity(self):
            self.disconnected = True

    async def scenario():
        manifest = manifest_factory(runtime_mode="formal_stage_1")
        core = SessionCore(dependencies=formal_dependencies())
        prepared = core.prepare(manifest, assignment_factory(manifest), 0)
        core.confirm_delivery(ack_for(prepared.control_events[0], now_ns=1), 1)
        server = FailingControlServer()
        host = SessionRuntimeHost(core, server)

        update = await host.apply_operator_request(
            OperatorRequest("REQ-START", "start"), 1
        )

        assert update.snapshot.status.value == "ABORTED"
        assert [event["event_type"] for event in server.events] == ["start", "abort"]
        assert server.disconnected is True

    asyncio.run(scenario())


def test_formal_end_delivery_failure_overrides_unconfirmed_completion(
    manifest_factory, assignment_factory
) -> None:
    class EndFailingControlServer:
        def __init__(self):
            self.events = []
            self.disconnected = False
            self.now_ns = lambda: 800_000_000_001

        async def publish_control(self, event):
            self.events.append(event)
            if event["event_type"] == "end":
                raise TransportError("CONTROL_ACK_TIMEOUT")
            return ack_for(event, now_ns=self.now_ns())

        def pop_delivery_update(self, event_id):
            del event_id
            return None

        async def disconnect_unity(self):
            self.disconnected = True

    async def scenario():
        manifest = manifest_factory(runtime_mode="formal_stage_1")
        config = fast_transport_config(max_scheduler_lag_ms=1_000_000)
        core = SessionCore(config=config, dependencies=formal_dependencies())
        prepared = core.prepare(manifest, assignment_factory(manifest), 0)
        core.confirm_delivery(ack_for(prepared.control_events[0], now_ns=0), 0)
        core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
        server = EndFailingControlServer()
        host = SessionRuntimeHost(core, server)

        update = await host.advance(800_000_000_000)

        assert update.snapshot.status.value == "ABORTED"
        assert [event["event_type"] for event in server.events][-2:] == ["end", "abort"]
        assert server.disconnected is True

    asyncio.run(scenario())
