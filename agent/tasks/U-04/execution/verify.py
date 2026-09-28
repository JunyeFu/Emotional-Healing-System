import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
UNITY = ROOT / '02-技术研发/04-Unity视觉/SRP-Weather-Visual'


def main():
    evidence = TASK / 'evidence'
    evidence.mkdir(exist_ok=True)
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
    checks = []
    commands = [
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_u04_contract.py'),
         str(ROOT / 'agent/tasks/V-02/execution/test_current.py')],
        [sys.executable, str(ROOT / 'agent/tasks/V-03/execution/validate_current.py')],
        ['D:/UnityEngine/6000.4.9f1/Editor/Unity.exe', '-batchmode', '-nographics',
         '-projectPath', str(UNITY), '-runTests', '-testPlatform', 'editmode',
         '-testFilter', 'SRP.V03.Tests;SRP.U01.Tests;SRP.F03.Tests',
         '-testResults', str(evidence / 'editmode-results.xml'),
         '-logFile', str(evidence / 'editmode-unity.log')],
    ]
    for index, command in enumerate(commands, 1):
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        (evidence / f'check-{index}.txt').write_text(output, encoding='utf-8')
        print(output, end='', flush=True)
        checks.append({'command': command, 'exit_code': result.returncode})
        if result.returncode:
            break
    passed = None
    if len(checks) == 3 and not result.returncode:
        run = ET.parse(evidence / 'editmode-results.xml').getroot()
        cases = list(run.iter('test-case'))
        if run.get('result') != 'Passed' or not cases or any(c.get('result') != 'Passed' for c in cases):
            raise ValueError('UNITY_NORMALIZATION_REGRESSION_FAILED')
        passed = len(cases)
        print(f'PASS shared Unity EditMode={passed}; no U-04 weather acceptance', flush=True)
    (evidence / 'verification.json').write_text(json.dumps({
        'task_id': 'U-04', 'checks': checks,
        'scope': 'design, legacy migration and shared Unity assembly regression only',
        'shared_editmode_passed': passed,
        'weather_adapter_acceptance': 'NOT_RUN', 'human_review': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
