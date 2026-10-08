"""Native TD test driven by full, literature-constrained synthetic recordings."""
import json
from pathlib import Path
import socket
import threading
import time
import uuid
from study_simulation import Replay


def exercise(command,pid,active,evidence,wait_for,dataset,speed=5):
    receipts=[]; current=None
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    def send(p):
        sock.sendto(json.dumps(p,ensure_ascii=False,allow_nan=False).encode(),('127.0.0.1',5005))
    def event(kind,**kwargs):
        p=dict(message_type='session_observation',version='1.0',source_mode='dev_mock',authority='python_session_core',
            session_id=current['current']['session_id'],event_id=str(uuid.uuid4()),event=kind)
        if current['pending']: p['request_id']=current['pending']['request_id']
        p.update(kwargs); send(p)
    def take(name,click=None,stage=None,curves=None,final=False):
        nonlocal current
        i=len(receipts); filename=f'{i:02d}-{name}.png'
        target=command.with_name(f'command-{i:03d}.json'); tmp=target.with_suffix('.tmp')
        tmp.write_text(json.dumps(dict(id=i,workflow=True,click=click,page='overview',width=1280,height=720,
            filename=filename,curves=curves or {},final=final,candidate='T01_Workbench_A.flow-v5.candidate.toe')),encoding='utf-8')
        tmp.replace(target)
        r=wait_for(evidence/(filename+'.json'),pid,90)
        assert not r['errors'],r['errors']
        assert len(r['visible_pages'])==1
        current=r['workflow']
        if stage: assert current['stage']==stage,current
        receipts.append(r); print('STUDY_CAPTURE',filename,flush=True)
        return r
    take('home',stage='HOME')
    take('prepare','Content/Pages/home/new/label','PREPARE')
    sent=[]
    for profile in ('A','B','abort'):
        sid=current['current']['session_id']; replay=Replay(Path(dataset)/profile,sid)
        # Separate preparation clock/identity; these preview samples must not enter a record.
        for p in replay.packets(0):
            p['clock_domain_id']='synthetic:preflight'; send(p)
        event('preparation_status',participant='SIM-'+profile,condition=replay.meta['condition'],pretest=True,unity_ready=True,store_ready=True)
        take(profile+'-ready',stage='PREPARE')
        assert current['record_count']==0
        take(profile+'-submit','Content/Pages/overview/flow_controls/submit/label','PREPARE')
        event('prepared'); take(profile+'-waiting',stage='WAITING')
        event('unity_start_clicked'); time.sleep(.1)
        event('started',unity_start_confirmed=True); time.sleep(.1)
        state={'index':0,'stop':False,'limit':len(replay.frames),'error':None}
        def stream():
            try:
                due=time.monotonic()
                while state['index']<len(replay.frames) and not state['stop']:
                    i=state['index']
                    if i>=state['limit']:
                        time.sleep(.01); due=time.monotonic(); continue
                    for p in replay.packets(i): send(p)
                    f=replay.frames[i]
                    event('guidance_status',ideal=f['ideal'],guide=f['guide'],actual=f['actual'])
                    event('study_status',weather=f['weather'],segment=f['segment'],quality=f['quality'],
                        effective_s=f['effective_s'],elapsed_s=f['t_s'],playback_speed=speed,unity=f)
                    state['index']+=1
                    due+=.1/speed
                    time.sleep(max(0,due-time.monotonic()))
            except Exception as error:
                state['error']=error
        def until(index):
            while state['index']<index:
                if state['error']: raise state['error']
                time.sleep(.05)
        worker=threading.Thread(target=stream)
        state['limit']=3200 if profile!='abort' else len(replay.frames)
        worker.start()
        try:
            take(profile+'-running',stage='RUNNING')
            until(1200)
            take(profile+'-motion-rr',curves={'resp':'acceleration','ecg':'rr'})
            state['limit']=2440
            until(2410)
            take(profile+'-motion-artifact',curves={'resp':'angular_velocity','ecg':'hr'})
            state['limit']=3200 if profile!='abort' else len(replay.frames)
            if profile!='abort':
                until(3200)
                take(profile+'-pause-request','Content/Pages/overview/flow_controls/pause/label','RUNNING')
                event('paused'); time.sleep(.1)
                state['limit']=3300
                take(profile+'-paused',stage='PAUSED',curves={'resp':'resp','ecg':'ecg'})
                until(3300)
                take(profile+'-resume-request','Content/Pages/overview/flow_controls/resume/label','PAUSED')
                event('resumed'); time.sleep(.1); state['limit']=4620
                until(4605)
                take(profile+'-missing-resp',curves={'resp':'resp','ecg':'ecg'})
                assert current['current']['quality']=='DISCONNECTED'
                state['limit']=len(replay.frames)
                until(6200)
                take(profile+'-fade',curves={'resp':'resp','ecg':'ecg'})
            until(len(replay.frames)); worker.join()
        finally:
            state['stop']=True; worker.join()
        if state['error']: raise state['error']
        duration=replay.meta['duration_s']
        event('study_status',weather=replay.frames[-1]['weather'],segment=replay.frames[-1]['segment'],quality='GOOD',
            effective_s=replay.meta['effective_s'],elapsed_s=duration,playback_speed=speed)
        if profile=='abort':
            take('abort-request','Content/Pages/overview/flow_controls/abort/label','RUNNING')
        event('aborted' if profile=='abort' else 'completed')
        take(profile+'-closeout',stage='CLOSEOUT')
        event('closeout_status',sealed=True,posttest=True)
        take(profile+'-export','Content/Pages/closeout/export/label','CLOSEOUT')
        sent.append(dict(session_id=sid,source_packets=len(replay.frames)*2,**replay.meta))
        if profile!='abort':
            take(profile+'-next','Content/Pages/closeout/next/label','PREPARE')
        else:
            take('history','Content/FlowNav/history/label','CLOSEOUT')
            take('history-selected','Content/Pages/history/rows/row_0/inspect','CLOSEOUT')
            take('history-export','Content/Pages/history/export/label','CLOSEOUT')
            take('back','Content/Pages/history/back/label','CLOSEOUT')
            take('home-final','Content/Pages/closeout/home/label','HOME',final=True)
    sock.close()
    (evidence/'study-inputs.json').write_text(json.dumps(dict(speed=speed,runs=sent),indent=2),encoding='utf-8')
    return receipts
