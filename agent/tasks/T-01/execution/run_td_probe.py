"""Reopen an isolated cleaned TOE and capture actual read-only UDP behaviour."""
from hashlib import sha256
import argparse
import json
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time

from replay_t01_udp import (_send_frames, anomaly_frames, fixture_frames,
                           publish_from_real_session_core, recovery_frames)

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
MODULE = ROOT / 'agent/modules/03-TouchDesigner/t01_telemetry_panel'
EVIDENCE = TASK / 'evidence/runtime'
TD_BIN = Path('D:/TouchDesigner/bin')


def ps(script):
    return subprocess.check_output(['powershell', '-NoProfile', '-Command', script + '; exit 0'], text=True).strip()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def wait_file(path, process_id, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        if not ps(f'Get-Process -Id {process_id} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'):
            raise RuntimeError('OWNED_TD_PROCESS_EXITED')
        time.sleep(.25)
    raise TimeoutError(str(path))


def main():
    global EVIDENCE
    parser = argparse.ArgumentParser()
    parser.add_argument('--readable', action='store_true')
    parser.add_argument('--evidence-root', type=Path, help='Keep this run separate from previous runtime evidence')
    args = parser.parse_args()
    if args.evidence_root:
        EVIDENCE = args.evidence_root.resolve()
        if EVIDENCE.exists():
            raise FileExistsError(EVIDENCE)
    if ps('Get-Process TouchDesigner -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'):
        raise RuntimeError('TouchDesigner is already running; preserve the open project')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as port_check:
        port_check.bind(('127.0.0.1', 5005))
    scratch = ROOT / '.artifacts-local/task-normalization/T-01/probe' / time.strftime('%Y%m%d-%H%M%S')
    scratch.mkdir(parents=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    toe = scratch / 'probe.toe'
    source = EVIDENCE / 'T01_ReadableBaseline.candidate.toe' if args.readable else MODULE / 'T01_TelemetryPanel.toe'
    shutil.copyfile(source, toe)
    expanded = Path(str(toe) + '.dir')
    expansion = subprocess.run([str(TD_BIN / 'toeexpand.exe'), str(toe)], capture_output=True, text=True)
    if not expanded.is_dir():
        raise RuntimeError(expansion.stdout + expansion.stderr)
    node = expanded / 'project1/T01_TelemetryPanel/Runtime/render_execute'
    raw = node.with_suffix('.text').read_bytes()
    # The expanded DAT stores its UTF-8 length in bytes 23..26, followed by LF.
    if raw[:2] != b'2\n' or raw[27:28] != b'\n' or struct.unpack('>I', raw[23:27])[0] != len(raw[27:]):
        raise ValueError('UNEXPECTED_EXPANDED_DAT_FORMAT')
    verifier = TASK / 'execution/verify_t01_touchdesigner_reopen.py'
    command = scratch / 'command.json'
    ready = scratch / 'ready.json'
    error = scratch / 'error.json'
    bootstrap = f'''
import traceback
import os
os.environ['SRP_T01_PROBE_EVIDENCE_ROOT'] = {str(EVIDENCE)!r}
sys.path.insert(0, {str(ROOT / 'agent/modules')!r})
_normal_frame = onFrameStart
_probe_ready = False
_probe_frames = 0
_handled = None
def onFrameStart(frame):
    global _probe_ready, _probe_frames, _handled
    try:
        _normal_frame(frame)
        _probe_frames += 1
        if not _probe_ready and _probe_frames >= 30:
            p = Path({str(verifier)!r})
            exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'), dict(globals(), __file__=str(p)))
            Path({str(ready)!r}).write_text(json.dumps({{'ready': True, 'build': str(app.build)}}), encoding='utf-8')
            _probe_ready = True
        p = Path({str(command)!r})
        if _probe_ready and p.exists():
            request = json.loads(p.read_text(encoding='utf-8'))
            if request['id'] != _handled:
                _handled = request['id']
                result = builtins.t01_capture(request['label'])
                Path(request['receipt']).write_text(json.dumps(result), encoding='utf-8')
    except Exception:
        Path({str(error)!r}).write_text(json.dumps({{'error': traceback.format_exc()}}), encoding='utf-8')
        me.par.active = False
'''
    content = raw[28:] + bootstrap.encode('utf-8')
    node.with_suffix('.text').write_bytes(raw[:23] + struct.pack('>I', len(content) + 1) + b'\n' + content)
    collapse = subprocess.run([str(TD_BIN / 'toecollapse.exe'), str(toe)], capture_output=True, text=True)
    if not toe.is_file() or toe.stat().st_size == source.stat().st_size:
        raise RuntimeError(collapse.stdout + collapse.stderr)
    write_json(EVIDENCE / 'probe_identity.json', {
        'source_toe_sha256': sha256(source.read_bytes()).hexdigest().upper(),
        'probe_toe_sha256': sha256(toe.read_bytes()).hexdigest().upper(),
        'change': 'Runtime render callback extended with isolated verification/capture hook',
        'source_preserved': True, 'probe_path': str(toe)})
    process_id = int(ps(f"(Start-Process -FilePath '{TD_BIN / 'TouchDesigner.exe'}' -ArgumentList '\"{toe}\"' -WindowStyle Hidden -PassThru).Id"))
    try:
        deadline = time.monotonic() + 60
        while not ready.exists() and time.monotonic() < deadline:
            if error.exists():
                raise RuntimeError(error.read_text(encoding='utf-8'))
            if not ps(f'Get-Process -Id {process_id} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'):
                raise RuntimeError('OWNED_TD_PROCESS_EXITED')
            time.sleep(.5)
        wait_file(ready, process_id, timeout=1)

        def capture(label):
            receipt = scratch / (label + '.receipt.json')
            write_json(command, {'id': label, 'label': label, 'receipt': str(receipt)})
            wait_file(receipt, process_id, timeout=10)
            return json.loads((EVIDENCE / 'touchdesigner/states' / (label + '.json')).read_text(encoding='utf-8'))

        publish_from_real_session_core(10)
        publisher = capture('publisher_live')
        _send_frames(fixture_frames(3))
        fixture = capture('fixture_good')
        frames = anomaly_frames(5)
        for frame in frames:
            frame['clock_domain_id'] = 'python:t01-probe-anomaly'
        _send_frames(frames)
        anomaly = capture('out_of_order')
        time.sleep(2.3)
        disconnected = capture('disconnected')
        _send_frames(recovery_frames(5))
        recovered = capture('recovered')
        counters = anomaly['display_only']['transport']
        checks = {
            'publisher_live': publisher['meta']['stream_state'] == 'LIVE',
            'fixture_live': fixture['meta']['stream_state'] == 'LIVE',
            'lost_two': counters['lost_frames'] == 2,
            'duplicate_one': counters['duplicate_frames'] == 1,
            'out_of_order_one': counters['out_of_order_frames'] == 1,
            'disconnect_after_two_seconds': disconnected['meta']['stream_state'] == 'DISCONNECTED',
            'recovered_live': recovered['meta']['stream_state'] == 'LIVE',
            'counters_preserved': all(recovered['display_only']['transport'][k] == counters[k]
                                      for k in ('lost_frames', 'duplicate_frames', 'out_of_order_frames')),
        }
        report = {'pass': all(checks.values()), 'checks': checks,
                  'source_toe': source.relative_to(ROOT).as_posix(),
                  'source_toe_sha256': sha256(source.read_bytes()).hexdigest().upper(),
                  'scope': 'Actual isolated TD reopen and fixture UDP consumption; no real devices or A-theme acceptance'}
        write_json(EVIDENCE / 'probe_report.json', report)
        if not report['pass']:
            raise RuntimeError(json.dumps(checks))
        print('T01_ISOLATED_TD_PROBE_PASS')
    finally:
        # Stop only the process started by this probe, never a user's other TD session.
        ps(f'Stop-Process -Id {process_id} -ErrorAction SilentlyContinue')


if __name__ == '__main__':
    main()
