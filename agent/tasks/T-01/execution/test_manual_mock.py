from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from manual_mock_service import ManualMockBridge


def status(stage='PREPARE', ready=False, pending=None, sid='DEV-manual-test'):
    return dict(message_type='td_mock_status', source_mode='dev_mock', session_id=sid,
                stage=stage, ready=ready, pending=pending, sealed=False, posttest=False)


def command(action):
    return dict(request_id=action, session_id='DEV-manual-test', source_mode='dev_mock', action=action)


def test_forged_waiting_status_cannot_start_unprepared_backend(tmp_path):
    messages = []
    bridge = ManualMockBridge(tmp_path, None, messages.append, clock=lambda: 0)
    try:
        bridge.on_status(status('WAITING', ready=True, pending=command('mock_start')))
        assert messages[-1]['event'] == 'request_rejected'
        assert bridge.backend.core.snapshot().status.value == 'CREATED'
        assert bridge.started_at is None
    finally:
        bridge.close()


def test_prepare_does_not_start_until_operator_clicks(tmp_path):
    messages = []
    clock = [0]
    bridge = ManualMockBridge(tmp_path, None, messages.append, clock=lambda: clock[0])
    try:
        bridge.on_status(status())
        assert messages[-1]['event'] == 'preparation_status'
        bridge.on_status(status(ready=True, pending=command('prepare')))
        assert bridge.backend.core.snapshot().status.value == 'PREPARED'
        clock[0] = 30_000_000_000
        bridge.on_status(status('WAITING', ready=True))
        assert bridge.backend.core.snapshot().status.value == 'PREPARED'
        bridge.on_status(status('WAITING', ready=True, pending=command('mock_start')))
        assert bridge.backend.core.snapshot().status.value == 'RUNNING'
        assert messages[-1]['event'] == 'started'
        assert messages[-1]['request_id'] == 'mock_start'
        clock[0] += 2_000_000_000
        bridge.on_status(status('RUNNING', ready=True, pending=command('pause')))
        assert bridge.backend.core.snapshot().status.value == 'PAUSED'
        elapsed = bridge.backend.core.snapshot().session_elapsed_ns
        clock[0] += 5_000_000_000
        bridge.on_status(status('PAUSED', ready=True, pending=command('resume')))
        assert bridge.backend.core.snapshot().session_elapsed_ns == elapsed
        clock[0] += 1_000_000_000
        bridge.on_status(status('RUNNING', ready=True, pending=command('abort')))
        assert bridge.backend.core.snapshot().status.value == 'ABORTED'
        assert bridge.sealed_report['replay']['valid']
        assert messages[-1]['sealed'] and not messages[-1]['posttest']
        bridge.on_status(status('CLOSEOUT', ready=True, pending=command('mock_posttest')))
        assert messages[-1]['posttest']
    finally:
        bridge.close()


def test_repeated_start_request_reuses_reply_without_restarting(tmp_path):
    messages = []
    bridge = ManualMockBridge(tmp_path, None, messages.append, clock=lambda: 0)
    try:
        bridge.on_status(status(ready=True, pending=command('prepare')))
        waiting = status('WAITING', ready=True, pending=command('mock_start'))
        bridge.on_status(waiting)
        reply = messages[-1]
        bridge.on_status(waiting)
        assert messages[-1] == reply
        assert bridge.backend.core.snapshot().status.value == 'RUNNING'
    finally:
        bridge.close()
