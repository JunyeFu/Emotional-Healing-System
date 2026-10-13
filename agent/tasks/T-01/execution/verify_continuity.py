"""Check native plot pixels and displayed numbers against known calibration inputs."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'modules/touchdesigner/t01_telemetry_panel'))
from workbench_session import COLORS,rgb,UNITS
from curve_continuity import packets


def verify(path):
    path=Path(path)
    inputs=json.loads((path/'continuity-inputs.json').read_text(encoding='utf-8'))
    captures=json.loads((path/'capture-report.json').read_text(encoding='utf-8'))['captures']
    rows=[]
    for receipt in captures:
        assert not receipt['errors'] and receipt['workflow']['record_count']==0
        for source,item in receipt.get('continuity',{}).items():
            key=item['key']
            p=item['payload']
            expected=next(p for p in packets(p['packet_seq'],inputs['session_id'],inputs['origin_ns'])
                          if p['source_id']==item['payload']['source_id'])
            assert p['sample_rate_hz']==(400 if source=='resp' else 130)
            assert item['plot_size']==[round(x) for x in item['displayed_size']]
            window=6 if key=='ecg' else 30
            assert item['axis_text']['axis_left']=='−00:'+str(window).zfill(2)
            assert item['axis_text']['axis']=='−00:'+str(window//2).zfill(2)
            assert item['axis_text']['axis_right']=='00:00'
            label=receipt['fields'][source+'_plot_label']['text']
            assert UNITS[key] in label and str(window)+'秒' in label
            assert receipt['fields'][source+'_rate']['text']==str(p['sample_rate_hz'])+' Hz'
            assert receipt['fields']['heart_rate']['text']==format(receipt['continuity']['ecg']['payload']['hr_bpm'],'.1f')
            assert receipt['fields']['rr_interval']['text']==format(receipt['continuity']['ecg']['payload']['rr_ms'],'.1f')
            image=np.asarray(Image.open(path/(Path(receipt['screenshot']).stem+'-'+source+'-plot.png'))).astype(float)/255
            for series in item['series']:
                axis=series['axis']
                target=(expected['samples'][-1] if key in ('resp','ecg') else
                        expected[key][axis][-1] if key in ('acceleration','angular_velocity') else
                        expected['hr_bpm' if key=='hr' else 'rr_ms'])
                assert abs(series['last_value']-target)<1e-8
                code=COLORS[axis] if axis in ('x','y','z') else COLORS[key]
                mask=abs(image[:,:,:3]-np.asarray(rgb(code))).max(axis=2)<.015
                coverage=float(mask.any(axis=0).mean())
                if '-continuous-' in receipt['screenshot']:
                    assert not series['has_gaps'] and coverage>.98,(key,axis,coverage)
                elif '-missing-' in receipt['screenshot'] or '-dropped-' in receipt['screenshot']:
                    assert series['has_gaps'],(key,receipt['screenshot'])
                else:
                    assert mask[:,-round(mask.shape[1]*.1):].any(axis=0).mean()>.98
                if '-missing-' in receipt['screenshot'] or '-dropped-' in receipt['screenshot']:
                    kind='missing' if '-missing-' in receipt['screenshot'] else 'dropped'
                    interval=next(g for g in inputs['intervals'] if g['kind']==kind)
                    start=series['end_ns']-window*1e9
                    left=round((inputs['origin_ns']+(interval['begin']/10+.3)*1e9-start)/(window*1e9)*(mask.shape[1]-1))
                    right=round((inputs['origin_ns']+(interval['end']/10-.3)*1e9-start)/(window*1e9)*(mask.shape[1]-1))
                    assert 0<=left<right<mask.shape[1],(key,left,right)
                    assert not mask[:,left:right].any(),(key,axis,'bridged missing interval')
                if axis=='value':
                    low,high=series['range']
                    assert item['axis_text']['ymax']==str(round(high,2))
                    assert item['axis_text']['ymin']==str(round(low,2))
                else:
                    idx=('x','y','z').index(axis)
                    low,high=series['range']
                    assert item['motion_labels'][idx]==axis.upper()+' '+format(high,'.2f')+'\n'+format(low,'.2f')
                rows.append(dict(screenshot=receipt['screenshot'],curve=key,axis=axis,
                    native_trace_column_fraction=coverage,unit=series['unit'],
                    window_s=window,has_gaps=series['has_gaps'],labels_match=True))
    assert {r['curve'] for r in rows}=={'resp','ecg','acceleration','angular_velocity','rr','hr'}
    assert {tuple(r['layout_size']) for r in captures}=={(1280,720),(1600,900),(1920,1080)}
    export_sizes=sorted({tuple(r['image_size']) for r in captures})
    assert (1280,720) in export_sizes
    for receipt in captures:
        assert Image.open(path/receipt['screenshot']).size==tuple(receipt['image_size'])
    result=dict(passed=True,native_captures=len(captures),checks=len(rows),recorded_experiment_rows=0,
                scope='six curve and label checks; native 1280x720 page and actual plot rasters',
                page_export_sizes=export_sizes,
                large_page_native_export_verified=all(r['image_size']==r['layout_size'] for r in captures),
                inputs=inputs,curves=rows)
    (path/'continuity-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='curves'},ensure_ascii=False,indent=2))
    return result


if __name__=='__main__':
    verify(sys.argv[1])
