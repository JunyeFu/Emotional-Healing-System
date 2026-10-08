"""Verify native consecutive-session UI and isolated development recordings."""
from pathlib import Path
import json
import sys


def verify(root):
    root=Path(root)
    report=json.loads((root/'capture-report.json').read_text(encoding='utf-8'))
    cases=report['captures']
    assert len(cases)==35
    assert all(not c['errors'] and len(c['visible_pages'])==1 for c in cases)
    final=cases[-1]['workflow']
    assert final['stage']=='HOME' and final['current'] is None
    history=final['history']
    assert [x['status'] for x in history]==['COMPLETED','ABORTED','COMPLETED']
    assert all(x['closed'] and x['sealed'] and x['posttest'] for x in history)
    assert len({x['session_id'] for x in history})==3
    recordings=list((root/'development-workflow'/'recordings').glob('*.jsonl'))
    assert len(recordings)==3
    counts=[]
    for path in recordings:
        rows=[json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()]
        assert rows[0]['kind']=='started' and rows[-1]['kind'] in ('completed','aborted')
        assert len({r['payload']['session_id'] for r in rows})==1
        assert rows[0]['payload']['session_id'] in {x['session_id'] for x in history}
        assert all(rows[0]['received_ns']<=r['received_ns']<=rows[-1]['received_ns'] for r in rows)
        counts.append(len(rows))
    for c in cases:
        flow=c['workflow']
        if flow['stage'] in ('PREPARE','WAITING'):
            assert flow['record_count']==0
        if 'next-blocked' in c['screenshot']:
            assert not flow['can_close'] and flow['stage']=='CLOSEOUT'
        if 'closeout-ready' in c['screenshot']:
            assert flow['can_close'] and not flow['error']
    paused=[c['workflow'] for c in cases if c['screenshot'].endswith(('paused.png','paused-again.png'))]
    assert paused[0]['effective_ns']==paused[1]['effective_ns']
    assert paused[1]['elapsed_ns']>paused[0]['elapsed_ns']
    assert paused[1]['record_count']>paused[0]['record_count']
    first=next(c for c in cases if c['screenshot'].endswith('1-ready.png'))
    second=next(c for c in cases if c['screenshot'].endswith('2-ready.png'))
    assert first['session_capture']['curves']=={'resp':'acceleration','ecg':'rr'}
    assert second['session_capture']['curves']=={'resp':'angular_velocity','ecg':'hr'}
    for c in (first,second):
        colors=c['device_preview']['plots']['resp']['color_pixels']
        assert all(colors[x]>10 for x in ('x','y','z'))
    assert first['device_preview']['plots']['ecg']['color_pixels']['rr']>10
    assert report['source_preserved']
    assert (root/'T01_Workbench_A.flow-v5.candidate.toe').is_file()
    return dict(native_cases=35, consecutive_sessions=3, normal=2, aborted=1,
                record_counts=counts, independent_files=True, preflight_rows=0,
                one_visible_page=True, pause_freezes_effective_time=True,
                scope='Development fixtures and simulated authority receipts, not formal experiment acceptance')


if __name__=='__main__':
    print(json.dumps(verify(sys.argv[1]),ensure_ascii=False,indent=2))
