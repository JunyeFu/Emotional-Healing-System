"""Build the single-window consecutive-experiment candidate from the monitor."""
from pathlib import Path

_monitor = Path(__file__).with_name('build_workbench_monitor.py')
exec(compile(_monitor.read_text(encoding='utf-8'), str(_monitor), 'exec'), globals())
_monitor_build = build
CANDIDATE = 'T01_Workbench_A.flow-v5.candidate.toe'

FLOW_RUNTIME = '''
flow_module = types.ModuleType('td_experiment_workflow')
exec(op(ROOT + '/WorkbenchA/Logic/workflow_source').text, flow_module.__dict__)
from pathlib import Path
workflow = flow_module.Workflow(Path(project.folder) / 'development-workflow', session_module.DevelopmentCapture)
capture = workflow.capture
_monitor_frame = onFrameStart
history_selection = None
flow_last = None

def action(name):
    global capture, channels, streams, history_selection
    try:
        previous = workflow.current
        workflow.action(name, time.monotonic_ns())
        capture = workflow.capture
        if workflow.current is not previous:
            import builtins
            preview.streams.clear()
            channels = session_module.Channels()
            streams = {}
            if hasattr(builtins, 'T01_TELEMETRY_ADAPTER'):
                del builtins.T01_TELEMETRY_ADAPTER
            history_selection = None
    except ValueError as error:
        workflow.error = str(error)
    except OSError:
        workflow.fault('WORKFLOW_STORAGE_FAILED')
    render_flow(time.monotonic_ns())

def inspect_history(index):
    global history_selection
    history_selection = index
    render_flow(time.monotonic_ns())

def open_record():
    import os
    from pathlib import Path
    item = workflow.history[history_selection] if history_selection is not None else workflow.current
    if item and item.get('path'):
        path = (workflow.root / item['path']).resolve()
        if path.is_relative_to(workflow.root.resolve()) and path.exists():
            os.startfile(str(path.parent))

def ingest_monitor(raw, now):
    global capture, interface_error
    import json
    try:
        p = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return False
    if not isinstance(p, dict):
        return False
    if p.get('message_type') == 'session_observation':
        try:
            workflow.event(p, now)
            capture = workflow.capture
            interface_error = None
        except ValueError as error:
            interface_error = str(error)
            workflow.error = str(error)
        except OSError:
            workflow.fault('WORKFLOW_STORAGE_FAILED')
        return True
    if not workflow.current or p.get('session_id') != workflow.current['session_id']:
        return True
    if p.get('message_type') == 'device_preview':
        if preview.ingest(raw, now):
            channels.append(p)
            try:
                workflow.append(p, now)
            except OSError:
                workflow.fault('CAPTURE_WRITE_FAILED')
        return True
    return False

def select_page(name):
    workflow.view = 'DETAILS' if name == 'timing' else None
    render_flow(time.monotonic_ns())

def _set_text(node, value):
    node.par.text = str(value)

def render_flow(now):
    shell = op(ROOT + '/WorkbenchA')
    content = shell.op('Content')
    pages = content.op('Pages')
    stage, view, c = workflow.stage, workflow.view, workflow.current
    page = 'history' if view == 'HISTORY' else 'timing' if view == 'DETAILS' else 'home' if stage == 'HOME' else 'closeout' if stage == 'CLOSEOUT' else 'overview'
    for node in pages.panelChildren:
        node.par.display = node.name == page
    shell.store('active_page', page)
    shell.store('flow_stage', stage)
    names = {'HOME':'主页面','PREPARE':'实验准备','WAITING':'正在等待Unity开始','RUNNING':'实验监控','PAUSED':'实验已暂停','CLOSEOUT':'本场实验收尾'}
    _set_text(content.op('Context/recording'), names[stage] + (' · ' + ('模拟模式' if c else '开发工作台')))
    eff, total = workflow.times(now)
    _set_text(content.op('Context/elapsed'), session_module.duration(eff))
    _set_text(content.op('Header/state'), '模拟模式 · 正式记录桥未接入')
    content.op('Header/state').par.bgalpha = 0
    _set_text(content.op('Header/source'), '会话：' + (c['session_id'] if c else '未创建'))
    _set_text(content.op('FlowNav/current/label'), names[stage])
    _set_text(content.op('FlowNav/history/label'), '本轮实验记录 (' + str(len(workflow.history)) + ')')
    content.op('FlowNav/back').par.display = view is not None
    content.op('FlowNav/current').par.enable = False
    done = sum(x['status'] == 'COMPLETED' for x in workflow.history)
    aborted = sum(x['status'] == 'ABORTED' for x in workflow.history)
    pending = sum(not x.get('closed', False) for x in workflow.history)
    _set_text(pages.op('home/counts'), f'完成 {done} 次    中止 {aborted} 次    待收尾 {pending} 次')
    _set_text(content.op('Footer/link'), 'UDP 5005 | 20 Hz | 总历时 ' + session_module.duration(total))
    for node in content.op('Footer').findChildren(type=textCOMP):
        if node.fetch('field',None) == 'footer':
            _set_text(node, '有效用时 ' + session_module.duration(eff) + '（分:秒）')
    if c:
        labels = {'COMPLETED':'正常完成','ABORTED':'已中止','RECORDING_FAILED':'录制失败'}
        fields = dict(participant=c['participant'], assignment=c['condition'], flow_session=c['session_id'],
                      pretest='已收到（模拟）' if c['pretest'] else '待回执',
                      unity_ready='已确认（模拟）' if c['unity_ready'] else '待回执',
                      store_ready='已确认（模拟）' if c['store_ready'] else '待回执',
                      ideal=c['ideal'], guide=c['guide'], measured=c['actual'],
                      result=labels.get(c['status'], c['status']), effective=session_module.duration(eff),
                      total=session_module.duration(total), sealed='已确认（模拟）' if c['sealed'] else '待封存确认',
                      posttest='已收到（模拟）' if c['posttest'] else '待回执', record_file=c['path'] or '准备期不写入实验记录')
        for node in pages.findChildren(type=textCOMP):
            field = node.fetch('flow_field', None)
            if field in fields:
                _set_text(node, fields[field])
    controls = pages.op('overview/flow_controls')
    visible = {'submit':stage=='PREPARE', 'cancel':stage in ('PREPARE','WAITING'),
               'pause':stage=='RUNNING','resume':stage=='PAUSED','abort':stage in ('RUNNING','PAUSED')}
    for key, show in visible.items():
        controls.op(key).par.display = show
        controls.op(key).par.enable = not workflow.pending and (workflow.ready if key == 'submit' else True)
    for key in ('next','home'):
        pages.op('closeout/' + key).par.enable = workflow.can_close and not workflow.pending
        pages.op('closeout/' + key).par.opacity = 1 if workflow.can_close and not workflow.pending else .4
    if workflow.error:
        note = '需处理：' + workflow.error
    elif workflow.pending:
        note = '请求已提交 · 等待Python确认：' + workflow.pending['action']
    elif stage == 'PREPARE':
        note = '检查曲线与设备；等待分配、前测、Unity及记录准备回执'
    elif stage == 'WAITING':
        note = 'Unity已点击开始 · 等待Python确认' if capture.state == 'CLICKED' else 'Unity开始请求未收到 · 实验记录未开始'
    elif stage == 'PAUSED':
        note = '有效计时冻结 · 数据记录保持连续'
    elif stage == 'CLOSEOUT':
        note = '可完成收尾并准备下一次' if workflow.can_close else '待封存及后测回执，保留本场，不创建下一场'
    else:
        note = '同一窗口连续运行 · 每场独立记录'
    _set_text(content.op('FlowNote'), note)
    table = pages.op('history/rows')
    template = shell.op('Logic/history_template')
    status = {'COMPLETED':'正常完成','ABORTED':'已中止','INTERRUPTED':'运行中断','RECORDING':'进行中','PAUSED':'已暂停','RECORDING_FAILED':'录制失败'}
    for i, item in enumerate(workflow.history):
        row = table.op('row_' + str(i))
        if row is None:
            row = table.copy(template, name='row_' + str(i))
            row.par.display = True
            callback = shell.op('Logic').create(panelexecuteDAT, 'history_click_' + str(i))
            callback.par.panels = row.op('inspect').path
            callback.par.panelvalue = 'lselect'
            callback.par.offtoon = True
            callback.text = 'def onOffToOn(v):\\n    op(' + repr(shell.op('Logic/render').path) + ').module.inspect_history(' + str(i) + ')\\n'
        row.par.y.expr = 'parent().height - ' + str((i+1)*38)
        values = (item['session_id'], status.get(item['status'],item['status']), '已封存' if item['sealed'] else '待确认', '已收到' if item['posttest'] else '待回执')
        for j, value in enumerate(values):
            _set_text(row.op('col_' + str(j)), value)
    item = workflow.history[history_selection] if history_selection is not None else None
    _set_text(pages.op('history/summary'), ('会话 ' + item['session_id'] + '  |  ' + str(item.get('path') or '无记录文件')) if item else '选择“查看”读取会话摘要，历史记录只读')
    pages.op('history/open').par.enable = bool(item and item.get('path'))

def onFrameStart(frame):
    global flow_last
    now = time.monotonic_ns()
    if flow_last is not None and now - flow_last < 50_000_000:
        return
    flow_last = now
    _monitor_frame(frame)
    render_flow(now)
'''


def flow_text(parent, name, value, field=None, **kw):
    node = text(parent, name, value, **kw)
    if field:
        node.store('flow_field', field)
    return node


def command(parent, name, label, action_name, x=0, top=0, width=180, primary=False):
    wrapper = panel(parent, name, x=x, top=top, width=width, height=36, background='blue' if primary else 'neutral')
    node = text(wrapper, 'label', label, align='center', size=16)
    if primary:
        color(wrapper, '#2563A6')
        setp(node,fontcolorr=1,fontcolorg=1,fontcolorb=1)
    callback = op(SHELL + '/Logic').create(panelexecuteDAT, 'action_' + parent.name + '_' + name)
    setp(callback, panels=node.path, panelvalue='lselect', offtoon=True)
    expr = 'open_record()' if action_name == 'open' else 'action(' + repr(action_name) + ')'
    callback.text = 'def onOffToOn(v):\n    op(' + repr(SHELL + '/Logic/render') + ').module.' + expr + '\n'
    return wrapper


def build():
    shell = _monitor_build()
    render = shell.op('Logic/render')
    render.par.active = False
    logic, content = shell.op('Logic'), shell.op('Content')
    content.op('Header/state').store('status_key',None)
    logic.create(textDAT, 'workflow_source').text = (BASE / 'experiment_workflow.py').read_text(encoding='utf-8')
    shell.store('workflow_root', str(Path(project.folder) / 'development-workflow'))
    content.op('Tabs').par.display = False
    nav = panel(content, 'FlowNav', top=36, height=36, background='neutral')
    command(nav, 'current', '主页面', 'back', width=220)
    command(nav, 'history', '本轮实验记录', 'history', x=228, width=230)
    command(nav, 'details', '设备明细', 'details', x=466, width=140)
    command(nav, 'back', '返回当前阶段', 'back', x='=parent().width - 170', width=170)
    # One rendered root, with only its current phase child visible.
    pages = content.op('Pages')
    bounds(pages, top=126, height='=parent().height - 192')
    flow_text(content, 'FlowNote', '', top='=parent().height - 60', height=28, size=14)
    overview = pages.op('overview')
    for name in ('devices','main'):
        overview.op(name).par.h.expr = 'parent().height - 66'
    overview.op('events').par.display = False
    controls = panel(overview, 'flow_controls', top='=parent().height - 40', height=36)
    for name,label,act,x,width in (('cancel','取消准备申请','cancel',0,180),('submit','提交准备确认','submit',200,180),('pause','暂停请求','pause',0,160),('resume','恢复请求','resume',0,160),('abort','中止请求','abort',180,160)):
        command(controls,name,label,act,x=x,width=width,primary=name in ('submit','resume'))
    # Replace the old target/actual interpretation with explicit I/G/X placeholders.
    sidebar = overview.op('main')
    for node in list(sidebar.children):
        node.destroy()
    heading(sidebar, '会话与准备 / 运行', height=26)
    entries=(('匿名编号','participant'),('条件（锁定）','assignment'),('前测回执','pretest'),('Unity准备','unity_ready'),('记录准备','store_ready'),('I 共同理想','ideal'),('G 实际下发','guide'),('X 实测呼吸','measured'))
    for i,(label,field) in enumerate(entries):
        row=panel(sidebar,'row_'+str(i),top=26+i*34,height=34)
        text(row,'label',label,width=118,size=14,ink='muted')
        flow_text(row,'value','未接入',field,x=118,width='=parent().width - 118',size=14)
        line(row,'line',33)
    home=panel(pages,'home')
    text(home,'title','连续实验工作台',top=28,height=52,size=26,align='center')
    command(home,'new','新建实验准备','new',x='=(parent().width - 300) / 2',top=104,width=300,primary=True).par.h=48
    command(home,'history','本轮实验记录','history',x='=(parent().width - 300) / 2',top=168,width=300)
    text(home,'status','Python / Unity：等待模拟桥回执\n设备与记录服务：在每场准备时核查',top=220,height=70,align='center',wrap=True)
    text(home,'counts','',top=320,height=36,align='center')
    close=panel(pages,'closeout')
    text(close,'title','本场实验收尾',height=44,size=24,align='center')
    for i,(label,field) in enumerate((('会话','flow_session'),('结束状态','result'),('有效用时','effective'),('总历时','total'),('记录封存','sealed'),('后测回执','posttest'))):
        row=panel(close,'row_'+str(i),x='=parent().width * .15',top=52+i*42,width='=parent().width * .7',height=42)
        text(row,'label',label,width=156,ink='muted')
        flow_text(row,'value','—',field,x=156,width='=parent().width - 156')
        line(row,'line',41)
    command(close,'open','打开记录目录','open',x='=parent().width * .15',top=314,width=180)
    command(close,'next','完成收尾并准备下一次','next',x='=parent().width * .15',top='=parent().height - 46',width=280,primary=True)
    command(close,'home','返回主页面','home',x='=parent().width * .15 + 292',top='=parent().height - 46',width=180)
    history=panel(pages,'history')
    text(history,'title','本轮实验记录 · 只读',height=40,size=22)
    head=panel(history,'columns',top=44,height=30,background='neutral')
    widths=(.38,.18,.16,.16,.12)
    start=0
    template=panel(logic,'history_template',height=38)
    template.par.display=False
    for i,(label,w) in enumerate(zip(('会话','结束状态','记录','后测','操作'),widths)):
        text(head,'col_'+str(i),label,x='=parent().width * '+str(start),width='=parent().width * '+str(w),size=14)
        text(template,'inspect' if i==4 else 'col_'+str(i),'查看' if i==4 else '',x='=parent().width * '+str(start),width='=parent().width * '+str(w),size=14)
        start+=w
    line(template,'line',37)
    rows=panel(history,'rows',top=76,height='=parent().height - 184')
    setp(rows,pvscrollbar='on',mousewheel=True)
    text(history,'summary','',top='=parent().height - 100',height=52,size=12,wrap=True)
    command(history,'open','打开记录目录','open',top='=parent().height - 42',width=180)
    command(history,'back','返回当前阶段','back',x='=parent().width - 190',top='=parent().height - 42',width=190,primary=True)
    render.text += '\n' + FLOW_RUNTIME
    cb=op(ROOT + '/Sources/UdpTelemetryAdapter/udp_callbacks')
    cb.text += '''
def onReceive(dat, rowIndex, message, bytes, peer):
    import builtins, time, json
    raw, now = builtins.bytes(bytes), time.monotonic_ns()
    runtime = op('/project1/T01_TelemetryPanel/WorkbenchA/Logic/render').module
    if runtime.ingest_monitor(raw, now):
        return
    result = _adapter().ingest_datagram(raw, now)
    if result.accepted:
        try:
            runtime.workflow.append(json.loads(raw), now)
        except OSError:
            runtime.workflow.fault('CAPTURE_WRITE_FAILED')
'''
    render.par.active=True
    render.module.onFrameStart(0)
    return shell
