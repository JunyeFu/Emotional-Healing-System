"""TD executeDAT callback used only by the isolated screenshot runner."""
from pathlib import Path
import json
import time
import traceback

_root = op('/project1/T01_TelemetryPanel')
_evidence = Path(me.fetch('evidence'))
_command = Path(me.fetch('command'))
_builder = Path(me.fetch('builder'))
_built = False
_handled = None
_pending = None
_input_owned = True
_scripted_click = None
_guarded = {}
_stage_deadline = None
_click_trace = []


def accept_click(path):
    global _scripted_click
    _click_trace.append((str(path),str(_scripted_click)))
    if not _input_owned:
        return True
    if path != _scripted_click:
        return False
    _scripted_click = None
    return True


def guard_inputs():
    for callback in _root.findChildren(type=panelexecuteDAT):
        if callback.path in _guarded or 'def onOffToOn(' not in callback.text:
            continue
        _guarded[callback.path] = callback.text
        callback.text += '''
_capture_original_click = onOffToOn
def onOffToOn(value):
    if op('/project1/T01_TelemetryPanel/_capture_runtime').module.accept_click(me.par.panels.eval()):
        _capture_original_click(value)
'''


def release_inputs():
    global _input_owned, _scripted_click
    _input_owned, _scripted_click = False, None
    for path, original in _guarded.items():
        callback = _root.op(path)
        if callback is not None:
            callback.text = original
    _guarded.clear()


def onFrameStart(frame):
    global _built, _handled, _pending, _scripted_click, _stage_deadline
    try:
        if not _built:
            _built = True
            me.par.active = False
            if not me.fetch('skip_build',False):
                scope = dict(globals(), __file__=str(_builder), __name__='td_capture')
                exec(compile(_builder.read_text(encoding='utf-8'), str(_builder), 'exec'), scope)
                scope['RUNTIME_DIR'] = Path(project.folder)
                scope['build']()
                if me.fetch('reopen_required',False):
                    me.store('skip_build',True)
                    built=Path(project.folder)/'built.toe'
                    me.par.active=True
                    project.save(str(built))
                    me.par.active=False
                    (_evidence/'built.json').write_text(json.dumps(dict(path=str(built))),encoding='utf-8')
                    return
            guard_inputs()
            me.par.active = True
            _root.op('WorkbenchA').par.sizefromwindow = False
            op('/perform').par.winopen.pulse()
            (_evidence / 'ready.json').write_text(json.dumps({
                'build': str(app.build), 'project': str(project.folder),
            }, ensure_ascii=False, indent=2), encoding='utf-8')
            if _root.op('WorkbenchA/Design'):
                (_evidence / 'layout-diagnostic.json').write_text(json.dumps({path:dict(
                    pars={p.name:str(p.eval()) for p in _root.op(path).pars()},
                    scrollv=_root.op(path).panel.scrollv.val)
                    for path in ('WorkbenchA','WorkbenchA/Design','WorkbenchA/Design/home')},indent=2),encoding='utf-8')
        guard_inputs()
        commands = sorted(_command.parent.glob('command-*.json'))
        if commands:
            request = json.loads(commands[-1].read_text(encoding='utf-8'))
            if request['id'] != _handled:
                (_evidence / 'capture-progress.json').write_text(json.dumps(dict(file=request['filename'],step='command_received')))
                _handled = request['id']
                shell = _root.op('WorkbenchA')
                shell.par.w, shell.par.h = request['width'], request['height']
                viewer = _root.op('Output/workbench_a_view')
                viewer.par.outputresolution = 'custom'
                viewer.par.resolutionw, viewer.par.resolutionh = request['width'], request['height']
                viewer.cook(force=True)
                _pending = (request, time.monotonic() + 2, 'press')
                _stage_deadline = time.monotonic() + request.get('wait_seconds', 60)
        if _pending and time.monotonic() >= _pending[1]:
            request, _, phase = _pending
            (_evidence / 'capture-progress.json').write_text(json.dumps(dict(file=request['filename'],step=phase)))
            shell = _root.op('WorkbenchA')
            if phase == 'press':
                # Exercise real panel clicks without a runner grant to reproduce the reported race.
                for path in request.get('manual_clicks', []):
                    panel = shell.op(path)
                    panel.interactMouse(.5, .5, left=True)
                    panel.interactMouse(.5, .5, left=False)
                    panel.interactClear()
            tab = shell.op(request['click']) if request.get('workflow') and request.get('click') else None if request.get('workflow') else shell.op('Content/Tabs/' + request['page'] + '/label')
            if request.get('_clicked_path'):
                tab = shell.op(request['_clicked_path'])
            elif request.get('design_action'):
                page = shell.op('Design/' + shell.fetch('design_page'))
                def visible(node):
                    while node.path != shell.path:
                        if hasattr(node.par,'display') and not node.par.display.eval():
                            return False
                        node=node.parent()
                    return True
                matches = [n for n in page.findChildren(type=textCOMP) if n.fetch('design_action',None) == request['design_action'] and visible(n)]
                if not matches:
                    raise RuntimeError(('ACTION_NOT_FOUND',request['design_action'],page.path))
                tab = page.op('raw/close') if request['design_action']=='raw' and shell.op('Logic/render').module.raw_expanded else matches[0]
                request['_clicked_path'] = tab.path
            if tab is None and phase in ('press','release'):
                phase = 'capture'
            if phase == 'press':
                _scripted_click = tab.path
                tab.interactMouse(.5, .5, left=True)
                chain = []
                node = tab
                while node is not None:
                    chain.append(dict(path=node.path, enable=str(node.par.enable.eval()) if hasattr(node.par, 'enable') else '',
                                      display=str(node.par.display.eval()) if hasattr(node.par, 'display') else '',
                                      opacity=str(node.par.opacity.eval()) if hasattr(node.par, 'opacity') else ''))
                    node = node.parent() if node.path != '/' else None
                (_evidence / 'press-diagnostic.json').write_text(json.dumps(dict(chain=chain,
                    interactions=str(tab.interactStatus()),
                    panel_values={key: getattr(tab.panel, key).val for key in ('lselect', 'select', 'inside', 'u', 'v')},
                    errors=shell.errors(recurse=True) + shell.scriptErrors(recurse=True)), indent=2), encoding='utf-8')
                _pending = (request, time.monotonic() + .2, 'release')
                return
            if phase == 'release':
                tab.interactMouse(.5, .5, left=False)
                _scripted_click = None
                _pending = (request, time.monotonic() + .3, 'capture')
                return
            if tab is not None:
                tab.interactClear()
            if request.get('expect_stage'):
                workflow = shell.op('Logic/render').module.workflow
                ready = request.get('expect_ready')
                if (workflow.stage != request['expect_stage'] or (ready is not None and workflow.ready != ready)
                        or (request.get('expect_sealed') is not None and (workflow.current or {}).get('sealed') != request['expect_sealed'])
                        or (request.get('expect_page') and shell.fetch('design_page') != request['expect_page'])):
                    if time.monotonic() >= _stage_deadline:
                        raise TimeoutError(workflow.snapshot(time.monotonic_ns()))
                    _pending = (request, time.monotonic() + .1, 'stage-waiting')
                    return
            curve_items = list(request.get('curves',{}).items())
            curve_index = request.get('_curve_index',0)
            if curve_index < len(curve_items):
                source,key = curve_items[curve_index]
                if shell.op('Design'):
                    page = shell.op('Design/' + shell.fetch('design_page'))
                    curve = next(n for n in page.findChildren(type=textCOMP) if n.fetch('design_curve',None) == (source,key))
                else:
                    curve = shell.op('Content/Pages/overview/devices/' + source + '/tabs/' + key + '/label')
                if phase == 'curve-release':
                    curve.interactMouse(.5,.5,left=False)
                    _scripted_click=None
                    _pending=(request,time.monotonic()+.3,'curve-check')
                elif phase == 'curve-check':
                    curve.interactClear()
                    if shell.op('Logic/render').module.selected[source] != key:
                        raise RuntimeError(('Curve click failed',key,curve.path,curve.par.enable.eval(),curve.par.display.eval(),str(curve.interactStatus()),_click_trace[-10:]))
                    request['_curve_index']=curve_index+1
                    _pending=(request,time.monotonic()+.1,'capture')
                elif phase != 'curve-layout':
                    _root.op('Output/workbench_a_view').cook(force=True)
                    _pending=(request,time.monotonic()+.2,'curve-layout')
                else:
                    _scripted_click=curve.path
                    curve.interactMouse(.5,.5,left=True)
                    _pending=(request,time.monotonic()+.2,'curve-release')
                return
            if not request.get('workflow') and shell.fetch('active_page') != request['page']:
                diagnostic = dict(page=shell.fetch('active_page'),
                    panel_values={key: getattr(tab.panel, key).val for key in ('lselect', 'select', 'inside', 'u', 'v')},
                    callback={p.name: str(p.eval()) for p in shell.op('Logic/tab_' + request['page']).pars()},
                    window={p.name: str(p.eval()) for p in op('/perform').pars()},
                    tab_geometry=[tab.x, tab.y, tab.width, tab.height])
                (_evidence / 'click-diagnostic.json').write_text(json.dumps(diagnostic, indent=2), encoding='utf-8')
                raise RuntimeError('Native tab click did not select ' + request['page'])
            if request.get('scroll') and phase != 'scrolled':
                body = shell.op('Content/Pages/timing/details')
                shell.store('scroll_before', body.panel.scrollv.val)
                body.interactMouse(.5, .5, wheel=-3)
                _pending = (request, time.monotonic() + .5, 'scrolled')
                return
            viewer = _root.op('Output/workbench_a_view')
            if request.get('scroll') and shell.fetch('scroll_before') == shell.op('Content/Pages/timing/details').panel.scrollv.val:
                raise RuntimeError('Native wheel did not move the detail body')
            (_evidence / 'capture-progress.json').write_text(json.dumps(dict(file=request['filename'], step='before_viewer')),encoding='utf-8')
            viewer.cook(force=True)
            viewer.save(str(_evidence / request['filename']))
            pixels = viewer.numpyArray(delayed=False)
            (_evidence / 'capture-progress.json').write_text(json.dumps(dict(file=request['filename'], step='after_viewer')),encoding='utf-8')
            panels = {name: shell.op('Content/' + name) for name in ('Header', 'Tabs', 'Context', 'Pages', 'Footer')}
            overview = shell.op('Content/Pages/overview')
            bands = {name: overview.op(name) for name in ('devices', 'main', 'feedback', 'counters', 'events') if overview.op(name) is not None}
            receipt = {
                'visible_ink_pixels':int((pixels[:,:,:3].min(axis=2)<.6).sum()),
                'pixel_variation':float(pixels[:,:,:3].std()),
                'clipboard':str(ui.clipboard) if request.get('design_action')=='copy' else None,
                'design_layout': {p.name:[dict(id=n.fetch('design_id'), actual=[n.x,n.y,n.width,n.height], xywh=[float(n.par.x.eval()),float(n.par.y.eval()),float(n.par.w.eval()),float(n.par.h.eval())]) for n in p.children if n.fetch('design_id',None)] for p in shell.op('Design').panelChildren} if shell.op('Design') else {},
                'design_controls': {n.fetch('design_action'): dict(path=n.path, enabled=bool(n.par.enable.eval()), visible=bool(n.par.display.eval())) for n in shell.op('Design/' + shell.fetch('design_page')).findChildren(type=textCOMP) if n.fetch('design_action',None)} if shell.op('Design') else {},
                'design_text': {n.name:n.par.text.eval() for n in shell.op('Design/' + shell.fetch('design_page')).findChildren(type=textCOMP) if n.par.display.eval()} if shell.op('Design') else {},
                'design_page': shell.fetch('design_page', None),
                'design_root': {'xywh': [shell.op('Design').x,shell.op('Design').y,shell.op('Design').width,shell.op('Design').height], 'pars': {p.name:str(p.eval()) for p in shell.op('Design').pars() if p.name in ('w','h','x','y','hmode','vmode','sizefromwindow','display','layer')}} if shell.op('Design') else None,
                'design_geometry': [{ 'name': n.path, 'xywh': [n.x,n.y,n.width,n.height], 'display': n.par.display.eval()} for n in shell.op('Design').panelChildren] if shell.op('Design') else [],
                'screenshot': request['filename'], 'layout_size': [shell.width, shell.height],
                'image_size': [viewer.width, viewer.height], 'page': shell.fetch('active_page'),
                'native_mouse_click': True, 'wheel_requested': bool(request.get('scroll')),
                'capture_input_owned': _input_owned,
                'blocked_manual_clicks': request.get('manual_clicks', []),
                'scroll_before': shell.fetch('scroll_before', None),
                'scroll_after': shell.op('Content/Pages/timing/details').panel.scrollv.val,
                'errors': shell.errors(recurse=True) + shell.scriptErrors(recurse=True),
                'panels': {k: [n.x, n.y, n.width, n.height] for k, n in panels.items()},
                'overview_bands': {k: [n.x, n.y, n.width, n.height] for k, n in bands.items()},
                'overview_scrollbar': overview.par.pvscrollbar.eval(),
                'fields': {n.fetch('field'): {'text': n.par.text.eval(), 'size': [n.width, n.height],
                          'font_size': n.par.fontsize.eval()}
                          for n in overview.findChildren(type=textCOMP) if n.fetch('field', None)},
                'scope': 'Native TD UI with synthetic development fixtures only',
            }
            if hasattr(shell.op('Logic/render').module, 'preview'):
                runtime = shell.op('Logic/render').module
                if hasattr(runtime,'workflow'):
                    receipt['workflow'] = runtime.workflow.snapshot(time.monotonic_ns())
                    receipt['workflow_root'] = str(runtime.workflow.root)
                    receipt['visible_pages'] = [p.name for p in shell.op('Content/Pages').panelChildren if p.par.display.eval()]
                    receipt['flow_fields'] = {n.fetch('flow_field'): n.par.text.eval() for n in shell.findChildren(type=textCOMP) if n.fetch('flow_field',None)}
                if hasattr(runtime, 'capture'):
                    receipt['session_capture'] = dict(state=runtime.capture.state, count=runtime.capture.count,
                        path=str(runtime.capture.path), elapsed=runtime.capture.elapsed(time.monotonic_ns()),
                        curves=runtime.selected)
                receipt['device_preview'] = dict(accepted=runtime.preview.accepted,
                    rejected=runtime.preview.rejected, last_error=runtime.preview.last_error,
                    error_counts=runtime.preview.errors,
                    streams={key: dict(state=s['state'], buffered_samples=len(s['points'])) for key, s in runtime.streams.items()})
                receipt['device_preview']['plots'] = {}
                for source in ('resp', 'ecg'):
                    if request.get('workflow') and shell.fetch('active_page') != 'overview':
                        continue
                    plot = shell.op('Logic/plot_' + source)
                    plot.cook(force=True)
                    arr = plot.numpyArray(delayed=False)
                    receipt['device_preview']['plots'][source] = dict(size=[plot.width, plot.height],
                        trace_pixels=int((arr[:, :, 0] < .6).sum()))
                    if hasattr(runtime, 'selected'):
                        colors = runtime.session_module.COLORS
                        receipt['device_preview']['plots'][source]['color_pixels'] = {
                            key: int((abs(arr[:,:,:3] - runtime.session_module.rgb(code)).max(axis=2) < .015).sum())
                            for key, code in colors.items()}
                    if request.get('continuity'):
                        import numpy as np
                        key=runtime.selected[source]
                        series=runtime.channels.series(key,runtime.streams[source])
                        device=shell.op('Content/Pages/overview/devices/'+source)
                        plot.save(str(_evidence/(Path(request['filename']).stem+'-'+source+'-plot.png')))
                        detail=[]
                        for i,item in enumerate(series):
                            pixels=arr[round(arr.shape[0]*(2-i)/3):round(arr.shape[0]*(3-i)/3)] if len(series)==3 else arr
                            mask=abs(pixels[:,:,:3]-np.asarray(item['color'])).max(axis=2)<.015
                            valid=[(t,v) for t,v in item['points'] if v is not None]
                            detail.append(dict(axis=item.get('axis','value'),unit=item['unit'],window=item['window'],
                                range=item.get('range'),points=len(item['points']),null_count=sum(v is None for _,v in item['points']),
                                has_gaps=item['has_gaps'],end_ns=item['end_ns'],last_value=valid[-1][1] if valid else None,
                                trace_columns=float(mask.any(axis=0).mean()),trace_pixels=int(mask.sum())))
                        receipt.setdefault('continuity',{})[source]=dict(key=key,series=detail,
                            payload=runtime.streams[source]['payload'],
                            axis_text={n:device.op(n).par.text.eval() for n in ('axis_left','axis','axis_right','ymax','ymin')},
                            motion_labels=[device.op('motion_axis_'+str(i)).par.text.eval() for i in range(3)],
                            displayed_size=[device.op('wave').width,device.op('wave').height],
                            plot_size=[plot.width,plot.height])
            if request.get('final'):
                me.par.active = False
                release_inputs()
                shell.par.sizefromwindow = True
                if shell.fetch('manual_workbench',False):
                    shell.store('workflow_root','../../../local/artifacts/td-manual-workbench/development-workflow')
                project.save(str(Path(project.folder) / request.get('candidate', 'T01_Workbench_A.readable-v2.candidate.toe')))
                op('/perform').par.winopen.pulse()
            (_evidence / (request['filename'] + '.json')).write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
            _pending = None
    except Exception:
        release_inputs()
        (_evidence / 'error.json').write_text(json.dumps({'error': traceback.format_exc()}, ensure_ascii=False, indent=2), encoding='utf-8')
        me.par.active = False
