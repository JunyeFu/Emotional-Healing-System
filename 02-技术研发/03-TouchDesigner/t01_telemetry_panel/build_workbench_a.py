"""Run in TD Textport; build the A-theme candidate without overwriting signed artifacts."""
from pathlib import Path

ROOT = "/project1/T01_TelemetryPanel"
BASE = Path(__file__).resolve().parent
SHELL = ROOT + "/WorkbenchA"

RUNTIME = '''
import time
import math
ROOT = '/project1/T01_TelemetryPanel'
last_tick = None
def onFrameStart(frame):
    global last_tick
    now = time.monotonic_ns()
    if last_tick is not None and now - last_tick < 50_000_000:
        return
    last_tick = now
    root = op(ROOT)
    snapshot = root.op('Sources/UdpTelemetryAdapter/udp_callbacks').module._adapter().read_snapshot(now)
    model = root.op('WorkbenchA/Logic/view_model').module.view_model(snapshot)
    for node in root.op('WorkbenchA').findChildren(type=textCOMP):
        key = node.fetch('field', None)
        if key:
            limit = max(4, int(max(1, node.width - 20) / 18) * max(1, int((node.height - 8) / 24)))
            text = root.op('WorkbenchA/Logic/view_model').module.compact(model['values'].get(key, '—'), limit)
            if node.par.text.eval() != text:
                node.par.text = text
    for source in ('resp', 'ecg'):
        fill = root.op('WorkbenchA/Pages/overview/main/signals/' + source + '/quality/fill')
        value = snapshot.telemetry.get('signal_quality', {}).get(source)
        fill.par.w.expr = 'parent().width * ' + repr(0 if value is None else value)
    for i, (key, value) in enumerate(model['details'].items()):
        body = root.op('WorkbenchA/Pages/timing/details')
        name = 'item_' + str(i)
        row = body.op(name)
        if row is None:
            row = body.copy(root.op('WorkbenchA/Logic/detail_template'), name=name)
            row.par.display = True
            row.par.alignorder = i
        text = key + '    ' + value
        if row.par.text.eval() != text:
            row.par.text = text
        row.par.h = max(40, math.ceil(len(text) / max(12, int(body.width / 20))) * 26 + 16)
    for row in root.op('WorkbenchA/Pages/timing/details').children:
        if row.name.startswith('item_') and int(row.name[5:]) >= len(model['details']):
            row.destroy()
    return
'''


def setp(node, **values):
    for name, value in values.items():
        getattr(node.par, name).val = value


def color(node, rgb):
    setp(node, bgcolorr=rgb[0], bgcolorg=rgb[1], bgcolorb=rgb[2], bgalpha=1)


def panel(parent, name, height=40, horizontal=False):
    node = parent.create(containerCOMP, name)
    setp(node, hmode="fill", vmode="fixed", h=height,
         align="horizlr" if horizontal else "verttb", spacing=4,
         alignorder=len(parent.children), crop="on")
    color(node, (1, 1, 1))
    return node


def text(parent, name, value, field=None, size=18):
    node = parent.create(textCOMP, name)
    setp(node, text=value, type="multiline", editmode="selectonly", wordwrap=True,
         formatcodes=False, font="Microsoft YaHei", fontsize=size, tracking=0,
         scaletofit="never", hmode="fill", vmode="fill", alignx="left", aligny="center",
         textpaddingl=10, textpaddingr=10, textpaddingt=4, textpaddingb=4,
         fontcolorr=.12, fontcolorg=.14, fontcolorb=.16, bgalpha=0,
         alignorder=len(parent.children))
    if field:
        node.store("field", field)
    return node


def row(parent, name, cells, height=44):
    node = panel(parent, name, height, horizontal=True)
    for i, (label, field) in enumerate(cells):
        text(node, "c" + str(i), label, field)
    return node


def button(parent, name, label, enabled=False):
    node = parent.create(buttonCOMP, name)
    setp(node, label=label, enable=enabled, hmode="fill", vmode="fill",
         fontsize=18, font="Microsoft YaHei", alignorder=len(parent.children))
    color(node, (.93, .96, .96) if enabled else (.96, .96, .96))
    return node


def _build():
    root = op(ROOT)
    if root is None or Path(project.folder).resolve() != BASE:
        raise RuntimeError("Open the authoritative T01 project before running this builder")
    if root.op('WorkbenchA') is not None:
        raise RuntimeError("WorkbenchA already exists; inspect it before rebuilding")
    shell = root.create(containerCOMP, "WorkbenchA")
    setp(shell, w=1600, h=900, align="verttb", spacing=8, crop="on", sizefromwindow=True)
    color(shell, (.97, .98, .985))
    logic = shell.create(baseCOMP, "Logic")
    model = logic.create(textDAT, "view_model")
    model.text = (BASE / "workbench_view.py").read_text(encoding="utf-8")
    template = text(logic, "detail_template", "")
    setp(template, display=False, vmode="fixed", h=40, aligny="top")
    header = panel(shell, "Header", 52, horizontal=True)
    title = text(header, "title", "SRP 实验工作台", size=26)
    title.par.hfillweight = 2
    text(header, "state", "等待遥测", "status")
    for name, label in (("export", "导出"), ("capture", "截图"), ("mark", "人工标记"), ("abort", "中止请求")):
        button(header, name, label)
    tabs = panel(shell, "Tabs", 40, horizontal=True)
    for name, label in (("overview", "总览"), ("timing", "链路与时钟"), ("audit", "事件与审计")):
        b = button(tabs, name, label, True)
        callback = logic.create(panelExecuteDAT, "tab_" + name)
        setp(callback, panels=b.path, panelvalue="select", offtoon=True)
        callback.text = "def onOffToOn(panelValue):\n    root = op(" + repr(SHELL) + ")\n    for page in root.op('Pages').children:\n        page.par.display = page.name == " + repr(name) + "\n    return\n"
    context = panel(shell, "Context", 112)
    row(context, "identity", [("会话 ID", None), ("—", "session_id"), ("运行模式", None), ("—", "runtime_mode"), ("协议版本", None), ("—", "schema_version")], 52)
    row(context, "condition", [("天气模块", None), ("—", "module_id"), ("位置", None), ("—", "module_position"), ("流程段", None), ("—", "segment"), ("提示条件", None), ("—", "cue_mode")], 52)
    pages = panel(shell, "Pages")
    setp(pages, vmode="fill", align="none")
    overview = panel(pages, "overview")
    setp(overview, vmode="fill", pvscrollbar="auto")
    main = panel(overview, "main", 232, horizontal=True)
    signals = panel(main, "signals", 232)
    signals.par.hfillweight = 4
    row(signals, "heading", [("设备与信号质量", None), ("设备状态", None), ("信号质量 SQI", None)], 36)
    for source, label in (("resp", "呼吸"), ("ecg", "心电")):
        r = row(signals, source, [(label, None), ("未知", source + "_state"), ("—", source + "_sqi")], 50)
        track = panel(r, "quality", 16)
        setp(track, vmode="fill", align="none")
        color(track, (.94, .95, .95))
        fill = panel(track, "fill", 16)
        setp(fill, hmode="fixed", w=0, vmode="fill")
        color(fill, (.05, .53, .57) if source == "resp" else (.78, .47, .10))
    follow = panel(main, "follow", 232)
    follow.par.hfillweight = 6
    row(follow, "follow_heading", [("呼吸跟随对照", None), ("目标", None), ("实际", None)], 34)
    for key, label in (("cycle_index", "周期序号"), ("step_id", "步骤标识"), ("phase", "呼吸相位"), ("progress", "相位进度")):
        row(follow, key, [(label, None), ("—", "target_" + key), ("—", "actual_" + key)], 38)
    row(overview, "feedback", [("实际识别置信度", None), ("—", "actual_confidence"), ("场景恢复值", None), ("—", "recovery_value"), ("恢复值锁定", None), ("—", "recovery_locked")], 46)
    row(overview, "fallback", [("降级状态", None), ("—", "fallback_state"), ("降级原因", None), ("—", "fallback_reason")], 54)
    row(overview, "error", [("最近接收错误", None), ("—", "last_error")], 40)
    from workbench_view import COUNTERS
    row(overview, "counter_labels", [(label, None) for _, label in COUNTERS], 30)
    row(overview, "counter_values", [("0", key) for key, _ in COUNTERS], 30)
    timing = panel(pages, "timing")
    setp(timing, vmode="fill", display=False)
    row(timing, "heading", [("链路、时钟与完整字段（时间字段保留原单位）", None)], 38)
    detail = panel(timing, "details")
    setp(detail, vmode="fill", pvscrollbar="auto")
    audit = panel(pages, "audit")
    setp(audit, vmode="fill", display=False)
    row(audit, "pending", [("请求与审计通道未接入", None)], 60)
    row(shell, "RequestState", [("请求与审计通道未接入", None), ("导出与截图待实现", None)], 34)
    row(shell, "Footer", [("—", "footer"), ("UDP 127.0.0.1:5005 · 显示上限 20 Hz", None)], 34)
    execute = logic.create(executeDAT, "render")
    execute.text = RUNTIME
    setp(execute, active=False, framestart=True)
    viewer = root.op('Output').create(opviewerTOP, 'workbench_a_view')
    viewer.par.opviewer = shell.path
    # Swap only the display binding after all native nodes have been constructed.
    root.op('Runtime/render_execute').par.active = False
    root.op('Output/display_source').par.top = viewer.path
    op('/perform').par.winop = shell.path
    execute.par.active = True
    execute.module.onFrameStart(0)
    for i, child in enumerate(root.children):
        child.nodeX, child.nodeY = (i % 4) * 240, -(i // 4) * 180
    for group in (shell, logic):
        for i, child in enumerate(group.children):
            child.nodeX, child.nodeY = (i % 4) * 220, -(i // 4) * 160
    errors = shell.errors(recurse=True) + shell.scriptErrors(recurse=True)
    if errors:
        raise RuntimeError(errors)
    target = BASE / 'T01_Workbench_A.candidate.toe'
    if target.exists():
        raise RuntimeError('Candidate file already exists; refusing overwrite')
    if not project.save(str(target)):
        raise RuntimeError('Candidate save failed')
    print('WORKBENCH_A_CANDIDATE_SAVED', target)
    return shell


def build():
    root = op(ROOT)
    target = BASE / 'T01_Workbench_A.candidate.toe'
    if root is None or Path(project.folder).resolve() != BASE:
        raise RuntimeError('Open the authoritative T01 project first')
    if root.op('WorkbenchA') is not None or root.op('Output/workbench_a_view') is not None or target.exists():
        raise RuntimeError('Candidate already exists; inspect it before rebuilding')
    source = root.op('Output/display_source')
    legacy = root.op('Runtime/render_execute')
    previous = (source.par.top.eval(), legacy.par.active.eval(), op('/perform').par.winop.eval())
    try:
        return _build()
    except Exception:
        source.par.top = previous[0]
        legacy.par.active = previous[1]
        op('/perform').par.winop = previous[2]
        for path in ('WorkbenchA', 'Output/workbench_a_view'):
            node = root.op(path)
            if node is not None:
                node.destroy()
        raise


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(BASE))
    build()
