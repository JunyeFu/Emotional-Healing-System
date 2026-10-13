"""SRP TD Builder — 一键重建完整节点树 + 连线 + UDP解析 (v2.1, 4-dim)

用法: 通过 WebServer DAT API (port 9980) 发送到 TD 执行
  python -c "
  import json, urllib.request
  code = open('build_srp.py', encoding='utf-8').read()
  req = urllib.request.Request('http://127.0.0.1:9980/api',
      data=json.dumps({'action':'execute','params':{'code':code}}).encode(),
      headers={'Content-Type':'application/json'})
  print(urllib.request.urlopen(req, timeout=60).read().decode())
  "
"""
root = op('/project1')

# ============================================================
# 0. 清理
# ============================================================
for name in ['SRP_BreathGuide']:
    existing = root.op(name)
    if existing:
        existing.destroy()
        print("- destroyed existing " + name)

# ============================================================
# 1. 根容器
# ============================================================
srp = root.create(containerCOMP, 'SRP_BreathGuide')
print("+ SRP_BreathGuide")

# ============================================================
# 2. UDP_Input — UDP In DAT 接收原始 JSON + 解析脚本
# ============================================================
udp = srp.create(containerCOMP, 'UDP_Input')

udp_in = udp.create(udpinDAT, 'udp_in')
try: udp_in.par.port = 5005
except: pass
try: udp_in.par.active = True
except: pass
try: udp_in.par.callbacks = 'json_parser'
except: pass
print("  + udp_in (port 5005)")

parser = udp.create(textDAT, 'json_parser')
parser.text = """import json

def onReceive(dat, rowIndex, message, byteData, peer):
    dc = op('/project1/SRP_BreathGuide/Data_CHOPs')
    mon = op('/project1/SRP_BreathGuide/Monitor_Panel')
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
print("  + json_parser (" + str(len(parser.text)) + " bytes)")

print("+ UDP_Input (2 nodes)")

# ============================================================
# 3. Data_CHOPs — 14 constant CHOPs
# ============================================================
dc = srp.create(containerCOMP, 'Data_CHOPs')
ch_names = [
    'ch_breath_sync', 'ch_breath_depth', 'ch_hrv_coherence',
    'ch_eda_calm', 'ch_weather_intensity', 'ch_circle_radius',
    'ch_phase_num', 'ch_hr', 'ch_rr'
]
for n in ch_names:
    ch = dc.create(constantCHOP, n)
    try: ch.par.value0 = 0.0
    except: pass
print("+ Data_CHOPs (" + str(len(ch_names)) + " nodes)")

# ============================================================
# 4. Breath_Guide — 引导圈
# ============================================================
bg = srp.create(containerCOMP, 'Breath_Guide')

bg_rect = bg.create(rectangleTOP, 'bg_rect')
for a in [('fillcolorr', 0.05), ('fillcolorg', 0.05), ('fillcolorb', 0.08)]:
    try: setattr(bg_rect.par, a[0], a[1])
    except: pass

circle = bg.create(circleTOP, 'guide_circle')
for a in [('fillcolorr', 0.3), ('fillcolorg', 0.7), ('fillcolorb', 0.3)]:
    try: setattr(circle.par, a[0], a[1])
    except: pass

xform = bg.create(transformTOP, 'circle_xform')
try: xform.par.sx = 0.3
except: pass
try: xform.par.sy = 0.3
except: pass

glow = bg.create(blurTOP, 'glow_blur')

tint = bg.create(rectangleTOP, 'phase_tint')
for a in [('fillcolorr', 0.0), ('fillcolorg', 0.3), ('fillcolorb', 0.6)]:
    try: setattr(tint.par, a[0], a[1])
    except: pass

gcomp = bg.create(compositeTOP, 'guide_comp')

# Breath_Guide 连线
circle.outputConnectors[0].connect(xform.inputConnectors[0])
xform.outputConnectors[0].connect(glow.inputConnectors[0])
bg_rect.outputConnectors[0].connect(gcomp.inputConnectors[0])
glow.outputConnectors[0].connect(gcomp.inputConnectors[1])
tint.outputConnectors[0].connect(gcomp.inputConnectors[2])
print("+ Breath_Guide (6 nodes, wired)")

# ============================================================
# 5. Monitor_Panel
# ============================================================
mon = srp.create(containerCOMP, 'Monitor_Panel')

mbg = mon.create(rectangleTOP, 'mon_bg')
for a in [('fillcolorr', 0.02), ('fillcolorg', 0.02), ('fillcolorb', 0.06)]:
    try: setattr(mbg.par, a[0], a[1])
    except: pass

labels = ['breath_sync', 'breath_depth', 'hrv_coherence', 'eda_calm']
for lb in labels:
    t = mon.create(textTOP, 'txt_' + lb)
    try: t.par.text = lb + ': --'
    except: pass
    try: t.par.fontsize = 16
    except: pass
    try: t.par.fontcolorr = 0.7
    except: pass
    try: t.par.fontcolorg = 0.7
    except: pass
    try: t.par.fontcolorb = 0.8
    except: pass

for name, txt, fs, cr, cg, cb in [
    ('txt_weather', 'Weather: --', 20, 1.0, 0.8, 0.3),
    ('txt_hr', 'HR: -- BPM  RR: -- bpm', 18, 0.9, 0.5, 0.4),
    ('txt_prompt', '', 22, 0.9, 0.9, 0.6),
]:
    t = mon.create(textTOP, name)
    try: t.par.text = txt
    except: pass
    try: t.par.fontsize = fs
    except: pass
    try: t.par.fontcolorr = cr
    except: pass
    try: t.par.fontcolorg = cg
    except: pass
    try: t.par.fontcolorb = cb
    except: pass

print("+ Monitor_Panel (" + str(len(labels) + 3) + " nodes)")

# ============================================================
# 6. Output
# ============================================================
out = srp.create(containerCOMP, 'Output')
fcomp = out.create(compositeTOP, 'final_comp')
dot = out.create(outTOP, 'display_out')

# 连线: Breath_Guide → Output
gcomp.outputConnectors[0].connect(fcomp.inputConnectors[0])

# 连线: Monitor_Panel → Output
if len(fcomp.inputConnectors) > 1:
    mbg.outputConnectors[0].connect(fcomp.inputConnectors[1])

# Output 内部
fcomp.outputConnectors[0].connect(dot.inputConnectors[0])
print("+ Output (2 nodes, wired)")

# ============================================================
# 7. 验证
# ============================================================
print()
print("=" * 50)
print("VERIFICATION")
print("=" * 50)
for cname in ['UDP_Input', 'Data_CHOPs', 'Breath_Guide', 'Monitor_Panel', 'Output']:
    c = srp.op(cname)
    children = [n.name for n in c.children] if c else []
    print("{}: {} nodes {}".format(cname, len(children), children))

total = sum(1 for _ in srp.children)
print("Total containers: " + str(total))
print("DONE - SRP node tree v2 ready")
