"""Build the device-separated native dashboard, leaving older candidates intact."""
from pathlib import Path

_legacy = Path(__file__).with_name('build_workbench_a.py')
exec(compile(_legacy.read_text(encoding='utf-8'), str(_legacy), 'exec'), globals())
CANDIDATE = 'T01_Workbench_A.devices-v3.candidate.toe'

DEVICE_CALLBACKS = '''
import builtins
import json
import time
def onReceive(dat, rowIndex, message, bytes, peer):
    raw = builtins.bytes(bytes)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        payload = None
    if isinstance(payload, dict) and payload.get('message_type') == 'device_preview':
        op('/project1/T01_TelemetryPanel/WorkbenchA/Logic/render').module.preview.ingest(raw, time.monotonic_ns())
    else:
        result = _adapter().ingest_datagram(raw, time.monotonic_ns())
        builtins.T01_LAST_INGEST = dict(accepted=result.accepted, disposition=result.disposition, code=result.code)
    return
'''

DEVICE_RUNTIME = '''
import time
import math
import types
device_module = types.ModuleType('td_device_preview')
exec(op('/project1/T01_TelemetryPanel/WorkbenchA/Logic/device_preview_source').text, device_module.__dict__)
DevicePreview, raster_waveform = device_module.DevicePreview, device_module.raster_waveform
preview = DevicePreview()
last_tick = None
streams = {}
ROOT = '/project1/T01_TelemetryPanel'

def _rgb(code):
    return tuple(int(code[i:i+2], 16) / 255 for i in (1, 3, 5))

def select_page(name):
    shell = op(ROOT + '/WorkbenchA')
    for page in shell.op('Content/Pages').panelChildren:
        page.par.display = page.name == name
    shell.store('active_page', name)
    for tab in shell.op('Content/Tabs').panelChildren:
        selected = tab.name == name
        tab.op('underline').par.display = selected
        tab.op('label').par.fontcolorr, tab.op('label').par.fontcolorg, tab.op('label').par.fontcolorb = _rgb('#235E8D' if selected else '#56616F')
    if name == 'timing':
        shell.op('Content/Pages/timing/details').panel.scrollv = 0

def onFrameStart(frame):
    global last_tick, streams
    now = time.monotonic_ns()
    if last_tick is not None and now - last_tick < 50_000_000:
        return
    last_tick = now
    root = op(ROOT)
    shell = root.op('WorkbenchA')
    snapshot = root.op('Sources/UdpTelemetryAdapter/udp_callbacks').module._adapter().read_snapshot(now)
    model = shell.op('Logic/view_model').module.view_model(snapshot)
    values = model['overview_values']
    values['status'] = 'TD 遥测：' + values['status']
    streams = preview.snapshot(now, snapshot.telemetry.get('session_id'))
    values['preview_status'] = '设备预览未接入'
    for source in ('resp', 'ecg'):
        stream = streams[source]
        payload = stream.get('payload', {})
        stale = stream['state'] == 'STALE'
        prefix = '历史 ' if stale else ''
        values[source + '_age'] = prefix + str(round(stream['age_ms'])) + ' ms' if payload else '未接入'
        values[source + '_rate'] = prefix + str(payload['sample_rate_hz']) + ' Hz' if payload else '未接入'
        values[source + '_wave_state'] = '末帧历史波形' if stale else ('模拟波形' if payload.get('source_mode') == 'dev_mock' else '真实预览') if payload else '波形未接入'
        samples = [value for _, value in stream['points'] if value is not None]
        values[source + '_max'] = str(round(max(samples), 2)) if samples else '—'
        values[source + '_min'] = str(round(min(samples), 2)) if samples else '—'
        if payload:
            values['preview_status'] = '设备预览：模拟输入' if payload['source_mode'] == 'dev_mock' else '设备预览：真实输入'
            if stale:
                values['preview_status'] += ' · 已断流'
        for key, field in (('hr_bpm', 'heart_rate'), ('rr_ms', 'rr_interval')):
            if source == 'ecg':
                val = payload.get(key)
                values[field] = prefix + format(val, '.1f') if val is not None else '未接入'
        if source == 'resp':
            values['motion_state'] = prefix + {'LIVE': '已接入', 'DISCONNECTED': '断流', 'UNKNOWN': '未知'}.get(payload.get('motion_state'), '未接入')
        else:
            values['rr_state'] = prefix + {'LIVE': '已接入', 'DISCONNECTED': '断流', 'UNKNOWN': '未知'}.get(payload.get('rr_state'), '未接入')
            values['ecg_wave_label'] = 'ECG (μV) | HR/RR：' + values['rr_state']
        shell.op('Logic/plot_' + source).cook(force=True)
    values['recording_state'] = '未接入'
    values['events_state'] = '事件通道未接入'
    values['module_position'] = str(snapshot.telemetry['module_position'] + 1) + '/4' if snapshot.telemetry else '—'
    for node in shell.findChildren(type=textCOMP):
        key = node.fetch('field', None)
        if key:
            value = values.get(key, '—')
            if key == 'session_id':
                value = shell.op('Logic/view_model').module.compact(value, 26)
            node.par.text = value
        status_key = node.fetch('status_key', None)
        if status_key:
            state = model['state'] if status_key == 'stream' else snapshot.telemetry.get(status_key, 'UNKNOWN')
            if model['state'] == 'DISCONNECTED' and status_key != 'stream':
                state = 'UNKNOWN'
            fg, bg = shell.fetch('status_colors').get(state, shell.fetch('status_colors')['UNKNOWN'])
            node.par.fontcolorr, node.par.fontcolorg, node.par.fontcolorb = _rgb(fg)
            node.par.bgcolorr, node.par.bgcolorg, node.par.bgcolorb = _rgb(bg)
            node.par.bgalpha = 1
        if key and ('历史' in node.par.text.eval() or '末帧' in node.par.text.eval()):
            node.par.fontcolorr, node.par.fontcolorg, node.par.fontcolorb = _rgb('#56616F')
    extra = shell.op('Logic/view_model').module.flatten({
        'device_preview': {key: {k: v for k, v in stream.get('payload', {}).items() if k != 'samples'} for key, stream in streams.items()},
        'preview_transport': dict(accepted=preview.accepted, rejected=preview.rejected, last_error=preview.last_error)})
    model['details'].update(extra)
    body = shell.op('Content/Pages/timing/details')
    template = shell.op('Logic/detail_template')
    y = 0
    for i, (key, value) in enumerate(model['details'].items()):
        row = body.op('item_' + str(i))
        if row is None:
            row = body.copy(template, name='item_' + str(i))
            row.par.display = True
        row.par.y.expr = 'parent().height - ' + str(y) + ' - me.height'
        row.par.w.expr = 'parent().width - 14'
        lines = max(math.ceil(len(key) / 42), math.ceil(len(value) / max(24, int((body.width * .60 - 24) / 16))))
        row.par.h = max(36, lines * 24 + 12)
        row.op('key').par.text = key
        row.op('value').par.text = value
        y += row.par.h.eval()
    for row in body.children:
        if row.name.startswith('item_') and int(row.name[5:]) >= len(model['details']):
            row.destroy()
'''


def build():
    import builtins
    root = op(ROOT)
    if Path(project.folder).resolve() != RUNTIME_DIR.resolve():
        raise RuntimeError('Build only in the dedicated candidate directory')
    for path in ('WorkbenchA', 'Output/workbench_a_view'):
        old = root.op(path)
        if old is not None:
            old.destroy()
    # Replace the embedded old receiver with current validation before building.
    root.op('Runtime/t01_adapter_module').text = (BASE / 't01_telemetry.py').read_text(encoding='utf-8')
    for key in ('T01_TELEMETRY_MODULE', 'T01_TELEMETRY_ADAPTER'):
        if hasattr(builtins, key):
            delattr(builtins, key)
    shell = _build(save_candidate=False)
    render = shell.op('Logic/render')
    render.par.active = False
    shell.op('Logic').create(textDAT, 'device_preview_source').text = (BASE / 'device_preview.py').read_text(encoding='utf-8')
    content = shell.op('Content')
    for path in ('Header', 'Context', 'Pages/overview'):
        content.op(path).destroy()
    header = panel(content, 'Header', height=32, background='canvas')
    state = text(header, 'state', '等待遥测', 'status', width='=parent().width * .52')
    state.store('status_key', 'stream')
    text(header, 'source', '设备预览未接入', 'preview_status', x='=parent().width * .52', width='=parent().width * .48', align='right', ink='muted')
    content.op('Tabs').par.y.expr = 'parent().height - 40 - me.height'
    content.op('Tabs/timing/label').par.text = '设备明细与链路'
    context = panel(content, 'Context', top=84, height=76, border=True)
    heading(context, '会话信息', height=28)
    for name, label, key, start, weight, label_w in (
        ('session', '会话 ID', 'session_id', 0, .32, 80),
        ('weather', '天气', 'module_id', .32, .12, 52),
        ('position', '模块', 'module_position', .44, .10, 52),
        ('segment', '流程段', 'segment', .54, .20, 72),
        ('cue', '提示条件', 'cue_mode', .74, .26, 88),
    ):
        pair(context, name, label, key, '=parent().width * ' + repr(start), 28,
             '=parent().width * ' + repr(weight), 46, label_w)
    pages = content.op('Pages')
    pages.par.y.expr = 'parent().height - 168 - me.height'
    pages.par.h.expr = 'parent().height - 208'
    overview = panel(pages, 'overview', background='canvas')
    devices = panel(overview, 'devices', height='=parent().height - 228', background='canvas')
    for i, (source, title, theme, ink) in enumerate((
        ('resp', 'PLUX respiBAN BLE | 呼吸胸带', 'teal', 'teal_text'),
        ('ecg', 'Polar H10 | 心电胸带', 'blue', 'blue_text'),
    )):
        device = panel(devices, source, x='=(parent().width + 8) * ' + repr(i / 2), width='=(parent().width - 8) / 2', border=True)
        heading(device, title, theme, ink, 28)
        for j, (label, field, status) in enumerate((('连接', source + '_state', source + '_device_state'),
            ('样本龄≈', source + '_age', None), ('SQI', source + '_sqi', None))):
            pair(device, 'status_' + str(j), label, field, '=parent().width * ' + repr(j / 3), 28, '=parent().width / 3', 34, 80 if j == 1 else 68, status_key=status)
        text(device, 'wave_label', '呼吸相对幅度' if source == 'resp' else 'ECG (μV)', field='ecg_wave_label' if source == 'ecg' else None, top=62, width='=parent().width * .60', height=26, size=14)
        text(device, 'wave_state', '未接入', source + '_wave_state', top=62, x='=parent().width * .60', width='=parent().width * .40', height=26, align='right', ink='muted', size=14)
        plot = shell.op('Logic').create(scriptTOP, 'plot_' + source)
        cb = shell.op('Logic').create(textDAT, 'plot_' + source + '_callbacks')
        cb.text = "def onCook(scriptOp):\n    runtime = op(" + repr(render.path) + ").module\n    stream = runtime.streams.get(" + repr(source) + ", dict(points=()))\n    scriptOp.copyNumpyArray(runtime.raster_waveform(stream, 640, 160))\n"
        plot.par.callbacks = cb.path
        graph = panel(device, 'wave', 52, 88, '=parent().width - 64', '=parent().height - 146')
        setp(graph, top=plot.path, topfill='stretch')
        text(device, 'ymax', '1200' if source == 'ecg' else '—', field=source + '_max' if source == 'resp' else None,
             top=84, width=52, height=24, align='right', size=12, ink='muted')
        text(device, 'ymin', '-1200' if source == 'ecg' else '—', field=source + '_min' if source == 'resp' else None,
             top='=parent().height - 74', width=52, height=24, align='right', size=12, ink='muted')
        text(device, 'axis', '−30 s                      时间（相对当前）                      0 s' if source == 'resp' else '−6 s                      时间（相对当前）                      0 s', top='=parent().height - 58', height=24, align='center', size=14, ink='muted')
        if source == 'resp':
            pair(device, 'rate', '采样率', 'resp_rate', 0, '=parent().height - 34', '=parent().width / 2', 34, 76)
            pair(device, 'motion', '运动通道', 'motion_state', '=parent().width / 2', '=parent().height - 34', '=parent().width / 2', 34, 92)
        else:
            for j, (label, field) in enumerate((('心率 bpm', 'heart_rate'), ('RR ms', 'rr_interval'), ('采样率', 'ecg_rate'))):
                pair(device, 'metric_' + str(j), label, field, '=parent().width * ' + repr(j / 3), '=parent().height - 34', '=parent().width / 3', 34, 80 if j == 0 else 64)
    main = panel(overview, 'main', top="=parent().op('devices').height + 8", height=140, background='canvas')
    follow = panel(main, 'follow', width='=(parent().width - 8) * .56', border=True)
    feedback = panel(main, 'feedback', x='=(parent().width - 8) * .56 + 8', width='=(parent().width - 8) * .44', border=True)
    heading(follow, '呼吸跟随对照', height=26)
    for j, label in enumerate(('指标', '目标', '实际')):
        text(follow, 'column_' + str(j), label, x='=parent().width * ' + repr(j / 3), top=26, width='=parent().width / 3', height=22, align='left' if j == 0 else 'center', ink='muted')
    for i, (key, label) in enumerate((('cycle_index', '周期'), ('step_id', '步骤'), ('phase', '相位'), ('progress', '进度'))):
        row = panel(follow, key, top=48 + i * 22, height=22)
        text(row, 'label', label, width='=parent().width / 3')
        for j, side in enumerate(('target', 'actual')):
            text(row, side, '—', side + '_' + key, x='=parent().width * ' + repr((j + 1) / 3), width='=parent().width / 3', align='center')
        line(row, 'line', 21)
    heading(feedback, '反馈与降级', height=26)
    for i, (label, field, status) in enumerate((('识别置信度', 'actual_confidence', None), ('恢复值 / 锁定', 'recovery_value', None), ('降级状态', 'fallback_state', 'fallback_state'), ('降级原因', 'fallback_reason', None))):
        pair(feedback, 'field_' + str(i), label, field, 0, 26 + i * 28, '=parent().width', 28, 144, status_key=status)
    # Keep lock separately visible without interpreting recovery as an outcome.
    feedback.op('field_1/value').par.w.expr = '(parent().width - 144) * .5'
    text(feedback.op('field_1'), 'locked', '—', 'recovery_locked', x='=144 + (parent().width - 144) * .5', width='=(parent().width - 144) * .5', align='center')
    counters = panel(overview, 'counters', top="=parent().op('devices').height + 156", height=44, border=True)
    text(counters, 'heading', 'TD 遥测统计', width='=parent().width * .14')
    from workbench_view import COUNTERS
    for i, (key, label) in enumerate(COUNTERS):
        cell = panel(counters, key, x='=parent().width * ' + repr(.14 + i * .12), width='=parent().width * .12')
        text(cell, 'label', label, height=20, align='center', ink='muted', size=14)
        text(cell, 'value', '0', key, top=20, height=24, align='center')
    cell = panel(counters, 'recording', x='=parent().width * .86', width='=parent().width * .14')
    text(cell, 'label', '追加记录', height=20, align='center', ink='muted', size=14)
    text(cell, 'value', '未接入', 'recording_state', top=20, height=24, align='center')
    events = panel(overview, 'events', top="=parent().op('devices').height + 204", height=24)
    text(events, 'heading', '最近事件', width=100)
    text(events, 'state', '事件通道未接入', 'events_state', x=100, width='=parent().width - 100', align='center', ink='muted')
    content.op('Footer/link').par.text = '协议 v2.2 | UDP 5005 | 刷新上限 20 Hz'
    render.text = 'import sys\nsys.path.insert(0, ' + repr(str(BASE)) + ')\n' + DEVICE_RUNTIME
    cb = root.op('Sources/UdpTelemetryAdapter/udp_callbacks')
    cb.text += '\n' + DEVICE_CALLBACKS
    render.module.select_page('overview')
    render.par.active = True
    render.module.onFrameStart(0)
    return shell
