"""Explicit synthetic source for the device-preview display interface."""
import math


def batch(source, seq, end_ns, session_id, *, state='CONNECTED', missing=False):
    resp = source == 'plux_respiban'
    rate = 400 if resp else 130
    count = rate // 10
    samples = []
    for i in range(count):
        t = (end_ns / 1e9) - (count - 1 - i) / rate
        if resp:
            phase = t % 10 / 10
            value = math.sin(2 * math.pi * phase) + .12 * math.sin(4 * math.pi * phase)
        else:
            phase = t % .882
            value = sum(a * math.exp(-((phase - c) / w) ** 2) for a, c, w in
                ((90, .13, .025), (-130, .24, .008), (950, .26, .009), (-230, .28, .01), (170, .43, .045)))
        samples.append(None if missing else round(value, 4))
    result = dict(message_type='device_preview', preview_version='1.0', source_id=source,
        source_mode='dev_mock', session_id=session_id, clock_domain_id='python:device-preview-demo',
        packet_seq=seq, last_sample_monotonic_ns=end_ns, sent_monotonic_ns=end_ns + 5_000_000, sample_rate_hz=rate,
        unit='relative' if resp else 'uV', samples=samples, device_state=state)
    if resp:
        result['motion_state'] = 'UNKNOWN'  # No synthetic motion axes were sent.
    else:
        result.update(hr_bpm=68, rr_ms=882, rr_state='LIVE')
    return result
