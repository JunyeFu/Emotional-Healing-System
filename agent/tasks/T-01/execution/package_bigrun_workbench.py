"""Offline native TOE packaging; never launches or controls the desktop."""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
PANEL = ROOT / 'agent/modules/touchdesigner/t01_telemetry_panel'
TARGET = PANEL / 'T01_BigRunWorkbench.toe'
REL_SHELL = 'project1/T01_TelemetryPanel/WorkbenchA'
TEXT = re.compile(r'^text 0 (?:\ufeff)?("(?:\\.|[^"\\])*"|[^\r\n]*)', re.MULTILINE)


def read_dat(path):
    raw = path.read_bytes()
    if raw[:2] != b'2\n' or struct.unpack('>I', raw[23:27])[0] != len(raw[27:]):
        raise ValueError('UNEXPECTED_TD_TEXT_FORMAT: ' + str(path))
    return raw, raw[27:].decode('utf-8')


def write_dat(path, source):
    raw, _ = read_dat(path)
    payload = source.encode('utf-8')
    path.write_bytes(raw[:23] + struct.pack('>I', len(payload)) + payload)


def parameter(path, key, value):
    source = path.read_text(encoding='utf-8')
    line = key + ' 0 ' + value
    pattern = TEXT if key == 'text' else re.compile(r'^' + re.escape(key) + r' .*$', re.MULTILINE)
    if pattern.search(source):
        source = pattern.sub(lambda _: line, source)
    else:
        source = source[:-2] + line + '\n?\n'
    path.write_text(source, encoding='utf-8')


def package(target=TARGET):
    if target.exists():
        raise FileExistsError('Candidate exists; choose a new --out or archive the old candidate first')
    scratch = ROOT / 'agent/local/artifacts'
    with tempfile.TemporaryDirectory(prefix='bigrun-toe-', dir=scratch) as temp:
        toe = Path(temp) / 'candidate.toe'
        shutil.copyfile(PANEL / 'T01_ManualWorkbench.toe', toe)
        subprocess.run(['D:/TouchDesigner/bin/toeexpand.exe', str(toe)], capture_output=True)
        directory = Path(str(toe) + '.dir')
        if not directory.is_dir():
            raise RuntimeError('TOE_EXPAND_FAILED')
        shell = directory / REL_SHELL
        runtime = Path(__file__).with_name('bigrun_workbench_runtime.py').read_text(encoding='utf-8')
        compile(runtime, 'bigrun_workbench_runtime.py', 'exec')
        write_dat(shell / 'Logic/render.text', runtime)
        write_dat(shell / 'Logic/device_preview_source.text', (PANEL / 'bigrun_preview.py').read_text(encoding='utf-8'))
        waveform = (PANEL / 'device_preview.py').read_text(encoding='utf-8')
        waveform = waveform[waveform.index('def raster_waveform('):]
        write_dat(shell / 'Logic/session_source.text', waveform)
        for path in shell.glob('Logic/monitor_plot_*_callbacks.text'):
            _, source = read_dat(path)
            compile(source, str(path), 'exec')
        callbacks = directory / 'project1/T01_TelemetryPanel/Sources/UdpTelemetryAdapter/udp_callbacks.text'
        write_dat(callbacks, '''def onReceive(dat, rowIndex, message, bytes, peer):
    import builtins, time
    op('/project1/T01_TelemetryPanel/WorkbenchA/Logic/render').module.ingest_monitor(builtins.bytes(bytes), time.monotonic_ns())
''')
        # All other session/mocking code is inert and removed from this candidate.
        for name in ('workflow_source', 'export_source'):
            write_dat(shell / ('Logic/' + name + '.text'), '# Not used by the BigRun read-only frontend.\n')
        for path in directory.rglob('*.parm'):
            if path.name.endswith('_callbacks.parm') or 'Logic' in path.parts:
                continue
            source = path.read_text(encoding='utf-8')
            match = TEXT.search(source)
            if not match:
                continue
            value = match[1]
            if value.startswith('"'):
                # TD's simple quoted text is not JSON-escaped; use literal contents.
                value = value[1:-1]
            replacements = {'呼吸胸带':'呼吸代理', '心电胸带':'心电通道', 'respiBAN BLE':'BigRun Team',
                            'Polar H10':'BigRun Team', '模拟模式':'BigRun 待实测',
                            '呼吸 / 相对幅度':'呼吸代理 / 相对幅度', '心电 / μV':'ECG / ADC',
                            'ECG / μV':'ECG / ADC', 'RR ms':'RR 原始整数', 'RR间期':'原生 RR',
                            'X 实测呼吸':'X 呼吸代理', '呼吸估计 X':'呼吸代理 X',
                            '信号质量':'校准状态', '原始采样':'输出率',
                            '已确认':'待回执', '已收到':'待回执'}
            changed = replacements.get(value)
            if 'Polar H10' in value:
                changed = 'BigRun Team / ECG'
            if 'PLUX' in value or 'respiBAN' in value:
                changed = 'BigRun Team / 呼吸代理'
            if '模拟' in value:
                changed = 'BigRun 待实测'
            if 'MOCK-' in value or '已收到' in value:
                changed = '未接入'
            if re.fullmatch(r'\d+(\.\d+)? Hz', value):
                changed = '输出率待核'
            if changed is not None:
                parameter(path, 'text', '\ufeff' + json.dumps(changed, ensure_ascii=False))
            if path.name == 'manual_mode.parm':
                parameter(path, 'text', '\ufeff"BigRun 待实测"')
                parameter(path, 'w', '152')
                parameter(path, 'x', '1092')
            if re.search(r'^text 0 .*角速度', source, re.MULTILINE):
                parameter(path, 'display', 'off')
        # Remove any saved mock values before the first render; use the same render
        # function for live updates, so all pages share the existing border geometry.
        for page in (shell / 'Design').iterdir():
            if not page.is_dir():
                continue
            for path in page.glob('c_*.parm'):
                raw = path.read_text(encoding='utf-8')
                if TEXT.search(raw):
                    match = TEXT.search(raw)
                    value = match[1].strip('"')
                    if (value.startswith(('MOCK-', '历史 ', 'HR ', '最近数据：', '信号质量 ', '呼吸估计置信度 '))
                            or value in ('已连接', '已确认', '已收到', '可提交准备', '正常结束', '已封存')
                            or re.fullmatch(r'\d+(\.\d+)?( Hz)?', value) or re.fullmatch(r'[0-9a-f]{14}', value)):
                        parameter(path, 'text', '\ufeff"未接入"')
                    elif re.fullmatch(r'\d\d:\d\d', value):
                        parameter(path, 'text', '00:00')
        # No root-level legacy telemetry renderer can feed old data into the UI.
        parameter(directory / 'project1/T01_TelemetryPanel/Runtime/render_execute.parm', 'active', 'off')
        parameter(shell / 'Logic/render.parm', 'active', 'on')
        parameter(shell / 'Design/home.parm', 'display', 'on')
        for page in (shell / 'Design').glob('*.parm'):
            if page.stem != 'home':
                parameter(page, 'display', 'off')
        parameter(directory / 'perform.parm', 'title', '"SRP BigRun Team"')
        before = toe.read_bytes()
        subprocess.run(['D:/TouchDesigner/bin/toecollapse.exe', str(toe)], capture_output=True)
        if not toe.is_file() or toe.read_bytes() == before:
            raise RuntimeError('TOE_COLLAPSE_FAILED')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(toe, target)
        print(target)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=TARGET)
    package(parser.parse_args().out.resolve())
