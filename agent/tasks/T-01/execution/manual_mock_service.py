"""Operator-driven development bridge. Device samples and Unity peer are simulated."""
from copy import deepcopy
from pathlib import Path
import time
import uuid

from session_backend import DevelopmentBackend
from study_simulation import Replay


class ManualMockBridge:
    def __init__(self, root, dataset, send, speed=1, clock=time.monotonic_ns):
        self.root, self.send, self.speed, self.clock = Path(root), send, speed, clock
        self.origin = clock()
        self.replay = Replay(dataset, '') if dataset is not None else None
        self.active_frames = ([i for i, f in enumerate(self.replay.frames) if f['unity_state'] != 'PAUSED']
                              if self.replay else [])
        self.backend = None
        self.status = None
        self.last_status = None
        self.sequence = 0
        self.started_at = None
        self.sealed_report = None
        self.replies = {}
        self.preparation = None
        self.closeout = None

    def now(self):
        return round((self.clock() - self.origin) * self.speed)

    def on_status(self, status):
        if status.get('message_type') != 'td_mock_status' or status.get('source_mode') != 'dev_mock':
            return
        self.status, self.last_status = status, self.clock()
        sid = status['session_id']
        if not sid:
            self.close()
            if self.replay:
                self.replay.session = 'DEV-preview'
            return
        if self.backend is None or sid != self.backend.session_id:
            self.close()
            self.backend = DevelopmentBackend(self.root, sid)
            self.started_at, self.sealed_report, self.closeout = None, None, None
            self.replies = {}
            self.sequence = 0
            self.preparation = self.backend.observation('preparation_status', participant='MOCK-A',
                condition='A', pretest=True, unity_ready=True, store_ready=True)
            if self.replay:
                self.replay.session = sid
        if status['stage'] == 'PREPARE' and not status['ready'] and not status['pending']:
            self.send(self.preparation)
        pending = status['pending']
        if pending:
            rid, action = pending['request_id'], pending['action']
            if rid not in self.replies:
                now = self.now()
                if pending['session_id'] != sid or (action == 'mock_start' and
                        (status['stage'] != 'WAITING' or self.backend.core.snapshot().status.value != 'PREPARED')):
                    reply = self.backend.observation('request_rejected', request_id=rid)
                elif action == 'mock_start':
                    self.send(self.backend.observation('unity_start_clicked'))
                    reply = self.backend.start_from_simulated_unity(now)
                    self.started_at = now
                    reply['request_id'] = rid
                elif action == 'mock_posttest':
                    reply = self.backend.observation('closeout_status', request_id=rid,
                                                     sealed=bool(self.sealed_report), posttest=True)
                elif action == 'cancel_prepare' and self.backend.core.snapshot().status.value == 'CREATED':
                    reply = self.backend.observation('cancelled', request_id=rid)
                else:
                    reply = self.backend.request(pending, now)
                self.replies[rid] = reply
                self.send(reply)
                if reply['event'] == 'aborted':
                    self.finish()
            else:
                self.send(self.replies[rid])
        if status['stage'] == 'CLOSEOUT' and not status['sealed'] and not pending and self.closeout:
            self.send(self.closeout)

    def finish(self):
        self.sealed_report = self.backend.seal()
        self.closeout = self.backend.observation('closeout_status', sealed=True, posttest=False)
        self.send(self.closeout)

    def tick(self):
        if self.last_status is None or self.clock() - self.last_status > 2_000_000_000:
            return
        now = self.now()
        state = self.backend.core.snapshot().status.value if self.backend else 'PREVIEW'
        if state in ('RUNNING', 'PAUSED'):
            snapshot = self.backend.advance(now)
            effective = snapshot.session_elapsed_ns / 1e9
            elapsed = (now - self.started_at) / 1e9
            index = min(int(effective * 10), len(self.active_frames) - 1)
            frame = deepcopy(self.replay.frames[self.active_frames[index]])
            frame.update(t_s=elapsed, effective_s=effective, weather=snapshot.module_id,
                         segment=snapshot.segment, unity_state=snapshot.status.value)
            self.send(self.backend.observation('guidance_status',
                ideal=frame['ideal'], guide=frame['guide'], actual=frame['actual']))
            self.send(self.backend.observation('study_status', weather=frame['weather'],
                segment=frame['segment'], quality=frame['quality'], effective_s=effective,
                elapsed_s=elapsed, playback_speed=self.speed, unity=frame))
            if snapshot.status.value == 'COMPLETED':
                self.send(self.backend.completed())
                self.finish()
                state = 'COMPLETED'
        if self.replay:
            for packet in self.replay.packets(self.sequence % len(self.replay.frames)):
                packet['packet_seq'] = self.sequence
                end = (self.sequence + 1) * 100_000_000
                packet['clock_domain_id'] = 'synthetic:manual-source-time'
                packet['last_sample_monotonic_ns'] = end - round(1e9 / packet['sample_rate_hz'])
                packet['sent_monotonic_ns'] = end
                if state in ('RUNNING', 'PAUSED'):
                    self.backend.append_packet(packet, now)
                self.send(packet)
            self.sequence += 1

    def close(self):
        if self.backend:
            try:
                if self.backend.core.snapshot().status.value in ('RUNNING', 'PAUSED'):
                    request = dict(request_id=str(uuid.uuid4()), session_id=self.backend.session_id,
                                   source_mode='dev_mock', action='abort')
                    self.send(self.backend.request(request, self.now()))
                    self.finish()
            finally:
                if not self.sealed_report and self.backend.core.snapshot().status.value == 'ABORTED':
                    self.backend.seal()
                self.backend.close()
                self.backend = None
