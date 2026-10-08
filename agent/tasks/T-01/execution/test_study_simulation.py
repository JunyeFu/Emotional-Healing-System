import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
BASE=HERE.parents[2]/'modules/03-TouchDesigner/t01_telemetry_panel'
sys.path.insert(0,str(BASE))
from study_simulation import Replay, step, ideal
from record_export import export_record
from workbench_session import DevelopmentCapture
from experiment_workflow import Workflow
from device_preview import DevicePreview


def test_four_weather_steps():
    assert [ideal(t)[0] for t in (0,200,400,600)]==['storm','heat','snow','fade']
    assert [step('storm',t)[1] for t in (0,3,6,9)]==['吸气','保持','呼气','保持']
    assert [step('fade',t)[0] for t in (0,2.5,4)]==[0,1,2]


def test_export_missing_and_closed(tmp_path):
    source=tmp_path/'recordings'/'test.jsonl'; source.parent.mkdir()
    rows=[dict(kind='started',received_ns=1,payload=dict(session_id='DEV-test')),
        dict(kind='data',received_ns=2,payload=dict(message_type='device_preview',source_id='plux_respiban',
            packet_seq=1,samples=[1,None,0],sample_rate_hz=400,last_sample_monotonic_ns=10000000,unit='relative')),
        dict(kind='completed',received_ns=3,payload=dict(session_id='DEV-test'))]
    source.write_text('\n'.join(json.dumps(r) for r in rows))
    original=source.read_bytes()
    target,summary=export_record(source)
    assert target.exists() and source.read_bytes()==original
    import csv
    with (target.with_suffix('')/'samples.csv').open(encoding='utf-8-sig') as f: data=list(csv.DictReader(f))
    assert [r['value'] for r in data]==['1','','0']
    assert summary['sample_counts']['plux_respiban']==3
    with pytest.raises(FileExistsError): export_record(source)
    source.write_text(json.dumps(rows[0]))
    with pytest.raises(ValueError,match='CLOSED'): export_record(source)


def test_replay_clock_is_explicit_dev_only(tmp_path):
    w=Workflow(tmp_path,DevelopmentCapture); w.new()
    w.stage='RUNNING'; w.current['start_ns']=1
    p=dict(message_type='session_observation',version='1.0',source_mode='dev_mock',authority='python_session_core',
        session_id=w.current['session_id'],event_id='clock',event='study_status',effective_s=320.,elapsed_s=330.,weather='heat')
    w.event(p,900)
    assert w.times(999)==(320000000000,330000000000)
    with pytest.raises(ValueError,match='REVERSED'): w.event(dict(p,event_id='2',elapsed_s=329),999)
    with pytest.raises(ValueError,match='FORMAL'): w.event(dict(p,source_mode='real'),999)


def test_preview_batch_sync_does_not_fsync_every_sample(tmp_path,monkeypatch):
    import workbench_session
    calls=[]
    monkeypatch.setattr(workbench_session.time,'monotonic',lambda:0)
    monkeypatch.setattr(workbench_session.os,'fsync',lambda fd:calls.append(fd))
    capture=DevelopmentCapture(tmp_path)
    p=dict(message_type='session_observation',version='1.0',source_mode='dev_mock',
        authority='python_session_core',session_id='DEV-sync',event_id='start',event='started',unity_start_confirmed=True)
    capture.event(p,0)
    for i in range(100): capture.append(dict(session_id='DEV-sync',source_mode='dev_mock',value=i),i)
    assert len(calls)==1
    capture.event(dict(p,event='completed',event_id='end'),101)
    assert len(calls)==2
    assert len(capture.path.read_text().splitlines())==102


def test_resp_loss_does_not_disconnect_ecg():
    preview=DevicePreview()
    common=dict(message_type='device_preview',preview_version='1.0',source_mode='dev_mock',session_id='DEV-loss',
        clock_domain_id='source',packet_seq=1,last_sample_monotonic_ns=100000000,sent_monotonic_ns=101000000)
    resp=dict(common,source_id='plux_respiban',unit='relative',sample_rate_hz=400,samples=[None]*40,device_state='DISCONNECTED')
    ecg=dict(common,source_id='polar_h10_ecg',unit='uV',sample_rate_hz=130,samples=[10]*13,device_state='CONNECTED')
    assert preview.ingest(json.dumps(resp),500000000)
    assert preview.ingest(json.dumps(ecg),500000000)
    snapshot=preview.snapshot(501000000,'DEV-loss')
    assert snapshot['resp']['state']=='STALE'
    assert snapshot['ecg']['state']=='LIVE'
