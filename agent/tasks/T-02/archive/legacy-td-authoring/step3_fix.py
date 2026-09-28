"""Step 3: Add circle animation + phase color driving to onReceive callback"""
parser = op('/project1/SRP_BreathGuide/UDP_Input/json_parser')

parser.text = """import json

def onReceive(dat, rowIndex, message, byteData, peer):
    dc = op('/project1/SRP_BreathGuide/Data_CHOPs')
    mon = op('/project1/SRP_BreathGuide/Monitor_Panel')
    bg = op('/project1/SRP_BreathGuide/Breath_Guide')
    try:
        data = json.loads(message)
    except:
        try:
            data = json.loads(byteData.decode('utf-8'))
        except:
            return

    scores = data.get('scores', {})
    ch_map = {
        'breath_sync': 'ch_breath_sync',
        'breath_depth': 'ch_breath_depth',
        'hrv_coherence': 'ch_hrv_coherence',
        'eda_calm': 'ch_eda_calm',
    }
    for key, ch_name in ch_map.items():
        ch = dc.op(ch_name)
        if ch:
            val = scores.get(key, 0.0)
            if isinstance(val, (int, float)):
                ch.par.value0 = val

    weather = data.get('weather', {})
    wi = dc.op('ch_weather_intensity')
    if wi: wi.par.value0 = float(weather.get('intensity', 0.0))

    breath = data.get('breath', {})
    cr = dc.op('ch_circle_radius')
    if cr: cr.par.value0 = float(breath.get('circle_radius', 0.3))
    pn = dc.op('ch_phase_num')
    if pn:
        phase_map = {'inhale': 0, 'hold': 1, 'exhale': 2}
        pn.par.value0 = phase_map.get(str(breath.get('phase', 'inhale')), 0)

    cardiac = data.get('cardiac', {})
    hr_ch = dc.op('ch_hr')
    if hr_ch: hr_ch.par.value0 = float(cardiac.get('hr', 0))
    rr_ch = dc.op('ch_rr')
    if rr_ch: rr_ch.par.value0 = float(breath.get('rate', 0))

    # ============================================================
    # 引导圈动画驱动 (Step 3)
    # ============================================================
    radius = float(breath.get('circle_radius', 0.3))
    xform = bg.op('circle_xform')
    if xform:
        xform.par.sx = radius
        xform.par.sy = radius

    phase = str(breath.get('phase', 'inhale'))
    tint = bg.op('phase_tint')
    if tint:
        if phase == 'inhale':
            tint.par.fillcolorr = 0.1
            tint.par.fillcolorg = 0.8
            tint.par.fillcolorb = 0.2
        elif phase == 'hold':
            tint.par.fillcolorr = 0.9
            tint.par.fillcolorg = 0.8
            tint.par.fillcolorb = 0.1
        else:  # exhale
            tint.par.fillcolorr = 0.1
            tint.par.fillcolorg = 0.3
            tint.par.fillcolorb = 0.8

    # ============================================================
    # 监控台文本刷新
    # ============================================================
    guidance = data.get('guidance', {})
    tp = mon.op('txt_prompt')
    if tp: tp.par.text = str(guidance.get('prompt', ''))

    for key in ch_map:
        txt = mon.op('txt_' + key)
        if txt:
            txt.par.text = key.replace('_', ' ') + ': ' + str(round(scores.get(key, 0), 1))

    tw = mon.op('txt_weather')
    if tw: tw.par.text = 'Weather: ' + str(weather.get('type', '--')) + ' (' + str(round(weather.get('intensity', 0), 1)) + ')'

    th = mon.op('txt_hr')
    if th: th.par.text = 'HR: ' + str(int(cardiac.get('hr', 0))) + ' BPM  RR: ' + str(int(breath.get('rate', 0))) + ' bpm'
"""

print("Step 3: onReceive updated with circle animation + phase color")
print("Script size:", len(parser.text))
print("DONE")
