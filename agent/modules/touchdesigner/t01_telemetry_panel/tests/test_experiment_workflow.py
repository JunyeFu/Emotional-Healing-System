import importlib.util
import json
from pathlib import Path
import uuid
import pytest


def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).parents[1]/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wmod=load('experiment_workflow')
cmod=load('workbench_session')


def make(tmp_path):
    return wmod.Workflow(tmp_path,cmod.DevelopmentCapture)


def receipt(w,kind,now=0,**kw):
    p=dict(message_type='session_observation',version='1.0',event_id=str(uuid.uuid4()),
           source_mode='dev_mock',authority='python_session_core',session_id=w.current['session_id'],event=kind)
    if w.pending:
        p['request_id']=w.pending['request_id']
    p.update(kw)
    w.event(p,now)
    return p


def prepare(w):
    w.action('new',0)
    receipt(w,'preparation_status',participant='DEMO',condition='A',pretest=True,unity_ready=True,store_ready=True)
    w.action('submit',0)
    receipt(w,'prepared')


def test_manual_start_waits_for_click_and_matching_mock_reply(tmp_path):
    w = make(tmp_path)
    prepare(w)
    assert w.stage == 'WAITING' and w.capture.path is None
    w.action('start', 10)
    assert w.pending['action'] == 'mock_start'
    with pytest.raises(ValueError, match='REQUEST_RECEIPT_MISMATCH'):
        receipt(w, 'started', 20, request_id='other', unity_start_confirmed=True)
    assert w.stage == 'WAITING' and w.capture.path is None
    receipt(w, 'started', 20, unity_start_confirmed=True)
    assert w.stage == 'RUNNING' and w.pending is None
    receipt(w, 'aborted', 30)
    receipt(w, 'closeout_status', 40, sealed=True, posttest=False)
    assert not w.can_close
    w.action('posttest', 50)
    receipt(w, 'closeout_status', 60, sealed=True, posttest=True)
    assert w.can_close and w.pending is None


def test_three_consecutive_sessions(tmp_path):
    w=make(tmp_path)
    ids=[]
    for i,result in enumerate(('completed','aborted','completed')):
        if i == 0:
            prepare(w)
        else:
            receipt(w,'preparation_status',participant='DEMO'+str(i),condition='B',pretest=True,unity_ready=True,store_ready=True)
            w.action('submit',0)
            receipt(w,'prepared')
        sid=w.current['session_id']
        ids.append(sid)
        data=dict(source_mode='dev_mock',session_id=sid,value=i)
        w.append(data,0)
        assert w.capture.path is None
        receipt(w,'unity_start_clicked')
        assert w.capture.path is None
        receipt(w,'started',10,unity_start_confirmed=True)
        w.append(data,20)
        w.append(dict(data,session_id='other'),21)
        receipt(w,result,800_000_000_010)
        w.append(data,800_000_000_020)
        with pytest.raises(ValueError,match='CLOSEOUT_INCOMPLETE'): w.action('next',0)
        receipt(w,'closeout_status',sealed=True,posttest=True)
        w.action('next' if i<2 else 'home',0)
    assert len(set(ids))==3
    files=list((tmp_path/'recordings').glob('*.jsonl'))
    assert len(files)==3
    for file in files:
        rows=[json.loads(x) for x in file.read_text(encoding='utf-8').splitlines()]
        assert [r['kind'] for r in rows] in (['started','data','completed'],['started','data','aborted'])
        assert len({r['payload']['session_id'] for r in rows})==1
    assert w.stage=='HOME'
    restored=make(tmp_path)
    assert len(restored.history)==3 and all(x['closed'] for x in restored.history)


def test_pause_keeps_file_and_freezes_effective_clock(tmp_path):
    w=make(tmp_path); prepare(w)
    receipt(w,'started',0,unity_start_confirmed=True)
    w.action('pause',10_000_000_000)
    assert w.stage=='RUNNING'
    receipt(w,'paused',10_000_000_000)
    assert w.times(20_000_000_000)==(10_000_000_000,20_000_000_000)
    w.append(dict(source_mode='dev_mock',session_id=w.current['session_id']),15_000_000_000)
    w.action('resume',20_000_000_000)
    receipt(w,'resumed',20_000_000_000)
    receipt(w,'completed',30_000_000_000)
    assert w.times(40_000_000_000)==(20_000_000_000,30_000_000_000)
    assert len(list((tmp_path/'recordings').glob('*.jsonl')))==1


def test_gates_and_mismatched_receipts(tmp_path):
    w=make(tmp_path); w.action('new',0)
    with pytest.raises(ValueError): w.action('submit',0)
    with pytest.raises(ValueError): receipt(w,'started',unity_start_confirmed=True)
    with pytest.raises(ValueError): receipt(w,'prepared')
    with pytest.raises(ValueError): receipt(w,'preparation_status',source_mode='real')
    with pytest.raises(ValueError): receipt(w,'preparation_status',session_id='old')
    assert w.stage=='PREPARE'


def test_seal_failure_blocks_next_and_history_does_not_change_stage(tmp_path):
    w=make(tmp_path); prepare(w)
    receipt(w,'started',0,unity_start_confirmed=True)
    w.action('history',0)
    assert w.stage=='RUNNING' and w.view=='HISTORY'
    w.action('back',0)
    receipt(w,'aborted',100)
    receipt(w,'closeout_status',sealed=False,posttest=True)
    with pytest.raises(ValueError): w.action('next',0)
    assert len(w.history)==1 and w.current['path']


def test_cancel_confirmed_before_home_and_reject_duplicate_request(tmp_path):
    w=make(tmp_path); prepare(w)
    w.action('cancel',0)
    with pytest.raises(ValueError): w.action('cancel',1)
    with pytest.raises(ValueError): receipt(w,'started',unity_start_confirmed=True)
    receipt(w,'cancelled')
    assert w.stage=='HOME' and not w.history


def test_process_interrupted_not_resumed(tmp_path):
    w=make(tmp_path); prepare(w)
    receipt(w,'started',0,unity_start_confirmed=True)
    w.capture.file.close()
    w.capture.file=None
    restored=make(tmp_path)
    assert restored.stage=='HOME'
    assert restored.history[0]['status']=='INTERRUPTED'
    assert not restored.history[0]['sealed']


def test_write_failure_blocks_progress(tmp_path,monkeypatch):
    w=make(tmp_path); prepare(w)
    receipt(w,'started',0,unity_start_confirmed=True)
    w.fault('CAPTURE_WRITE_FAILED')
    assert w.stage=='CLOSEOUT' and not w.can_close
    assert w.capture.file is None


def test_fault_freezes_clock_and_can_be_archived_without_false_seal(tmp_path):
    w=make(tmp_path); prepare(w)
    receipt(w,'started',0,unity_start_confirmed=True)
    w.fault('CAPTURE_WRITE_FAILED', 10_000_000_000)
    assert w.times(30_000_000_000)==(10_000_000_000,10_000_000_000)
    w.action('dismiss_fault',30_000_000_000)
    assert w.stage=='HOME' and w.history[0]['closed']
    assert w.history[0]['status']=='RECORDING_FAILED' and not w.history[0]['sealed']


def test_manual_workbench_rejects_unsolicited_start_even_after_preparation(tmp_path):
    w=make(tmp_path); w.manual_start_required=True; prepare(w)
    with pytest.raises(ValueError,match='OPERATOR_START_REQUIRED'):
        receipt(w,'started',unity_start_confirmed=True)
    assert w.stage=='WAITING' and w.capture.path is None
    w.action('start',10)
    receipt(w,'started',20,unity_start_confirmed=True)
    receipt(w,'aborted',30)
