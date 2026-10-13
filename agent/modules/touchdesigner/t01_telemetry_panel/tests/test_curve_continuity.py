import json
from pathlib import Path
import sys

import numpy as np
import pytest

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
sys.path.insert(0,str(BASE.parents[2]/'tasks/T-01/execution'))
from curve_continuity import packets
from device_preview import DevicePreview,raster_waveform
from workbench_session import Channels,UNITS


def feed(indices,missing=()):
    preview,channels=DevicePreview(),Channels()
    for i in indices:
        for p in packets(i,'MOCK-continuity',missing=i in missing):
            assert preview.ingest(json.dumps(p),1_000_000_000+(i+1)*100_000_000)
            channels.append(p)
    i=max(indices)
    return preview.snapshot(1_000_000_000+(i+1)*100_000_000,'MOCK-continuity'),channels


@pytest.mark.parametrize('source,key,unit,window',[
    ('resp','resp','relative',30),('ecg','ecg','uV',6),
    ('resp','acceleration','m/s²',30),('resp','angular_velocity','rad/s',30),
    ('ecg','rr','ms',30),('ecg','hr','bpm',30)])
def test_all_six_views_continuous_at_actual_panel_resolution(source,key,unit,window):
    streams,channels=feed(range(400))
    for series in channels.series(key,streams[source]):
        assert series['unit']==unit and series['window']==window
        values=[v for _,v in series['points'] if v is not None]
        assert series['range'][0]<=min(values) and series['range'][1]>=max(values)
        arr=raster_waveform(series,876,72 if key not in ('acceleration','angular_velocity') else 24)
        ink=np.asarray(series['color'])
        mask=abs(arr[:,:,:3]-ink).max(axis=2)<.001
        # Every x column contains the trace, including packet boundaries and viewport edges.
        assert mask.any(axis=0).mean()>.99
        assert mask.sum()/mask.any(axis=0).sum()>=1.9


@pytest.mark.parametrize('key', ['resp','ecg','acceleration','angular_velocity','rr','hr'])
@pytest.mark.parametrize('kind', ['null','dropped'])
def test_missing_interval_breaks_every_view_without_filling(key,kind):
    indices=list(range(400))
    if kind=='dropped': indices=[i for i in indices if not 380<=i<390]
    streams,channels=feed(indices,range(380,390) if kind=='null' else ())
    source='ecg' if key in ('ecg','rr','hr') else 'resp'
    for series in channels.series(key,streams[source]):
        arr=raster_waveform(series,876,72)
        mask=abs(arr[:,:,:3]-np.asarray(series['color'])).max(axis=2)<.001
        start=series['end_ns']-series['window']*1e9
        left=round((39.05e9-start)/(series['window']*1e9)*875)
        right=round((39.85e9-start)/(series['window']*1e9)*875)
        assert not mask[:,left:right].any()
        assert mask[:,right+10:].any()


def test_known_values_units_and_window_reset():
    streams,channels=feed(range(400))
    resp=channels.series('resp',streams['resp'])[0]
    assert min(v for _,v in resp['points'])==pytest.approx(.1)
    assert max(v for _,v in resp['points'])==pytest.approx(.9)
    assert streams['resp']['payload']['sample_rate_hz']==400
    assert streams['ecg']['payload']['sample_rate_hz']==130
    p=streams['ecg']['payload']
    assert p['hr_bpm']*p['rr_ms']==pytest.approx(60000)
    assert UNITS['ecg']=='μV' and UNITS['resp']=='相对幅度'
    for p in packets(0,'new-session'):
        channels.append(p)
    assert len(channels.data['hr']['value'])==1


def test_known_frequency_is_preserved_on_source_time_axis():
    streams,channels=feed(range(400))
    for source,key,baseline,period,rate in (('resp','resp',.5,5,400),('ecg','ecg',0,1,130)):
        points=channels.series(key,streams[source])[0]['points']
        rises=[b[0] for a,b in zip(points,points[1:]) if a[1]<=baseline<b[1]]
        assert len(rises)>=5
        assert np.median(np.diff(rises))/1e9==pytest.approx(period,abs=1/rate)
