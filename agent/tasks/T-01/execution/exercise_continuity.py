"""Six native curve views under continuous, missing and dropped mock batches."""
import json
import socket
import threading
import time
from curve_continuity import packets


def exercise(command,pid,active,evidence,wait_for):
    receipts=[]
    current=None
    def take(name,curves=None,click=None,final=False,width=1280,height=720):
        nonlocal current
        i=len(receipts)
        target=command.with_name(f'command-{i:03d}.json')
        temp=target.with_suffix('.tmp')
        temp.write_text(json.dumps(dict(id=i,workflow=True,continuity=bool(curves),click=click,
            page='overview',width=width,height=height,filename=f'{i:02d}-{name}.png',
            curves=curves or {},final=final,candidate='T01_Workbench_A.continuity-v8.candidate.toe')))
        temp.replace(target)
        r=wait_for(evidence/(f'{i:02d}-{name}.png.json'),pid,60)
        assert not r['errors'],r['errors']
        assert len(r['visible_pages'])==1
        current=r['workflow']
        receipts.append(r)
        print('CONTINUITY_CAPTURE',r['screenshot'],flush=True)
        return r
    take('home')
    take('prepare',click='Content/Pages/home/new/label')
    sid=current['current']['session_id']
    origin=time.monotonic_ns()
    state={'index':0,'stop':False,'missing':False,'dropped':False,'error':None}
    sent=[]
    def stream():
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                due=time.monotonic()
                while not state['stop']:
                    i=state['index']
                    if not state['dropped']:
                        for p in packets(i,sid,origin,missing=state['missing']):
                            sock.sendto(json.dumps(p).encode(),('127.0.0.1',5005))
                            sent.append((p['source_id'],i))
                    state['index']+=1
                    due+=.1
                    time.sleep(max(0,due-time.monotonic()))
        except Exception as error:
            state['error']=error
    worker=threading.Thread(target=stream)
    worker.start()
    try:
        while state['index']<400:
            if state['error']: raise state['error']
            time.sleep(.1)
        pairs=[dict(resp='resp',ecg='ecg'),dict(resp='acceleration',ecg='rr'),
               dict(resp='angular_velocity',ecg='hr')]
        for i,views in enumerate(pairs): take('continuous-'+str(i),curves=views)
        take('continuous-1600',curves=pairs[1],width=1600,height=900)
        take('continuous-1920',curves=pairs[0],width=1920,height=1080)
        intervals=[]
        for name in ('missing','dropped'):
            begin=state['index']
            state[name]=True
            while state['index']<begin+20: time.sleep(.02)
            state[name]=False
            end=state['index']
            intervals.append(dict(kind=name,begin=begin,end=end))
            for i,views in enumerate(pairs): take(name+'-'+str(i),curves=views)
        take('recovered',curves=pairs[0],final=True)
    finally:
        state['stop']=True
        worker.join()
    if state['error']: raise state['error']
    assert current['stage']=='PREPARE' and current['record_count']==0
    (evidence/'continuity-inputs.json').write_text(json.dumps(dict(
        session_id=sid,origin_ns=origin,packet_count=len(sent),duration_s=state['index']/10,
        intervals=intervals,source='known mathematical calibration signals; dev_mock'),indent=2))
    return receipts
