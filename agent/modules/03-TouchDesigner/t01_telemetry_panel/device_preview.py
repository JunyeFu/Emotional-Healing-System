"""Read-only display batches, independent of the research/control contract."""
from collections import deque
import json
import math

SOURCES = {
    'plux_respiban': ('resp', 'relative', 30),
    'polar_h10_ecg': ('ecg', 'uV', 6),
}


class DevicePreview:
    def __init__(self):
        self.streams = {}
        self.accepted = 0
        self.rejected = 0
        self.last_error = None
        self.errors = {}

    def ingest(self, raw, now_ns):
        try:
            p = json.loads(raw)
            source = p['source_id']
            _, unit, window = SOURCES[source]
            if p['message_type'] != 'device_preview' or p['preview_version'] != '1.0':
                raise ValueError('PREVIEW_VERSION')
            if p['source_mode'] not in ('dev_mock', 'real') or p['unit'] != unit:
                raise ValueError('PREVIEW_SOURCE_OR_UNIT')
            for key in ('session_id', 'clock_domain_id'):
                if not isinstance(p[key], str) or not p[key]:
                    raise ValueError('PREVIEW_IDENTITY')
            for key in ('packet_seq', 'last_sample_monotonic_ns', 'sent_monotonic_ns'):
                if type(p[key]) is not int or p[key] < 0:
                    raise ValueError('PREVIEW_SEQUENCE_OR_TIME')
            rate = p['sample_rate_hz']
            if type(rate) not in (int, float) or not math.isfinite(rate) or not 0 < rate <= 4000:
                raise ValueError('PREVIEW_RATE')
            samples = p['samples']
            if not isinstance(samples, list) or not 1 <= len(samples) <= 400:
                raise ValueError('PREVIEW_BATCH_SIZE')
            if any(v is not None and (type(v) not in (int, float) or not math.isfinite(v)) for v in samples):
                raise ValueError('PREVIEW_SAMPLE')
            for channel in ('acceleration', 'angular_velocity'):
                axes = p.get(channel)
                if axes is not None:
                    if p.get(channel + '_unit') != ('m/s2' if channel == 'acceleration' else 'rad/s'):
                        raise ValueError('PREVIEW_MOTION_UNIT')
                    if source != 'plux_respiban' or set(axes) != {'x', 'y', 'z'}:
                        raise ValueError('PREVIEW_MOTION_AXES')
                    for values in axes.values():
                        if not isinstance(values, list) or len(values) != len(samples) or any(
                            v is not None and (type(v) not in (int, float) or not math.isfinite(v)) for v in values):
                            raise ValueError('PREVIEW_MOTION_SAMPLES')
            if p['device_state'] not in ('CONNECTED', 'DISCONNECTED', 'UNKNOWN'):
                raise ValueError('PREVIEW_DEVICE_STATE')
            for key in ('hr_bpm', 'rr_ms'):
                v = p.get(key)
                if v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v <= 0):
                    raise ValueError('PREVIEW_MEASUREMENT')
            for key in ('motion_state', 'rr_state'):
                if p.get(key, 'UNKNOWN') not in ('LIVE', 'DISCONNECTED', 'UNKNOWN'):
                    raise ValueError('PREVIEW_CHANNEL_STATE')
            if p['last_sample_monotonic_ns'] > p['sent_monotonic_ns']:
                raise ValueError('PREVIEW_FUTURE_SAMPLE')
            epoch = (p['session_id'], p['clock_domain_id'], p['source_mode'])
            old = self.streams.get(source)
            if old and old['epoch'] == epoch:
                if p['packet_seq'] <= old['payload']['packet_seq']:
                    raise ValueError('PREVIEW_STALE_SEQUENCE')
                first = p['last_sample_monotonic_ns'] - round((len(samples) - 1) * 1e9 / rate)
                if first <= old['payload']['last_sample_monotonic_ns']:
                    raise ValueError('PREVIEW_OVERLAPPING_BATCH')
                points = old['points']
            else:
                points = deque(maxlen=round(4000 * window) + 1)
            end = p['last_sample_monotonic_ns']
            for i, value in enumerate(samples):
                points.append((end - round((len(samples) - 1 - i) * 1e9 / rate), value))
            cutoff = end - window * 1_000_000_000
            while points and points[0][0] < cutoff:
                points.popleft()
            self.streams[source] = dict(epoch=epoch, payload=p, points=points, received_ns=now_ns)
        except (KeyError, TypeError, ValueError) as error:
            self.rejected += 1
            self.last_error = str(error)
            self.errors[self.last_error] = self.errors.get(self.last_error, 0) + 1
            return False
        self.accepted += 1
        self.last_error = None
        return True

    def snapshot(self, now_ns, session_id):
        result = {}
        for source, (name, unit, window) in SOURCES.items():
            stream = self.streams.get(source)
            if not stream or stream['payload']['session_id'] != session_id:
                result[name] = dict(state='WAITING', points=(), window=window, unit=unit)
                continue
            p = stream['payload']
            # Source and TD clocks are distinct. Never subtract their absolute readings.
            age_ns = now_ns - stream['received_ns'] + p['sent_monotonic_ns'] - p['last_sample_monotonic_ns']
            age = age_ns / 1e6
            stale = age >= 2000 or p['device_state'] == 'DISCONNECTED'
            result[name] = dict(state='STALE' if stale else 'LIVE', points=tuple(stream['points']),
                window=window, unit=unit, age_ms=age, payload=p,
                end_ns=p['last_sample_monotonic_ns'] if stale else p['last_sample_monotonic_ns'] + age_ns)
        return result


def raster_waveform(stream, width, height):
    """Draw timestamped samples; absent samples and time gaps break the trace."""
    import numpy as np  # TouchDesigner ships numpy; host tests need it only for plots.
    image = np.ones((height, width, 4), dtype=np.float32)
    for x in range(0, width, max(1, width // 6)):
        image[:, x, :3] = (.87, .90, .93)
    for y in range(0, height, max(1, height // 4)):
        image[y, :, :3] = (.87, .90, .93)
    points = stream['points']
    if not points:
        return image
    values = [v for _, v in points if v is not None]
    if not values:
        return image
    low, high = stream.get('range', (-1200, 1200) if stream['unit'] == 'uV' else (min(values), max(values)))
    if high == low:
        low, high = low - 1, high + 1
    span = stream['window'] * 1e9
    start = stream['end_ns'] - span
    ink = (.34, .40, .47) if stream['state'] == 'STALE' else stream.get('color', (37/255, 99/255, 166/255) if stream['unit'] == 'relative' else (35/255, 122/255, 71/255))
    # Keep per-pixel extrema instead of issuing a draw for every 400 Hz sample.
    reduced = []
    bucket = []
    column = None
    last_stamp = None
    def flush():
        if bucket:
            ends = {min(bucket, key=lambda p: p[1]), max(bucket, key=lambda p: p[1])}
            reduced.extend(sorted(ends))
            bucket.clear()
    for stamp, value in points:
        x = round((stamp - start) / span * (width - 1))
        if value is None or (last_stamp is not None and stamp - last_stamp >= stream.get('gap_ns', 500_000_000)):
            flush()
            reduced.append((stamp, None))
        if value is not None:
            if column != x:
                flush()
                column = x
            bucket.append((stamp, value))
        last_stamp = stamp
    flush()
    previous = None
    for stamp, value in reduced:
        if value is None:
            previous = None
            continue
        x = round((stamp - start) / span * (width - 1))
        y = round((value - low) / (high - low) * (height - 1))
        if not 0 <= x < width:
            previous = None
            continue
        y = min(height - 1, max(0, y))
        if previous and stamp - previous[2] < stream.get('gap_ns', 500_000_000):
            px, py, _ = previous
            steps = max(abs(x - px), abs(y - py), 1) + 1
            xx = np.rint(np.linspace(px, x, steps)).astype(int)
            yy = np.rint(np.linspace(py, y, steps)).astype(int)
            image[yy, xx, :3] = ink
        else:
            image[y, x, :3] = ink
        previous = x, y, stamp
    return image
