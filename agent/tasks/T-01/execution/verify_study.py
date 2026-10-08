"""Compare received/exported samples with the generated inputs, not UI appearances."""
import argparse
import csv
import json
from pathlib import Path
import zipfile

import numpy as np


def verify(evidence,dataset):
    evidence=Path(evidence); dataset=Path(dataset)
    inputs=json.loads((evidence/'study-inputs.json').read_text())
    history=json.loads((evidence/'development-workflow/workflow.json').read_text())
    assert len(history)==3
    report=[]
    for run,item in zip(inputs['runs'],history):
        assert run['session_id']==item['session_id']
        assert item['closed'] and item['sealed'] and item['posttest']
        assert item['status']==('ABORTED' if run['profile']=='abort' else 'COMPLETED')
        assert item['effective_ns']==run['effective_s']*1e9
        path=evidence/'development-workflow'/item['path']
        rows=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
        assert rows[0]['kind']=='started' and rows[-1]['kind'] in ('completed','aborted')
        assert all(r['payload']['session_id']==item['session_id'] for r in rows)
        packets=[r['payload'] for r in rows if r['payload'].get('message_type')=='device_preview']
        assert len(packets)==run['source_packets'],(run['profile'],len(packets),run['source_packets'])
        raw=np.load(dataset/run['profile']/'raw.npz')
        for source,key in (('plux_respiban','resp_relative'),('polar_h10_ecg','ecg_uV')):
            selected=[p for p in packets if p['source_id']==source]
            assert [p['packet_seq'] for p in selected]==list(range(run['unity_frames']))
            assert all(p['clock_domain_id']=='synthetic:source-time' for p in selected)
            actual=np.array([v if v is not None else np.nan for p in selected for v in p['samples']])
            assert np.array_equal(actual,raw[key],equal_nan=True)
        guidance=[r['payload'] for r in rows if r['payload'].get('event')=='guidance_status']
        unity=[r['payload'] for r in rows if r['payload'].get('event')=='study_status' and 'unity' in r['payload']]
        assert len(guidance)==len(unity)==run['unity_frames']
        assert {p['weather'] for p in unity}==({'storm','heat'} if run['profile']=='abort' else {'storm','heat','snow','fade'})
        for weather in {p['weather'] for p in unity}:
            assert {p['segment'] for p in unity if p['weather']==weather}=={'demo','closed_loop','lock_transition'}
        if run['profile']!='abort':
            paused=[p for p in unity if p['unity']['unity_state']=='PAUSED']
            assert len(paused)==100
            assert {p['effective_s'] for p in paused}=={320.}
            assert len({p['unity']['guide_step'] for p in paused})==1
            assert all(guidance[i]['actual']=='未接入' for i,p in enumerate(unity) if p['quality']!='GOOD')
        difference=sum(p['ideal']!=p['guide'] for p in guidance)
        assert difference>0 if run['profile']=='B' else difference==0
        with (evidence/('analysis-'+run['profile']+'.csv')).open('w',newline='',encoding='utf-8-sig') as out:
            writer=csv.writer(out)
            writer.writerow(['weather','frame_count','known_X_fraction','I_G_different_fraction','note'])
            for weather in ('storm','heat','snow','fade'):
                indices=[i for i,p in enumerate(unity) if p['weather']==weather]
                if indices:
                    writer.writerow([weather,len(indices),sum(guidance[i]['actual']!='未接入' for i in indices)/len(indices),
                        sum(guidance[i]['ideal']!=guidance[i]['guide'] for i in indices)/len(indices),
                        'synthetic descriptive process metrics; not research outcomes'])
        exported=evidence/'development-workflow/exports'/path.stem
        assert exported.with_suffix('.zip').is_file()
        counts={}; missing=0
        with (exported/'samples.csv').open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                counts[r['source_id']]=counts.get(r['source_id'],0)+1
                missing+=r['value']==''
        assert counts=={'plux_respiban':run['resp_samples'],'polar_h10_ecg':run['ecg_samples']}
        assert missing==run['missing_resp_samples']
        with zipfile.ZipFile(exported.with_suffix('.zip')) as z: assert z.testzip() is None
        report.append(dict(profile=run['profile'],session_id=run['session_id'],
            effective_s=run['effective_s'],elapsed_s=run['duration_s'],sample_counts=counts,
            source_to_td_sample_equality=True,export_missing_samples=missing,
            unity_frames=len(unity),I_G_different_frames=difference,
            estimates='Python; TD only displays and exports',
            mean_hr_bpm=run['mean_hr_bpm'],rr_rmssd_ms=run['rr_rmssd_ms']))
    captures=json.loads((evidence/'capture-report.json').read_text(encoding='utf-8'))['captures']
    assert all(not r['errors'] and len(r['visible_pages'])==1 for r in captures)
    assert all(r['workflow']['record_count']==0 for r in captures if r['workflow']['stage'] in ('PREPARE','WAITING'))
    result=dict(passed=True,runs=report,native_checks=len(captures),playback_speed=inputs['speed'],
        boundaries=['synthetic samples not vendor BLE bytes','simulated Unity peer not Unity rendering',
                    'accelerated replay not real-time performance evidence','800s candidate not research freeze'])
    (evidence/'study-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('evidence'); p.add_argument('dataset'); a=p.parse_args()
    print(json.dumps(verify(a.evidence,a.dataset),ensure_ascii=False,indent=2))
