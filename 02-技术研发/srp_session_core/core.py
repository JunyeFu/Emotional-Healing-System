from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Mapping

from .config import ProtocolConfig, load_protocol_config
from .contract_adapter import SCHEMA_VERSION, validate_message
from .errors import SessionCoreError
from .gates import RuntimeDependencies
from .models import (
    AssignmentBundle,
    AuditRecord,
    CoreUpdate,
    GateReceipt,
    OperatorRequest,
    SessionEvent,
    SessionSnapshot,
    SessionStatus,
    SessionSummary,
)
from .sequence import FixedSequenceProvider, ModuleDecision, SequenceProvider


_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SEGMENTS = ("demo", "closed_loop", "lock_transition")


class SessionCore:
    """Deterministic authority for the four-module SRP core experience."""

    def __init__(
        self,
        *,
        config: ProtocolConfig | None = None,
        dependencies: RuntimeDependencies | None = None,
        sequence_provider: SequenceProvider | None = None,
    ) -> None:
        self.config = config or load_protocol_config()
        self.dependencies = dependencies or RuntimeDependencies.development()
        self.sequence_provider = sequence_provider or FixedSequenceProvider()

        self._status = SessionStatus.CREATED
        self._manifest: dict[str, Any] | None = None
        self._assignment: AssignmentBundle | None = None
        self._module_position: int | None = None
        self._module_id: str | None = None
        self._segment: str | None = None
        self._segment_start_ns: int | None = None
        self._segment_deadline_ns: int | None = None
        self._session_start_ns: int | None = None
        self._pause_start_ns: int | None = None
        self._total_paused_ns = 0
        self._last_now_ns = 0
        self._control_seq = 0
        self._session_event_seq = 0
        self._audit_seq = 0
        self._control_log: list[dict[str, Any]] = []
        self._session_event_log: list[SessionEvent] = []
        self._audit_log: list[AuditRecord] = []
        self._control_by_id: dict[str, dict[str, Any]] = {}
        self._acked_event_ids: set[str] = set()
        self._receipt_ids: set[str] = set()
        self._request_ids: set[str] = set()
        self._completed_modules: list[str] = []
        self._prepare_event_id: str | None = None
        self._end_event_id: str | None = None
        self._exposed = False
        self._finished_reason: str | None = None
        self._gate_receipts: tuple[GateReceipt, ...] = ()

    def prepare(
        self,
        manifest: Mapping[str, Any],
        assignment: AssignmentBundle,
        now_ns: int,
    ) -> CoreUpdate:
        self._require_status(SessionStatus.CREATED, "prepare")
        self._observe_time(now_ns)
        filtered = validate_message("session_manifest", manifest)
        self._validate_manifest_semantics(filtered)
        privacy_receipt = self.dependencies.privacy_receipt(
            deepcopy(dict(manifest)), assignment, self.config.config_hash
        )
        self.sequence_provider.prepare(filtered, assignment)
        receipts = (
            privacy_receipt,
            self.dependencies.assignment_receipt(
                filtered, assignment, self.config.config_hash
            ),
            self.dependencies.store_receipt(filtered, self.config.config_hash),
            self.dependencies.readiness_receipt(
                filtered, assignment, self.config.config_hash
            ),
        )

        before = self._status
        self._manifest = filtered
        self._assignment = assignment
        self._status = SessionStatus.PREPARED
        self._gate_receipts = receipts

        event = self._make_control(
            "prepare",
            now_ns,
            {
                "manifest": deepcopy(filtered),
                "protocol_config_hash": self.config.config_hash,
                "sequence_mode": "fixed",
            },
        )
        self._prepare_event_id = str(event["event_id"])
        session_event = self._make_session_event(
            "session_prepared",
            scheduled_ns=now_ns,
            observed_ns=now_ns,
            state_before=before,
            state_after=self._status,
            payload={
                "gate_evidence_ids": [receipt.evidence_id for receipt in receipts],
                "protocol_config_hash": self.config.config_hash,
            },
        )
        return self._update(
            control_events=(event,),
            session_events=(session_event,),
            gate_receipts=receipts,
        )

    def apply_operator_request(
        self, request: OperatorRequest, now_ns: int
    ) -> CoreUpdate:
        self._observe_time(now_ns)
        if not request.request_id:
            raise SessionCoreError("EMPTY_OPERATOR_REQUEST_ID")
        if request.request_id in self._request_ids:
            audit = self._audit(
                request.request_id, "rejected", "DUPLICATE_OPERATOR_REQUEST", now_ns
            )
            return self._update(audit_records=(audit,))
        self._request_ids.add(request.request_id)
        if self._end_event_id is not None and self._end_event_id not in self._acked_event_ids:
            return self._reject_request(request, "COMPLETION_ACK_PENDING", now_ns)

        if request.action == "start":
            return self._start_or_resume(request, now_ns)
        if request.action == "pause":
            return self._pause(request, now_ns)
        if request.action == "abort":
            return self._abort_request(request, now_ns)

        audit = self._audit(
            request.request_id, "rejected", "UNKNOWN_OPERATOR_ACTION", now_ns
        )
        return self._update(audit_records=(audit,))

    def advance(self, now_ns: int) -> CoreUpdate:
        self._observe_time(now_ns)
        if self._status is not SessionStatus.RUNNING:
            return self._update()

        controls: list[Mapping[str, Any]] = []
        events: list[SessionEvent] = []
        decisions: list[Mapping[str, Any]] = []
        while (
            self._status is SessionStatus.RUNNING
            and self._segment_deadline_ns is not None
            and now_ns >= self._segment_deadline_ns
        ):
            scheduled_ns = self._segment_deadline_ns
            lag_ns = now_ns - scheduled_ns
            if self._is_formal() and lag_ns > self.config.transport.max_scheduler_lag_ms * 1_000_000:
                failure = self._abort_internal("SCHEDULER_LAG_EXCEEDED", now_ns)
                controls.extend(failure.control_events)
                events.extend(failure.session_events)
                break

            step_controls, step_events, step_decisions = self._advance_boundary(
                scheduled_ns, now_ns, lag_ns
            )
            controls.extend(step_controls)
            events.extend(step_events)
            decisions.extend(step_decisions)

        return self._update(
            control_events=tuple(controls),
            session_events=tuple(events),
            policy_decisions=tuple(decisions),
        )

    def confirm_delivery(
        self, ack_or_receipt: Mapping[str, Any], now_ns: int
    ) -> CoreUpdate:
        self._observe_time(now_ns)
        message_type = ack_or_receipt.get("message_type")
        if message_type not in {"ack", "render_receipt"}:
            raise SessionCoreError("DELIVERY_MESSAGE_TYPE_INVALID", str(message_type))
        message = validate_message(str(message_type), ack_or_receipt)
        self._require_session_match(message)

        if message_type == "ack":
            return self._confirm_ack(message, now_ns)
        return self._confirm_receipt(message, now_ns)

    def transport_failure(self, reason_code: str, now_ns: int) -> CoreUpdate:
        self._observe_time(now_ns)
        self._validate_reason_code(reason_code)
        if self._is_formal():
            return self._abort_internal(reason_code, now_ns)
        if self._status is SessionStatus.RUNNING:
            request = OperatorRequest(
                request_id=f"transport:{self._audit_seq + 1}",
                action="pause",
                reason_code=reason_code,
            )
            return self.apply_operator_request(request, now_ns)
        audit = self._audit("transport", "rejected", reason_code, now_ns)
        return self._update(audit_records=(audit,))

    def finish(self, reason_code: str, now_ns: int) -> SessionSummary:
        self._observe_time(now_ns)
        self._validate_reason_code(reason_code)
        if self._status not in {SessionStatus.COMPLETED, SessionStatus.ABORTED}:
            self._abort_internal(reason_code, now_ns)
        if self._finished_reason is None:
            self._finished_reason = reason_code
        if self._manifest is None:
            raise SessionCoreError("SESSION_NOT_PREPARED")
        return SessionSummary(
            session_id=str(self._manifest["session_id"]),
            status=self._status,
            reason_code=self._finished_reason,
            completed_modules=tuple(self._completed_modules),
            session_elapsed_ns=self._session_elapsed_ns(),
            paused_duration_ns=self._paused_duration_ns(),
            control_event_count=len(self._control_log),
            session_event_count=len(self._session_event_log),
            protocol_config_hash=self.config.config_hash,
        )

    def snapshot(self) -> SessionSnapshot:
        duration_ns = self._current_segment_duration_ns()
        if (
            duration_ns is None
            or self._segment_start_ns is None
            or self._segment is None
        ):
            progress = 0.0
        else:
            clock_ns = self._pause_start_ns if self._status is SessionStatus.PAUSED else self._last_now_ns
            elapsed = max(0, clock_ns - self._segment_start_ns)
            progress = min(1.0, elapsed / duration_ns)
        manifest = self._manifest or {}
        return SessionSnapshot(
            session_id=manifest.get("session_id"),
            status=self._status,
            module_id=self._module_id,
            module_position=self._module_position,
            segment=self._segment,
            segment_progress=progress,
            session_elapsed_ns=self._session_elapsed_ns(),
            paused_duration_ns=self._paused_duration_ns(),
            last_control_seq=self._control_seq,
            runtime_mode=manifest.get("runtime_mode"),
            cue_mode=manifest.get("cue_mode"),
            protocol_config_hash=self.config.config_hash,
        )

    @property
    def control_log(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(deepcopy(self._control_log))

    @property
    def session_event_log(self) -> tuple[SessionEvent, ...]:
        return tuple(self._session_event_log)

    @property
    def audit_log(self) -> tuple[AuditRecord, ...]:
        return tuple(self._audit_log)

    def _validate_manifest_semantics(self, manifest: Mapping[str, Any]) -> None:
        if manifest["protocol_config_version"] != self.config.protocol_config_version:
            raise SessionCoreError(
                "PROTOCOL_CONFIG_VERSION_MISMATCH",
                str(manifest["protocol_config_version"]),
            )
        for segment in _SEGMENTS:
            value = float(manifest["module_durations"][segment])
            allowed = self.config.durations[segment]
            if not allowed.minimum_seconds <= value <= allowed.maximum_seconds:
                raise SessionCoreError("DURATION_OUT_OF_RANGE", segment)

        stage = str(manifest["study_stage"])
        arm = str(manifest["assignment_arm"])
        cue_mode = str(manifest["cue_mode"])
        strategy_version = manifest["strategy_version"]
        if stage in {"level_c", "stage_1"}:
            if arm != cue_mode:
                raise SessionCoreError("ASSIGNMENT_CUE_MISMATCH", f"{arm}:{cue_mode}")
            if strategy_version is not None:
                raise SessionCoreError("STRATEGY_VERSION_FORBIDDEN", stage)
        elif stage == "stage_3":
            if cue_mode != "scene_native":
                raise SessionCoreError("STAGE_3_SCENE_NATIVE_REQUIRED")
            if arm == "frozen_policy":
                raise SessionCoreError("ADAPTIVE_SEQUENCE_REQUIRES_V2_2")
            if arm != "balanced_random":
                raise SessionCoreError("STAGE_3_ARM_INVALID", arm)
            if strategy_version is not None:
                raise SessionCoreError("STRATEGY_VERSION_FORBIDDEN", arm)

    def _start_or_resume(
        self, request: OperatorRequest, now_ns: int
    ) -> CoreUpdate:
        if request.reason_code is not None:
            return self._reject_request(request, "START_REASON_FORBIDDEN", now_ns)
        if self._status is SessionStatus.PREPARED:
            if self._is_formal() and self._prepare_event_id not in self._acked_event_ids:
                return self._reject_request(request, "PREPARE_ACK_REQUIRED", now_ns)
            assert self._manifest is not None and self._assignment is not None
            try:
                exposure_receipt = self.dependencies.mark_exposed(
                    self._manifest, self._assignment
                )
            except SessionCoreError as error:
                return self._reject_request(request, error.code, now_ns)
            if self._is_formal() and not exposure_receipt.formal_capable:
                return self._reject_request(request, "FORMAL_EXPOSURE_GATE_UNAVAILABLE", now_ns)
            self._exposed = True

            before = self._status
            self._status = SessionStatus.RUNNING
            self._session_start_ns = now_ns
            self._module_position = 0
            decision = self.sequence_provider.next(0, self.snapshot())
            self._module_id = decision.module_id
            self._segment = "demo"
            self._segment_start_ns = now_ns
            self._segment_deadline_ns = now_ns + self._duration_ns("demo")

            controls = (
                self._make_control("start", now_ns, {"resumed": False}),
                self._make_control(
                    "module", now_ns, self._module_payload(decision)
                ),
                self._make_control(
                    "segment", now_ns, self._segment_payload(now_ns, now_ns, 0)
                ),
            )
            events = (
                self._make_session_event(
                    "session_started", now_ns, now_ns, before, self._status
                ),
                self._make_session_event(
                    "module_started", now_ns, now_ns, self._status, self._status
                ),
                self._make_session_event(
                    "segment_started", now_ns, now_ns, self._status, self._status
                ),
            )
            policies = () if decision.policy_decision is None else (decision.policy_decision,)
            return self._update(
                control_events=controls,
                session_events=events,
                policy_decisions=policies,
                gate_receipts=(exposure_receipt,),
            )

        if self._status is SessionStatus.PAUSED:
            assert self._pause_start_ns is not None
            paused_ns = now_ns - self._pause_start_ns
            self._total_paused_ns += paused_ns
            self._pause_start_ns = None
            assert self._segment_start_ns is not None and self._segment_deadline_ns is not None
            self._segment_start_ns += paused_ns
            self._segment_deadline_ns += paused_ns
            before = self._status
            self._status = SessionStatus.RUNNING
            control = self._make_control("start", now_ns, {"resumed": True})
            event = self._make_session_event(
                "session_resumed", now_ns, now_ns, before, self._status
            )
            return self._update(control_events=(control,), session_events=(event,))

        return self._reject_request(request, "ILLEGAL_TRANSITION", now_ns)

    def _pause(self, request: OperatorRequest, now_ns: int) -> CoreUpdate:
        if self._status is not SessionStatus.RUNNING:
            return self._reject_request(request, "ILLEGAL_TRANSITION", now_ns)
        reason = request.reason_code or "OPERATOR_PAUSE"
        if not self._reason_code_is_valid(reason):
            return self._reject_request(request, "INVALID_REASON_CODE", now_ns)
        before = self._status
        self._status = SessionStatus.PAUSED
        self._pause_start_ns = now_ns
        control = self._make_control("pause", now_ns, {"reason_code": reason})
        event = self._make_session_event(
            "session_paused", now_ns, now_ns, before, self._status, reason_code=reason
        )
        return self._update(control_events=(control,), session_events=(event,))

    def _abort_request(self, request: OperatorRequest, now_ns: int) -> CoreUpdate:
        if self._status not in {
            SessionStatus.PREPARED,
            SessionStatus.RUNNING,
            SessionStatus.PAUSED,
        }:
            return self._reject_request(request, "ILLEGAL_TRANSITION", now_ns)
        reason = request.reason_code or "OPERATOR_ABORT"
        if not self._reason_code_is_valid(reason):
            return self._reject_request(request, "INVALID_REASON_CODE", now_ns)
        return self._abort_internal(reason, now_ns)

    def _abort_internal(self, reason_code: str, now_ns: int) -> CoreUpdate:
        if self._status in {SessionStatus.COMPLETED, SessionStatus.ABORTED}:
            audit = self._audit("abort", "rejected", "TERMINAL_STATE", now_ns)
            return self._update(audit_records=(audit,))
        before = self._status
        if self._status is SessionStatus.PAUSED and self._pause_start_ns is not None:
            self._total_paused_ns += now_ns - self._pause_start_ns
            self._pause_start_ns = None
        self._status = SessionStatus.ABORTED
        self._finished_reason = reason_code
        control = self._make_control("abort", now_ns, {"reason_code": reason_code})
        event = self._make_session_event(
            "session_aborted",
            now_ns,
            now_ns,
            before,
            self._status,
            reason_code=reason_code,
        )
        return self._update(control_events=(control,), session_events=(event,))

    def _advance_boundary(
        self, scheduled_ns: int, observed_ns: int, lag_ns: int
    ) -> tuple[list[Mapping[str, Any]], list[SessionEvent], list[Mapping[str, Any]]]:
        assert self._segment is not None
        controls: list[Mapping[str, Any]] = []
        events: list[SessionEvent] = []
        decisions: list[Mapping[str, Any]] = []

        if self._segment == "demo":
            self._segment = "closed_loop"
            self._segment_start_ns = scheduled_ns
            self._segment_deadline_ns = scheduled_ns + self._duration_ns("closed_loop")
            controls.append(self._make_control(
                "segment", observed_ns, self._segment_payload(scheduled_ns, observed_ns, lag_ns)
            ))
            events.append(self._make_session_event(
                "segment_started", scheduled_ns, observed_ns, self._status, self._status,
                payload={"scheduler_lag_ns": lag_ns},
            ))
            return controls, events, decisions

        if self._segment == "closed_loop":
            self._segment = "lock_transition"
            self._segment_start_ns = scheduled_ns
            self._segment_deadline_ns = scheduled_ns + self._duration_ns("lock_transition")
            controls.append(self._make_control(
                "segment", observed_ns, self._segment_payload(scheduled_ns, observed_ns, lag_ns)
            ))
            events.append(self._make_session_event(
                "segment_started", scheduled_ns, observed_ns, self._status, self._status,
                payload={"scheduler_lag_ns": lag_ns},
            ))
            return controls, events, decisions

        assert self._module_id is not None and self._module_position is not None
        self._completed_modules.append(self._module_id)
        events.append(self._make_session_event(
            "module_completed", scheduled_ns, observed_ns, self._status, self._status,
            payload={"scheduler_lag_ns": lag_ns},
        ))
        if self._module_position == 3:
            self._segment_deadline_ns = None
            end_event = self._make_control(
                "end",
                observed_ns,
                {"reason_code": "COMPLETED", "scheduled_monotonic_ns": scheduled_ns},
            )
            self._end_event_id = str(end_event["event_id"])
            controls.append(end_event)
            return controls, events, decisions

        self._module_position += 1
        decision = self.sequence_provider.next(self._module_position, self.snapshot())
        self._module_id = decision.module_id
        self._segment = "demo"
        self._segment_start_ns = scheduled_ns
        self._segment_deadline_ns = scheduled_ns + self._duration_ns("demo")
        controls.extend((
            self._make_control("module", observed_ns, self._module_payload(decision)),
            self._make_control(
                "segment", observed_ns, self._segment_payload(scheduled_ns, observed_ns, lag_ns)
            ),
        ))
        events.extend((
            self._make_session_event(
                "module_started", scheduled_ns, observed_ns, self._status, self._status,
                payload={"scheduler_lag_ns": lag_ns},
            ),
            self._make_session_event(
                "segment_started", scheduled_ns, observed_ns, self._status, self._status,
                payload={"scheduler_lag_ns": lag_ns},
            ),
        ))
        if decision.policy_decision is not None:
            decisions.append(decision.policy_decision)
        return controls, events, decisions

    def _confirm_ack(self, ack: Mapping[str, Any], now_ns: int) -> CoreUpdate:
        event_id = str(ack["event_id"])
        if event_id not in self._control_by_id:
            audit = self._audit(event_id, "rejected", "UNKNOWN_CONTROL_EVENT", now_ns)
            return self._update(audit_records=(audit,))
        if event_id in self._acked_event_ids:
            audit = self._audit(event_id, "duplicate_ignored", "DUPLICATE_ACK", now_ns)
            return self._update(audit_records=(audit,))

        result = str(ack["result"])
        if result in {"applied", "duplicate_ignored"}:
            self._acked_event_ids.add(event_id)
            audit = self._audit(
                event_id,
                "applied" if result == "applied" else "duplicate_ignored",
                None if result == "applied" else str(ack["error_code"]),
                now_ns,
            )
            event = self._make_session_event(
                "control_acknowledged",
                now_ns,
                now_ns,
                self._status,
                self._status,
                payload={"control_event_id": event_id, "ack_result": result},
            )
            events = [event]
            control = self._control_by_id[event_id]
            if control["event_type"] == "end":
                before = self._status
                self._status = SessionStatus.COMPLETED
                self._finished_reason = "COMPLETED"
                events.append(
                    self._make_session_event(
                        "session_completed",
                        int(control["payload"]["scheduled_monotonic_ns"]),
                        now_ns,
                        before,
                        self._status,
                        reason_code="COMPLETED",
                    )
                )
            return self._update(session_events=tuple(events), audit_records=(audit,))

        reason = str(ack["error_code"] or "CONTROL_ACK_FAILED")
        return self.transport_failure(reason, now_ns)

    def _confirm_receipt(
        self, receipt: Mapping[str, Any], now_ns: int
    ) -> CoreUpdate:
        receipt_id = str(receipt["receipt_id"])
        if receipt_id in self._receipt_ids:
            audit = self._audit(
                receipt_id, "duplicate_ignored", "DUPLICATE_RENDER_RECEIPT", now_ns
            )
            return self._update(audit_records=(audit,))
        event_id = str(receipt["event_id"])
        if event_id not in self._control_by_id:
            audit = self._audit(receipt_id, "rejected", "UNKNOWN_CONTROL_EVENT", now_ns)
            return self._update(audit_records=(audit,))
        if event_id not in self._acked_event_ids:
            audit = self._audit(
                receipt_id, "rejected", "CONTROL_NOT_ACKNOWLEDGED", now_ns
            )
            return self._update(audit_records=(audit,))
        control = self._control_by_id[event_id]
        if control["event_type"] != "segment":
            audit = self._audit(
                receipt_id, "rejected", "RENDER_RECEIPT_CONTROL_TYPE_INVALID", now_ns
            )
            return self._update(audit_records=(audit,))
        payload = control["payload"]
        if receipt["module_id"] != payload.get("module_id"):
            audit = self._audit(
                receipt_id, "rejected", "RENDER_RECEIPT_MODULE_MISMATCH", now_ns
            )
            return self._update(audit_records=(audit,))
        if receipt["segment"] != payload.get("segment"):
            audit = self._audit(
                receipt_id, "rejected", "RENDER_RECEIPT_SEGMENT_MISMATCH", now_ns
            )
            return self._update(audit_records=(audit,))
        self._receipt_ids.add(receipt_id)
        if receipt["result"] != "rendered":
            reason = str(receipt["error_code"] or "RENDER_NOT_CONFIRMED")
            return self.transport_failure(reason, now_ns)
        event = self._make_session_event(
            "render_receipt",
            int(receipt["rendered_monotonic_ns"]),
            now_ns,
            self._status,
            self._status,
            payload={
                "receipt_id": receipt_id,
                "control_event_id": event_id,
                "unity_frame": int(receipt["unity_frame"]),
            },
        )
        audit = self._audit(receipt_id, "applied", None, now_ns)
        return self._update(session_events=(event,), audit_records=(audit,))

    def _make_control(
        self, event_type: str, observed_ns: int, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        if self._manifest is None:
            raise SessionCoreError("SESSION_NOT_PREPARED")
        self._control_seq += 1
        event = {
            "schema_version": SCHEMA_VERSION,
            "message_type": "control_event",
            "session_id": self._manifest["session_id"],
            "event_id": f"{self._manifest['session_id']}:control:{self._control_seq:06d}",
            "control_seq": self._control_seq,
            "event_type": event_type,
            "issued_monotonic_ns": observed_ns,
            "effective_monotonic_ns": observed_ns,
            "clock_domain_id": f"python:{self._manifest['session_id']}",
            "payload": dict(payload),
        }
        validated = validate_message("control_event", event)
        self._control_log.append(validated)
        self._control_by_id[str(validated["event_id"])] = validated
        return validated

    def _make_session_event(
        self,
        event_type: str,
        scheduled_ns: int,
        observed_ns: int,
        state_before: SessionStatus,
        state_after: SessionStatus,
        *,
        reason_code: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> SessionEvent:
        if self._manifest is None:
            raise SessionCoreError("SESSION_NOT_PREPARED")
        self._session_event_seq += 1
        event = SessionEvent(
            event_schema_version="1.0",
            session_id=str(self._manifest["session_id"]),
            event_id=f"{self._manifest['session_id']}:session:{self._session_event_seq:06d}",
            event_seq=self._session_event_seq,
            event_type=event_type,
            scheduled_monotonic_ns=scheduled_ns,
            observed_monotonic_ns=observed_ns,
            state_before=state_before.value,
            state_after=state_after.value,
            module_position=self._module_position,
            module_id=self._module_id,
            segment=self._segment,
            reason_code=reason_code,
            payload=dict(payload or {}),
        )
        self._session_event_log.append(event)
        return event

    def _module_payload(self, decision: ModuleDecision) -> dict[str, Any]:
        return {
            "module_id": decision.module_id,
            "module_position": decision.position,
            "policy_decision_id": (
                None
                if decision.policy_decision is None
                else decision.policy_decision["decision_id"]
            ),
        }

    def _segment_payload(
        self, scheduled_ns: int, observed_ns: int, lag_ns: int
    ) -> dict[str, Any]:
        return {
            "module_id": self._module_id,
            "module_position": self._module_position,
            "segment": self._segment,
            "scheduled_monotonic_ns": scheduled_ns,
            "observed_monotonic_ns": observed_ns,
            "scheduler_lag_ns": lag_ns,
        }

    def _audit(
        self,
        event_id: str,
        result: str,
        reason_code: str | None,
        now_ns: int,
    ) -> AuditRecord:
        self._audit_seq += 1
        record = AuditRecord(
            audit_seq=self._audit_seq,
            event_id=event_id,
            result=result,
            reason_code=reason_code,
            observed_monotonic_ns=now_ns,
        )
        self._audit_log.append(record)
        return record

    def _reject_request(
        self, request: OperatorRequest, reason_code: str, now_ns: int
    ) -> CoreUpdate:
        audit = self._audit(request.request_id, "rejected", reason_code, now_ns)
        return self._update(audit_records=(audit,))

    def _update(
        self,
        *,
        control_events: tuple[Mapping[str, Any], ...] = (),
        session_events: tuple[SessionEvent, ...] = (),
        policy_decisions: tuple[Mapping[str, Any], ...] = (),
        audit_records: tuple[AuditRecord, ...] = (),
        gate_receipts: tuple[GateReceipt, ...] = (),
    ) -> CoreUpdate:
        return CoreUpdate(
            snapshot=self.snapshot(),
            control_events=control_events,
            session_events=session_events,
            policy_decisions=policy_decisions,
            audit_records=audit_records,
            gate_receipts=gate_receipts,
        )

    def _observe_time(self, now_ns: int) -> None:
        if isinstance(now_ns, bool) or not isinstance(now_ns, int) or now_ns < 0:
            raise SessionCoreError("INVALID_MONOTONIC_TIME")
        if now_ns < self._last_now_ns:
            self._audit("clock", "rejected", "NON_MONOTONIC_CLOCK", self._last_now_ns)
            raise SessionCoreError("NON_MONOTONIC_CLOCK")
        self._last_now_ns = now_ns

    def _require_status(self, expected: SessionStatus, action: str) -> None:
        if self._status is not expected:
            raise SessionCoreError("ILLEGAL_TRANSITION", f"{self._status.value}:{action}")

    def _require_session_match(self, message: Mapping[str, Any]) -> None:
        if self._manifest is None or message["session_id"] != self._manifest["session_id"]:
            raise SessionCoreError("SESSION_ID_MISMATCH")

    def _duration_ns(self, segment: str) -> int:
        assert self._manifest is not None
        return round(float(self._manifest["module_durations"][segment]) * 1_000_000_000)

    def _current_segment_duration_ns(self) -> int | None:
        if self._manifest is None or self._segment is None:
            return None
        return self._duration_ns(self._segment)

    def _session_elapsed_ns(self) -> int:
        if self._session_start_ns is None:
            return 0
        end_ns = self._pause_start_ns if self._status is SessionStatus.PAUSED else self._last_now_ns
        return max(0, end_ns - self._session_start_ns - self._total_paused_ns)

    def _paused_duration_ns(self) -> int:
        current = 0
        if self._status is SessionStatus.PAUSED and self._pause_start_ns is not None:
            current = self._last_now_ns - self._pause_start_ns
        return self._total_paused_ns + current

    def _is_formal(self) -> bool:
        return bool(
            self._manifest
            and str(self._manifest["runtime_mode"]).startswith("formal_")
        )

    def _validate_reason_code(self, reason_code: str) -> None:
        if not self._reason_code_is_valid(reason_code):
            raise SessionCoreError("INVALID_REASON_CODE")

    @staticmethod
    def _reason_code_is_valid(reason_code: str) -> bool:
        return isinstance(reason_code, str) and bool(_REASON_CODE.fullmatch(reason_code))
