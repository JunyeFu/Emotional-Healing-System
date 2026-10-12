"""Known calibration signals for testing TD plots, not physiological observations."""
import math


def packets(index, session_id, origin_ns=1_000_000_000, missing=False):
    for source, rate, unit in (('plux_respiban',400,'relative'),('polar_h10_ecg',130,'uV')):
        count=rate//10
        ts=[index/10+j/rate for j in range(count)]
        end=origin_ns+round(ts[-1]*1e9)
        values=[.5+.4*math.sin(2*math.pi*.2*t) if source=='plux_respiban'
                else 1000*math.sin(2*math.pi*t) for t in ts]
        p=dict(message_type='device_preview',preview_version='1.0',source_mode='dev_mock',
               session_id=session_id,clock_domain_id='mock:continuity-calibration',
               source_id=source,sample_rate_hz=rate,unit=unit,packet_seq=index,
               last_sample_monotonic_ns=end,sent_monotonic_ns=origin_ns+round((index+1)*1e8),
               samples=[None]*count if missing else values,device_state='CONNECTED')
        if source=='plux_respiban':
            p.update(motion_state='LIVE',acceleration_unit='m/s2',angular_velocity_unit='rad/s')
            p['acceleration']={axis:[None if missing else value(t) for t in ts]
                for axis,value in {'x':lambda t:2*math.sin(2*math.pi*.2*t),
                    'y':lambda t:3*math.cos(2*math.pi*.2*t),
                    'z':lambda t:9.81+.5*math.sin(2*math.pi*.1*t)}.items()}
            p['angular_velocity']={axis:[None if missing else value(t) for t in ts]
                for axis,value in {'x':lambda t:.5*math.sin(2*math.pi*.2*t),
                    'y':lambda t:.25*math.cos(2*math.pi*.2*t),
                    'z':lambda t:.1*math.sin(2*math.pi*.1*t)}.items()}
        else:
            hr=72+6*math.sin(2*math.pi*.05*ts[-1])
            p.update(hr_bpm=None if missing else hr,rr_ms=None if missing else 60000/hr,
                     rr_state='UNKNOWN' if missing else 'LIVE')
        yield p
