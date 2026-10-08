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


def main():
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
        hook.store('builder', {str(EXECUTION / 'build_workbench_a.py')!r})
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
    active = {'frame': None}
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
                sock.sendto(json.dumps(frame, ensure_ascii=False).encode('utf-8'), ('127.0.0.1', 5005))

    sender = threading.Thread(target=send_frames)
    sender.start()
    success = False
    try:
        ready = wait_for(EVIDENCE / 'ready.json', pid)
        print('TD_READY', ready, flush=True)
        time.sleep(3)
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
        receipts = []
        for i, (page, width, height, filename, frame, scroll) in enumerate(cases):
            active['frame'] = frame
            time.sleep(2.2 if filename == '12-disconnected.png' else .2)
            next_command = command.with_name(f'command-{i:03d}.json')
            pending_command = next_command.with_suffix('.tmp')
            pending_command.write_text(json.dumps(dict(id=i, page=page, width=width, height=height,
                               filename=filename, scroll=scroll, final=i == len(cases)-1)), encoding='utf-8')
            pending_command.replace(next_command)
            receipt = wait_for(EVIDENCE / (filename + '.json'), pid, 30)
            if receipt['errors']:
                raise RuntimeError(receipt['errors'])
            receipts.append(receipt)
            print('CAPTURED', filename, receipt['layout_size'], receipt['image_size'], flush=True)
        assert SOURCE.read_bytes() == source_bytes
        candidate = SCRATCH / 'T01_Workbench_A.readable-v2.candidate.toe'
        shutil.copyfile(candidate, EVIDENCE / candidate.name)
        report = dict(source_toe=str(SOURCE.relative_to(ROOT)), source_preserved=True,
                      td=ready, captures=receipts, owned_process_id=pid,
                      candidate=str(candidate), input_source='v2.2 synthetic development fixtures; no real devices')
        (EVIDENCE / 'capture-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        success = True
        print('EVIDENCE', EVIDENCE, flush=True)
    finally:
        stop.set()
        sender.join()
        if not success:
            ps(f'Stop-Process -Id {pid} -ErrorAction SilentlyContinue')


if __name__ == '__main__':
    main()
