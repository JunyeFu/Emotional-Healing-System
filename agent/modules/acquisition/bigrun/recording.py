"""P-02 storage adapter for device preflight, never a formal session host."""
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from srp_session_store import RawPacket, ReplayReader, SessionArchive
from .protocol import decode_packet

SCOPE = "DEVELOPMENT_UNVERIFIED"


class CandidateRecording:
    def __init__(self, root, session_id, source_policy, settings):
        self.seq = 0
        self.session_id = session_id
        self.counts = Counter()
        self.first_ns = None
        self.last_ns = None
        self.source_policy = source_policy
        self.archive = SessionArchive.create(
            Path(root),
            {"session_id": session_id, "source_policy": source_policy,
             "runtime_mode": "device_preflight", "evidence_scope": SCOPE,
             "created_utc": datetime.now(timezone.utc).isoformat(),
             "device_settings": settings,
             "unverified": ["firmware_protocol", "ecg_acc_concurrency", "rr_units",
                            "device_clock", "sample_rates", "respiration_events"]},
            protocol_config_hash="bigrun-reverse-candidate-not-formal",
        )
        self.path = self.archive.path

    def record(self, raw, received_ns):
        packet = decode_packet(raw)
        self.seq += 1
        self.counts[packet.kind] += 1
        if self.first_ns is None:
            self.first_ns = received_ns
        self.last_ns = received_ns
        if packet.kind in {"ecg", "acc", "rr", "hr"} and packet.samples:
            self.archive.append_raw_packet(RawPacket(
                source_id=f"bigrun_team_{packet.kind}", source_policy=self.source_policy,
                packet_seq=self.seq, device_time_ns=None,
                host_received_monotonic_ns=received_ns,
                clock_domain_id="bigrun:device-clock-unavailable",
                sample_count=len(packet.samples), payload=bytes(raw),
            ))
        else:
            self.archive.append_l1("bigrun_notification", {
                "packet_seq": self.seq, "raw_hex": bytes(raw).hex(),
                "decoded_kind": packet.kind, "metadata": packet.metadata,
            }, received_ns)
        return packet

    def connection_status(self, phase, error=None):
        self.archive.append_l1("bigrun_connection", {
            "phase": phase, "error": error, "automatic_resume": False,
        }, time.monotonic_ns())

    def close(self, status):
        now = time.monotonic_ns()
        try:
            self.archive.seal({
                "status": status, "reason_code": "DEVICE_PREFLIGHT_ENDED",
                "evidence_scope": SCOPE, "packet_counts": dict(self.counts),
                "first_received_ns": self.first_ns, "last_received_ns": self.last_ns,
                "real_device_acceptance": "NOT_RUN",
            }, now)
        finally:
            self.archive.close()


def open_recording(path):
    path = Path(path)
    envelope = json.loads((path / "archive.json").read_text(encoding="utf-8"))
    reader = ReplayReader.open(path.parent.parent, envelope["manifest"]["session_id"])
    report = reader.verify()
    if not report.valid:
        raise ValueError(f"ARCHIVE_NOT_VERIFIED: {report.reason_codes}")
    return reader


def export_recording(path, destination, ecg_hz, acc_hz):
    """Nominal sample-index timing only; no invented device timestamps/gap repair."""
    reader = open_recording(path)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    packets = list(reader.iter_l0())
    origin = min((p.host_received_monotonic_ns for p in packets), default=0)
    rows = {kind: [] for kind in ("ecg", "acc", "rr", "hr")}
    anchors = {}
    counts = Counter()
    for raw in packets:
        if raw.payload is None:
            continue
        packet = decode_packet(raw.payload)
        kind = packet.kind
        rate = {"ecg": ecg_hz, "acc": acc_hz}.get(kind)
        received_s = (raw.host_received_monotonic_ns - origin) / 1e9
        if rate:
            anchors.setdefault(kind, received_s - (len(packet.samples) - 1) / rate)
        for sample in packet.samples:
            index = counts[kind]
            estimated_s = anchors[kind] + index / rate if rate else received_s
            values = sample if kind == "acc" else (sample,)
            rows[kind].append((estimated_s, *values, raw.packet_seq, received_s,
                               packet.metadata.get("device_seq", "")))
            counts[kind] += 1
    for kind, data in rows.items():
        columns = ["time_s", *( ["x", "y", "z"] if kind == "acc" else ["value"]),
                   "packet_seq", "received_s", "device_seq"]
        with (destination / f"{kind}.csv").open("x", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(data)
    metadata = {
        "evidence_scope": SCOPE, "sample_counts": dict(counts),
        "ecg_hz_nominal": ecg_hz, "acc_hz_nominal": acc_hz,
        "timing": "NOMINAL_SAMPLE_INDEX_UNVERIFIED_NO_GAP_RECONSTRUCTION",
        "rr_time_s": "packet reception, NOT per-beat timestamps",
        "ecg_acc_units": "raw ADC counts; physical conversion unverified",
        "source_policy": reader.envelope["manifest"]["source_policy"],
    }
    (destination / "export.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def inspect_recording(path):
    reader = open_recording(path)
    stats, bins = {}, {"ecg": set(), "acc": set()}
    for raw in reader.iter_l0():
        kind = raw.source_id.removeprefix("bigrun_team_")
        item = stats.setdefault(kind, {"packets": 0, "samples": 0,
                                       "first_ns": raw.host_received_monotonic_ns,
                                       "first_batch_samples": raw.sample_count})
        item["packets"] += 1
        item["samples"] += raw.sample_count
        item["last_ns"] = raw.host_received_monotonic_ns
        if kind in bins:
            bins[kind].add(raw.host_received_monotonic_ns // 1_000_000_000)
    for item in stats.values():
        elapsed = (item["last_ns"] - item["first_ns"]) / 1e9
        item["host_rate_estimate_hz"] = ((item["samples"] - item["first_batch_samples"]) / elapsed
                                           if elapsed > 0 else None)
    return {"evidence_scope": SCOPE, "streams": stats,
            "seconds_bins_with_both_ecg_and_acc": len(bins["ecg"] & bins["acc"]),
            "unknown_or_config_notifications": sum(1 for _ in reader.iter_l1("bigrun_notification")),
            "rates_are": "HOST_ESTIMATES_NOT_DEVICE_CLOCK_VERIFICATION",
            "real_device_acceptance": "NOT_RUN"}
