"""Build a native read-only A theme in a dedicated TouchDesigner project."""
from pathlib import Path
import sys

ROOT = '/project1/T01_TelemetryPanel'
TASK_DIR = Path(__file__).resolve().parents[1]
BASE = TASK_DIR.parents[2] / 'agent/modules/03-TouchDesigner/t01_telemetry_panel'
RUNTIME_DIR = TASK_DIR / 'evidence/runtime'
ASSETS = TASK_DIR / 'design/workbench-icons'
SHELL = ROOT + '/WorkbenchA'
CANDIDATE = 'T01_Workbench_A.readable-v2.candidate.toe'
sys.path.insert(0, str(BASE))

PALETTE = {
    'canvas': '#F2F5F8', 'body': '#FFFFFF', 'text': '#202832', 'muted': '#56616F',
    'line': '#7C8D9F', 'rowline': '#D3DBE4', 'neutral': '#E9EDF2',
    'teal': '#E4F1EF', 'teal_text': '#0C666A', 'blue': '#E8EFF8',
    'blue_text': '#235E8D', 'selected': '#1D6095',
}
STATUS_COLORS = {
    'LIVE': ('#235E8D', '#E8EFF8'), 'CONNECTED': ('#235E8D', '#E8EFF8'),
    'GOOD': ('#176B42', '#E7F2EB'), 'DEGRADED': ('#895300', '#FFF2D9'),
    'UNUSABLE': ('#A82A32', '#FBEAEC'), 'DISCONNECTED': ('#A82A32', '#FBEAEC'),
    'WAITING': ('#596574', '#EEF1F4'), 'UNKNOWN': ('#596574', '#EEF1F4'),
}

RUNTIME = '''
import time
import math
ROOT = '/project1/T01_TelemetryPanel'
last_tick = None

def _rgb(code):
    return tuple(int(code[i:i+2], 16) / 255 for i in (1, 3, 5))

def select_page(name):
    shell = op(ROOT + '/WorkbenchA')
    for page in shell.op('Content/Pages').panelChildren:
        page.par.display = page.name == name
    shell.store('active_page', name)
    if name == 'timing':
        shell.op('Content/Pages/timing/details').panel.scrollv = 0
    for tab in shell.op('Content/Tabs').panelChildren:
        selected = tab.name == name
        tab.par.bgcolorr, tab.par.bgcolorg, tab.par.bgcolorb = _rgb('#E8EFF8' if selected else '#E9EDF2')
        tab.op('underline').par.display = selected
        label = tab.op('label')
        label.par.fontcolorr, label.par.fontcolorg, label.par.fontcolorb = _rgb('#235E8D' if selected else '#56616F')

def onFrameStart(frame):
    global last_tick
    now = time.monotonic_ns()
    if last_tick is not None and now - last_tick < 50_000_000:
        return
    last_tick = now
    root = op(ROOT)
    shell = root.op('WorkbenchA')
    snapshot = root.op('Sources/UdpTelemetryAdapter/udp_callbacks').module._adapter().read_snapshot(now)
    model = shell.op('Logic/view_model').module.view_model(snapshot)
    styles = shell.fetch('status_colors')
    for node in shell.findChildren(type=textCOMP):
        key = node.fetch('field', None)
        if key:
            value = model['overview_values'].get(key, '—')
            if key == 'session_id':
                value = shell.op('Logic/view_model').module.compact(value, 32)
            if node.par.text.eval() != value:
                node.par.text = value
        status_key = node.fetch('status_key', None)
        if status_key:
            state = model['state'] if status_key == 'stream' else snapshot.telemetry.get(status_key, 'UNKNOWN')
            fg, bg = styles.get(state, styles['UNKNOWN'])
            node.par.fontcolorr, node.par.fontcolorg, node.par.fontcolorb = _rgb(fg)
            node.par.bgcolorr, node.par.bgcolorg, node.par.bgcolorb = _rgb(bg)
            node.par.bgalpha = 1
    for source in ('resp', 'ecg'):
        fill = shell.op('Content/Pages/overview/main/signals/' + source + '/quality/fill')
        value = snapshot.telemetry.get('signal_quality', {}).get(source)
        fill.par.display = value is not None
        if value is not None:
            fill.par.w.expr = 'parent().width * ' + repr(value)
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
    return
'''


def rgb(code):
    return tuple(int(code[i:i + 2], 16) / 255 for i in (1, 3, 5))


def setp(node, **values):
    for name, value in values.items():
        par = getattr(node.par, name)
        if isinstance(value, str) and value.startswith('='):
            par.expr = value[1:]
        else:
            par.val = value


def color(node, code):
    r, g, b = rgb(code)
    setp(node, bgcolorr=r, bgcolorg=g, bgcolorb=b, bgalpha=1)


def bounds(node, x=0, top=0, width='=parent().width', height='=parent().height'):
    setp(node, hmode='fixed', vmode='fixed', x=x, w=width, h=height)
    top = top[1:] if isinstance(top, str) and top.startswith('=') else repr(top)
    node.par.y.expr = 'parent().height - (' + top + ') - me.height'


def panel(parent, name, x=0, top=0, width='=parent().width', height='=parent().height', background='body', border=False):
    node = parent.create(containerCOMP, name)
    bounds(node, x, top, width, height)
    setp(node, align='none', crop='on')
    color(node, PALETTE[background])
    if border:
        r, g, b = rgb(PALETTE['line'])
        setp(node, borderar=r, borderag=g, borderab=b, borderaalpha=1,
             leftborder='bordera', rightborder='bordera', topborder='bordera',
             bottomborder='bordera', borderover=True)
    return node


def line(parent, name, top, x=0, width='=parent().width', height=1, code=None):
    node = panel(parent, name, x, top, width, height)
    color(node, code or PALETTE['rowline'])
    node.par.enable = False
    return node


def text(parent, name, value, field=None, x=0, top=0, width='=parent().width', height='=parent().height', size=16, align='left', ink='text', wrap=False):
    node = parent.create(textCOMP, name)
    bounds(node, x, top, width, height)
    r, g, b = rgb(PALETTE[ink])
    setp(node, text=value, type='multiline' if wrap else 'string', editmode='selectonly',
         mousewheel=False,
         wordwrap=wrap, formatcodes=False, font='Microsoft YaHei', fontsize=size,
         tracking=0, scaletofit='never', alignx=align, aligny='center',
         textpaddingl=12, textpaddingr=12, textpaddingt=2, textpaddingb=2,
         fontcolorr=r, fontcolorg=g, fontcolorb=b, bgalpha=0)
    if field:
        node.store('field', field)
    return node


def heading(parent, label, theme='neutral', ink='text', height=28):
    stripe = panel(parent, 'heading', height=height, background=theme)
    text(stripe, 'label', label, size=18, ink=ink)
    line(parent, 'heading_line', height)


def pair(parent, name, label, field, x, top, width, height=40, label_width=104, align='left', status_key=None):
    cell = panel(parent, name, x, top, width, height)
    text(cell, 'label', label, width=label_width, ink='muted')
    value = text(cell, 'value', '—', field, x=label_width,
                 width='=parent().width - ' + str(label_width), size=18, align=align)
    if status_key:
        value.store('status_key', status_key)
    return cell


def _build(save_candidate=True):
    root = op(ROOT)
    shell = root.create(containerCOMP, 'WorkbenchA')
    setp(shell, w=1280, h=720, align='none', crop='on', sizefromwindow=True)
    color(shell, PALETTE['canvas'])
    shell.store('status_colors', STATUS_COLORS)
    logic = shell.create(baseCOMP, 'Logic')
    model = logic.create(textDAT, 'view_model')
    model.text = (BASE / 'workbench_view.py').read_text(encoding='utf-8')
    content = panel(shell, 'Content', 16, 16, '=parent().width - 32', '=parent().height - 32', 'canvas')
    header = panel(content, 'Header', height=48, background='canvas')
    state = text(header, 'state', '等待遥测', 'status',
                 width='=parent().width - 200', align='center', size=18)
    state.store('status_key', 'stream')
    tools = panel(header, 'Tools', '=parent().width - 192', 4, 192, 40, 'canvas')
    for i, (icon, label) in enumerate((('download', '导出'), ('camera', '截图'), ('bookmark', '人工标记'), ('circle-x', '中止请求'))):
        wrapper = panel(tools, icon.replace('-', '_'), i * 48, 0, 40, 40, 'neutral')
        help_dat = logic.create(textDAT, 'help_' + wrapper.name)
        help_dat.text = label + '（未接入）'
        wrapper.par.helpdat = help_dat.path
        image = logic.create(moviefileinTOP, 'icon_' + wrapper.name)
        image.par.file = str(ASSETS / (icon + '.png'))
        setp(wrapper, top=image.path, topfill='native')
        button = wrapper.create(buttonCOMP, 'button')
        bounds(button)
        setp(button, label='', enable=False, top=image.path, topfill='native', dodisablecolor=False)
        button.par.opacity = 0
        color(button, PALETTE['neutral'])
    tabs = panel(content, 'Tabs', top=56, height=36, background='neutral')
    for i, (name, label) in enumerate((('overview', '总览'), ('timing', '链路与时钟'), ('audit', '事件与审计'))):
        tab = panel(tabs, name, '=parent().width * ' + repr(i / 3), 0, '=parent().width / 3', 36, 'neutral')
        label_node = text(tab, 'label', label, align='center', size=18)
        line(tab, 'underline', 33, height=3, code=PALETTE['selected'])
        callback = logic.create(panelexecuteDAT, 'tab_' + name)
        setp(callback, panels=label_node.path, panelvalue='lselect', offtoon=True)
        callback.text = "def onOffToOn(panelValue):\n    op(" + repr(SHELL + '/Logic/render') + ").module.select_page(" + repr(name) + ")\n    return\n"
    context = panel(content, 'Context', top=100, height=116, border=True)
    heading(context, '会话信息')
    for name, label, key, start, weight, label_w in (
        ('session', '会话 ID', 'session_id', 0, .50, 92),
        ('mode', '运行模式', 'runtime_mode', .50, .30, 104),
        ('schema', '协议', 'schema_version', .80, .20, 68),
    ):
        pair(context, name, label, key, '=parent().width * ' + repr(start), 28,
             '=parent().width * ' + repr(weight), 40, label_w)
    for name, label, key, start, weight, label_w in (
        ('weather', '天气模块', 'module_id', 0, .22, 104),
        ('position', '位置', 'module_position', .22, .13, 60),
        ('segment', '流程段', 'segment', .35, .27, 84),
        ('cue', '提示条件', 'cue_mode', .62, .38, 104),
    ):
        pair(context, name, label, key, '=parent().width * ' + repr(start), 70,
             '=parent().width * ' + repr(weight), 44, label_w)
    line(context, 'row_line', 68)
    pages = panel(content, 'Pages', top=224, height='=parent().height - 264', background='canvas')
    overview = panel(pages, 'overview', background='canvas')
    main = panel(overview, 'main', height='=min(240, parent().height - 208)', background='canvas')
    signals = panel(main, 'signals', width='=(parent().width - 8) * .40', border=True)
    follow = panel(main, 'follow', x='=(parent().width - 8) * .40 + 8', width='=(parent().width - 8) * .60', border=True)
    heading(signals, '设备与信号质量', 'teal', 'teal_text', 32)
    heading(follow, '呼吸跟随对照', 'blue', 'blue_text', 32)
    for name, label, start, weight, align in (
        ('device', '设备', 0, .18, 'left'), ('state', '状态', .18, .35, 'center'), ('sqi', 'SQI', .53, .47, 'right'),
    ):
        text(signals, 'col_' + name, label, x='=parent().width * ' + repr(start), top=32,
             width='=parent().width * ' + repr(weight), height=32, align=align, ink='muted')
    line(signals, 'column_line', 64)
    for i, (source, label) in enumerate((('resp', '呼吸'), ('ecg', '心电'))):
        cell = panel(signals, source, top='=64 + (parent().height - 64) * ' + repr(i / 2), height='=(parent().height - 64) / 2')
        text(cell, 'name', label, width='=parent().width * .18')
        state = text(cell, 'state', '未知', source + '_state', x='=parent().width * .18',
                     width='=parent().width * .35', top=8, height='=parent().height - 16', align='center')
        state.store('status_key', source + '_device_state')
        text(cell, 'sqi', '—', source + '_sqi', x='=parent().width * .53', width='=parent().width * .47', top=3, height=30, size=18, align='right')
        quality = panel(cell, 'quality', x='=parent().width * .57', top=38, width='=parent().width * .43 - 12', height=8, background='neutral')
        color(panel(quality, 'fill', width=0), PALETTE['blue_text'])
        line(cell, 'row_line', '=parent().height - 1')
    for i, label in enumerate(('指标', '目标', '实际')):
        text(follow, 'col_' + str(i), label, x='=parent().width * ' + repr(i / 3), top=32,
             width='=parent().width / 3', height=32, align='left' if i == 0 else 'center', ink='muted')
    line(follow, 'column_line', 64)
    for i, (key, label, align) in enumerate((('cycle_index', '周期序号', 'right'), ('step_id', '步骤标识', 'center'), ('phase', '呼吸相位', 'center'), ('progress', '相位进度', 'right'))):
        r = panel(follow, key, top='=64 + (parent().height - 64) * ' + repr(i / 4), height='=(parent().height - 64) / 4')
        text(r, 'label', label, width='=parent().width / 3')
        for j, side in enumerate(('target', 'actual')):
            text(r, side, '—', side + '_' + key, x='=parent().width * ' + repr((j + 1) / 3), width='=parent().width / 3', size=18, align=align)
        line(r, 'row_line', '=parent().height - 1')
    feedback = panel(overview, 'feedback', top="=parent().op('main').height + 8", height=112, border=True)
    heading(feedback, '交互反馈与降级')
    for i, (name, label, key, align) in enumerate((('confidence', '识别置信度', 'actual_confidence', 'right'), ('recovery', '场景恢复值', 'recovery_value', 'right'), ('locked', '恢复值锁定', 'recovery_locked', 'center'))):
        pair(feedback, name, label, key, '=parent().width * ' + repr(i / 3), 28, '=parent().width / 3', 40, 128, align)
    for i, (name, label, key, state_key) in enumerate((('fallback', '降级状态', 'fallback_state', 'fallback_state'), ('reason', '降级原因', 'fallback_reason', None), ('error', '最近接收错误', 'last_error', None))):
        pair(feedback, name, label, key, '=parent().width * ' + repr(i / 3), 70, '=parent().width / 3', 40, 128, 'center' if i == 0 else 'left', state_key)
    line(feedback, 'row_line', 68)
    counters = panel(overview, 'counters', top="=parent().op('feedback').height + parent().op('main').height + 16", height=80, border=True)
    heading(counters, '接收统计', height=24)
    from workbench_view import COUNTERS
    for i, (key, label) in enumerate(COUNTERS):
        cell = panel(counters, key, '=parent().width * ' + repr(i / 6), 24, '=parent().width / 6', 56)
        stripe = panel(cell, 'heading', height=24, background='neutral')
        text(stripe, 'label', label, align='center')
        text(cell, 'value', '0', key, top=24, height=30, size=18, align='center')
        if i:
            line(cell, 'column_line', 0, height='=parent().height', width=1)
    timing = panel(pages, 'timing', border=True)
    timing.par.display = False
    heading(timing, '链路与时钟 · 完整原始字段', height=32)
    text(timing, 'key_heading', '字段名', top=32, width='=parent().width * .40', height=32, ink='muted')
    text(timing, 'value_heading', '完整值（保留原单位）', top=32, x='=parent().width * .40', width='=parent().width * .60', height=32, ink='muted')
    line(timing, 'column_line', 64)
    details = panel(timing, 'details', top=65, height='=parent().height - 67')
    setp(details, pvscrollbar='auto', scrollbarthickness=12, mousewheel=True)
    template = panel(logic, 'detail_template', height=36)
    template.par.mousewheel = False
    template.par.display = False
    text(template, 'key', '', width='=parent().width * .40', wrap=True)
    text(template, 'value', '', x='=parent().width * .40', width='=parent().width * .60', wrap=True)
    for child in ('key', 'value'):
        template.op(child).par.mousewheel = True
    line(template, 'row_line', '=parent().height - 1')
    wheel = logic.create(panelexecuteDAT, 'detail_wheel')
    setp(wheel, panels=details.path + ' ' + details.path + '/*/key ' + details.path + '/*/value',
         panelvalue='wheel', valuechange=True, offtoon=False)
    wheel.text = "def onValueChange(panelValue, previous):\n    if panelValue.val:\n        body = op(" + repr(details.path) + ")\n        body.panel.scrollv = max(0, min(1, body.panel.scrollv.val - panelValue.val * .06))\n    return\n"
    audit = panel(pages, 'audit', border=True)
    audit.par.display = False
    heading(audit, '事件与审计', height=32)
    text(audit, 'pending', '请求与审计通道未接入', top=32, height='=parent().height - 32', align='center', size=18, ink='muted')
    footer = panel(content, 'Footer', top='=parent().height - 32', height=32, background='canvas')
    line(footer, 'top_line', 0, code=PALETTE['line'])
    text(footer, 'age', '—', 'footer', width='=parent().width * .60')
    text(footer, 'link', 'UDP 127.0.0.1:5005 · 20 Hz', x='=parent().width * .60', width='=parent().width * .40', align='right', ink='muted')
    execute = logic.create(executeDAT, 'render')
    execute.text = ('import sys\n' + f'sys.path.insert(0, {str(BASE.parent.parent)!r})\n'
                    + f'sys.path.insert(0, {str(BASE)!r})\n' + RUNTIME)
    setp(execute, active=False, framestart=True)
    viewer = root.op('Output').create(opviewerTOP, 'workbench_a_view')
    viewer.par.opviewer = shell.path
    root.op('Runtime/render_execute').par.active = False
    root.op('Output/display_source').par.top = viewer.path
    op('/perform').par.winop = shell.path
    op('/perform').par.interact = True
    execute.module.select_page('overview')
    execute.par.active = True
    execute.module.onFrameStart(0)
    errors = shell.errors(recurse=True) + shell.scriptErrors(recurse=True)
    if errors:
        raise RuntimeError(errors)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if save_candidate:
        if not project.save(str(RUNTIME_DIR / CANDIDATE)):
            raise RuntimeError('Candidate save failed')
        print('WORKBENCH_A_READABLE_V2_SAVED', RUNTIME_DIR / CANDIDATE)
    return shell


def build():
    root = op(ROOT)
    if root is None or Path(project.folder).resolve() not in (BASE, RUNTIME_DIR):
        raise RuntimeError('Open the authoritative T01 project or dedicated runtime copy first')
    if root.op('WorkbenchA') is not None or root.op('Output/workbench_a_view') is not None or (RUNTIME_DIR / CANDIDATE).exists():
        raise RuntimeError('Candidate already exists; inspect it before rebuilding')
    source, legacy = root.op('Output/display_source'), root.op('Runtime/render_execute')
    previous = (source.par.top.eval(), legacy.par.active.eval(), op('/perform').par.winop.eval())
    try:
        return _build()
    except Exception:
        source.par.top, legacy.par.active, op('/perform').par.winop = previous
        for path in ('WorkbenchA', 'Output/workbench_a_view'):
            node = root.op(path)
            if node is not None:
                node.destroy()
        raise


if __name__ == '__main__':
    build()
