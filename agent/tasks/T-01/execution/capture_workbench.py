"""Launch a dedicated TD copy and capture native tabs, layouts and read-only states."""
from pathlib import Path
from copy import deepcopy
import json
import shutil
import socket
import struct
import subprocess
import threading
import time

from run_td_probe import ps
from replay_t01_udp import _fixture

ROOT = Path(__file__).resolve().parents[4]
TD_BIN = Path('D:/TouchDesigner/bin')
SOURCE = ROOT / 'agent/tasks/T-01/evidence/runtime/T01_ReadableBaseline.candidate.toe'
EXECUTION = Path(__file__).resolve().parent
RUN_ID = time.strftime('%Y%m%d-%H%M%S')
EVIDENCE = EXECUTION.parent / 'evidence' / ('readable-v2-' + RUN_ID)
SCRATCH = ROOT / 'agent/local/artifacts/td-workbench-readable-v2' / RUN_ID


def wait_for(path, pid, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        error = EVIDENCE / 'error.json'
        if error.exists():
            raise RuntimeError(error.read_text(encoding='utf-8'))
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        if not ps(f'Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'):
            raise RuntimeError('Owned TD process exited')
        time.sleep(.1)
    raise TimeoutError(path)


def main(device_mode=False, monitor_mode=False, flow_mode=False):
    global EVIDENCE, SCRATCH
    if device_mode:
        EVIDENCE = EXECUTION.parent / 'evidence' / ('devices-v3-' + RUN_ID)
        SCRATCH = ROOT / 'agent/local/artifacts/td-workbench-devices-v3' / RUN_ID
    if monitor_mode:
        EVIDENCE = EXECUTION.parent / 'evidence' / ('monitor-v4-' + RUN_ID)
        SCRATCH = ROOT / 'agent/local/artifacts/td-workbench-monitor-v4' / RUN_ID
    candidate_name = 'T01_Workbench_A.monitor-v4.candidate.toe' if monitor_mode else 'T01_Workbench_A.devices-v3.candidate.toe' if device_mode else 'T01_Workbench_A.readable-v2.candidate.toe'
    if flow_mode:
        EVIDENCE = EXECUTION.parent / 'evidence' / ('flow-v5-' + RUN_ID)
        SCRATCH = ROOT / 'agent/local/artifacts/td-workbench-flow-v5' / RUN_ID
        candidate_name = 'T01_Workbench_A.flow-v5.candidate.toe'
    if ps('Get-Process TouchDesigner -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'):
        raise RuntimeError('Preserve already open TD projects; close the owned capture copy first')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as check:
        check.bind(('127.0.0.1', 5005))
    source_bytes = SOURCE.read_bytes()
    EVIDENCE.mkdir()
    SCRATCH.mkdir(parents=True)
    toe = SCRATCH / 'capture.toe'
    shutil.copyfile(SOURCE, toe)
    expanded = subprocess.run([str(TD_BIN / 'toeexpand.exe'), str(toe)], capture_output=True)
    directory = Path(str(toe) + '.dir')
    if not directory.exists():
        raise RuntimeError(expanded.stderr.decode(errors='replace'))
    node = directory / 'project1/T01_TelemetryPanel/Runtime/render_execute.text'
    raw = node.read_bytes()
    assert raw[:2] == b'2\n' and struct.unpack('>I', raw[23:27])[0] == len(raw[27:])
    original = SCRATCH / 'original_runtime.py'
    original.write_bytes(raw[28:])
    command = SCRATCH / 'command.json'
    bootstrap = f'''
sys.path.insert(0, {str(ROOT / 'agent/modules')!r})
_capture_original = onFrameStart
_capture_ticks = 0
def onFrameStart(frame):
    global _capture_ticks
    _capture_original(frame)
    _capture_ticks += 1
    if _capture_ticks == 30:
        hook = op('/project1/T01_TelemetryPanel').create(executeDAT, '_capture_runtime')
        hook.store('evidence', {str(EVIDENCE)!r})
        hook.store('command', {str(command)!r})
        hook.store('builder', {str(EXECUTION / ('build_workbench_flow.py' if flow_mode else 'build_workbench_monitor.py' if monitor_mode else 'build_workbench_devices.py' if device_mode else 'build_workbench_a.py'))!r})
        hook.text = Path({str(EXECUTION / 'capture_workbench_sdk.py')!r}).read_text(encoding='utf-8')
        hook.par.framestart = True
        hook.par.active = True
        me.text = Path({str(original)!r}).read_text(encoding='utf-8')
'''
    payload = raw[28:] + bootstrap.encode('utf-8')
    node.write_bytes(raw[:23] + struct.pack('>I', len(payload) + 1) + b'\n' + payload)
    collapsed = subprocess.run([str(TD_BIN / 'toecollapse.exe'), str(toe)], capture_output=True)
    if not toe.exists() or toe.stat().st_size == len(source_bytes):
        raise RuntimeError(collapsed.stderr.decode(errors='replace'))
    pid = int(ps(f"(Start-Process -FilePath '{TD_BIN / 'TouchDesigner.exe'}' -ArgumentList '\"{toe}\"' -WindowStyle Hidden -PassThru).Id"))
    active = {'frame': None, 'preview': True, 'missing': False, 'device_state': 'CONNECTED', 'inject': False, 'telemetry': True}
    stop = threading.Event()

    def send_frames():
        seq = 0
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            while not stop.wait(.1):
                if active['frame'] is None:
                    continue
                seq += 1
                frame = deepcopy(active['frame'])
                now = time.monotonic_ns()
                frame.update(frame_seq=seq, runtime_mode='dev_replay', clock_domain_id='python:td-readable-v2',
                             source_monotonic_ns=now-2_000_000, received_monotonic_ns=now-1_000_000, sent_monotonic_ns=now)
                if active['telemetry']:
                    sock.sendto(json.dumps(frame, ensure_ascii=False).encode('utf-8'), ('127.0.0.1', 5005))
                if device_mode and active['preview']:
                    from simulate_device_preview import batch
                    for source in ('plux_respiban', 'polar_h10_ecg'):
                        data = batch(source, seq, now - 5_000_000, frame['session_id'],
                                     state=active['device_state'], missing=active['missing'])
                        if monitor_mode and source == 'plux_respiban':
                            import math
                            data['motion_state'] = 'LIVE'
                            for channel in ('acceleration', 'angular_velocity'):
                                data[channel + '_unit'] = 'm/s2' if channel == 'acceleration' else 'rad/s'
                                data[channel] = {axis: [math.sin((seq * 40 + j) / (300 + k*100)) * (.2 if channel == 'angular_velocity' else 1) for j in range(40)] for k, axis in enumerate(('x','y','z'))}
                        raw = json.dumps(data).encode('utf-8')
                        sock.sendto(raw, ('127.0.0.1', 5005))
                        if active['inject']:
                            sock.sendto(raw, ('127.0.0.1', 5005))  # Duplicate batch.
                            data['samples'][0] = 'invalid'
                            sock.sendto(json.dumps(data).encode('utf-8'), ('127.0.0.1', 5005))
                    if active['inject']:
                        bad = deepcopy(frame)
                        bad['signal_quality']['resp'] = 'invalid'
                        sock.sendto(json.dumps(bad).encode('utf-8'), ('127.0.0.1', 5005))
                        active['inject'] = False

    sender = threading.Thread(target=send_frames)
    sender.start()
    success = False
    try:
        ready = wait_for(EVIDENCE / 'ready.json', pid)
        print('TD_READY', ready, flush=True)
        time.sleep(3)
        if flow_mode:
            from exercise_workbench_flow import exercise
            receipts = exercise(command, pid, active, EVIDENCE, wait_for)
            assert SOURCE.read_bytes() == source_bytes
            candidate = SCRATCH / candidate_name
            shutil.copyfile(candidate, EVIDENCE / candidate_name)
            shutil.copytree(SCRATCH / 'development-workflow', EVIDENCE / 'development-workflow')
            report = dict(source_preserved=True, td=ready, captures=receipts, owned_process_id=pid,
                          candidate=str(candidate), input_source='Synthetic fixtures and simulated authority receipts only')
            (EVIDENCE / 'capture-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            success = True
            print('EVIDENCE', EVIDENCE, flush=True)
            return
        good = _fixture('telemetry-fade-inhale-1.json')
        degraded = deepcopy(good)
        degraded.update(fallback_state='DEGRADED', fallback_reason='RESP_SQI_LOW', resp_device_state='DEGRADED')
        unusable = deepcopy(good)
        unusable.update(fallback_state='UNUSABLE', fallback_reason='RESP_UNUSABLE', resp_device_state='UNUSABLE')
        long = deepcopy(good)
        long['session_id'] = 'session-' + 'x' * 200
        cases = [
            ('overview', 1280, 720, '01-waiting.png', None, False),
            ('overview', 1280, 720, '02-overview-1280.png', good, False),
            ('overview', 1600, 900, '03-overview-1600.png', good, False),
            ('overview', 1920, 1080, '04-overview-1920.png', good, False),
            ('timing', 1280, 720, '05-timing.png', good, False),
            ('timing', 1280, 720, '06-timing-scrolled.png', good, True),
            ('audit', 1280, 720, '07-audit.png', good, False),
            ('overview', 1280, 720, '08-degraded.png', degraded, False),
            ('overview', 1280, 720, '09-unusable.png', unusable, False),
            ('overview', 1280, 720, '10-long-id.png', long, False),
            ('timing', 1280, 720, '11-long-id-detail.png', long, False),
            ('overview', 1280, 720, '12-disconnected.png', None, False),
            ('overview', 1280, 720, '13-final-overview.png', good, False),
        ]
        if device_mode:
            cases = [
                ('overview', 1280, 720, '01-waiting.png', None, False),
                ('overview', 1280, 720, '02-devices-live.png', good, False),
                ('overview', 1600, 900, '03-devices-1600.png', good, False),
                ('overview', 1920, 1080, '04-devices-1920.png', good, False),
                ('timing', 1280, 720, '05-device-details.png', good, False),
                ('timing', 1280, 720, '06-details-scrolled.png', good, True),
                ('overview', 1280, 720, '07-invalid-duplicate.png', good, False),
                ('overview', 1280, 720, '08-missing-samples.png', good, False),
                ('overview', 1280, 720, '09-preview-stale.png', good, False),
                ('overview', 1280, 720, '10-device-disconnected.png', dict(good, resp_device_state='DISCONNECTED', ecg_device_state='DISCONNECTED'), False),
                ('overview', 1280, 720, '11-telemetry-stale.png', None, False),
                ('overview', 1280, 720, '12-degraded.png', degraded, False),
                ('audit', 1280, 720, '13-audit.png', good, False),
                ('overview', 1280, 720, '14-final.png', good, False),
            ]
        receipts = []
        if monitor_mode:
            cases = [
                ('overview',1280,720,'01-waiting.png',None,False),
                ('overview',1280,720,'01-device-only.png',good,False),
                ('overview',1280,720,'02-devices-live.png',good,False),
                ('overview',1280,720,'03-motion-rr.png',good,False),
                ('overview',1280,720,'04-gyro-hr.png',good,False),
                ('overview',1280,720,'05-clicked.png',good,False),
                ('overview',1280,720,'06-recording.png',good,False),
                ('overview',1600,900,'07-large.png',good,False),
                ('overview',1920,1080,'08-large.png',good,False),
                ('overview',1280,720,'09-completed.png',good,False),
                ('timing',1280,720,'10-details.png',good,False),
                ('overview',1280,720,'11-final.png',good,False),
            ]
        for i, (page, width, height, filename, frame, scroll) in enumerate(cases):
            active['frame'] = frame
            active['telemetry'] = filename != '01-device-only.png'
            active['preview'] = filename != '09-preview-stale.png'
            active['missing'] = filename == '08-missing-samples.png'
            active['device_state'] = 'DISCONNECTED' if filename == '10-device-disconnected.png' else 'CONNECTED'
            active['inject'] = filename == '07-invalid-duplicate.png'
            if monitor_mode and filename in ('05-clicked.png','06-recording.png','09-completed.png'):
                event = {'05-clicked.png':'unity_start_clicked','06-recording.png':'started','09-completed.png':'completed'}[filename]
                payload = dict(message_type='session_observation', version='1.0', event_id=filename,
                    session_id=good['session_id'], source_mode='dev_mock', event=event,
                    authority='python_session_core', unity_start_confirmed=True)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(json.dumps(payload).encode(), ('127.0.0.1',5005))
            time.sleep(31 if device_mode and filename == '02-devices-live.png' else 2.2 if 'stale' in filename or filename == '12-disconnected.png' else .2)
            next_command = command.with_name(f'command-{i:03d}.json')
            pending_command = next_command.with_suffix('.tmp')
            pending_command.write_text(json.dumps(dict(id=i, page=page, width=width, height=height,
                               filename=filename, scroll=scroll, final=i == len(cases)-1,
                               curves={'resp':'acceleration','ecg':'rr'} if monitor_mode and filename == '03-motion-rr.png' else {'resp':'angular_velocity','ecg':'hr'} if monitor_mode and filename == '04-gyro-hr.png' else {'resp':'resp','ecg':'ecg'} if monitor_mode else {},
                               candidate=candidate_name)), encoding='utf-8')
            pending_command.replace(next_command)
            receipt = wait_for(EVIDENCE / (filename + '.json'), pid, 30)
            if receipt['errors']:
                raise RuntimeError(receipt['errors'])
            receipts.append(receipt)
            print('CAPTURED', filename, receipt['layout_size'], receipt['image_size'], flush=True)
        assert SOURCE.read_bytes() == source_bytes
        candidate = SCRATCH / candidate_name
        shutil.copyfile(candidate, EVIDENCE / candidate.name)
        report = dict(source_toe=str(SOURCE.relative_to(ROOT)), source_preserved=True,
                      td=ready, captures=receipts, owned_process_id=pid,
                      candidate=str(candidate), input_source='v2.2 synthetic development fixtures; no real devices')
        (EVIDENCE / 'capture-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if monitor_mode:
            import shutil as files
            files.copytree(SCRATCH / 'development-recordings', EVIDENCE / 'development-recordings')
        success = True
        print('EVIDENCE', EVIDENCE, flush=True)
    finally:
        stop.set()
        sender.join()
        if not success:
            ps(f'Stop-Process -Id {pid} -ErrorAction SilentlyContinue')


if __name__ == '__main__':
    import sys
    main(device_mode=any(x in sys.argv for x in ('--devices','--monitor','--flow')), monitor_mode='--monitor' in sys.argv or '--flow' in sys.argv, flow_mode='--flow' in sys.argv)
