"""Create a readable legacy candidate without changing the signed/current TOE."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import time

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
MODULE = ROOT / 'agent/modules/03-TouchDesigner/t01_telemetry_panel'
RUNTIME = TASK / 'evidence/runtime'
TD_BIN = Path('D:/TouchDesigner/bin')


def main():
    source = MODULE / 'T01_TelemetryPanel.toe'
    target = RUNTIME / 'T01_ReadableBaseline.candidate.toe'
    if target.exists():
        raise FileExistsError('Inspect the existing candidate before replacing it')
    scratch = ROOT / '.artifacts-local/task-normalization/T-01/layout' / time.strftime('%Y%m%d-%H%M%S')
    scratch.mkdir(parents=True)
    toe = scratch / 'candidate.toe'
    shutil.copyfile(source, toe)
    subprocess.run([str(TD_BIN / 'toeexpand.exe'), str(toe)], capture_output=True)
    folder = Path(str(toe) + '.dir') / 'project1/T01_TelemetryPanel/ConsoleShell'
    patches = {
        'panel_text': {'fontsizexunit': 'pixels', 'fontsizeyunit': 'pixels',
                       'fontsizex': '18', 'fontsizey': '18', 'fontautosize': 'nofit',
                       'positionunit': 'pixels', 'position1': '20', 'position2': '-20',
                       'linespacingunit': 'pixels', 'linespacing': '6'},
        'resp_sqi_bar': {'centery': '-0.36', 'centerx': '-0.21', 'sizey': '0.025'},
        'ecg_sqi_bar': {'centery': '-0.36', 'centerx': '0.21', 'sizey': '0.025'},
        'stream_badge': {'centerx': '0.46', 'centery': '0.46', 'sizey': '0.035', 'sizex': '0.035'},
    }
    for name, values in patches.items():
        path = folder / (name + '.parm')
        lines = path.read_text(encoding='utf-8').splitlines()
        lines = [line for line in lines if line.split(' ', 1)[0] not in values]
        if lines[-1] != '?':
            raise ValueError('UNEXPECTED_PARAMETER_FORMAT')
        lines[-1:-1] = [f'{key} 0 {value}' for key, value in values.items()]
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    subprocess.run([str(TD_BIN / 'toecollapse.exe'), str(toe)], capture_output=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(toe, target)
    report = {'source_sha256': sha256(source.read_bytes()).hexdigest().upper(),
              'candidate_sha256': sha256(target.read_bytes()).hexdigest().upper(),
              'scope': 'Legacy Text TOP readability only, not A-theme implementation', 'patches': patches,
              'official_parameter_reference': 'https://derivative.ca/UserGuide/Text_TOP'}
    (RUNTIME / 'layout_repair.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('T01_READABLE_BASELINE_CANDIDATE_CREATED')


if __name__ == '__main__':
    main()
