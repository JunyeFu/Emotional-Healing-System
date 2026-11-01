import importlib.util
from pathlib import Path
from types import SimpleNamespace


def load_sdk(tmp_path):
    path = Path(__file__).with_name('capture_workbench_sdk.py')
    spec = importlib.util.spec_from_file_location('capture_sdk', path)
    sdk = importlib.util.module_from_spec(spec)
    sdk.me = SimpleNamespace(fetch=lambda key: str(tmp_path / key))
    sdk.op = lambda path: SimpleNamespace(module=sdk)
    spec.loader.exec_module(sdk)
    return sdk


def test_manual_click_cannot_advance_automated_capture(tmp_path):
    sdk = load_sdk(tmp_path)
    path = '/project1/T01_TelemetryPanel/WorkbenchA/Content/Pages/home/new/label'
    assert not sdk.accept_click(path)
    sdk._scripted_click = path
    assert not sdk.accept_click(path.replace('/new/', '/history/'))
    assert sdk.accept_click(path)
    assert not sdk.accept_click(path)
    sdk._input_owned = False
    assert sdk.accept_click(path)


def test_native_callback_is_guarded_then_restored(tmp_path):
    sdk = load_sdk(tmp_path)
    path = '/project1/T01_TelemetryPanel/WorkbenchA/Content/Pages/home/new/label'
    original = 'events = []\ndef onOffToOn(value):\n    events.append(value)\n'
    callback = SimpleNamespace(path='/project1/test_click', text=original,
                               par=SimpleNamespace(panels=SimpleNamespace(eval=lambda: path)))
    sdk._root = SimpleNamespace(findChildren=lambda **kwargs: [callback])
    sdk.panelexecuteDAT = object()
    sdk.guard_inputs()
    guarded = callback.text
    sdk.guard_inputs()
    assert callback.text == guarded
    scope = dict(me=callback, op=sdk.op)
    exec(callback.text, scope)
    scope['onOffToOn']('manual')
    assert scope['events'] == []
    sdk._scripted_click = path
    scope['onOffToOn']('scripted')
    scope['onOffToOn']('duplicate')
    assert scope['events'] == ['scripted']
    sdk._root.op = lambda node: callback
    sdk.release_inputs()
    assert callback.text == original
    exec(callback.text, scope)
    scope['onOffToOn']('manual-after-capture')
    assert scope['events'] == ['manual-after-capture']
