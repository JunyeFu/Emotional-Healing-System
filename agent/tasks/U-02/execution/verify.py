"""Recheck signed evidence and the current Unity layer implementation."""
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
OUTPUT = PACKAGE / 'evidence/runtime'
UNITY = 'D:/UnityEngine/6000.4.9f1/Editor/Unity.exe'
PROJECT = ROOT / '02-技术研发/04-Unity视觉/SRP-Weather-Visual'
PARAMETERS = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/20_产品与场景设计/V-03_四层视听映射与资产来源基线/V-03_参数边界与锁定规则_v1.0.json'


def check_xml(path, expected):
    run = ET.parse(path).getroot()
    cases = list(run.iter('test-case'))
    if run.get('result') != 'Passed' or len(cases) != expected or any(c.get('result') != 'Passed' for c in cases):
        raise ValueError('U02_UNITY_TESTS_FAILED')
    return Counter(c.get('classname') for c in cases)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def run(name, command, unity=False):
        log = OUTPUT / f'{name}.log'
        if unity:
            result = subprocess.run(command + ['-logFile', str(log)], cwd=ROOT,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        else:
            with log.open('w', encoding='utf-8') as stream:
                result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        checks.append({'name': name, 'exit_code': result.returncode, 'log': log.relative_to(ROOT).as_posix()})
        (PACKAGE / 'evidence/verification.json').write_text(json.dumps(
            {'task_id': 'U-02', 'checks': checks}, indent=2) + '\n', encoding='utf-8')
        if result.returncode:
            raise SystemExit(result.returncode)

    run('historical-import', [sys.executable, str(PACKAGE / 'execution/import_historical.py')])
    archive = PACKAGE / 'archive/evidence-v1'
    check_xml(archive / '01_editmode_results.xml', 98)
    parameter_hash = hashlib.sha256(PARAMETERS.read_text(encoding='utf-8-sig').encode('utf-8')).hexdigest()
    if parameter_hash != '8b7d2335cadbfdbe30e0a4364b644610cdc1bf13eb3da5651740635e4e90d937':
        raise ValueError('U02_PARAMETER_INPUT_DRIFT')
    frames = sorted((archive / '04_degradation_demo/frames').glob('frame_*.png'))
    if [p.name for p in frames] != [f'frame_{n:04d}.png' for n in range(120)]:
        raise ValueError('U02_DEMO_FRAME_SET')
    if any(not p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for p in frames):
        raise ValueError('U02_DEMO_FRAME_BYTES')
    video = archive / '04_degradation_demo/V03_degradation_demo.mp4'
    if video.read_bytes()[4:8] != b'ftyp':
        raise ValueError('U02_DEMO_VIDEO_BYTES')
    run('editmode', [UNITY, '-batchmode', '-nographics', '-projectPath', str(PROJECT),
                     '-runTests', '-testPlatform', 'editmode',
                     '-testFilter', 'SRP.V03.Tests;SRP.U01.Tests;SRP.F03.Tests',
                     '-testResults', str(OUTPUT / 'editmode-results.xml')], unity=True)
    suites = check_xml(OUTPUT / 'editmode-results.xml', 105)
    run('playmode', [UNITY, '-batchmode', '-nographics', '-projectPath', str(PROJECT),
                     '-runTests', '-testPlatform', 'playmode', '-testFilter', 'SRP.U01.Tests',
                     '-testResults', str(OUTPUT / 'playmode-results.xml')], unity=True)
    check_xml(OUTPUT / 'playmode-results.xml', 3)
    (OUTPUT / 'results.json').write_text(json.dumps({
        'editmode_passed': 105, 'playmode_passed': 3, 'suites': dict(suites),
        'historical_editmode_passed': 98, 'historical_frames': 120,
        'parameter_normalized_text_sha256': parameter_hash,
        'scope': 'Synthetic layers and Unity control probe; no formal build, final weather scene video or live devices'
    }, indent=2) + '\n', encoding='utf-8')
    print('PASS U-02 current EditMode 105 PlayMode 3; historical 98 and 127 files verified')


if __name__ == '__main__':
    main()
