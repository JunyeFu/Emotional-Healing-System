from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_backend import DevelopmentBackend


@pytest.mark.parametrize('persistent', [False, True])
def test_windows_tail_replacement_contention(tmp_path, monkeypatch, persistent):
    from srp_session_store import archive, StoreError
    target = tmp_path / 'tail.json'
    original = archive.os.replace
    calls = []
    def replace(source, destination):
        calls.append(source)
        if persistent or len(calls) == 1:
            error = PermissionError('temporary Windows contention')
            error.winerror = 5
            raise error
        original(source, destination)
    monkeypatch.setattr(archive.os, 'replace', replace)
    monkeypatch.setattr(archive.time, 'sleep', lambda _: None)
    if persistent:
        with pytest.raises(StoreError, match='STORAGE_SYNC_FAILED'):
            archive._atomic_json(target, {'seq': 1})
        assert len(calls) == 3 and not target.exists()
    else:
        archive._atomic_json(target, {'seq': 1})
        assert len(calls) == 2 and target.read_text().strip() == '{"seq":1}'


def test_digest_digits_are_not_contact_but_contact_fields_stay_blocked():
    from srp_session_store.privacy import privacy_lint
    from srp_session_store import StoreError
    digest = 'sha256:' + 'a' * 20 + '13800138000' + 'b' * 33
    privacy_lint({'output_hash': digest})
    for payload in ({'phone': digest}, {'output_hash': digest + ' 13800138000'},
                    {'note': '13800138000'}):
        with pytest.raises(StoreError):
            privacy_lint(payload)


def request(b, action, now, request_id=None):
    return b.request(dict(session_id=b.session_id, source_mode='dev_mock',
                          action=action, request_id=request_id or action), now)


def test_real_core_store_full_pause_and_replay(tmp_path):
    b = DevelopmentBackend(tmp_path, 'DEV-test-full')
    try:
        assert request(b, 'prepare', 0)['event'] == 'prepared'
        assert not b.store.formal_capable
        assert b.start_from_simulated_unity(1_000_000_000)['event'] == 'started'
        assert request(b, 'pause', 321_000_000_000)['event'] == 'paused'
        assert b.advance(326_000_000_000).session_elapsed_ns == 320_000_000_000
        assert request(b, 'resume', 331_000_000_000)['event'] == 'resumed'
        b.advance(810_000_000_000)
        with pytest.raises(ValueError, match='CORE_NOT_COMPLETED'):
            b.completed()
        b.advance(811_000_000_000)
        assert b.completed()['event'] == 'completed'
        report = b.seal()
        assert report['integrity']['valid'] and report['replay']['valid']
        assert report['summary']['session_elapsed_ns'] == 800_000_000_000
        assert report['summary']['paused_duration_ns'] == 10_000_000_000
    finally:
        b.close()


def test_two_sessions_abort_and_raw_payload(tmp_path):
    for sid in ('DEV-first','DEV-second'):
        b = DevelopmentBackend(tmp_path, sid)
        try:
            request(b, 'prepare', 0)
            b.start_from_simulated_unity(1_000_000_000)
            packet = dict(session_id=sid,source_mode='dev_mock',source_id='plux_respiban',
                          clock_domain_id='synthetic:source-time',packet_seq=0,samples=[None,.2])
            b.append_packet(packet, 1_000_000_000)
            assert request(b, 'abort', 401_000_000_000)['event'] == 'aborted'
            report = b.seal()
            assert report['integrity']['l0_count'] == 1
            assert report['summary']['status'] == 'ABORTED'
            assert report['replay']['valid']
        finally:
            b.close()


def test_reject_other_session_duplicate_and_new_b(tmp_path):
    with pytest.raises(ValueError, match='ADAPTIVE_B'):
        DevelopmentBackend(tmp_path, 'DEV-b', 'B')
    b = DevelopmentBackend(tmp_path, 'DEV-invalid')
    try:
        with pytest.raises(ValueError, match='IDENTITY'):
            b.request(dict(session_id='other',source_mode='dev_mock',action='prepare'),0)
        request(b, 'prepare', 0)
        assert request(b, 'prepare', 0)['event'] == 'request_rejected'
        b.start_from_simulated_unity(1_000_000_000)
        assert request(b, 'pause', 2_000_000_000)['event'] == 'paused'
        assert request(b, 'pause', 2_000_000_000)['event'] == 'request_rejected'
        with pytest.raises(ValueError, match='SEAL_STATE'):
            b.seal()
    finally:
        b.close()


def test_storage_error_propagates_before_send(tmp_path, monkeypatch):
    b = DevelopmentBackend(tmp_path, 'DEV-storage')
    try:
        request(b, 'prepare', 0)
        b.start_from_simulated_unity(1_000_000_000)
        def fail(packet):
            raise OSError('disk full')
        monkeypatch.setattr(b.store.archive, 'append_raw_packet', fail)
        packet = dict(session_id=b.session_id,source_mode='dev_mock',source_id='polar_h10_ecg',
                      packet_seq=0,clock_domain_id='synthetic:source-time',samples=[1.])
        with pytest.raises(OSError, match='disk full'):
            b.append_packet(packet, 1_000_000_000)
        assert not b.sealed
    finally:
        b.close()
