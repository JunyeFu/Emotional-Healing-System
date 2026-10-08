"""Single-window development workflow. Authoritative confirmations enter as receipts."""
import json
import os
from pathlib import Path
import uuid


class Workflow:
    def __init__(self, root, capture_factory):
        self.root = Path(root)
        self.capture_factory = capture_factory
        self.capture = capture_factory(self.root / 'recordings')
        self.index = self.root / 'workflow.json'
        self.history = json.loads(self.index.read_text(encoding='utf-8')) if self.index.exists() else []
        self.current = None
        self.stage = 'HOME'
        self.view = None
        self.pending = None
        self.error = None
        self.seen = set()
        # A reopened application must not resume an interrupted participant experience.
        for item in self.history:
            if item['status'] in ('RECORDING', 'PAUSED', 'STARTED'):
                item.update(status='INTERRUPTED', sealed=False, closed=False)
        if self.history:
            self._save()

    def _save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        temp = self.index.with_suffix('.tmp')
        with temp.open('w', encoding='utf-8') as handle:
            json.dump(self.history, handle, ensure_ascii=False, allow_nan=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(self.index)

    def _request(self, action, now):
        if self.pending:
            raise ValueError('REQUEST_PENDING')
        request = dict(request_id=str(uuid.uuid4()), session_id=self.current['session_id'],
                       action=action, source_mode='dev_mock', requested_ns=now)
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / 'operator-requests.jsonl').open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(request) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        self.pending = request
        return request

    def new(self):
        if self.stage != 'HOME':
            raise ValueError('CLOSE_CURRENT_FIRST')
        self.current = dict(session_id='DEV-' + uuid.uuid4().hex[:16], participant='未分配', condition='未分配',
                            status='PREPARING', pretest=False, unity_ready=False, store_ready=False,
                            posttest=False, sealed=False, closed=False, path=None,
                            effective_ns=0, elapsed_ns=0, paused_ns=0, pause_at=None, start_ns=None,
                            end_ns=None, ideal='未接入', guide='未接入', actual='未接入')
        self.capture = self.capture_factory(self.root / 'recordings')
        self.stage, self.view, self.pending, self.error = 'PREPARE', None, None, None

    def action(self, action, now):
        self.error = None
        if action == 'new':
            self.new()
        elif action == 'history':
            self.view = 'HISTORY'
        elif action == 'back':
            self.view = None
        elif action == 'details':
            self.view = 'DETAILS'
        elif action == 'submit':
            if self.stage != 'PREPARE' or not self.ready:
                raise ValueError('PREPARATION_INCOMPLETE')
            self._request('prepare', now)
        elif action == 'cancel':
            if self.stage not in ('PREPARE', 'WAITING'):
                raise ValueError('CANNOT_CANCEL_ACTIVE_SESSION')
            self._request('cancel_prepare', now)
        elif action in ('pause', 'resume', 'abort'):
            expected = ('PAUSED',) if action == 'resume' else ('RUNNING',) if action == 'pause' else ('RUNNING', 'PAUSED')
            if self.stage not in expected:
                raise ValueError('CONTROL_STATE')
            self._request(action, now)
        elif action in ('next', 'home'):
            if self.stage != 'CLOSEOUT' or not self.can_close:
                raise ValueError('CLOSEOUT_INCOMPLETE')
            self.current['closed'] = True
            self._save()
            self.stage, self.view, self.pending = 'HOME', None, None
            self.current = None
            if action == 'next':
                self.new()
        else:
            raise ValueError('UNKNOWN_ACTION')

    @property
    def ready(self):
        c = self.current
        return bool(c and c['pretest'] and c['unity_ready'] and c['store_ready']
                    and c['participant'] != '未分配' and c['condition'] in ('A', 'B'))

    @property
    def can_close(self):
        return bool(self.current and self.current['sealed'] and self.current['posttest']
                    and self.current['status'] in ('COMPLETED', 'ABORTED'))

    def _match_request(self, p, action):
        if not self.pending or self.pending['action'] != action or p.get('request_id') != self.pending['request_id']:
            raise ValueError('REQUEST_RECEIPT_MISMATCH')

    def event(self, p, now):
        if p.get('message_type') != 'session_observation' or p.get('version') != '1.0':
            raise ValueError('SESSION_MESSAGE_VERSION')
        if p.get('source_mode') != 'dev_mock':
            raise ValueError('FORMAL_RECORDING_REQUIRES_P02_BRIDGE')
        if not self.current or p.get('session_id') != self.current['session_id']:
            raise ValueError('SESSION_MISMATCH')
        eid = p.get('event_id')
        if not isinstance(eid, str) or not eid:
            raise ValueError('EVENT_ID_REQUIRED')
        identity = (p['session_id'], eid)
        if identity in self.seen:
            return False
        if p.get('authority') != 'python_session_core':
            raise ValueError('CORE_CONFIRMATION_REQUIRED')
        c, event = self.current, p.get('event')
        if event == 'preparation_status':
            if self.stage != 'PREPARE' or self.pending:
                raise ValueError('PREPARATION_LOCKED')
            if p.get('condition') not in ('A', 'B') or not isinstance(p.get('participant'), str) or not p['participant']:
                raise ValueError('ASSIGNMENT_REQUIRED')
            for key in ('pretest', 'unity_ready', 'store_ready'):
                if type(p.get(key)) is not bool:
                    raise ValueError('PREPARATION_RECEIPT_REQUIRED')
            c.update({k: p[k] for k in ('condition','participant','pretest','unity_ready','store_ready')})
        elif event == 'prepared':
            self._match_request(p, 'prepare')
            if self.stage != 'PREPARE' or not self.ready:
                raise ValueError('PREPARATION_INCOMPLETE')
            self.stage, self.pending = 'WAITING', None
        elif event == 'cancelled':
            self._match_request(p, 'cancel_prepare')
            if self.stage not in ('PREPARE','WAITING'):
                raise ValueError('ALREADY_STARTED')
            self.stage, self.current, self.pending = 'HOME', None, None
        elif event == 'request_rejected':
            if not self.pending or p.get('request_id') != self.pending['request_id']:
                raise ValueError('REQUEST_RECEIPT_MISMATCH')
            self.pending = None
            self.error = 'REQUEST_REJECTED'
        elif event == 'unity_start_clicked':
            if self.stage != 'WAITING':
                raise ValueError('NOT_WAITING')
            self.capture.event(p, now)
        elif event == 'started':
            if self.stage != 'WAITING' or self.pending:
                raise ValueError('NOT_READY_TO_START')
            self.capture.event(p, now)
            c.update(status='RECORDING', start_ns=now, path=str(self.capture.path.relative_to(self.root)))
            self.history.append(c)
            self.stage = 'RUNNING'
            self._save()
        elif event in ('paused', 'resumed'):
            expected, action = ('RUNNING', 'pause') if event == 'paused' else ('PAUSED','resume')
            if self.stage != expected:
                raise ValueError('PAUSE_STATE')
            self._match_request(p, action)
            self.capture._write(event, p, now)
            if event == 'paused':
                c['pause_at'] = now
                self.stage, c['status'] = 'PAUSED', 'PAUSED'
            else:
                c['paused_ns'] += now - c['pause_at']
                c['pause_at'] = None
                self.stage, c['status'] = 'RUNNING', 'RECORDING'
            self.pending = None
        elif event in ('completed','aborted'):
            if self.stage not in ('RUNNING','PAUSED'):
                raise ValueError('NOT_RUNNING')
            if event == 'completed' and self.stage != 'RUNNING':
                raise ValueError('COMPLETION_WHILE_PAUSED')
            self.capture.event(p, now)
            c.update(status=event.upper(), end_ns=now)
            c['effective_ns'], c['elapsed_ns'] = self.times(now)
            self.stage, self.pending = 'CLOSEOUT', None
            self._save()
        elif event == 'closeout_status':
            if self.stage != 'CLOSEOUT' or type(p.get('sealed')) is not bool or type(p.get('posttest')) is not bool:
                raise ValueError('CLOSEOUT_RECEIPT_REQUIRED')
            # A receipt cannot turn a truncated local development file into a sealed record.
            c['sealed'] = p['sealed'] and self.capture.state in ('COMPLETED','ABORTED')
            c['posttest'] = p['posttest']
            self._save()
        elif event == 'guidance_status':
            if self.stage not in ('RUNNING','PAUSED') or any(p.get(k) not in ('吸气','呼气','保持','未接入') for k in ('ideal','guide','actual')):
                raise ValueError('GUIDANCE_STATUS')
            c.update({k:p[k] for k in ('ideal','guide','actual')})
            self.append(p, now)
        elif event == 'study_status':
            if self.stage not in ('RUNNING','PAUSED'):
                raise ValueError('STUDY_NOT_RUNNING')
            if any(type(p.get(k)) not in (int,float) or not 0 <= p[k] < 86400 for k in ('effective_s','elapsed_s')):
                raise ValueError('STUDY_TIME')
            if p['effective_s'] > p['elapsed_s'] or p.get('weather') not in ('storm','heat','snow','fade'):
                raise ValueError('STUDY_CONTEXT')
            if c.get('replay_elapsed_s',0) > p['elapsed_s']:
                raise ValueError('STUDY_CLOCK_REVERSED')
            c.update(replay_effective_s=p['effective_s'],replay_elapsed_s=p['elapsed_s'],
                     weather=p['weather'],segment=p.get('segment'),quality=p.get('quality'),
                     playback_speed=p.get('playback_speed',1))
            self.append(p,now)
        else:
            raise ValueError('UNKNOWN_SESSION_EVENT')
        if event != 'request_rejected':
            self.error = None
        self.seen.add(identity)
        return True

    def append(self, p, now):
        if self.stage in ('RUNNING','PAUSED'):
            self.capture.append(p, now)

    def times(self, now):
        c = self.current
        if not c or c['start_ns'] is None:
            return 0, 0
        if 'replay_effective_s' in c:
            return round(c['replay_effective_s']*1e9),round(c['replay_elapsed_s']*1e9)
        end = c['end_ns'] if c['end_ns'] is not None else now
        elapsed = max(0, end - c['start_ns'])
        pause = end - c['pause_at'] if c['pause_at'] is not None else 0
        return max(0, elapsed - c['paused_ns'] - pause), elapsed

    def fault(self, code):
        self.error = code
        if self.capture.file:
            self.capture.file.close()
            self.capture.file = None
        if self.current and self.stage in ('RUNNING','PAUSED'):
            self.current.update(status='RECORDING_FAILED', sealed=False)
            self.stage = 'CLOSEOUT'

    def snapshot(self, now):
        effective, elapsed = self.times(now)
        return dict(stage=self.stage, view=self.view, current=self.current,
                    history=self.history, ready=self.ready, can_close=self.can_close,
                    pending=self.pending, error=self.error, effective_ns=effective,
                    elapsed_ns=elapsed, record_count=self.capture.count)
