"""Canonical native workbench. Mock ingress is a separately launched process."""
from pathlib import Path

_base = Path(__file__).with_name('build_workbench_redesign.py')
exec(compile(_base.read_text(encoding='utf-8'), str(_base), 'exec'), globals())
_manual_build = build
CANDIDATE = 'T01_ManualWorkbench.toe'

MANUAL_RUNTIME = '''
import socket
import json
_mock_status_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_mock_last_status = None
_manual_opened = False
_manual_design_frame = onFrameStart
workflow.manual_start_required = True

def onFrameStart(frame):
    global _mock_last_status, _manual_opened
    _manual_design_frame(frame)
    connected = all(streams.get(k,{}).get('age_ms',1e9) < 1000 for k in ('resp','ecg'))
    if workflow.stage in ('RUNNING','PAUSED') and not connected:
        workflow.fault('MOCK_DISCONNECTED', time.monotonic_ns())
    if not _manual_opened:
        _manual_opened = True
        op('/perform').par.winopen.pulse()
    now = time.monotonic_ns()
    if _mock_last_status is not None and now - _mock_last_status < 100_000_000:
        return
    _mock_last_status = now
    c = workflow.current
    status = dict(message_type='td_mock_status', source_mode='dev_mock',
        session_id=c['session_id'] if c else None, stage=workflow.stage,
        pending=workflow.pending, ready=workflow.ready,
        sealed=c['sealed'] if c else False, posttest=c['posttest'] if c else False)
    _mock_status_socket.sendto(json.dumps(status).encode('utf-8'), ('127.0.0.1', 5007))
'''


def build():
    shell = _manual_build()
    render = shell.op('Logic/render')
    render.par.active = False
    shell.store('manual_workbench', True)
    shell.store('workflow_root', str(Path(project.folder) / 'development-workflow'))
    render.text = render.text.split('_flow_frame = onFrameStart')[0]
    render.text = 'import sys\nsys.path.insert(0, ' + repr(str(BASE.parent.parent)) + ')\n' + render.text
    render.text += '\n' + Path(__file__).with_name('workbench_redesign_runtime.py').read_text(encoding='utf-8')
    render.text += '\n' + MANUAL_RUNTIME
    for name in ('session_source', 'workflow_source', 'export_source'):
        node = shell.op('Logic/' + name)
        node.text = node.text.encode('ascii', 'backslashreplace').decode('ascii')
    render.text = render.text.encode('ascii', 'backslashreplace').decode('ascii')
    content = shell.op('Content')
    content.op('FlowNote').par.display = False
    content.op('Footer').par.display = False
    content.op('Pages/home/status').par.display = False
    controls = content.op('Pages/overview/flow_controls')
    command(controls, 'start', '开始实验', 'start', x=200, primary=True)
    controls.op('submit/label').par.text = '确认准备'
    controls.op('cancel/label').par.text = '取消准备'
    controls.op('pause/label').par.text = '暂停实验'
    controls.op('resume/label').par.text = '继续实验'
    controls.op('abort/label').par.text = '中止实验'
    closeout = content.op('Pages/closeout')
    command(closeout, 'posttest', '确认后测', 'posttest', x='=parent().width * .15 + 384', top=314)
    root = shell.op('Design')
    root.par.sizefromwindow = True
    root.par.x.mode = ParMode.CONSTANT
    root.par.y.mode = ParMode.CONSTANT
    root.par.x,root.par.y = 0,0
    explanations = ('实验记录与后测分别确认后，才能准备下一位。', '完整会话编号与文件路径')
    for page in root.panelChildren:
        page.par.display = False
        page.par.x = 0
        page.par.y.mode = ParMode.CONSTANT
        page.par.y = 0
        setp(page,hmode='anchors',vmode='anchors',leftanchor=0,rightanchor=1,bottomanchor=0,topanchor=1)
        mode = text(page, 'manual_mode', '模拟模式', x=1120, top=10, width=124, height=28, size=14, align='right')
        setp(mode, layer=300)
        for node in page.findChildren(type=textCOMP):
            value = node.fetch('design_text', '')
            x, y = node.fetch('design_xy', (-1, -1))
            if ((x == 36 and y == 674) or (x == 726 and y in (199, 449)) or value in explanations
                    or node.name in ('c_prepare_105','c_closeout_42','c_closed_42')):
                node.par.display = False
            if value in ('导出本场数据', '打开记录位置'):
                node.store('design_action', 'export' if value.startswith('导出') else 'open')
                callback = shell.op('Logic').create(panelexecuteDAT, 'manual_' + page.name + '_' + node.name)
                setp(callback, panels=node.path, panelvalue='lselect', offtoon=True)
                callback.text = 'def onOffToOn(v):\n    op(' + repr(render.path) + ').module.design_action(' + repr(node.fetch('design_action')) + ')\n'
        for node in page.children:
            if node.fetch('design_xy',None) is not None:
                x,y = node.fetch('design_xy')
                node.par.y.mode = ParMode.CONSTANT
                node.par.y = 720-y-float(node.par.h.eval())
    for page_name, name, label, action_name, x, top in (
        ('waiting', 'manual_start', '开始实验', 'start', 896, 590),
        ('closeout', 'manual_posttest', '确认后测', 'posttest', 800, 603),
        ('fault', 'manual_fault_close', '保留记录并返回', 'dismiss_fault', 896, 640),
        ('history', 'manual_history_open', '打开记录目录', 'open', 36, 670),
    ):
        node = text(root.op(page_name), name, label, x=x, top=top, width=180, height=36, size=16, align='center')
        node.store('design_action', action_name)
        setp(node, layer=250, bgcolorr=.145, bgcolorg=.388, bgcolorb=.651, bgalpha=1,
             fontcolorr=1, fontcolorg=1, fontcolorb=1)
        callback = shell.op('Logic').create(panelexecuteDAT, name + '_click')
        setp(callback, panels=node.path, panelvalue='lselect', offtoon=True)
        callback.text = 'def onOffToOn(v):\n    op(' + repr(render.path) + ').module.design_action(' + repr(action_name) + ')\n'
    op('/perform').par.title = 'SRP Workbench'
    setp(op('/perform'),size='custom',winw=1280,winh=720)
    op('/perform').par.winop = root.path
    op(ROOT + '/Output/workbench_a_view').par.opviewer = root.path
    render.par.active = True
    render.module.onFrameStart(0)
    return shell
