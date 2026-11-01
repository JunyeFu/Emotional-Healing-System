"""Offline TOE checks; these are not a TouchDesigner runtime acceptance."""
from pathlib import Path
import io
import pickle
import re
import struct
import subprocess
from types import SimpleNamespace

from package_bigrun_workbench import PANEL, REL_SHELL, TEXT, package, parameter, read_dat, write_dat


def test_dat_roundtrip_does_not_drop_the_first_character(tmp_path):
    source = tmp_path / 'test.text'
    header = b'2\n*' + b'\x00' * 20
    assert len(header) == 23
    data = b'def f():\n    pass\n'
    source.write_bytes(header + struct.pack('>I', len(data)) + data)
    assert read_dat(source)[1].startswith('def ')
    write_dat(source, 'import json\n')
    assert read_dat(source)[1] == 'import json\n'


def test_multiline_text_parameter_replacement_preserves_geometry(tmp_path):
    path = tmp_path / 'node.parm'
    path.write_text('?\ntext 0 \ufeff"old\nmessage"\nx 0 20\nw 0 100\n?\n', encoding='utf-8')
    parameter(path, 'text', '\ufeff"BigRun Team"')
    assert path.read_text(encoding='utf-8') == '?\ntext 0 \ufeff"BigRun Team"\nx 0 20\nw 0 100\n?\n'


def test_native_package_embeds_current_sources_and_keeps_aligned_geometry(tmp_path):
    original = (PANEL / 'T01_ManualWorkbench.toe').read_bytes()
    target = package(tmp_path / 'bigrun.toe')
    subprocess.run(['D:/TouchDesigner/bin/toeexpand.exe', str(target)], capture_output=True)
    directory = Path(str(target) + '.dir')
    shell = directory / REL_SHELL
    runtime = read_dat(shell / 'Logic/render.text')[1]
    assert runtime == Path(__file__).with_name('bigrun_workbench_runtime.py').read_text(encoding='utf-8')
    assert 'sendto(' not in runtime and 'workflow.event(' not in runtime
    assert read_dat(shell / 'Logic/device_preview_source.text')[1] == (PANEL / 'bigrun_preview.py').read_text(encoding='utf-8')
    for node in shell.glob('Logic/*.text'):
        _, code = read_dat(node)
        if node.stem in ('render', 'device_preview_source', 'session_source') or node.stem.endswith('_callbacks'):
            compile(code, str(node), 'exec')
    values = []
    for node in shell.rglob('*.parm'):
        match = TEXT.search(node.read_text(encoding='utf-8'))
        if match:
            values.append(match[1])
    assert not any(any(old in value for old in ('Polar H10', 'respiBAN', 'PLUX', 'MOCK-', '模拟', 'μV', 'RR ms')) for value in values)
    assert 'active 0 off' in (directory / 'project1/T01_TelemetryPanel/Runtime/render_execute.parm').read_text()
    design = shell / 'Design'
    pages = sorted(n.stem for n in design.glob('*.parm'))
    assert pages == ['abort', 'closed', 'closeout', 'details', 'fault', 'history', 'home', 'paused', 'prepare', 'running', 'unselected', 'waiting']
    # Shared top and footer borders retain identical x/w/y across the six monitor pages.
    for index in (2, 23, 24, 25):
        geometry = []
        for page in ('prepare', 'waiting', 'running', 'paused', 'abort'):
            node = design / page / f'c_{page}_{index}.parm'
            text = node.read_text(encoding='utf-8')
            geometry.append(tuple(re.findall(r'^(?:x|y|w|h) .*$', text, re.MULTILINE)))
        assert len(set(geometry)) == 1, (index, geometry)
    assert (PANEL / 'T01_ManualWorkbench.toe').read_bytes() == original
    exercise_embedded_runtime(shell)


def exercise_embedded_runtime(shell):
    """Execute the embedded renderer against native-node metadata, not native TD."""
    class PrimitiveUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            raise ValueError('Only primitive TD storage is read by this test')
    nodes = {}
    class Node:
        def __init__(self, path, text_node=False):
            self.path, self.name = path, path.rsplit('/', 1)[-1]
            self.storage, self.children, self.is_text = {}, [], text_node
            self.cook_count = 0
            self.par = SimpleNamespace(text='', display=True, enable=True, opacity=1,
                                       winopen=SimpleNamespace(pulse=lambda: None))
            self.width, self.height = 756, 110
            nodes[path] = self
        @property
        def panelChildren(self): return self.children
        def fetch(self, key, default=None): return self.storage.get(key, default)
        def store(self, key, value): self.storage[key] = value
        def op(self, path): return nodes.get(path if path.startswith('/') else self.path + '/' + path)
        def findChildren(self, type=None):
            return [n for key, n in nodes.items() if key.startswith(self.path + '/') and n.is_text]
        def cook(self, **kw): self.cook_count += 1
    base = '/project1/T01_TelemetryPanel/WorkbenchA'
    Node('/perform')
    udp = Node('/project1/T01_TelemetryPanel/Sources/UdpTelemetryAdapter/udp_in')
    Node(base)
    root = Node(base + '/Design')
    for node_file in sorted((shell / 'Design').rglob('*.n'), key=lambda p: len(p.parts)):
        relative = node_file.relative_to(shell).with_suffix('').as_posix()
        text = node_file.read_text(encoding='utf-8')
        if not text.startswith('COMP:'):
            continue
        node = Node(base + '/' + relative, text.startswith('COMP:text'))
        parent = nodes.get(node.path.rsplit('/', 1)[0])
        if parent: parent.children.append(node)
        storage = re.search(r'^dict ([A-Fa-f0-9]+)$', text, re.MULTILINE)
        if storage:
            node.storage = PrimitiveUnpickler(io.BytesIO(bytes.fromhex(storage[1]))).load()
        parameter_file = node_file.with_suffix('.parm')
        parameter_text = parameter_file.read_text(encoding='utf-8')
        value = TEXT.search(parameter_text)
        if value: node.par.text = value[1].lstrip('\ufeff').strip('"')
    for name in ('device_preview_source', 'session_source'):
        node = Node(base + '/Logic/' + name)
        node.text = read_dat(shell / ('Logic/' + name + '.text'))[1]
    for source in ('resp', 'ecg'):
        Node(base + '/Logic/plot_' + source)
    context = dict(op=lambda path: nodes[path], textCOMP='textCOMP',
                   project=SimpleNamespace(folder=str(PANEL)), ui=SimpleNamespace(clipboard=''))
    exec(compile(read_dat(shell / 'Logic/render.text')[1], 'embedded-runtime', 'exec'), context)
    render = context['onFrameStart']
    for page in root.children:
        context['page_name'] = page.name
        context['last_tick'] = None
        render(0)
        assert [n.name for n in root.children if n.par.display] == [page.name]
        for node in page.findChildren():
            if node.fetch('design_action') in ('submit', 'start', 'pause', 'resume', 'posttest', 'abort_confirm'):
                assert node.par.enable is False
    assert context['design_action']('start') is False
    assert udp.cook_count >= len(root.children), 'UDP receive callbacks must be serviced without the legacy renderer'
    assert context['design_action']('new') is True
    assert context['page_name'] == 'prepare'
    assert context['design_action']('submit') is False
    assert context['design_action']('cancel') is True
    assert context['page_name'] == 'home'
    for source, key in (('resp', 'acceleration'), ('ecg', 'rr'), ('ecg', 'hr')):
        context['select_curve'](source, key)
        assert context['selected'][source] == key
