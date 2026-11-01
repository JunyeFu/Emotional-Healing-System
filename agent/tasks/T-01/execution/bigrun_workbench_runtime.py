"""Embedded BigRun frontend, using the existing aligned native workbench geometry."""
import json
import os
from pathlib import Path
import time
import types

ROOT = '/project1/T01_TelemetryPanel'
SHELL = ROOT + '/WorkbenchA'
model_module = types.ModuleType('td_bigrun_preview')
exec(op(SHELL + '/Logic/device_preview_source').text, model_module.__dict__)
wave_module = types.ModuleType('td_waveform')
exec(op(SHELL + '/Logic/session_source').text, wave_module.__dict__)
preview = model_module.BigRunPreview()
selected = {'resp': 'resp', 'ecg': 'ecg'}
page_name = 'home'
return_page = 'home'
raw_expanded = False
last_tick = None
interface_error = None
_opened = False


def ingest_monitor(raw, now):
    return preview.ingest(raw, now)


def select_curve(source, key):
    if key not in model_module.VIEWS[source]:
        raise ValueError('BIGRUN_CURVE_UNAVAILABLE')
    selected[source] = key


def design_action(name):
    global page_name, return_page, raw_expanded, interface_error
    if not preview.action_allowed(name):
        interface_error = '实验桥未接入'
        return False
    interface_error = None
    if name == 'new':
        page_name = 'prepare'
    elif name == 'cancel':
        page_name = 'home'
    elif name in ('details', 'history'):
        if page_name not in ('details', 'unselected'):
            return_page = page_name
        page_name = 'details' if name == 'details' else 'unselected'
    elif name == 'back':
        page_name = return_page
    elif name == 'raw':
        raw_expanded = not raw_expanded
    elif name == 'copy':
        ui.clipboard = preview.stream_id or ''
    elif name == 'open':
        path = Path(preview.status.get('archive', ''))
        allowed = (Path(project.folder) / '../../../local/artifacts/bigrun-preflight').resolve()
        if path.is_dir() and path.resolve().is_relative_to(allowed):
            os.startfile(str(path.resolve()))
    return True


def plot(source, width, height):
    import numpy as np
    series = preview.series(selected[source], time.monotonic_ns())
    if not series:
        return wave_module.raster_waveform(dict(points=()), width, height)
    if selected[source] == 'acceleration':
        result = np.ones((height, width, 4), dtype=np.float32)
        for i, item in enumerate(series):
            lo, hi = round(height * (2-i)/3), round(height * (3-i)/3)
            result[lo:hi] = wave_module.raster_waveform(item, width, hi-lo)
        return result
    return wave_module.raster_waveform(series[0], width, height)


def onFrameStart(frame):
    global last_tick, _opened
    now = time.monotonic_ns()
    if last_tick is not None and now - last_tick < 50_000_000:
        return
    last_tick = now
    # No downstream consumer remains after disabling the legacy renderer.
    op(ROOT + '/Sources/UdpTelemetryAdapter/udp_in').cook(force=True)
    if not _opened:
        _opened = True
        op('/perform').par.winopen.pulse()
    shell = op(SHELL)
    root = shell.op('Design')
    fields = preview.fields(now)
    shell.store('design_page', page_name)
    # These all-page labels are deliberately short; no explanatory footers.
    replacements = {'呼吸胸带': '呼吸代理', '心电胸带': '心电通道', 'respiBAN BLE': 'BigRun Team',
                    'Polar H10': 'BigRun Team', '模拟模式': 'BigRun 待实测',
                    '信号质量': '质量状态', '原始采样': '输出率', '复制会话编号': '复制采集编号',
                    'X 实测呼吸': 'X 呼吸代理', '实际呼吸': '呼吸代理',
                    '运动通道': '三轴 ACC', '最近数据': '时轴',
                    '未准备': '待实测', '呼吸 / 心电': 'BigRun BLE'}
    for page in root.panelChildren:
        page.par.display = page.name == page_name
        for node in page.findChildren(type=textCOMP):
            value = node.fetch('design_text', '')
            if value in replacements:
                node.par.text = replacements[value]
            if node.name == 'manual_mode':
                node.par.text = 'BigRun 待实测'
            curve = node.fetch('design_curve', None)
            act = node.fetch('design_action', None)
            if curve:
                node.par.display = curve[1] != 'angular_velocity'
                node.par.enable = curve[1] in model_module.VIEWS[curve[0]]
                if curve[1] == 'resp':
                    node.par.text = '呼吸代理'
                elif curve[1] == 'rr':
                    node.par.text = '原生 RR'
                node.par.opacity = 1 if selected[curve[0]] == curve[1] else .6
            if act:
                enabled = preview.action_allowed(act)
                if act == 'open':
                    enabled = enabled and bool(fields['archive'])
                node.par.enable = enabled
                node.par.opacity = 1 if enabled else .4
            x, y = node.fetch('design_xy', (-1, -1))
            if x == 36 and y == 674:
                node.par.display = False
    p = root.op(page_name)
    def put(index, value):
        node = p.op('c_' + page_name + '_' + str(index))
        if node is not None:
            node.par.text = str(value)
    put(12, interface_error or ('采集异常' if fields['error'] else fields['connection']))
    for i, v in ((14, '未分配'), (16, '未分配'), (18, '未建场'), (20, '00:00'), (22, '00:00')):
        put(i, v)
    if page_name == 'home':
        for i, v in {23: fields['connection'], 24: 'BigRun Team', 27: fields['resp_calibration'],
                     28: '呼吸代理', 31: fields['heart_calibration'], 32: '心率校准',
                     34: fields['resp_state'], 35: fields['ecg_state'], 36: '实验 0 场'}.items():
            put(i, v)
    if page_name in ('prepare', 'waiting', 'running', 'paused', 'abort', 'fault'):
        for n in p.findChildren(type=textCOMP):
            x, y = n.fetch('design_xy', (-1, -1))
            source = 'resp' if y < 400 else 'ecg'
            key = selected[source]
            series = preview.series(key, now)
            bounds = series[0]['range'] if series else None
            value = None
            if x == 570 and y in (163, 413): value = fields[source + '_state']
            if x == 36 and y in (199, 449):
                value = model_module.LABELS[key] + ' / ' + model_module.UNITS[key]
                n.par.display = True
            if x == 726 and y in (199, 449):
                value = '名义时轴' if preview.status.get(('acc' if source == 'resp' else 'ecg') + '_hz_nominal') else '接收时轴'
                n.par.display = True
            base = 0 if source == 'resp' else 250
            if x == 29 and y-base in (224, 279, 334):
                value = (format(bounds[1 if y-base == 224 else 0], '.1f') if bounds else '—') if y-base != 279 else ''
            if x in (40, 418, 796) and y-base == 345:
                value = {40: '-00:06' if key == 'ecg' else '-00:30', 418: '', 796: '00:00'}[x]
            if x == 418 and y in (367, 617): value = fields[source + '_rate']
            if x == 638 and y == 367: value = fields['resp_calibration']
            if x == 638 and y == 617: value = 'HR ' + fields['heart_rate'] + '  RR ' + fields['rr_interval']
            if x == 1040 and y in (207, 251): value = '未接入'
            if x == 1040 and y == 295: value = '未识别'
            if x == 1048 and y in (386, 443, 500): value = '未识别' if y == 500 else '未接入'
            if x == 896 and y == 566: value = fields['gate']
            if value is not None: n.par.text = str(value)
        if page_name == 'prepare':
            for i, v in {88:'未分配', 91:'待回执', 94:'未接入', 97:'待回执', 100:'原始采集' if fields['archive'] else '未接入',
                         103:fields['connection'], 105:fields['gate']}.items(): put(i, v)
        if page_name == 'fault': put(110, fields['error'] or fields['gate'])
        if page_name == 'abort': put(115, '未建场')
    if page_name in ('closeout', 'closed'):
        for i, v in {26:'BigRun Team', 28:'总历时 00:00', 31:'未开始', 34:'未封存',
                     37:'待回执', 40:'不可导出', 42:fields['gate']}.items(): put(i, v)
    if page_name == 'details':
        for i, v in {26:'BigRun Team', 31:fields['connection'], 33:fields['resp_calibration'],
                     35:fields['resp_rate'], 37:fields['motion_state'], 39:fields['timing'],
                     44:fields['ecg_state'], 46:fields['heart_calibration'], 48:fields['ecg_rate'],
                     50:'ECG / RR / HR / ACC', 52:fields['timing'], 56:'采集包 ' + str(preview.accepted),
                     58:'丢包 ' + str(preview.lost) + ' / 拒收 ' + str(preview.rejected)}.items(): put(i, v)
        put(59, '收起原始协议字段' if raw_expanded else '展开原始协议字段')
        p.op('raw').par.display = raw_expanded
        p.op('raw/body').par.text = json.dumps(dict(status=preview.status, latest=preview.raw,
                                                   error=preview.last_error), ensure_ascii=False, indent=2)
    if page_name in ('history', 'unselected'):
        put(20, '实验记录 · 共 0 场')
        put(21, '未开始')
        put(58, '暂无实验记录')
        put(60, '')
    for source in ('resp', 'ecg'):
        shell.op('Logic/plot_' + source).cook(force=True)


def onExit():
    pass
