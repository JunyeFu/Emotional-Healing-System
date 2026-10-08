"""Six display channels and a development-only session capture bridge."""
from collections import deque
from pathlib import Path
import json
import os
import uuid
import time

COLORS = {'resp': '#2563A6', 'ecg': '#237A47', 'rr': '#7850A0', 'hr': '#237A47',
          'x': '#B63B3B', 'y': '#237A47', 'z': '#2563A6'}
VIEWS = {'resp': ('resp', 'acceleration', 'angular_velocity'), 'ecg': ('ecg', 'rr', 'hr')}
LABELS = {'resp': '呼吸', 'acceleration': '加速度', 'angular_velocity': '角速度',
          'ecg': 'ECG', 'rr': 'RR间期', 'hr': '心率'}
UNITS = {'resp': '相对幅度', 'acceleration': 'm/s²', 'angular_velocity': 'rad/s',
         'ecg': 'μV', 'rr': 'ms', 'hr': 'bpm'}


def duration(ns):
    seconds = max(0, int(ns // 1_000_000_000))
    minutes, seconds = divmod(seconds, 60)
    return f'{minutes:02d}:{seconds:02d}'


def age(ms):
    return '未接入' if ms is None else (f'{ms / 1000:.2f} 秒' if ms < 60000 else duration(ms * 1_000_000))


class Channels:
    def __init__(self):
        self.epochs = {}
        self.data = {}

    def append(self, p):
        source = p['source_id']
        epoch = (p['session_id'], p['clock_domain_id'], p['source_mode'])
        keys = ('acceleration', 'angular_velocity') if source == 'plux_respiban' else ('hr', 'rr')
        if self.epochs.get(source) != epoch:
            for key in keys:
                self.data[key] = {}
            self.epochs[source] = epoch
        end = p['last_sample_monotonic_ns']
        for key in keys:
            values = p.get(key) if source == 'plux_respiban' else {'value': [p.get('hr_bpm' if key == 'hr' else 'rr_ms')]}
            # Missing packets break curves instead of extending the last observation.
            if values is None:
                values = {axis: [None] for axis in ('x', 'y', 'z')}
            for axis, samples in values.items():
                q = self.data[key].setdefault(axis, deque(maxlen=120001))
                for i, value in enumerate(samples):
                    q.append((end - round((len(samples)-1-i) * 1e9 / p['sample_rate_hz']), value))
                while q and q[0][0] < end - 30_000_000_000:
                    q.popleft()

    def series(self, key, stream):
        if not stream.get('payload'):
            return []
        if key in ('resp', 'ecg'):
            return [dict(stream, color=rgb(COLORS[key]))]
        result = []
        for axis, points in self.data.get(key, {}).items():
            result.append(dict(stream, points=tuple(points), window=30, unit=UNITS[key],
                               color=rgb(COLORS.get(axis, COLORS.get(key, '#2563A6'))),
                               gap_ns=2_000_000_000 if key in ('hr', 'rr') else 500_000_000))
        values = [v for s in result for _, v in s['points'] if v is not None]
        if values:
            for s in result:
                s['range'] = (min(values), max(values))
        return result


def rgb(code):
    return tuple(int(code[i:i+2], 16) / 255 for i in (1, 3, 5))


class DevelopmentCapture:
    """One append-only mock capture per session. Not a replacement for P-02."""
    def __init__(self, root):
        self.root = Path(root)
        self.state = 'WAITING'
        self.session = None
        self.file = None
        self.path = None
        self.started = None
        self.ended = None
        self.seen = set()
        self.closed = set()
        self.error = None
        self.count = 0
        self.last_sync = time.monotonic()

    def event(self, p, now):
        if p.get('message_type') != 'session_observation' or p.get('version') != '1.0':
            raise ValueError('SESSION_MESSAGE_VERSION')
        if p.get('source_mode') != 'dev_mock':
            raise ValueError('FORMAL_RECORDING_REQUIRES_P02_BRIDGE')
        sid, eid, action = p.get('session_id'), p.get('event_id'), p.get('event')
        if not isinstance(sid, str) or not sid or not isinstance(eid, str) or not eid:
            raise ValueError('SESSION_IDENTITY')
        if (sid, eid) in self.seen:
            return False
        if action == 'unity_start_clicked':
            if self.state not in ('WAITING', 'CLICKED'):
                raise ValueError('SESSION_ALREADY_ACTIVE')
            self.state = 'CLICKED'
        elif action == 'started':
            if self.file or sid in self.closed or self.state == 'ERROR':
                raise ValueError('SESSION_ALREADY_CAPTURED')
            if p.get('authority') != 'python_session_core' or p.get('unity_start_confirmed') is not True:
                raise ValueError('START_NOT_CONFIRMED')
            self.root.mkdir(parents=True, exist_ok=True)
            self.path = self.root / (str(uuid.uuid4()) + '.jsonl')
            self.file = self.path.open('x', encoding='utf-8')
            self.session, self.started, self.ended = sid, now, None
            self.count = 0
            self.state = 'RECORDING'
            self._write('started', p, now)
        elif action in ('completed', 'aborted'):
            if not self.file or sid != self.session or p.get('authority') != 'python_session_core':
                raise ValueError('SESSION_END_MISMATCH')
            self._write(action, p, now)
            self.file.close()
            self.file = None
            self.closed.add(sid)
            self.ended, self.state = now, action.upper()
        else:
            raise ValueError('SESSION_EVENT')
        self.seen.add((sid, eid))
        return True

    def _write(self, kind, payload, now):
        try:
            self.file.write(json.dumps(dict(kind=kind, received_ns=now, payload=payload), ensure_ascii=False, allow_nan=False) + '\n')
            # Raw preview batches share a bounded sync; lifecycle events remain durable.
            sync_now = time.monotonic()
            if kind != 'data' or sync_now - self.last_sync >= .1:
                self.file.flush()
                os.fsync(self.file.fileno())
                self.last_sync = sync_now
            self.count += 1
        except OSError:
            self.file.close()
            self.file = None
            self.state, self.error = 'ERROR', 'CAPTURE_WRITE_FAILED'
            raise

    def append(self, p, now):
        if self.file and p.get('session_id') == self.session:
            if p.get('source_mode') == 'dev_mock' or p.get('runtime_mode') in ('dev_replay', 'dev_mock'):
                self._write('data', p, now)

    def elapsed(self, now):
        return duration((self.ended if self.ended is not None else now) - self.started) if self.started is not None else '00:00'

    def label(self):
        return {'WAITING': '正在等待Unity开始 · 预览不计入录制',
                'CLICKED': 'Unity已点击开始 · 等待Python确认',
                'RECORDING': '模拟会话录制中', 'COMPLETED': '模拟录制已完成',
                'ABORTED': '模拟录制已中止', 'ERROR': '录制失败'}[self.state]
