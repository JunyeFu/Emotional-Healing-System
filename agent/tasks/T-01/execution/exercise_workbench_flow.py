"""Native click sequence with an explicitly simulated Python/Unity peer."""
import json
import socket
import time
import uuid
from replay_t01_udp import _fixture


def exercise(command, pid, active, evidence, wait_for):
    receipts=[]
    current=None

    def take(name,click=None,stage=None,curves=None,width=1280,height=720,final=False):
        nonlocal current
        i=len(receipts)
        filename=f'{i:02d}-{name}.png'
        target=command.with_name(f'command-{i:03d}.json')
        pending=target.with_suffix('.tmp')
        pending.write_text(json.dumps(dict(id=i,workflow=True,click=click,page='overview',width=width,height=height,
            filename=filename,curves=curves or {},final=final,candidate='T01_Workbench_A.flow-v5.candidate.toe')),encoding='utf-8')
        pending.replace(target)
        receipt=wait_for(evidence/(filename+'.json'),pid,40)
        assert not receipt['errors'],receipt['errors']
        assert len(receipt['visible_pages'])==1,receipt['visible_pages']
        if stage:
            assert receipt['workflow']['stage']==stage,receipt['workflow']
        receipts.append(receipt)
        current=receipt['workflow']
        print('CAPTURED',filename,current['stage'],flush=True)
        return receipt

    def send(event,**extra):
        payload=dict(message_type='session_observation',version='1.0',source_mode='dev_mock',authority='python_session_core',
                     session_id=current['current']['session_id'],event_id=str(uuid.uuid4()),event=event)
        if current['pending']:
            payload['request_id']=current['pending']['request_id']
        payload.update(extra)
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.sendto(json.dumps(payload,ensure_ascii=False).encode(),('127.0.0.1',5005))
        time.sleep(.25)

    def assign(index):
        frame=_fixture('telemetry-fade-inhale-1.json')
        frame['session_id']=current['current']['session_id']
        active['frame']=frame
        send('preparation_status',participant=f'DEMO-{index:03d}',condition='A',pretest=True,unity_ready=True,store_ready=True)

    take('home',stage='HOME')
    take('prepare','Content/Pages/home/new/label','PREPARE')
    for i,result in enumerate(('completed','aborted','completed'),1):
        assign(i)
        take(f'{i}-ready',stage='PREPARE',curves={'resp':'acceleration','ecg':'rr'} if i==1 else {'resp':'angular_velocity','ecg':'hr'} if i==2 else {})
        take(f'{i}-prepare-request','Content/Pages/overview/flow_controls/submit/label','PREPARE')
        assert current['pending']['action']=='prepare'
        send('prepared')
        take(f'{i}-waiting',stage='WAITING')
        send('unity_start_clicked')
        send('started',unity_start_confirmed=True)
        send('guidance_status',ideal='呼气',guide='呼气',actual='吸气')
        take(f'{i}-running',stage='RUNNING',curves={'resp':'resp','ecg':'ecg'})
        if i==1:
            take('pause-request','Content/Pages/overview/flow_controls/pause/label','RUNNING')
            send('paused')
            paused=take('paused',stage='PAUSED')['workflow']
            paused2=take('paused-again',stage='PAUSED')['workflow']
            assert paused['effective_ns']==paused2['effective_ns']
            assert paused2['record_count']>paused['record_count']
            take('resume-request','Content/Pages/overview/flow_controls/resume/label','PAUSED')
            send('resumed')
            take('resumed',stage='RUNNING')
        if result=='aborted':
            take('abort-request','Content/Pages/overview/flow_controls/abort/label','RUNNING')
        send(result)
        take(f'{i}-closeout-pending',stage='CLOSEOUT')
        assert not current['can_close']
        take(f'{i}-next-blocked','Content/Pages/closeout/next/label','CLOSEOUT')
        send('closeout_status',sealed=True,posttest=True)
        take(f'{i}-closeout-ready',stage='CLOSEOUT',width=1600 if i==2 else 1920 if i==3 else 1280,height=900 if i==2 else 1080 if i==3 else 720)
        assert current['can_close']
        active['frame']=None
        if i<3:
            take(f'{i}-next','Content/Pages/closeout/next/label','PREPARE')
        else:
            take('history','Content/FlowNav/history/label','CLOSEOUT')
            take('history-detail','Content/Pages/history/rows/row_0/inspect','CLOSEOUT')
            take('return-closeout','Content/Pages/history/back/label','CLOSEOUT')
            take('return-home','Content/Pages/closeout/home/label','HOME',final=True)
    return receipts
