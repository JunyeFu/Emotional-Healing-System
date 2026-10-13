from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping


MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from srp_session_core import AssignmentBundle, OperatorRequest, RuntimeDependencies, SessionCore
from srp_session_store import (
    DurableManifestStore,
    RecordingSessionCore,
    ReplayReader,
    SessionReplayer,
)
from srp_session_store.canonical import canonical_bytes, file_sha256


def _load_trace() -> dict[str, Any]:
    path = MODULE_ROOT / "srp_session_core" / "fixtures" / "golden" / "four-module-trace-v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _assignment(trace: Mapping[str, Any]) -> AssignmentBundle:
    source = trace["assignment"]
    return AssignmentBundle(
        allocation_index=int(source["allocation_index"]),
        randomization_list_hash=str(source["randomization_list_hash"]),
        weather_sequence=tuple(source["weather_sequence"]),
        policy_decisions=tuple(trace["policy_decisions"]),
        permit_id=source.get("permit_id"),
        reservation_id=source.get("reservation_id"),
    )


def _receipt_for(event: Mapping[str, Any], receipts: list[dict[str, Any]]) -> dict[str, Any] | None:
    for receipt in receipts:
        if receipt["event_id"] == event["event_id"]:
            return receipt
    return None


def build_archive(root: Path) -> dict[str, Any]:
    trace = _load_trace()
    manifest = trace["manifest"]
    store = DurableManifestStore.development(root)
    dependencies = RuntimeDependencies.development()
    dependencies.manifest_store = store
    inner = SessionCore(dependencies=dependencies)
    core = RecordingSessionCore(inner, store)
    controls: list[dict[str, Any]] = []
    ack_index = {item["event_id"]: item for item in trace["acks"]}
    receipts = list(trace["render_receipts"])

    def deliver(update, now_ns: int) -> None:
        for event in update.control_events:
            controls.append(dict(event))
            core.confirm_delivery(ack_index[event["event_id"]], now_ns)
            receipt = _receipt_for(event, receipts)
            if receipt is not None:
                core.confirm_delivery(receipt, now_ns)

    update = core.prepare(manifest, _assignment(trace), 0)
    deliver(update, 0)
    update = core.apply_operator_request(
        OperatorRequest("REQ-GOLDEN-START", "start"), 1_000_000_000
    )
    deliver(update, 1_000_000_000)
    now_ns = 1_000_000_000
    for _ in range(4):
        for seconds in (25, 150, 25):
            now_ns += seconds * 1_000_000_000
            update = core.advance(now_ns)
            deliver(update, now_ns)
    summary = core.finish("COMPLETED", now_ns)
    seal = store.archive.seal(summary, now_ns)
    archive_path = store.archive.path
    store.archive.close()
    reader = ReplayReader.open(root, manifest["session_id"])
    replay = SessionReplayer(reader).replay_core()
    return {
        "archive_path": archive_path,
        "control_count": len(controls),
        "ack_count": len(trace["acks"]),
        "render_receipt_count": len(trace["render_receipts"]),
        "session_event_count": len(inner.session_event_log),
        "l0_count": reader.verify().l0_count,
        "l1_count": reader.verify().l1_count,
        "seal_hash": seal.seal_hash,
        "final_state_hash": seal.final_state_hash,
        "replay_hash": replay.actual_final_hash,
        "replay_valid": replay.valid,
        "operation_count": replay.operation_count,
        "trace_hash": trace["trace_hash"],
    }


def main() -> int:
    expected_parent = (Path(__file__).with_name("fixtures") / "golden").resolve()
    output = expected_parent / "session-archive-v1"
    if output.exists():
        resolved = output.resolve()
        if resolved.parent != expected_parent or resolved.name != "session-archive-v1":
            raise SystemExit("refusing to replace unexpected output path")
        shutil.rmtree(resolved)
    with tempfile.TemporaryDirectory(prefix="p02-golden-") as temporary:
        root = Path(temporary)
        evidence = build_archive(root)
        archive_path = Path(evidence.pop("archive_path"))
        target_archive = output / "sessions" / archive_path.name
        target_archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(archive_path, target_archive)
        lock = target_archive / "writer.lock"
        if lock.exists():
            lock.unlink()
        evidence["files"] = [
            {
                "path": path.relative_to(output).as_posix(),
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(target_archive.rglob("*"))
            if path.is_file()
        ]
        (output / "evidence.json").write_bytes(canonical_bytes(evidence) + b"\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
