import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('workbench_session', Path(__file__).parents[1] / 'workbench_session.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def event(kind, eid=None):
    return dict(message_type='session_observation',version='1.0',event_id=eid or kind,
                session_id='s1',source_mode='dev_mock',event=kind,
                authority='python_session_core',unity_start_confirmed=True)


def test_clock():
    assert m.duration(800_000_000_000) == '13:20'
    assert m.duration(3601_000_000_000) == '60:01'
    assert m.age(20) == '0.02 秒'
    assert m.age(800000) == '13:20'


def test_preflight_one_file_and_complete(tmp_path):
    c = m.DevelopmentCapture(tmp_path / 'records')
    packet = dict(session_id='s1',source_mode='dev_mock')
    c.append(packet, 0)
    c.event(event('unity_start_clicked'), 1)
    c.append(packet, 2)
    assert not c.root.exists()
    c.event(event('started'), 10)
    assert not c.event(event('started'), 11)
    c.append(packet, 12)
    c.append(dict(packet,session_id='other'), 13)
    c.event(event('completed'), 800_000_000_010)
    c.append(packet, 800_000_000_020)
    rows = [json.loads(s) for s in c.path.read_text(encoding='utf-8').splitlines()]
    assert [r['kind'] for r in rows] == ['started','data','completed']
    assert c.elapsed(900_000_000_000) == '13:20'
    with pytest.raises(ValueError):
        c.event(event('started','again'), 900_000_000_000)


def test_start_requires_confirmation_and_formal_not_faked(tmp_path):
    c = m.DevelopmentCapture(tmp_path)
    p = event('started')
    p['unity_start_confirmed'] = False
    with pytest.raises(ValueError): c.event(p, 0)
    p['source_mode'] = 'real'
    with pytest.raises(ValueError): c.event(p, 0)
    assert c.state == 'WAITING'
    assert not list(tmp_path.iterdir())


def test_six_views_and_trends():
    assert sum(map(len,m.VIEWS.values())) == 6
    c = m.Channels()
    p = dict(source_id='polar_h10_ecg', session_id='s',clock_domain_id='c',source_mode='dev_mock',
             last_sample_monotonic_ns=1000000000,sample_rate_hz=130,hr_bpm=68,rr_ms=882)
    c.append(p)
    stream = dict(payload=p, points=(),window=6,unit='uV',state='LIVE',end_ns=1000000000)
    assert c.series('hr',stream)[0]['points'][0][1] == 68
    assert c.series('rr',stream)[0]['unit'] == 'ms'
