"""Stacked acquisition view with preflight and reserved Unity start observation."""
from pathlib import Path

_base = Path(__file__).with_name('build_workbench_devices.py')
exec(compile(_base.read_text(encoding='utf-8'), str(_base), 'exec'), globals())
_device_build = build
CANDIDATE = 'T01_Workbench_A.monitor-v4.candidate.toe'

MONITOR_RUNTIME = '''
session_module = types.ModuleType('td_workbench_session')
exec(op(ROOT + '/WorkbenchA/Logic/session_source').text, session_module.__dict__)
channels = session_module.Channels()
capture = session_module.DevelopmentCapture(op(ROOT + '/WorkbenchA').fetch('capture_root'))
selected = {'resp': 'resp', 'ecg': 'ecg'}
interface_error = None
_device_frame = onFrameStart

def ingest_monitor(raw, now):
    global interface_error
    import json
    try:
        p = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return False
    if not isinstance(p, dict):
        return False
    if p.get('message_type') == 'session_observation':
        try:
            capture.event(p, now)
            interface_error = None
        except (ValueError, OSError) as error:
            interface_error = str(error)
        return True
    if p.get('message_type') == 'device_preview':
        if preview.ingest(raw, now):
            channels.append(p)
            try:
                capture.append(p, now)
            except OSError:
                interface_error = 'CAPTURE_WRITE_FAILED'
        return True
    return False

def select_curve(source, key):
    if key not in session_module.VIEWS[source]:
        raise ValueError('CURVE_VIEW')
    selected[source] = key
    device = op(ROOT + '/WorkbenchA/Content/Pages/overview/devices/' + source)
    for name in session_module.VIEWS[source]:
        device.op('tabs/' + name + '/underline').par.display = name == key

def plot(source, width, height):
    stream = streams.get(source, dict(points=()))
    series = channels.series(selected[source], stream)
    if not series:
        return raster_waveform(dict(points=()), width, height)
    result = raster_waveform(series[0], width, height)
    for item in series[1:]:
        image = raster_waveform(item, width, height)
        mask = image[:, :, :3].min(axis=2) < .7
        result[mask] = image[mask]
    return result

def onFrameStart(frame):
    _device_frame(frame)
    now = time.monotonic_ns()
    shell = op(ROOT + '/WorkbenchA')
    values = {'recording_state': capture.label(), 'elapsed': capture.elapsed(now),
              'record_count': str(capture.count), 'record_error': interface_error or '无',
              'record_file': str(capture.path) if capture.path else '尚未建立录制文件'}
    shell.op('Content/Context/recording').par.text = capture.label()
    shell.op('Content/Tabs/overview/label').par.text = '实验录制' if capture.state == 'RECORDING' else '录制前检查 / 监控'
    for source in ('resp', 'ecg'):
        stream = streams.get(source, {})
        key = selected[source]
        payload = stream.get('payload', {})
        if payload:
            values[source + '_state'] = ('历史 ' if stream.get('state') == 'STALE' else '') + {'CONNECTED':'已连接', 'DISCONNECTED':'断连', 'UNKNOWN':'未知'}[payload['device_state']]
        values[source + '_age'] = ('历史 ' if stream.get('state') == 'STALE' else '') + session_module.age(stream.get('age_ms'))
        series = channels.series(key, stream)
        actual = [v for item in series for _, v in item['points'] if v is not None]
        label = session_module.LABELS[key] + ' / ' + session_module.UNITS[key]
        if key in ('acceleration', 'angular_velocity'):
            label += '   X红  Y绿  Z蓝'
        values[source + '_plot_label'] = label
        values[source + '_plot_state'] = ('历史 · ' if stream.get('state') == 'STALE' else '') + ('有数据' if actual else '未接入')
        window = 6 if key == 'ecg' else 30
        device = shell.op('Content/Pages/overview/devices/' + source)
        device.op('axis_left').par.text = '−00:' + str(window).zfill(2)
        low, high = (-1200, 1200) if key == 'ecg' else (min(actual), max(actual)) if actual else (None, None)
        if low is not None and high == low:
            low, high = low - 1, high + 1
        device.op('ymax').par.text = str(round(high, 2)) if high is not None else '—'
        device.op('ymin').par.text = str(round(low, 2)) if low is not None else '—'
        shell.op('Logic/plot_' + source).cook(force=True)
    for node in shell.findChildren(type=textCOMP):
        key = node.fetch('field', None)
        if key in values:
            node.par.text = values[key]
    snapshot = op(ROOT + '/Sources/UdpTelemetryAdapter/udp_callbacks').module._adapter().read_snapshot(now)
    shell.op('Content/Footer/link').par.text = 'UDP 5005 | 20 Hz | 末帧 ' + session_module.age(snapshot.display_only['transport'].get('frame_age_ms'))
    for node in shell.op('Content/Footer').findChildren(type=textCOMP):
        if node.fetch('field', None) == 'footer':
            node.par.text = '会话用时 ' + capture.elapsed(now) + '（分:秒）'
'''


def build():
    shell = _device_build()
    render = shell.op('Logic/render')
    render.par.active = False
    shell.op('Logic').create(textDAT, 'session_source').text = (BASE / 'workbench_session.py').read_text(encoding='utf-8')
    shell.store('capture_root', str(Path(project.folder) / 'development-recordings'))
    content = shell.op('Content')
    content.op('Context').destroy()
    context = panel(content, 'Context', top=80, height=38, background='neutral')
    text(context, 'recording', '正在等待Unity开始 · 预览不计入录制', width='=parent().width - 160', size=18)
    text(context, 'elapsed', '00:00', 'elapsed', x='=parent().width - 160', width=160, align='right', size=22)
    pages = content.op('Pages')
    bounds(pages, top=126, height='=parent().height - 166')
    pages.op('overview').destroy()
    overview = panel(pages, 'overview')
    devices = panel(overview, 'devices', width='=parent().width * .76 - 8', height='=parent().height - 30')
    sidebar = panel(overview, 'main', x='=parent().width * .76', width='=parent().width * .24', height='=parent().height - 30', border=True)
    for i, (source, title, keys) in enumerate((
        ('resp', '01 呼吸  ·  PLUX respiBAN BLE', ('resp', 'acceleration', 'angular_velocity')),
        ('ecg', '02 心电  ·  Polar H10', ('ecg', 'rr', 'hr')),
    )):
        device = panel(devices, source, top='=(parent().height + 8) * ' + str(i / 2), height='=(parent().height - 8) / 2', border=True)
        heading(device, title, height=26)
        for j, (label, field) in enumerate((('连接', source + '_state'), ('SQI', source + '_sqi'), ('采样率', source + '_rate'))):
            cell = pair(device, 'status_' + str(j), label, field, '=parent().width * ' + str(j/3), 26, '=parent().width / 3', 26, 64)
            cell.op('value').par.fontsize = 14
        text(device, 'plot_label', '', source + '_plot_label', top=52, height=22, width='=parent().width - 110', size=13)
        text(device, 'plot_state', '', source + '_plot_state', top=52, height=22, x='=parent().width - 110', width=110, align='right', size=13)
        graph = panel(device, 'wave', 52, 76, '=parent().width - 64', '=parent().height - 150')
        setp(graph, top=shell.op('Logic/plot_' + source).path, topfill='stretch')
        cb = shell.op('Logic').create(textDAT, 'monitor_plot_' + source + '_callbacks')
        cb.text = 'def onCook(scriptOp):\n    runtime = op(' + repr(render.path) + ').module\n    scriptOp.copyNumpyArray(runtime.plot(' + repr(source) + ', 960, 240))\n'
        shell.op('Logic/plot_' + source).par.callbacks = cb.path
        text(device, 'ymax', '—', top=74, width=52, height=20, align='right', size=12)
        text(device, 'ymin', '—', top='=parent().height - 94', width=52, height=20, align='right', size=12)
        text(device, 'axis_left', '', x=40, top='=parent().height - 74', width=88, height=22, size=12)
        text(device, 'axis', '相对当前时间（分:秒）', top='=parent().height - 74', height=22, align='center', size=12)
        text(device, 'axis_right', '00:00', x='=parent().width - 76', top='=parent().height - 74', width=76, height=22, align='right', size=12)
        tabs = panel(device, 'tabs', top='=parent().height - 52', height=26)
        for j, key in enumerate(keys):
            labels = {'resp':'呼吸', 'acceleration':'加速度', 'angular_velocity':'角速度', 'ecg':'ECG', 'rr':'RR间期', 'hr':'心率'}
            tab = panel(tabs, key, j*132, width=132, height=26)
            label = text(tab, 'label', labels[key], size=14, align='center')
            code = {'resp':'#2563A6', 'ecg':'#237A47', 'rr':'#7850A0', 'hr':'#237A47'}.get(key, '#56616F')
            line(tab, 'underline', 24, height=2, code=code).par.display = j == 0
            callback = shell.op('Logic').create(panelexecuteDAT, 'curve_' + key)
            setp(callback, panels=label.path, panelvalue='lselect', offtoon=True)
            callback.text = 'def onOffToOn(panelValue):\n    op(' + repr(render.path) + ').module.select_curve(' + repr(source) + ', ' + repr(key) + ')\n'
        pair(device, 'age', '样本龄≈', source + '_age', 0, '=parent().height - 26', '=parent().width * .45', 26, 86).op('value').par.fontsize=14
        if source == 'ecg':
            pair(device, 'hr', 'HR bpm', 'heart_rate', '=parent().width * .45', '=parent().height - 26', '=parent().width * .25', 26, 72).op('value').par.fontsize=14
            pair(device, 'rr', 'RR ms', 'rr_interval', '=parent().width * .70', '=parent().height - 26', '=parent().width * .30', 26, 64).op('value').par.fontsize=14
        else:
            pair(device, 'motion', '运动通道', 'motion_state', '=parent().width * .45', '=parent().height - 26', '=parent().width * .55', 26, 86).op('value').par.fontsize=14
    heading(sidebar, '会话与运行', height=26)
    for i, (label, key) in enumerate((('会话','session_id'),('天气','module_id'),('位置','module_position'),('流程段','segment'),('提示','cue_mode'),('目标步骤','target_step_id'),('实际步骤','actual_step_id'),('置信度','actual_confidence'),('恢复值','recovery_value'),('恢复锁定','recovery_locked'),('降级','fallback_state'),('录制条数','record_count'),('接口错误','record_error'))):
        row = pair(sidebar, 'row_' + str(i), label, key, 0, 26+i*27, '=parent().width', 27, 94)
        row.op('value').par.fontsize = 14
        line(row, 'line', 26)
    events = panel(overview, 'events', top='=parent().height - 26', height=26, background='neutral')
    from workbench_view import COUNTERS
    for i, (key, label) in enumerate(COUNTERS):
        cell = panel(sidebar, 'counter_' + key, x='=parent().width * ' + str((i % 3)/3), top='=parent().height - ' + str(76 if i < 3 else 38), width='=parent().width / 3', height=38)
        text(cell, 'label', label, height=18, align='center', size=12, ink='muted')
        text(cell, 'value', '0', key, top=18, height=20, align='center', size=13)
    text(events, 'file', '尚未建立录制文件', 'record_file', size=12)
    base_runtime = DEVICE_RUNTIME.replace("streams = preview.snapshot(now, snapshot.telemetry.get('session_id'))", "preview_session = snapshot.telemetry.get('session_id') or (next(reversed(preview.streams.values()))['payload']['session_id'] if preview.streams else None)\n    streams = preview.snapshot(now, preview_session)")
    render.text = base_runtime + '\n' + MONITOR_RUNTIME
    cb = op(ROOT + '/Sources/UdpTelemetryAdapter/udp_callbacks')
    cb.text += '''
def onReceive(dat, rowIndex, message, bytes, peer):
    import builtins, time, json
    raw = builtins.bytes(bytes)
    now = time.monotonic_ns()
    runtime = op('/project1/T01_TelemetryPanel/WorkbenchA/Logic/render').module
    if runtime.ingest_monitor(raw, now):
        return
    result = _adapter().ingest_datagram(raw, now)
    if result.accepted:
        try:
            runtime.capture.append(json.loads(raw), now)
        except OSError:
            runtime.interface_error = 'CAPTURE_WRITE_FAILED'
'''
    render.module.select_page('overview')
    render.par.active = True
    render.module.onFrameStart(0)
    return shell
