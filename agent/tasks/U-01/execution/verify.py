"""Run Unity control tests and regenerate current evidence, not signed originals."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
OUTPUT = PACKAGE / 'evidence/runtime'
UNITY = Path('D:/UnityEngine/6000.4.9f1/Editor/Unity.exe')
PROJECT = ROOT / 'agent/modules/04-Unity视觉/SRP-Weather-Visual'


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def run(label, command):
        if '-logFile' in command:
            log = Path(command[command.index('-logFile') + 1])
            result = subprocess.run(command, cwd=ROOT, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.STDOUT)
        else:
            log = OUTPUT / f'{label}.log'
            with log.open('w', encoding='utf-8') as stream:
                result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        checks.append({'name': label, 'exit_code': result.returncode,
                       'log': log.relative_to(ROOT).as_posix()})
        (PACKAGE / 'evidence/verification.json').write_text(json.dumps(
            {'task_id': 'U-01', 'scope': 'Unity control probe; synthetic golden, not formal build or live device chain',
             'checks': checks}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if result.returncode:
            raise SystemExit(result.returncode)

    for platform in ('editmode', 'playmode'):
        run(platform, [str(UNITY), '-batchmode', '-nographics', '-projectPath', str(PROJECT),
                       '-runTests', '-testPlatform', platform, '-testFilter', 'SRP.U01.Tests',
                       '-testResults', str(OUTPUT / f'{platform}-results.xml'),
                       '-logFile', str(OUTPUT / f'{platform}-unity.log')])
    run('generate', [str(UNITY), '-batchmode', '-nographics', '-quit', '-projectPath', str(PROJECT),
                     '-executeMethod', 'SRP.U01.Editor.U01EvidenceBuilder.Generate',
                     '-logFile', str(OUTPUT / 'generate-unity.log')])
    run('verify-current', [sys.executable, str(PACKAGE / 'execution/verify_u01.py')])
    run('verify-historical', [sys.executable, str(PACKAGE / 'execution/verify_u01.py'),
                             '--evidence-dir', str(ROOT / 'agent/validation/evidence/U-01')])
    names = ('state-mirror-trace.json', 'ack-render-receipt-sequence.json', 'network-fault-log.json')
    comparison = {name: json.loads((OUTPUT / name).read_text(encoding='utf-8-sig')) ==
                  json.loads((ROOT / 'agent/validation/evidence/U-01' / name).read_text(encoding='utf-8-sig'))
                  for name in names}
    (OUTPUT / 'historical-comparison.json').write_text(
        json.dumps(comparison, indent=2) + '\n', encoding='utf-8')
    if not all(comparison.values()):
        raise SystemExit('U01_HISTORICAL_SEMANTICS_DRIFT')
    print('PASS U-01 EditMode 14 PlayMode 3; current and historical evidence agree')


if __name__ == '__main__':
    main()
