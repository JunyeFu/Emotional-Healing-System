from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from srp_session_store import (
    RawPacket,
    ReplayReader,
    SessionArchive,
    StoreError,
    load_store_config,
)


def create_archive(tmp_path: Path, manifest: dict) -> SessionArchive:
    return SessionArchive.create(
        tmp_path,
        manifest,
        protocol_config_hash="sha256:protocol",
        store_config=load_store_config(),
    )


def test_manifest_is_exclusive_and_session_id_is_not_used_as_a_path(tmp_path, manifest_factory):
    manifest = manifest_factory(session_id="../../unsafe/session")
    archive = create_archive(tmp_path, manifest)
    assert archive.path.parent == tmp_path / "sessions"
    assert archive.path.name != manifest["session_id"]
    assert len(archive.path.name) == 64
    archive.close()

    with pytest.raises(StoreError, match="SESSION_ALREADY_EXISTS"):
        create_archive(tmp_path, manifest)


def test_l0_round_trip_preserves_bytes_and_missing_reason(tmp_path, manifest_factory):
    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    first = RawPacket(
        source_id="plux_respiban",
        source_policy="replay",
        packet_seq=1,
        device_time_ns=12,
        host_received_monotonic_ns=100,
        clock_domain_id="device:resp",
        sample_count=4,
        payload=b"\x00\x01\xfe\xff",
    )
    second = RawPacket(
        source_id="polar_h10_ecg",
        source_policy="replay",
        packet_seq=1,
        device_time_ns=None,
        host_received_monotonic_ns=200,
        clock_domain_id="device:ecg",
        sample_count=0,
        payload=None,
        missing_reason_code="DEVICE_GAP",
    )
    archive.append_raw_packet(first)
    archive.append_raw_packet(second)
    archive.seal({"status": "ABORTED", "reason_code": "TEST"}, 300)
    archive.close()

    reader = ReplayReader.open(tmp_path, manifest["session_id"])
    assert reader.verify().valid
    packets = list(reader.iter_l0())
    assert packets == [first, second]


@pytest.mark.parametrize(
    "packet",
    [
        RawPacket("source", "replay", 0, None, 1, "clock", 1, None, None),
        RawPacket("source", "replay", 0, None, 1, "clock", 0, b"", "GAP"),
    ],
)
def test_missing_packet_requires_null_payload_and_reason(packet, tmp_path, manifest_factory):
    archive = create_archive(tmp_path, manifest_factory())
    with pytest.raises(StoreError, match="RAW_PACKET_INVALID"):
        archive.append_raw_packet(packet)
    archive.close()


def test_hash_chain_detects_rewrite(tmp_path, manifest_factory):
    archive = create_archive(tmp_path, manifest_factory())
    archive.append_l1("clock_sync", {"offset_ns": 2, "uncertainty_ns": 4}, 10)
    archive.seal({"status": "COMPLETED"}, 20)
    archive.close()

    segment = archive.path / "l1" / "segment-000001.jsonl"
    data = segment.read_bytes()
    segment.write_bytes(data.replace(b'"offset_ns":2', b'"offset_ns":3', 1))
    report = ReplayReader.open(tmp_path, manifest_factory()["session_id"]).verify()
    assert not report.valid
    assert "INTEGRITY_MISMATCH" in report.reason_codes


def test_sealed_archive_rejects_append(tmp_path, manifest_factory):
    archive = create_archive(tmp_path, manifest_factory())
    archive.seal({"status": "COMPLETED"}, 10)
    with pytest.raises(StoreError, match="SESSION_SEALED"):
        archive.append_l1("clock_sync", {"offset_ns": 0}, 11)
    archive.close()


def test_recovery_keeps_old_segments_byte_identical(tmp_path, manifest_factory):
    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.append_l1("clock_sync", {"offset_ns": 1}, 10)
    segment = archive.path / "l1" / "segment-000001.jsonl"
    archive.close()
    old_bytes = segment.read_bytes()

    seal = SessionArchive.recover_interrupted(
        tmp_path,
        manifest["session_id"],
        now_ns=20,
    )
    assert seal.reason_code == "PROCESS_INTERRUPTED"
    assert segment.read_bytes() == old_bytes
    report = ReplayReader.open(tmp_path, manifest["session_id"]).verify()
    assert report.valid
    assert report.sealed


def test_recovery_rejects_modified_unsealed_archive_envelope(
    tmp_path, manifest_factory
):
    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.close()
    envelope_path = archive.path / "archive.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope["protocol_config_hash"] = "sha256:modified"
    envelope_path.write_text(json.dumps(envelope), encoding="utf-8")

    report = ReplayReader.open(tmp_path, manifest["session_id"]).verify(mode="recover")

    assert not report.valid
    assert not report.recoverable
    assert "INTEGRITY_MISMATCH" in report.reason_codes


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(extra_field="unexpected"),
        lambda value: value.pop("protocol_config_hash"),
        lambda value: value.update(archive_schema_version="2.0"),
        lambda value: value.update(formal_capable="false"),
    ],
)
def test_self_consistent_archive_envelope_schema_mutation_is_rejected(
    mutation, tmp_path, manifest_factory
):
    from srp_session_store.archive import _ENVELOPE_DOMAIN
    from srp_session_store.canonical import canonical_bytes, domain_hash

    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.close()
    envelope_path = archive.path / "archive.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    mutation(envelope)
    body = {key: value for key, value in envelope.items() if key != "envelope_hash"}
    envelope["envelope_hash"] = domain_hash(_ENVELOPE_DOMAIN, body)
    envelope_path.write_bytes(canonical_bytes(envelope) + b"\n")

    report = ReplayReader.open(tmp_path, manifest["session_id"]).verify(mode="recover")
    assert not report.valid
    assert "INTEGRITY_MISMATCH" in report.reason_codes


def test_non_object_archive_envelope_maps_to_store_error(tmp_path, manifest_factory):
    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.close()
    (archive.path / "archive.json").write_text("[]\n", encoding="utf-8")

    with pytest.raises(StoreError, match="INTEGRITY_MISMATCH"):
        ReplayReader.open(tmp_path, manifest["session_id"])


def test_recovery_rechecks_archive_after_acquiring_writer_lock(
    tmp_path, manifest_factory, monkeypatch
):
    import srp_session_store.archive as archive_module

    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.append_l1("clock_sync", {"offset_ns": 1}, 10)
    archive.close()
    existing_segments = {
        path.relative_to(archive.path).as_posix(): path.read_bytes()
        for path in archive.path.glob("*/*.jsonl")
    }
    original_acquire = archive_module._WriterLock.acquire

    def seal_before_lock(self):
        (self.path.parent / "seal.json").write_text("{}\n", encoding="utf-8")
        original_acquire(self)

    monkeypatch.setattr(archive_module._WriterLock, "acquire", seal_before_lock)

    with pytest.raises(StoreError, match="INTEGRITY_MISMATCH"):
        SessionArchive.recover_interrupted(
            tmp_path, manifest["session_id"], now_ns=20
        )

    current_segments = {
        path.relative_to(archive.path).as_posix(): path.read_bytes()
        for path in archive.path.glob("*/*.jsonl")
    }
    assert current_segments == existing_segments


def test_partial_tail_is_preserved_and_acknowledged_by_recovery(tmp_path, manifest_factory):
    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.append_l1("clock_sync", {"offset_ns": 1}, 10)
    segment = archive.path / "l1" / "segment-000001.jsonl"
    archive.close()
    with segment.open("ab") as handle:
        handle.write(b'{"partial":')
    old_bytes = segment.read_bytes()

    SessionArchive.recover_interrupted(tmp_path, manifest["session_id"], now_ns=20)
    assert segment.read_bytes() == old_bytes
    report = ReplayReader.open(tmp_path, manifest["session_id"]).verify()
    assert report.valid
    assert "UNCLEAN_TAIL" in report.reason_codes


def test_partial_tail_in_nonfinal_segment_is_not_recoverable(tmp_path, manifest_factory):
    config = replace(load_store_config(), segment_max_bytes=350)
    manifest = manifest_factory()
    archive = SessionArchive.create(
        tmp_path,
        manifest,
        protocol_config_hash="sha256:protocol",
        store_config=config,
    )
    for index in range(5):
        archive.append_l1("clock_sync", {"offset_ns": index}, index + 1)
    archive.close()
    segments = sorted((archive.path / "l1").glob("segment-*.jsonl"))
    assert len(segments) > 1
    with segments[0].open("ab") as handle:
        handle.write(b'{"partial":')

    report = ReplayReader.open(tmp_path, manifest["session_id"]).verify(mode="recover")
    assert not report.valid
    assert "INTEGRITY_MISMATCH" in report.reason_codes


def test_deleting_last_durable_l1_record_breaks_tail_anchor(tmp_path, manifest_factory):
    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.append_l1("clock_sync", {"offset_ns": 1}, 1)
    archive.close()
    segment = archive.path / "l1" / "segment-000001.jsonl"
    segment.write_bytes(b"")

    report = ReplayReader.open(tmp_path, manifest["session_id"]).verify(mode="recover")
    assert not report.valid
    assert "INTEGRITY_MISMATCH" in report.reason_codes


def test_recovery_failure_restores_all_files(tmp_path, manifest_factory):
    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.append_l1("clock_sync", {"offset_ns": 1}, 1)
    archive.checkpoint(2)
    archive.checkpoint(3)
    archive.close()
    (archive.path / "checkpoints" / "checkpoint-000001.json").unlink()
    before = {
        path.relative_to(archive.path).as_posix(): path.read_bytes()
        for path in archive.path.rglob("*")
        if path.is_file() and path.name != "writer.lock"
    }

    with pytest.raises(StoreError, match="INTEGRITY_MISMATCH"):
        SessionArchive.recover_interrupted(tmp_path, manifest["session_id"], now_ns=4)

    after = {
        path.relative_to(archive.path).as_posix(): path.read_bytes()
        for path in archive.path.rglob("*")
        if path.is_file() and path.name != "writer.lock"
    }
    assert after == before


def test_recovery_sync_failure_cannot_skip_baseline_rollback(
    tmp_path, manifest_factory, monkeypatch
):
    import srp_session_store.archive as archive_module

    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.append_l1("clock_sync", {"offset_ns": 1}, 1)
    archive.close()
    before = {
        path.relative_to(archive.path).as_posix(): path.read_bytes()
        for path in archive.path.rglob("*")
        if path.is_file() and path.name != "writer.lock"
    }

    def fail_atomic(*_args, **_kwargs):
        raise StoreError("STORAGE_SYNC_FAILED")

    monkeypatch.setattr(archive_module, "_atomic_json", fail_atomic)
    with pytest.raises(StoreError, match="STORAGE_SYNC_FAILED"):
        SessionArchive.recover_interrupted(tmp_path, manifest["session_id"], now_ns=2)

    after = {
        path.relative_to(archive.path).as_posix(): path.read_bytes()
        for path in archive.path.rglob("*")
        if path.is_file() and path.name != "writer.lock"
    }
    assert after == before


def test_recovery_missing_session_maps_to_store_error(tmp_path):
    with pytest.raises(StoreError, match="ARCHIVE_UNAVAILABLE"):
        SessionArchive.recover_interrupted(tmp_path, "S-MISSING", now_ns=1)


def test_active_writer_blocks_recovery(tmp_path, manifest_factory):
    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    with pytest.raises(StoreError, match="SESSION_WRITER_LOCKED"):
        SessionArchive.recover_interrupted(tmp_path, manifest["session_id"], now_ns=20)
    archive.close()


def test_packet_sequence_and_source_policy_fail_closed(tmp_path, manifest_factory):
    archive = create_archive(tmp_path, manifest_factory())
    packet = RawPacket("plux_respiban", "replay", 1, None, 1, "clock", 1, b"x")
    archive.append_raw_packet(packet)
    with pytest.raises(StoreError, match="NON_MONOTONIC_PACKET_SEQUENCE"):
        archive.append_raw_packet(packet)
    with pytest.raises(StoreError, match="SOURCE_POLICY_MISMATCH"):
        archive.append_raw_packet(
            RawPacket("polar_h10_ecg", "mock", 1, None, 2, "clock", 1, b"x")
        )
    archive.close()


def test_privacy_fields_are_rejected_without_echoing_value(tmp_path, manifest_factory):
    archive = create_archive(tmp_path, manifest_factory())
    with pytest.raises(StoreError) as captured:
        archive.append_l1("storage_event", {"phone": "+8613900000000"}, 10)
    assert captured.value.code == "PRIVACY_FORBIDDEN"
    assert "+8613900000000" not in str(captured.value)
    archive.close()


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "subject_token",
        "participant_hmac_sha256",
        "api_key",
        "credential",
        "recruitment_reference",
        "identity_mapping_id",
        "identity_map_id",
    ],
)
def test_p02_specific_privacy_fields_are_rejected(
    forbidden_key, tmp_path, manifest_factory
):
    archive = create_archive(tmp_path, manifest_factory())
    with pytest.raises(StoreError, match="PRIVACY_FORBIDDEN") as captured:
        archive.append_l1("storage_event", {forbidden_key: "opaque"}, 10)
    assert forbidden_key not in str(captured.value)
    archive.close()


def test_privacy_error_path_does_not_echo_dynamic_key(tmp_path, manifest_factory):
    archive = create_archive(tmp_path, manifest_factory())
    dynamic_key = "phone_+8613800138000"
    with pytest.raises(StoreError) as captured:
        archive.append_l1("storage_event", {dynamic_key: "opaque"}, 10)
    assert "+8613800138000" not in str(captured.value)
    archive.close()


def test_segment_rollover_preserves_one_hash_chain(tmp_path, manifest_factory):
    config = replace(load_store_config(), segment_max_bytes=350)
    archive = SessionArchive.create(
        tmp_path,
        manifest_factory(),
        protocol_config_hash="sha256:protocol",
        store_config=config,
    )
    for index in range(4):
        archive.append_l1("clock_sync", {"offset_ns": index}, index + 1)
    archive.seal({"status": "COMPLETED"}, 10)
    archive.close()
    assert len(list((archive.path / "l1").glob("segment-*.jsonl"))) > 1
    assert ReplayReader.open(tmp_path, manifest_factory()["session_id"]).verify().valid


def test_segment_filename_gap_is_rejected(tmp_path, manifest_factory):
    config = replace(load_store_config(), segment_max_bytes=350)
    manifest = manifest_factory()
    archive = SessionArchive.create(
        tmp_path,
        manifest,
        protocol_config_hash="sha256:protocol",
        store_config=config,
    )
    for index in range(5):
        archive.append_l1("clock_sync", {"offset_ns": index}, index + 1)
    archive.close()
    segments = sorted((archive.path / "l1").glob("segment-*.jsonl"))
    assert len(segments) > 1
    segments[1].rename(segments[1].with_name("segment-999999.jsonl"))

    report = ReplayReader.open(tmp_path, manifest["session_id"]).verify(mode="recover")
    assert not report.valid
    assert "INTEGRITY_MISMATCH" in report.reason_codes


def test_checkpoint_rewrite_is_detected(tmp_path, manifest_factory):
    archive = create_archive(tmp_path, manifest_factory())
    archive.checkpoint(1)
    archive.seal({"status": "COMPLETED"}, 2)
    archive.close()
    checkpoint = archive.path / "checkpoints" / "checkpoint-000001.json"
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["l0_seq"] = 99
    checkpoint.write_text(json.dumps(payload), encoding="utf-8")
    assert not ReplayReader.open(tmp_path, manifest_factory()["session_id"]).verify().valid


def test_self_consistent_checkpoint_with_wrong_chain_tail_is_detected(
    tmp_path, manifest_factory
):
    from srp_session_store.archive import _CHECKPOINT_DOMAIN
    from srp_session_store.canonical import canonical_bytes, domain_hash

    archive = create_archive(tmp_path, manifest_factory())
    archive.append_l1("clock_sync", {"offset_ns": 1}, 1)
    archive.checkpoint(2)
    archive.close()

    checkpoint = archive.path / "checkpoints" / "checkpoint-000001.json"
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["l1_tail_hash"] = "sha256:" + "f" * 64
    body = {key: value for key, value in payload.items() if key != "checkpoint_hash"}
    payload["checkpoint_hash"] = domain_hash(_CHECKPOINT_DOMAIN, body)
    checkpoint.write_bytes(canonical_bytes(payload))

    report = ReplayReader.open(tmp_path, manifest_factory()["session_id"]).verify(
        mode="recover"
    )
    assert not report.valid
    assert "INTEGRITY_MISMATCH" in report.reason_codes


def test_self_consistent_seal_with_wrong_declared_tail_is_detected(
    tmp_path, manifest_factory
):
    from srp_session_store.archive import _SEAL_DOMAIN
    from srp_session_store.canonical import canonical_bytes, domain_hash

    archive = create_archive(tmp_path, manifest_factory())
    archive.append_l1("clock_sync", {"offset_ns": 1}, 1)
    archive.seal({"status": "COMPLETED"}, 2)
    archive.close()

    seal_path = archive.path / "seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["l1_tail_hash"] = "sha256:" + "f" * 64
    body = {key: value for key, value in seal.items() if key != "seal_hash"}
    seal["seal_hash"] = domain_hash(_SEAL_DOMAIN, body)
    seal_path.write_bytes(canonical_bytes(seal) + b"\n")

    assert not ReplayReader.open(tmp_path, manifest_factory()["session_id"]).verify().valid


def test_self_consistent_seal_with_wrong_reason_is_detected(
    tmp_path, manifest_factory
):
    from srp_session_store.archive import _SEAL_DOMAIN
    from srp_session_store.canonical import canonical_bytes, domain_hash

    archive = create_archive(tmp_path, manifest_factory())
    archive.seal({"status": "COMPLETED"}, 2)
    archive.close()
    seal_path = archive.path / "seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["reason_code"] = "WRONG_REASON"
    body = {key: value for key, value in seal.items() if key != "seal_hash"}
    seal["seal_hash"] = domain_hash(_SEAL_DOMAIN, body)
    seal_path.write_bytes(canonical_bytes(seal) + b"\n")
    assert not ReplayReader.open(tmp_path, manifest_factory()["session_id"]).verify().valid


def test_self_consistent_seal_with_non_object_file_entry_is_rejected(
    tmp_path, manifest_factory
):
    from srp_session_store.archive import _SEAL_DOMAIN
    from srp_session_store.canonical import canonical_bytes, domain_hash

    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.seal({"status": "COMPLETED"}, 2)
    archive.close()
    seal_path = archive.path / "seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["files"] = [1]
    body = {key: value for key, value in seal.items() if key != "seal_hash"}
    seal["seal_hash"] = domain_hash(_SEAL_DOMAIN, body)
    seal_path.write_bytes(canonical_bytes(seal) + b"\n")

    report = ReplayReader.open(tmp_path, manifest["session_id"]).verify()
    assert not report.valid
    assert "INTEGRITY_MISMATCH" in report.reason_codes


def test_checkpoint_time_and_sequences_must_be_monotonic(tmp_path, manifest_factory):
    from srp_session_store.archive import _CHECKPOINT_DOMAIN
    from srp_session_store.canonical import canonical_bytes, domain_hash

    manifest = manifest_factory()
    archive = create_archive(tmp_path, manifest)
    archive.append_l1("clock_sync", {"offset_ns": 1}, 1)
    archive.checkpoint(2)
    archive.append_l1("clock_sync", {"offset_ns": 2}, 3)
    archive.checkpoint(4)
    archive.close()
    checkpoint = archive.path / "checkpoints" / "checkpoint-000002.json"
    value = json.loads(checkpoint.read_text(encoding="utf-8"))
    value["created_monotonic_ns"] = 1
    value["l1_seq"] = 0
    value["l1_tail_hash"] = "sha256:" + "0" * 64
    body = {key: item for key, item in value.items() if key != "checkpoint_hash"}
    value["checkpoint_hash"] = domain_hash(_CHECKPOINT_DOMAIN, body)
    checkpoint.write_bytes(canonical_bytes(value) + b"\n")

    report = ReplayReader.open(tmp_path, manifest["session_id"]).verify(mode="recover")
    assert not report.valid
    assert "INTEGRITY_MISMATCH" in report.reason_codes
