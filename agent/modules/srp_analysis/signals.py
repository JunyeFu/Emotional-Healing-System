"""Decode verified P-02 archives; never invent device clocks or repair gaps."""
import json

import numpy as np
import pandas as pd

from .io import safe_input, save_frame
from acquisition.bigrun.protocol import decode_packet
from srp_session_store import ReplayReader


def fixed_rr_windows(values, duration, accept_ms):
    if duration <= 0:
        raise ValueError('HRV_WINDOW_REQUIRES_POSITIVE_SECONDS')
    rr = np.asarray(values, dtype=float)
    valid = (rr >= accept_ms[0]) & (rr <= accept_ms[1])
    edges = np.diff(np.r_[False, valid, False].astype(int))
    for run, (start, end) in enumerate(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1))):
        good = rr[start:end]
        beat_ends = np.cumsum(good) / 1000
        # Assign each RR by its ending beat on a fixed, sequence-relative time grid.
        for index in range(int((beat_ends[-1] + 1e-9) // duration)):
            left, right = index * duration, (index + 1) * duration
            window = good[(beat_ends > left + 1e-9) & (beat_ends <= right + 1e-9)]
            if len(window) >= 3:
                yield dict(quality_run=run, window_s=duration, actual_window_s=duration,
                           window_start_s=left, window_end_s=right, rr_span_s=float(window.sum() / 1000),
                           beat_count=len(window), window_time_basis='RR_SEQUENCE_RELATIVE_NOT_DEVICE_CLOCK',
                           RMSSD_ms=float(np.sqrt(np.mean(np.diff(window) ** 2))),
                           SDNN_ms=float(np.std(window, ddof=1)))


def decode_recordings(index, base, out, spec):
    samples, quality, windows = [], [], []
    if index.empty:
        save_frame(out / 'signals.csv', pd.DataFrame(columns=['research_id', 'kind', 'value', 'time_s']))
        return [dict(domain='signals', research_id='', status='UNAVAILABLE', reason='NO_DEVICE_INDEX')], pd.DataFrame()
    for record in index.itertuples():
        envelope_path = safe_input(base, record.archive_ref + '/archive.json')
        envelope = json.loads(envelope_path.read_text(encoding='utf-8'))
        reader = ReplayReader.open(envelope_path.parent.parent.parent, envelope['manifest']['session_id'])
        check = reader.verify(mode='strict')
        if not check.valid or not check.sealed:
            raise ValueError('DEVICE_ARCHIVE_INVALID_OR_NOT_SEALED')
        settings = spec['signals']
        origin = int(record.host_origin_ns)
        segment, previous = 0, None
        segment_rr = {}
        for raw in reader.iter_l0():
            received = (raw.host_received_monotonic_ns - origin) / 1e9
            gap_limit = settings.get('gap_limit_s')
            gap = (previous is not None and gap_limit is not None and received - previous > gap_limit)
            if raw.payload is None or gap:
                segment += 1
                quality.append(dict(domain='signals', research_id=record.research_id,
                                    status='GAP', reason=raw.missing_reason_code or 'PACKET_TIME_GAP'))
            previous = received
            if raw.payload is None:
                continue
            packet = decode_packet(raw.payload)
            rate = settings.get(f'{packet.kind}_hz')
            for i, value in enumerate(packet.samples):
                estimated = received - (len(packet.samples) - 1 - i) / rate if rate else received
                row = dict(research_id=record.research_id, kind=packet.kind, segment_id=segment,
                           time_s=estimated, packet_received_s=received, packet_seq=raw.packet_seq,
                           sample_in_packet=i, device_time_ns=raw.device_time_ns,
                           units=packet.metadata.get('units'),
                           time_basis='PACKET_RECEIVED' if not rate else 'NOMINAL_BATCH_TIME_UNVERIFIED',
                           x=None, y=None, z=None, value=None)
                if packet.kind == 'acc':
                    row.update(zip(('x', 'y', 'z'), value))
                else:
                    row['value'] = value
                samples.append(row)
                if packet.kind == 'rr':
                    segment_rr.setdefault(segment, []).append(float(value))
        qualified = settings.get('gap_limit_s') is not None and all(settings.get(key) for key in
                        ('rr_units_validated', 'rr_sequence_validated', 'quality_validated', 'validation_ref'))
        duration = settings.get('hrv_window_s')
        if qualified and settings.get('rr_units') == 'ms' and duration and settings.get('rr_accept_ms'):
            for seg, values in segment_rr.items():
                for window in fixed_rr_windows(values, duration, settings['rr_accept_ms']):
                    windows.append(dict(research_id=record.research_id, segment_id=seg, **window))
        valid_count = sum(w['research_id'] == record.research_id for w in windows)
        quality.append(dict(domain='HRV', research_id=record.research_id,
                            status='EXPLORATORY_WINDOWS' if valid_count else 'UNAVAILABLE',
                            reason='QUALIFIED_FIXED_WINDOWS' if valid_count else 'UNVERIFIED_UNITS_SEQUENCE_QUALITY_OR_SHORT_WINDOW'))
    columns = ['research_id', 'kind', 'segment_id', 'time_s', 'packet_received_s', 'packet_seq',
               'sample_in_packet', 'device_time_ns', 'units', 'time_basis', 'x', 'y', 'z', 'value']
    save_frame(out / 'signals.csv', pd.DataFrame(samples, columns=columns))
    return quality, pd.DataFrame(windows)
