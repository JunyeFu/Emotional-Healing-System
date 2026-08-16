from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import socket
import time
from typing import Any, Callable, Mapping

from .config import ProtocolConfig, load_protocol_config
from .contract_adapter import SCHEMA_VERSION, validate_message
from .core import SessionCore
from .errors import SessionCoreError, TransportError
from .models import CoreUpdate, OperatorRequest, SessionStatus


TRANSPORT_VERSION = "1.0"


@dataclass(frozen=True)
class Handshake:
    role: str
    client_instance_id: str


class ControlServer:
    """Loopback JSON Lines control server for one Unity client and reserved TD access."""

    def __init__(
        self,
        core: SessionCore,
        *,
        config: ProtocolConfig | None = None,
        host: str | None = None,
        port: int | None = None,
        now_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self.core = core
        self.config = config or load_protocol_config()
        self.host = host or self.config.transport.bind_host
        self.port = self.config.transport.tcp_control_port if port is None else port
        if self.host != "127.0.0.1":
            raise TransportError("NON_LOOPBACK_BIND_FORBIDDEN", self.host)
        self.now_ns = now_ns
        self._server: asyncio.AbstractServer | None = None
        self._unity_writer: asyncio.StreamWriter | None = None
        self._unity_client_id: str | None = None
        self._unity_connected = asyncio.Event()
        self._unity_generation = 0
        self._pending_acks: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._pending_ack_generations: dict[str, int] = {}
        self._sent_event_ids: set[str] = set()
        self._delivered_event_ids: set[str] = set()
        self._delivery_updates: dict[str, CoreUpdate] = {}
        self._client_tasks: set[asyncio.Task[Any]] = set()

    @property
    def bound_port(self) -> int | None:
        if not self._server or not self._server.sockets:
            return None
        return int(self._server.sockets[0].getsockname()[1])

    @property
    def unity_connected(self) -> bool:
        return self._unity_connected.is_set()

    async def start(self) -> None:
        if self._server is not None:
            return
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port,
                limit=self.config.transport.max_json_line_bytes,
            )
        except OSError as error:
            raise TransportError("PORT_BIND_FAILED", f"{self.host}:{self.port}") from error

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        await self.disconnect_unity()
        tasks = tuple(self._client_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for future in self._pending_acks.values():
            if not future.done():
                future.set_exception(TransportError("CONTROL_SERVER_CLOSED"))
        self._pending_acks.clear()
        self._pending_ack_generations.clear()
        self._sent_event_ids.clear()
        self._delivered_event_ids.clear()
        self._delivery_updates.clear()

    async def disconnect_unity(self) -> None:
        """Close only the active Unity connection while keeping the listener available."""
        writer = self._unity_writer
        self._unity_writer = None
        self._unity_client_id = None
        self._unity_generation += 1
        self._unity_connected.clear()
        if writer is None:
            return
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass

    async def wait_for_unity(self, timeout_ms: int | None = None) -> None:
        timeout = (
            self.config.transport.reconnect_grace_ms
            if timeout_ms is None
            else timeout_ms
        ) / 1000
        try:
            await asyncio.wait_for(self._unity_connected.wait(), timeout)
        except TimeoutError as error:
            raise TransportError("UNITY_HANDSHAKE_REQUIRED") from error

    async def publish_control(self, event: Mapping[str, Any]) -> dict[str, Any]:
        validated = validate_message("control_event", event)
        event_id = str(validated["event_id"])
        loop = asyncio.get_running_loop()
        future = self._pending_acks.get(event_id)
        if future is None or future.done():
            future = loop.create_future()
            self._pending_acks[event_id] = future

        try:
            timeout = self.config.transport.ack_timeout_ms / 1000
            attempts = self.config.transport.max_send_attempts
            for _ in range(attempts):
                if not self._unity_connected.is_set():
                    try:
                        await self.wait_for_unity()
                    except TransportError:
                        continue
                writer = self._unity_writer
                if writer is None:
                    continue
                generation = self._unity_generation
                try:
                    self._pending_ack_generations[event_id] = generation
                    self._sent_event_ids.add(event_id)
                    await self._write_json(writer, validated)
                except (ConnectionError, OSError):
                    self._sent_event_ids.discard(event_id)
                    if self._pending_ack_generations.get(event_id) == generation:
                        self._pending_ack_generations.pop(event_id, None)
                    self._unity_connected.clear()
                    continue
                try:
                    ack = await asyncio.wait_for(asyncio.shield(future), timeout)
                except TimeoutError:
                    continue
                if ack["result"] in {"applied", "duplicate_ignored"}:
                    return ack
                raise TransportError(
                    "CONTROL_ACK_REJECTED", str(ack.get("error_code") or "UNKNOWN")
                )

            raise TransportError("CONTROL_ACK_TIMEOUT", event_id)
        finally:
            self._sent_event_ids.discard(event_id)
            self._pending_ack_generations.pop(event_id, None)
            if self._pending_acks.get(event_id) is future:
                self._pending_acks.pop(event_id, None)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._client_tasks.add(task)
        handshake: Handshake | None = None
        connection_generation: int | None = None
        try:
            raw = await asyncio.wait_for(
                reader.readline(), self.config.transport.reconnect_grace_ms / 1000
            )
            payload = self._decode_line(raw)
            handshake = self._validate_handshake(payload)
            if handshake.role == "unity":
                if (
                    self._unity_writer is not None
                    and not self._unity_writer.is_closing()
                    and self._unity_client_id != handshake.client_instance_id
                ):
                    await self._send_welcome(
                        writer, handshake, accepted=False, error_code="UNITY_CLIENT_ALREADY_CONNECTED"
                    )
                    return
                previous_writer = self._unity_writer
                if previous_writer is not None and previous_writer is not writer:
                    previous_writer.close()
                self._unity_generation += 1
                connection_generation = self._unity_generation
                self._unity_writer = writer
                self._unity_client_id = handshake.client_instance_id
                self._unity_connected.set()
            await self._send_welcome(writer, handshake, accepted=True, error_code=None)

            while not reader.at_eof():
                raw = await reader.readline()
                if not raw:
                    break
                message = self._decode_line(raw)
                if handshake.role == "unity":
                    try:
                        await self._handle_unity_message(
                            message, connection_generation=connection_generation
                        )
                    except TransportError as error:
                        if error.code in {
                            "CONTROL_ACK_NOT_PENDING",
                            "CONTROL_ACK_CONNECTION_MISMATCH",
                        }:
                            await self._write_json(writer, self._transport_error(error.code))
                            continue
                        raise
                else:
                    await self._write_json(
                        writer,
                        self._transport_error("TD_STATE_CHANGE_NOT_AVAILABLE"),
                    )
        except (
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
            SessionCoreError,
        ) as error:
            try:
                code = (
                    error.code
                    if isinstance(error, SessionCoreError)
                    else "TRANSPORT_FRAME_INVALID"
                )
                if (
                    handshake is not None
                    and handshake.role == "unity"
                    and connection_generation == self._unity_generation
                ):
                    self._fail_pending_acks(code, connection_generation)
                await self._write_json(writer, self._transport_error(code))
            except (ConnectionError, OSError):
                pass
        finally:
            if handshake and handshake.role == "unity" and self._unity_writer is writer:
                self._unity_writer = None
                self._unity_connected.clear()
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass
            if task is not None:
                self._client_tasks.discard(task)

    async def _handle_unity_message(
        self,
        message: Mapping[str, Any],
        *,
        connection_generation: int | None = None,
    ) -> None:
        message_type = message.get("message_type")
        if message_type not in {"ack", "render_receipt"}:
            raise TransportError("MESSAGE_NOT_ALLOWED_FOR_ROLE", str(message_type))
        actual_generation = (
            self._unity_generation
            if connection_generation is None
            else connection_generation
        )
        if actual_generation != self._unity_generation:
            raise TransportError("CONTROL_ACK_CONNECTION_MISMATCH")
        if message_type == "ack":
            event_id = str(message.get("event_id", ""))
            if event_id in self._delivered_event_ids:
                update = self.core.confirm_delivery(message, self.now_ns())
                self._delivery_updates[event_id] = update
                future = self._pending_acks.get(event_id)
                if future is not None and not future.done():
                    future.set_result(dict(message))
                return
            future = self._pending_acks.get(event_id)
            if (
                event_id not in self._sent_event_ids
                or future is None
                or future.done()
            ):
                raise TransportError("CONTROL_ACK_NOT_PENDING")
            expected_generation = self._pending_ack_generations.get(event_id)
            if expected_generation != actual_generation:
                raise TransportError("CONTROL_ACK_CONNECTION_MISMATCH")
        update = self.core.confirm_delivery(message, self.now_ns())
        if message_type == "ack":
            event_id = str(message["event_id"])
            self._delivery_updates[event_id] = update
            if message.get("result") in {"applied", "duplicate_ignored"}:
                self._delivered_event_ids.add(event_id)
            future = self._pending_acks.get(event_id)
            if future is not None and not future.done():
                future.set_result(dict(message))
        del update

    def pop_delivery_update(self, event_id: str) -> CoreUpdate | None:
        return self._delivery_updates.pop(event_id, None)

    def _fail_pending_acks(self, code: str, generation: int) -> None:
        for event_id, future in self._pending_acks.items():
            if (
                self._pending_ack_generations.get(event_id) == generation
                and not future.done()
            ):
                future.set_exception(TransportError(code))

    def _validate_handshake(self, payload: Mapping[str, Any]) -> Handshake:
        required = {
            "transport_type",
            "transport_version",
            "role",
            "schema_version",
            "client_instance_id",
        }
        if set(payload) != required or payload.get("transport_type") != "hello":
            raise TransportError("TRANSPORT_HANDSHAKE_INVALID")
        if payload.get("transport_version") != TRANSPORT_VERSION:
            raise TransportError("TRANSPORT_VERSION_MISMATCH")
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise TransportError("SCHEMA_VERSION_MISMATCH")
        role = payload.get("role")
        if role not in {"unity", "td"}:
            raise TransportError("TRANSPORT_ROLE_INVALID")
        client_id = payload.get("client_instance_id")
        if not isinstance(client_id, str) or not client_id:
            raise TransportError("CLIENT_INSTANCE_ID_INVALID")
        return Handshake(str(role), client_id)

    def _decode_line(self, raw: bytes) -> dict[str, Any]:
        if not raw or len(raw) > self.config.transport.max_json_line_bytes:
            raise TransportError("TRANSPORT_FRAME_TOO_LARGE")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise TransportError("TRANSPORT_ENCODING_INVALID") from error
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise TransportError("TRANSPORT_FRAME_INVALID")
        return payload

    async def _send_welcome(
        self,
        writer: asyncio.StreamWriter,
        handshake: Handshake,
        *,
        accepted: bool,
        error_code: str | None,
    ) -> None:
        await self._write_json(
            writer,
            {
                "transport_type": "welcome",
                "transport_version": TRANSPORT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "role": handshake.role,
                "client_instance_id": handshake.client_instance_id,
                "accepted": accepted,
                "error_code": error_code,
            },
        )

    @staticmethod
    async def _write_json(
        writer: asyncio.StreamWriter, payload: Mapping[str, Any]
    ) -> None:
        encoded = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8") + b"\n"
        writer.write(encoded)
        await writer.drain()

    @staticmethod
    def _transport_error(code: str) -> dict[str, Any]:
        return {
            "transport_type": "error",
            "transport_version": TRANSPORT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "error_code": code,
        }


class TelemetryPublisher:
    """Validate and mirror a complete v2.1 frame to Unity and TD at no more than 20 Hz."""

    def __init__(
        self,
        core: SessionCore,
        *,
        config: ProtocolConfig | None = None,
        targets: tuple[tuple[str, int], ...] | None = None,
        sock: socket.socket | None = None,
        now_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self.core = core
        self.config = config or load_protocol_config()
        self.targets = targets or (
            (self.config.transport.bind_host, self.config.transport.udp_td_port),
            (self.config.transport.bind_host, self.config.transport.udp_unity_port),
        )
        if any(host != "127.0.0.1" for host, _ in self.targets):
            raise TransportError("NON_LOOPBACK_TARGET_FORBIDDEN")
        self.socket = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.now_ns = now_ns
        self._owns_socket = sock is None
        self._last_frame_seq = -1
        self._last_publish_ns: int | None = None

    def publish(self, frame: Mapping[str, Any]) -> bool:
        validated = validate_message("telemetry_frame", frame)
        snapshot = self.core.snapshot()
        if snapshot.status not in {
            SessionStatus.RUNNING,
            SessionStatus.PAUSED,
            SessionStatus.COMPLETED,
        }:
            raise TransportError("TELEMETRY_SESSION_NOT_ACTIVE")
        expected = {
            "session_id": snapshot.session_id,
            "module_id": snapshot.module_id,
            "module_position": snapshot.module_position,
            "segment": snapshot.segment,
            "cue_mode": snapshot.cue_mode,
            "runtime_mode": snapshot.runtime_mode,
        }
        mismatches = [key for key, value in expected.items() if validated[key] != value]
        if mismatches:
            raise TransportError("TELEMETRY_SNAPSHOT_MISMATCH", ",".join(mismatches))
        frame_seq = int(validated["frame_seq"])
        if frame_seq <= self._last_frame_seq:
            raise TransportError("STALE_TELEMETRY_SEQUENCE", str(frame_seq))
        publish_ns = self.now_ns()
        if (
            isinstance(publish_ns, bool)
            or not isinstance(publish_ns, int)
            or publish_ns < 0
        ):
            raise TransportError("INVALID_PUBLISH_CLOCK")
        if self._last_publish_ns is not None and publish_ns < self._last_publish_ns:
            raise TransportError("NON_MONOTONIC_PUBLISH_CLOCK")
        minimum_interval_ns = round(1_000_000_000 / self.config.transport.telemetry_hz)
        if (
            self._last_publish_ns is not None
            and publish_ns - self._last_publish_ns < minimum_interval_ns
        ):
            return False

        payload = json.dumps(
            validated, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        failures: list[str] = []
        for host, port in self.targets:
            try:
                self.socket.sendto(payload, (host, port))
            except OSError:
                failures.append(f"{host}:{port}")
        if failures:
            raise TransportError("UDP_SEND_FAILED", ",".join(failures))
        self._last_frame_seq = frame_seq
        self._last_publish_ns = publish_ns
        return True

    def close(self) -> None:
        if self._owns_socket:
            self.socket.close()


class SessionRuntimeHost:
    """Compose SessionCore with reliable control without moving authority into sockets."""

    def __init__(self, core: SessionCore, control_server: ControlServer) -> None:
        self.core = core
        self.control_server = control_server
        self._operation_lock = asyncio.Lock()

    async def prepare(
        self,
        manifest: Mapping[str, Any],
        assignment: Any,
        now_ns: int,
    ) -> CoreUpdate:
        async with self._operation_lock:
            await self.control_server.wait_for_unity()
            update = self.core.prepare(manifest, assignment, now_ns)
            return await self._deliver(update, now_ns)

    async def apply_operator_request(
        self, request: OperatorRequest, now_ns: int
    ) -> CoreUpdate:
        async with self._operation_lock:
            update = self.core.apply_operator_request(request, now_ns)
            return await self._deliver(update, now_ns)

    async def advance(self, now_ns: int) -> CoreUpdate:
        async with self._operation_lock:
            update = self.core.advance(now_ns)
            return await self._deliver(update, now_ns)

    async def _deliver(self, update: CoreUpdate, now_ns: int) -> CoreUpdate:
        current_event_id: str | None = None
        delivery_updates: list[CoreUpdate] = []

        def merge(final: CoreUpdate) -> CoreUpdate:
            updates = (update, *delivery_updates)
            if final is not update and final not in delivery_updates:
                updates = (*updates, final)
            return CoreUpdate(
                snapshot=final.snapshot,
                control_events=tuple(
                    item for candidate in updates for item in candidate.control_events
                ),
                session_events=tuple(
                    item for candidate in updates for item in candidate.session_events
                ),
                policy_decisions=tuple(
                    item for candidate in updates for item in candidate.policy_decisions
                ),
                audit_records=tuple(
                    item for candidate in updates for item in candidate.audit_records
                ),
                gate_receipts=tuple(
                    item for candidate in updates for item in candidate.gate_receipts
                ),
            )

        try:
            for event in update.control_events:
                current_event_id = str(event["event_id"])
                await self.control_server.publish_control(event)
                delivered = self.control_server.pop_delivery_update(current_event_id)
                if delivered is not None:
                    delivery_updates.append(delivered)
            if not delivery_updates:
                return update
            return merge(delivery_updates[-1])
        except TransportError as error:
            failure = (
                None
                if current_event_id is None
                else self.control_server.pop_delivery_update(current_event_id)
            )
            if failure is None:
                failure_now_ns = max(now_ns, self.control_server.now_ns())
                failure = self.core.transport_failure(error.code, failure_now_ns)

            delivery_updates.append(failure)

            for event in failure.control_events:
                try:
                    await self.control_server.publish_control(event)
                    delivered = self.control_server.pop_delivery_update(
                        str(event["event_id"])
                    )
                    if delivered is not None:
                        delivery_updates.append(delivered)
                except TransportError:
                    break

            if str(failure.snapshot.runtime_mode or "").startswith("formal_"):
                await self.control_server.disconnect_unity()
            return merge(delivery_updates[-1])
