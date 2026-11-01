"""Native operator clicks against the independently running mock ingress script."""
import json
from pathlib import Path
import subprocess
import sys
import time
import socket
import uuid

ROOT = Path(__file__).resolve().parents[4]


def exercise(command, pid, active, evidence, wait_for):
    receipts = []
    current = None
    active['preview'] = False
    def take(name, click=None, stage=None, curves=None, final=False, ready=None, page=None, size=(1280,720), sealed=None, error=None):
        nonlocal current
        i = len(receipts)
        filename = f'{i:02d}-{name}.png'
        target = command.with_name(f'command-{i:03d}.json')
        tmp = target.with_suffix('.tmp')
        tmp.write_text(json.dumps(dict(id=i, workflow=True, design_action=click if click and not click.startswith('Design/') else None,
            click=click if click and click.startswith('Design/') else None, page='overview',
            width=size[0], height=size[1], filename=filename, curves=curves or {}, final=final,
            expect_stage=stage, expect_ready=ready,
            expect_page=page,
            expect_sealed=sealed, wait_seconds=85 if name=='normal-completion' else 60,
            candidate='T01_ManualWorkbench.toe')), encoding='utf-8')
        tmp.replace(target)
        result = wait_for(evidence / (filename + '.json'), pid, 100 if name=='normal-completion' else 90)
        assert not result['errors'], result['errors']
        current = result['workflow']
        if stage:
            assert current['stage'] == stage, current
        assert current['error'] == error, current
        assert result['visible_ink_pixels'] > 1000 and result['pixel_variation']>.03, 'Blank native page'
        receipts.append(result)
        print('MANUAL_CAPTURE', filename, flush=True)
        return result
    def send(event, **extra):
        payload = dict(message_type='session_observation',version='1.0',source_mode='dev_mock',
            authority='python_session_core',session_id=current['current']['session_id'],event_id=str(uuid.uuid4()),event=event)
        payload.update(extra)
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.sendto(json.dumps(payload).encode('utf-8'),('127.0.0.1',5005))
        time.sleep(.2)
    take('disconnected', stage='HOME', page='home')
    assert not current['ready'] and current['record_count'] == 0
    with (evidence / 'mock-service.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('run_manual_mock.py')),
                                    '--speed', '10'], cwd=ROOT, stdout=log, stderr=log)
        try:
            time.sleep(1)
            take('home-connected', stage='HOME')
            take('new-preparation', 'new', 'PREPARE', ready=True)
            assert current['ready'] and current['record_count'] == 0
            assert current['current']['participant'] == 'MOCK-A'
            send('started',unity_start_confirmed=True)
            take('unconfirmed-start-rejected',stage='PREPARE',error='NOT_READY_TO_START')
            assert current['record_count']==0 and current['current']['path'] is None
            take('clear-rejection','back','PREPARE')
            send('prepared',request_id='not-requested')
            take('unsolicited-prepare-rejected',stage='PREPARE',error='REQUEST_RECEIPT_MISMATCH')
            take('clear-prepare-rejection','back','PREPARE')
            take('preparation-details','details','PREPARE',page='details')
            take('raw-expand','raw','PREPARE')
            take('raw-collapse','raw','PREPARE')
            take('back-to-preparation','back','PREPARE',page='prepare')
            take('prepared', 'submit', 'WAITING', page='waiting')
            take('still-waiting', stage='WAITING')
            assert current['record_count'] == current['effective_ns'] == 0
            send('started',unity_start_confirmed=True)
            take('no-manual-start-rejected',stage='WAITING',error='OPERATOR_START_REQUIRED')
            take('clear-start-rejection','back','WAITING')
            take('cancel-after-confirm','cancel','HOME',page='home')
            take('new-after-cancel','new','PREPARE',ready=True)
            take('confirm-new-session','submit','WAITING')
            take('started', 'start', 'RUNNING', page='running')
            assert current['record_count'] > 0
            assert '\ufffd' not in ''.join(current['current'].get(k,'') for k in ('ideal','guide','actual'))
            take('motion-rr', curves={'resp': 'acceleration', 'ecg': 'rr'})
            take('angular-hr', curves={'resp': 'angular_velocity', 'ecg': 'hr'})
            take('paused', 'pause', 'PAUSED',
                 curves={'resp': 'resp', 'ecg': 'ecg'})
            paused, count = current['effective_ns'], current['record_count']
            take('pause-continues-recording', stage='PAUSED')
            assert current['effective_ns'] == paused and current['record_count'] > count
            take('resumed', 'resume', 'RUNNING')
            assert current['effective_ns'] > paused
            take('abort-dialog', 'abort_dialog', 'RUNNING', page='abort')
            take('abort-cancel', 'abort_cancel', 'RUNNING', page='running')
            take('abort-dialog-again', 'abort_dialog', 'RUNNING', page='abort')
            take('aborted', 'abort_confirm', 'CLOSEOUT', page='closeout',sealed=True)
            assert current['current']['sealed'] and not current['can_close']
            take('next-blocked-until-posttest','next','CLOSEOUT')
            take('home-blocked-until-posttest','home','CLOSEOUT')
            take('posttest', 'posttest', 'CLOSEOUT', page='closed')
            assert current['can_close']
            exported = take('export', 'export', 'CLOSEOUT')
            folder = Path(exported['workflow_root'])
            record = folder / current['current']['path']
            assert (folder / 'exports' / record.stem / 'samples.csv').is_file()
            take('open-record-folder','open','CLOSEOUT')
            take('next', 'next', 'PREPARE')
            assert current['record_count'] == 0
            take('cancel', 'cancel', 'HOME')
            take('history-unselected','history','HOME',page='unselected')
            take('history-selected','Design/unselected/rows/row_0/select','HOME',page='history')
            take('history-export','export','HOME')
            take('history-open','open','HOME')
            take('history-back','back','HOME',page='home')
            take('normal-new','new','PREPARE',ready=True)
            take('normal-confirm','submit','WAITING')
            take('normal-start','start','RUNNING')
            take('running-history','history','RUNNING',page='unselected')
            take('running-history-selected','Design/unselected/rows/row_0/select','RUNNING',page='history')
            take('running-history-back','back','RUNNING',page='running')
            take('normal-details','details','RUNNING',page='details')
            copied=take('copy-session','copy','RUNNING')
            assert copied['clipboard']==current['current']['session_id']
            take('normal-details-back','back','RUNNING',page='running')
            take('normal-completion',stage='CLOSEOUT',page='closeout',sealed=True)
            assert current['current']['status']=='COMPLETED'
            take('normal-posttest','posttest','CLOSEOUT',page='closed')
            take('normal-home','home','HOME')
            take('paused-abort-new','new','PREPARE',ready=True)
            take('paused-abort-confirm','submit','WAITING')
            take('paused-abort-start','start','RUNNING')
            take('paused-abort-pause','pause','PAUSED')
            take('paused-abort-dialog','abort_dialog','PAUSED',page='abort')
            take('paused-abort-cancel','abort_cancel','PAUSED',page='paused')
            take('paused-abort-dialog-again','abort_dialog','PAUSED',page='abort')
            take('paused-abort-end','abort_confirm','CLOSEOUT',page='closeout',sealed=True)
            take('paused-abort-posttest','posttest','CLOSEOUT',page='closed')
            take('paused-abort-home','home','HOME')
            take('large-home',stage='HOME',size=(1920,1080))
            take('fault-new','new','PREPARE',ready=True)
            take('fault-confirm','submit','WAITING')
            take('fault-start','start','RUNNING')
            process.terminate(); process.wait(timeout=10)
            take('disconnected-record-fault',stage='CLOSEOUT',page='fault',error='MOCK_DISCONNECTED')
            assert not current['can_close'] and not current['current']['sealed']
            take('fault-details','details','CLOSEOUT',page='details',error=None)
            take('fault-details-back','back','CLOSEOUT',page='fault')
            take('fault-preserved-home','dismiss_fault','HOME',page='home')
            take('home-final', stage='HOME', final=True)
            (evidence / 'manual-verification.json').write_text(json.dumps(dict(passed=True,
                captures=len(receipts), operator_start_required=True, preflight_record_count=0,
                pause_keeps_samples=True, abort_sealed=True, posttest_operator_required=True,
                export_samples=True, input='synthetic', unity_endpoint='simulated'), indent=2), encoding='utf-8')
        finally:
            process.terminate()
            process.wait(timeout=10)
    return receipts
