"""Real-source wire shape with synthetic inputs and an in-memory socket only."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

MODULES = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODULES))
sys.path.insert(0, str(MODULES / 'acquisition'))
from bigrun.td_stream import TDPublisher
from bigrun.protocol import Packet


def test_publisher_preserves_all_xyz_and_sends_no_control(monkeypatch):
    from bigrun import td_stream
    sent = []
    class Socket:
        def sendto(self, data, peer): sent.append((json.loads(data), peer))
        def close(self): pass
    monkeypatch.setattr(td_stream.socket, 'socket', lambda *args: Socket())
    recording = SimpleNamespace(source_policy='real', session_id='SYNTHETIC', path=Path('synthetic'))
    pub = TDPublisher(recording, None, None)
    driver = SimpleNamespace(resp_estimator=None, is_connected=True)
    pub.packet(Packet('acc', ((1, 2, 3), (4, 5, 6))), 1000, driver, None)
    pub.status(driver, {'heart_rate_bpm':None})
    pub.close()
    assert sent[0][0]['samples'] == [[1, 2, 3], [4, 5, 6]]
    assert sent[0][0]['respiration_proxy'] == []
    assert sent[1][0]['formal_capable'] is False
    assert sent[1][0]['packet_seq'] == 2
    assert all(peer == ('127.0.0.1', 5005) and 'action' not in p for p, peer in sent)
    assert sent[1][0]['archive'] == 'synthetic'


def test_mock_recording_cannot_be_published_as_real():
    with pytest.raises(ValueError, match='REAL_SOURCE'):
        TDPublisher(SimpleNamespace(source_policy='mock'), 125, 25)
