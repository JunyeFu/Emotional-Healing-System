"""Validate native six-view clicks and mock recording boundaries."""
from pathlib import Path
import json
import sys


def verify(root):
    root = Path(root)
    report = json.loads((root / 'capture-report.json').read_text(encoding='utf-8'))
    captures = {c['screenshot']: c for c in report['captures']}
    assert len(captures) == 12
    assert all(not c['errors'] and c['native_mouse_click'] for c in captures.values())
    for name in ('01-waiting.png','01-device-only.png','02-devices-live.png','03-motion-rr.png','04-gyro-hr.png','05-clicked.png'):
        assert captures[name]['session_capture']['count'] == 0
        assert captures[name]['session_capture']['path'] == 'None'
    assert captures['03-motion-rr.png']['session_capture']['curves'] == {'resp':'acceleration','ecg':'rr'}
    assert captures['04-gyro-hr.png']['session_capture']['curves'] == {'resp':'angular_velocity','ecg':'hr'}
    for source in ('resp','ecg'):
        assert captures['01-device-only.png']['fields'][source + '_state']['text'] == '已连接'
        assert captures['01-device-only.png']['device_preview']['plots'][source]['trace_pixels'] > 50
    for name in ('03-motion-rr.png','04-gyro-hr.png'):
        axes = captures[name]['device_preview']['plots']['resp']['color_pixels']
        assert all(axes[axis] > 50 for axis in ('x','y','z'))
    assert captures['03-motion-rr.png']['device_preview']['plots']['ecg']['color_pixels']['rr'] > 50
    assert all(p['size'] == [960,240] for c in captures.values() for p in c['device_preview']['plots'].values())
    assert captures['06-recording.png']['session_capture']['state'] == 'RECORDING'
    end = captures['09-completed.png']['session_capture']
    assert end['state'] == 'COMPLETED'
    assert captures['11-final.png']['session_capture']['count'] == end['count']
    files = list((root / 'development-recordings').glob('*.jsonl'))
    assert len(files) == 1
    rows = [json.loads(line) for line in files[0].read_text(encoding='utf-8').splitlines()]
    assert len(rows) == end['count']
    assert rows[0]['kind'] == 'started' and rows[-1]['kind'] == 'completed'
    sid = rows[0]['payload']['session_id']
    assert all(r['payload']['session_id'] == sid for r in rows)
    assert all(rows[0]['received_ns'] <= r['received_ns'] <= rows[-1]['received_ns'] for r in rows)
    assert all(c['device_preview']['rejected'] == 0 for c in captures.values())
    return dict(native_cases=len(captures), recording_files=1, recording_rows=len(rows),
                preflight_rows=0, six_view_clicks=True, after_completion_rows=0,
                scope='Synthetic data and simulated Unity/Python notifications; not LIVE_E2E')


if __name__ == '__main__':
    print(json.dumps(verify(sys.argv[1]),ensure_ascii=False,indent=2))
