from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Mapping

from srp_session_core import AssignmentBundle, GateReceipt, OperatorRequest, SessionCore

from .archive import ReplayReader
from .canonical import domain_hash
from .errors import StoreError
from .models import ReplayReport
from .serialization import serialize_core_output


class _ReplayDependencies:
    def __init__(self, receipts: Mapping[str, list[Mapping[str, Any]]]) -> None:
        self.receipts = {name: deque(values) for name, values in receipts.items()}

    def _take(self, name: str) -> GateReceipt:
        try:
            value = self.receipts[name].popleft()
            if not isinstance(value, Mapping):
                raise TypeError
            gate = value["gate"]
            evidence_id = value["evidence_id"]
            formal_capable = value["formal_capable"]
            if not isinstance(gate, str) or not isinstance(evidence_id, str) or not isinstance(formal_capable, bool):
                raise TypeError
        except (KeyError, IndexError, TypeError) as error:
            raise StoreError("REPLAY_GATE_RECEIPT_MISSING", name) from error
        return GateReceipt(gate, evidence_id, formal_capable)

    def privacy_receipt(self, manifest, assignment, config_hash):
        del manifest, assignment, config_hash
        return self._take("privacy")

    def assignment_receipt(self, manifest, assignment, config_hash):
        del manifest, assignment, config_hash
        return self._take("assignment")

    def store_receipt(self, manifest, config_hash):
        del manifest, config_hash
        return self._take("manifest_store")

    def readiness_receipt(self, manifest, assignment, config_hash):
        del manifest, assignment, config_hash
        return self._take("formal_readiness")

    def mark_exposed(self, manifest, assignment):
        del manifest, assignment
        return self._take("exposure")


class SessionReplayer:
    def __init__(self, reader: ReplayReader) -> None:
        self.reader = reader

    def replay_core(
        self,
        core_factory: type[SessionCore] | None = None,
    ) -> ReplayReport:
        integrity = self.reader.verify()
        if not integrity.valid:
            raise StoreError("INTEGRITY_MISMATCH")
        begins: dict[str, dict[str, Any]] = {}
        commits: list[dict[str, Any]] = []
        failed: set[str] = set()
        for record in self.reader.iter_l1():
            payload = record.get("payload")
            if not isinstance(payload, dict):
                raise StoreError("REPLAY_RECORD_INVALID")
            if record["record_type"] == "operation_begin":
                operation_id = payload.get("operation_id")
                if (
                    not isinstance(operation_id, str)
                    or not operation_id
                    or not isinstance(payload.get("method"), str)
                    or not isinstance(payload.get("arguments"), dict)
                    or operation_id in begins
                ):
                    raise StoreError("REPLAY_RECORD_INVALID")
                begins[operation_id] = payload
            elif record["record_type"] == "operation_commit":
                if (
                    not isinstance(payload.get("operation_id"), str)
                    or not isinstance(payload.get("method"), str)
                    or not isinstance(payload.get("output"), dict)
                ):
                    raise StoreError("REPLAY_RECORD_INVALID")
                commits.append(payload)
            elif record["record_type"] == "operation_failed":
                operation_id = payload.get("operation_id")
                if not isinstance(operation_id, str) or not operation_id:
                    raise StoreError("REPLAY_RECORD_INVALID")
                failed.add(operation_id)
        committed = {item["operation_id"] for item in commits}
        incomplete = sorted(set(begins) - committed - failed)
        if incomplete:
            raise StoreError("INCOMPLETE_OPERATION", incomplete[0])
        receipts: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for commit in commits:
            output = commit["output"]
            if output.get("output_type") == "CoreUpdate":
                gate_receipts = output.get("gate_receipts", [])
                if not isinstance(gate_receipts, list):
                    raise StoreError("REPLAY_RECORD_INVALID")
                for receipt in gate_receipts:
                    if not isinstance(receipt, dict) or not isinstance(receipt.get("gate"), str):
                        raise StoreError("REPLAY_RECORD_INVALID")
                    receipts[receipt["gate"]].append(receipt)
        dependencies = _ReplayDependencies(receipts)
        if core_factory is not None and core_factory is not SessionCore:
            raise StoreError("REPLAY_CORE_UNSAFE")
        core = SessionCore(dependencies=dependencies)
        expected_outputs: list[dict[str, Any]] = []
        actual_outputs: list[dict[str, Any]] = []
        mismatches: list[str] = []
        for commit in commits:
            operation_id = str(commit["operation_id"])
            begin = begins.get(operation_id)
            if begin is None:
                raise StoreError("INCOMPLETE_OPERATION", operation_id)
            expected = commit["output"]
            try:
                actual_value = self._execute(core, begin["method"], begin["arguments"])
            except StoreError:
                raise
            except (KeyError, TypeError, ValueError) as error:
                raise StoreError("REPLAY_RECORD_INVALID", operation_id) from error
            actual = serialize_core_output(actual_value)
            expected_outputs.append(expected)
            actual_outputs.append(actual)
            if actual != expected:
                mismatches.append(operation_id)
        expected_hash = domain_hash(b"srp:p02:replay-result:v1\0", expected_outputs)
        actual_hash = domain_hash(b"srp:p02:replay-result:v1\0", actual_outputs)
        return ReplayReport(
            valid=not mismatches and expected_hash == actual_hash,
            operation_count=len(commits),
            expected_final_hash=expected_hash,
            actual_final_hash=actual_hash,
            mismatch_operation_ids=tuple(mismatches),
        )

    @staticmethod
    def _execute(core: Any, method: str, arguments: Mapping[str, Any]) -> Any:
        now_ns = int(arguments["now_ns"])
        if method == "prepare":
            assignment = arguments["assignment"]
            bundle = AssignmentBundle(
                allocation_index=int(assignment["allocation_index"]),
                randomization_list_hash=str(assignment["randomization_list_hash"]),
                weather_sequence=tuple(assignment["weather_sequence"]),
                policy_decisions=tuple(assignment["policy_decisions"]),
                permit_id=assignment.get("permit_id"),
                reservation_id=assignment.get("reservation_id"),
            )
            return core.prepare(arguments["manifest"], bundle, now_ns)
        if method == "apply_operator_request":
            request = arguments["request"]
            return core.apply_operator_request(
                OperatorRequest(
                    str(request["request_id"]),
                    str(request["action"]),
                    request.get("reason_code"),
                ),
                now_ns,
            )
        if method == "advance":
            return core.advance(now_ns)
        if method == "confirm_delivery":
            return core.confirm_delivery(arguments["message"], now_ns)
        if method == "transport_failure":
            return core.transport_failure(str(arguments["reason_code"]), now_ns)
        if method == "finish":
            return core.finish(str(arguments["reason_code"]), now_ns)
        raise StoreError("REPLAY_METHOD_UNSUPPORTED", method)
