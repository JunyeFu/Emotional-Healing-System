"""Export closed development recordings without changing their original bytes."""
import csv
import json
from pathlib import Path
import zipfile


def export_record(path):
    path=Path(path)
    rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    if not rows or rows[-1]['kind'] not in ('completed','aborted'):
        raise ValueError('EXPORT_REQUIRES_CLOSED_RECORD')
    out=path.parent.parent/'exports'/path.stem
    out.mkdir(parents=True,exist_ok=False)
    counts={}
    fields=['source_id','packet_seq','sample_index','source_time_s','received_ns','value','unit',
            'acc_x','acc_y','acc_z','gyro_x','gyro_y','gyro_z','hr_bpm','rr_ms','quality']
    with (out/'samples.csv').open('w',newline='',encoding='utf-8-sig') as f, (out/'events.csv').open('w',newline='',encoding='utf-8-sig') as ef:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        events=csv.writer(ef); events.writerow(['kind','received_ns','payload_json'])
        for row in rows:
            p=row['payload']
            if p.get('message_type')!='device_preview':
                events.writerow([row['kind'],row['received_ns'],json.dumps(p,ensure_ascii=False)])
                continue
            counts[p['source_id']]=counts.get(p['source_id'],0)+len(p['samples'])
            for i,value in enumerate(p['samples']):
                r=dict(source_id=p['source_id'],packet_seq=p['packet_seq'],sample_index=i,
                    source_time_s=p['last_sample_monotonic_ns']/1e9-(len(p['samples'])-1-i)/p['sample_rate_hz'],
                    received_ns=row['received_ns'],value=value,unit=p['unit'],hr_bpm=p.get('hr_bpm'),rr_ms=p.get('rr_ms'),quality=p.get('quality','UNKNOWN'))
                for channel,prefix in (('acceleration','acc'),('angular_velocity','gyro')):
                    for axis in 'xyz':
                        r[prefix+'_'+axis]=p.get(channel,{}).get(axis,[None]*len(p['samples']))[i]
                writer.writerow(r)
    summary=dict(source_mode='dev_mock',session_id=rows[0]['payload']['session_id'],sample_counts=counts,
                 missing_values='empty CSV cell, never zero-filled',original=path.name)
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as z:
        for f in out.iterdir(): z.write(f,f.name)
    return out.with_suffix('.zip'),summary
