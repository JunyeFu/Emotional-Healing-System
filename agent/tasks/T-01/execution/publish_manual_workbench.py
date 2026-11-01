"""Run inside the verified TD copy to save a clean, operator-owned project."""
from pathlib import Path


def publish():
    root = op('/project1/T01_TelemetryPanel')
    shell = root.op('WorkbenchA')
    runtime = shell.op('Logic/render').module
    if runtime.workflow.stage != 'HOME':
        raise RuntimeError('Return to HOME before publishing the workbench')
    render=shell.op('Logic/render')
    manual=render.text[render.text.index('\nimport socket\nimport json\n_mock_status_socket'):]
    design=Path(__file__).with_name('workbench_redesign_runtime.py').read_text(encoding='utf-8')
    render.text=render.text.split('_flow_frame = onFrameStart')[0]+design.encode('ascii','backslashreplace').decode('ascii')+manual
    for page in ('history', 'unselected'):
        for row in shell.op('Design/' + page + '/rows').children:
            row.destroy()
    for callback in shell.op('Logic').children:
        if callback.name.startswith(('design_history_', 'history_click_')):
            callback.destroy()
    for row in shell.op('Content/Pages/history/rows').children:
        row.destroy()
    hook = root.op('_capture_runtime')
    if hook is not None:
        hook.destroy()
    shell.store('workflow_root', '../../../local/artifacts/td-manual-workbench/development-workflow')
    target = Path(__file__).resolve().parents[3] / 'modules/touchdesigner/t01_telemetry_panel/T01_ManualWorkbench.toe'
    project.save(str(target))
    print('MANUAL_WORKBENCH_PUBLISHED', str(target))


publish()
