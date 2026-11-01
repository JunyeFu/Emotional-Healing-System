"""Exercise the native redesign with simulated authority receipts."""
import json
import socket
import time
import uuid
from replay_t01_udp import _fixture


def exercise(command, pid, active, evidence, wait_for):
    receipts = []
    current = None

    def take(page, click=None, final=False):
        nonlocal current
        i = len(receipts)
        filename = f'{i:02d}-{page}.png'
        target = command.with_name(f'command-{i:03d}.json')
        pending = target.with_suffix('.tmp')
        pending.write_text(json.dumps(dict(id=i, workflow=True, click=click,
            width=1280, height=720, filename=filename, final=final,
            candidate='T01_Workbench.redesign.candidate.toe')), encoding='utf-8')
        pending.replace(target)
        receipt = wait_for(evidence/(filename+'.json'), pid, 60)
        assert not receipt['errors'], receipt['errors']
        assert receipt['design_page'] == page, receipt['design_page']
        receipts.append(receipt)
        current = receipt['workflow']
        print('CAPTURED', filename, flush=True)
        return receipt

    def click(page, index):
        return f'Design/{page}/c_{page}_{index}'

    def send(event, **extra):
        payload = dict(message_type='session_observation', version='1.0',
            source_mode='dev_mock', authority='python_session_core',
            session_id=current['current']['session_id'], event_id=str(uuid.uuid4()), event=event)
        if current['pending']:
            payload['request_id'] = current['pending']['request_id']
        payload.update(extra)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(json.dumps(payload).encode(), ('127.0.0.1', active['port']))
        time.sleep(.3)

    take('home')
    take('prepare', click('home',38))
    for i in range(2):
        frame = _fixture('telemetry-fade-inhale-1.json')
        frame['session_id'] = current['current']['session_id']
        active['frame'] = frame
        send('preparation_status', participant=f'DEMO-{i+1}', condition='A', pretest=True, unity_ready=True, store_ready=True)
        take('prepare')
        take('prepare', 'Design/prepare/c_prepare_prepare_confirm')
        assert current['pending']['action'] == 'prepare'
        send('prepared')
        take('waiting')
        send('unity_start_clicked')
        send('started', unity_start_confirmed=True)
        take('running')
        take('running', click('running',110))
        send('paused')
        first = take('paused')['workflow']
        second = take('paused')['workflow']
        assert first['effective_ns'] == second['effective_ns']
        take('paused', click('paused',110))
        send('resumed')
        take('running')
        take('abort', click('running',111))
        take('running', click('abort',117))
        if i:
            take('abort', click('running',111))
            take('running', click('abort',118))
            assert current['pending']['action'] == 'abort'
        send('aborted' if i else 'completed')
        take('closeout')
        take('closeout', click('closeout',46))
        send('closeout_status', sealed=True, posttest=True)
        take('closed')
        active['frame'] = None
        if not i:
            take('prepare', click('closed',46))
    take('home', click('closed',47))
    take('unselected', click('home',39))
    take('history','Design/unselected/rows/row_0')
    take('home', click('history',64), final=True)
    return receipts
