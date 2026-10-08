"""Reproducible synthetic samples, independent signal estimates and Unity peer states."""
import argparse
import json
from pathlib import Path

import neurokit2 as nk
import numpy as np
from scipy.signal import butter, sosfilt, find_peaks

WEATHER = ('storm', 'heat', 'snow', 'fade')
STEPS = {'storm': (3, 3, 3, 3), 'heat': (4, 6), 'snow': (5, 5), 'fade': (2.5, 1.5, 6)}
NAMES = {'storm': ('吸气', '保持', '呼气', '保持'), 'heat': ('吸气', '呼气'),
         'snow': ('吸气', '呼气'), 'fade': ('吸气', '吸气', '呼气')}


def ideal(t):
    position = min(int(t // 200), 3)
    local = t - position * 200
    return WEATHER[position], 'demo' if local < 25 else 'closed_loop' if local < 175 else 'lock_transition', local


def step(weather, phase):
    durations = STEPS[weather]
    value = phase % sum(durations)
    for i, length in enumerate(durations):
        if value < length:
            return i, NAMES[weather][i], value / length
        value -= length
    raise AssertionError('step range')


def make(root, profile, seed=20261008):
    """800 effective seconds plus a 10-second pause, or an aborted 400-second run."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    duration = 810 if profile != 'abort' else 400
    rng = np.random.default_rng(seed)
    te = np.arange(duration * 130) / 130
    tr = np.arange(duration * 400) / 400
    # ECGSYN morphology and beat variability; amplitude is a declared fixture scale.
    ecg = nk.ecg_simulate(duration=duration, sampling_rate=130, heart_rate=72,
                          heart_rate_std=2, noise=.01, method='ecgsyn', random_state=seed) * 900
    clean = nk.ecg_clean(ecg, sampling_rate=130)
    _, info = nk.ecg_peaks(clean, sampling_rate=130)
    peaks = np.asarray(info['ECG_R_Peaks'])
    rr_t = peaks[1:] / 130
    rr = np.diff(peaks) / 130 * 1000
    effective = tr - np.clip(tr - 320, 0, 10) if duration == 810 else tr
    # Participant oscillator is independent of I/G: rhythm errors, amplitude drift and holds.
    resp = np.zeros_like(tr)
    for k, weather in enumerate(WEATHER):
        mask = (effective >= k*200) & (effective < (k+1)*200)
        local = tr[mask] - k*200
        phase = (local + .35*np.sin(local/17)) % (sum(STEPS[weather]) * 1.07)
        phase /= 1.07
        if weather == 'storm':
            values = np.interp(phase, [0,3,6,9,12], [0,1,.97,0,0])
        elif weather == 'fade':
            values = np.interp(phase, [0,2.5,2.8,4,10], [0,.72,.69,1,0])
        else:
            values = np.interp(phase, [0,STEPS[weather][0],10], [0,1,0])
        resp[mask] = values
    resp *= 1 + .09*np.sin(tr/21)
    resp += .04*np.sin(tr/37) + rng.normal(0,.008,len(tr))
    acc = rng.normal(0,.025,(len(tr),3)); acc[:,2] += 9.80665
    gyro = rng.normal(0,.003,(len(tr),3))
    motion = (tr >= 240) & (tr < 248)
    resp[motion] += .35*np.sin(tr[motion]*15)
    acc[motion,0] += 2*np.sin(tr[motion]*12)
    gyro[motion,1] += .4*np.sin(tr[motion]*12)
    missing = (tr >= 460) & (tr < 465)
    resp[missing] = np.nan; acc[missing] = np.nan; gyro[missing] = np.nan
    # Causal filter/difference uses only raw samples; never consumes I/G or generator labels.
    filtered = sosfilt(butter(2, 1, fs=400, output='sos'), np.nan_to_num(resp))
    slope = (filtered - np.concatenate((np.repeat(filtered[0],80),filtered[:-80]))) / .2
    actual = np.where(slope > .045, 1, np.where(slope < -.045, -1, 0))
    quality = np.full(len(tr), 'GOOD', dtype='<U12')
    quality[motion] = 'DEGRADED'; quality[missing] = 'DISCONNECTED'
    quality[(tr >= 465) & (tr < 467)] = 'UNUSABLE'
    actual[quality != 'GOOD'] = 9
    np.savez_compressed(root/'raw.npz', ecg_uV=ecg, resp_relative=resp, acceleration=acc,
                        angular_velocity=gyro, rr_t=rr_t, rr_ms=rr, actual=actual, quality=quality)
    # Adaptation is a declared test policy, not the unapproved research controller.
    frames=[]; gphase=0.; prev_weather=None; scale=1.; prior_actual=None
    for i in range(duration*10):
        t = i/10
        e = t-min(max(t-320,0),10) if duration==810 else t
        weather, segment, local = ideal(e)
        if weather != prev_weather:
            gphase=0.; scale=1.; prev_weather=weather
        ii, iname, _ = step(weather,local)
        gi,gname,_ = step(weather,gphase)
        a = int(actual[min(i*40+39,len(actual)-1)])
        q = str(quality[min(i*40+39,len(quality)-1)])
        if profile == 'B' and gphase % sum(STEPS[weather]) < .11 and prior_actual is not None:
            scale = 1.05 if prior_actual != 1 else 1.
        paused = duration==810 and 320 <= t < 330
        frames.append(dict(t_s=t,effective_s=e,weather=weather,segment=segment,
            ideal=iname,guide=gname if profile=='B' else iname,
            actual={1:'吸气',-1:'呼气',0:'保持',9:'未接入'}[a], quality=q,
            ideal_step=ii,guide_step=gi if profile=='B' else ii,
            unity_state='PAUSED' if paused else 'RUNNING',condition='B' if profile=='B' else 'A',
            guide_scale=scale if profile=='B' else 1., render_seq=i,
            render_ack='simulated',source_mode='dev_mock'))
        if not paused:
            gphase += .1/scale
        prior_actual=a
    with (root/'unity-state.jsonl').open('w',encoding='utf-8') as f:
        for frame in frames:
            f.write(json.dumps(frame,ensure_ascii=False)+'\n')
    # No efficacy trend is built into the heart signal or questionnaires.
    meta=dict(profile=profile,seed=seed,duration_s=duration,effective_s=800 if duration==810 else 400,
        neurokit_version=nk.__version__,ecg_hz=130,resp_hz=400,motion_hz=400,
        signal_origin='synthetic_sensor_domain_not_vendor_notification_bytes',
        duration_status='candidate_not_frozen',condition=frames[0]['condition'],
        respiration_unit='relative_not_litres',estimated_rr_count=len(rr),
        ecg_samples=len(ecg),resp_samples=len(resp),unity_frames=len(frames),
        mean_hr_bpm=float(np.mean(60000/rr)),rr_rmssd_ms=float(np.sqrt(np.mean(np.diff(rr)**2))),
        missing_resp_samples=int(missing.sum()),motion_s=8,
        analysis_scope='Python causal respiration estimate; offline ECG peaks and descriptive RR, not online validation')
    (root/'manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    return meta


def nullable(values):
    return [float(v) if np.isfinite(v) else None for v in values]


class Replay:
    def __init__(self, root, session):
        root=Path(root)
        with np.load(root/'raw.npz') as archive:
            self.data={key:archive[key] for key in archive.files}
        self.meta=json.loads((root/'manifest.json').read_text())
        self.frames=[json.loads(x) for x in (root/'unity-state.jsonl').read_text(encoding='utf-8').splitlines()]
        self.session=session

    def packets(self, index):
        f=self.frames[index]; end_ns=round((index+1)*.1*1e9)
        for source,rate,key,unit in (('plux_respiban',400,'resp_relative','relative'),('polar_h10_ecg',130,'ecg_uV','uV')):
            n=rate//10; start=index*n; end=start+n
            p=dict(message_type='device_preview',preview_version='1.0',source_id=source,source_mode='dev_mock',
                session_id=self.session,clock_domain_id='synthetic:source-time',packet_seq=index,
                last_sample_monotonic_ns=end_ns-round(1e9/rate),sent_monotonic_ns=end_ns,
                sample_rate_hz=rate,unit=unit,samples=nullable(self.data[key][start:end]),
                device_state='DISCONNECTED' if source=='plux_respiban' and f['quality']=='DISCONNECTED' else 'CONNECTED',
                source_elapsed_s=f['t_s'],quality=f['quality'] if source=='plux_respiban' else 'GOOD')
            if source=='plux_respiban':
                p['motion_state']='DISCONNECTED' if f['quality']=='DISCONNECTED' else 'LIVE'
                for channel,units in (('acceleration','m/s2'),('angular_velocity','rad/s')):
                    p[channel]={axis:nullable(self.data[channel][start:end,k]) for k,axis in enumerate('xyz')}
                    p[channel+'_unit']=units
            else:
                j=np.searchsorted(self.data['rr_t'],(index+1)/10,side='right')-1
                rr=float(self.data['rr_ms'][j]) if j>=0 else None
                p.update(rr_ms=rr,hr_bpm=60000/rr if rr else None,rr_state='LIVE' if rr else 'UNKNOWN')
            yield p


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output'); args=parser.parse_args()
    for j,profile in enumerate(('A','B','abort')):
        print(make(Path(args.output)/profile,profile,20261008+j),flush=True)
