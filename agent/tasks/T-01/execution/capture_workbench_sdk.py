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


def onFrameStart(frame):
    global _built, _handled, _pending
    try:
        if not _built:
            _built = True
            me.par.active = False
            scope = dict(globals(), __file__=str(_builder), __name__='td_capture')
            exec(compile(_builder.read_text(encoding='utf-8'), str(_builder), 'exec'), scope)
            scope['RUNTIME_DIR'] = Path(project.folder)
            scope['build']()
            me.par.active = True
            _root.op('WorkbenchA').par.sizefromwindow = False
            op('/perform').par.winopen.pulse()
            (_evidence / 'ready.json').write_text(json.dumps({
                'build': str(app.build), 'project': str(project.folder),
            }, ensure_ascii=False, indent=2), encoding='utf-8')
        commands = sorted(_command.parent.glob('command-*.json'))
        if commands:
            request = json.loads(commands[-1].read_text(encoding='utf-8'))
            if request['id'] != _handled:
                _handled = request['id']
                shell = _root.op('WorkbenchA')
                shell.par.w, shell.par.h = request['width'], request['height']
                viewer = _root.op('Output/workbench_a_view')
                viewer.par.outputresolution = 'custom'
                viewer.par.resolutionw, viewer.par.resolutionh = request['width'], request['height']
                viewer.cook(force=True)
                _pending = (request, time.monotonic() + 2, 'press')
        if _pending and time.monotonic() >= _pending[1]:
            request, _, phase = _pending
            shell = _root.op('WorkbenchA')
            tab = shell.op('Content/Tabs/' + request['page'] + '/label')
            if phase == 'press':
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
                _pending = (request, time.monotonic() + .3, 'capture')
                return
            tab.interactClear()
            for source, key in request.get('curves', {}).items():
                curve = shell.op('Content/Pages/overview/devices/' + source + '/tabs/' + key + '/label')
                curve.interactMouse(.5, .5, left=True)
                curve.interactMouse(.5, .5, left=False)
                curve.interactClear()
                if shell.op('Logic/render').module.selected[source] != key:
                    raise RuntimeError('Curve click failed: ' + key)
            if request.get('curves') and phase == 'capture':
                _pending = (request, time.monotonic() + .5, 'curves-ready')
                return
            if shell.fetch('active_page') != request['page']:
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
            viewer.cook(force=True)
            viewer.save(str(_evidence / request['filename']))
            panels = {name: shell.op('Content/' + name) for name in ('Header', 'Tabs', 'Context', 'Pages', 'Footer')}
            overview = shell.op('Content/Pages/overview')
            bands = {name: overview.op(name) for name in ('devices', 'main', 'feedback', 'counters', 'events') if overview.op(name) is not None}
            receipt = {
                'screenshot': request['filename'], 'layout_size': [shell.width, shell.height],
                'image_size': [viewer.width, viewer.height], 'page': shell.fetch('active_page'),
                'native_mouse_click': True, 'wheel_requested': bool(request.get('scroll')),
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
            (_evidence / (request['filename'] + '.json')).write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
            if request.get('final'):
                me.par.active = False
                shell.par.sizefromwindow = True
                project.save(str(Path(project.folder) / request.get('candidate', 'T01_Workbench_A.readable-v2.candidate.toe')))
                op('/perform').par.winopen.pulse()
            _pending = None
    except Exception:
        (_evidence / 'error.json').write_text(json.dumps({'error': traceback.format_exc()}, ensure_ascii=False, indent=2), encoding='utf-8')
        me.par.active = False
