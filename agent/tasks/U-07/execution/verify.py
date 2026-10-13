import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]


def main():
    evidence = TASK / 'evidence'
    evidence.mkdir(exist_ok=True)
    commands = [
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_u07_contract.py'),
         str(ROOT / 'agent/tasks/V-02/execution/test_current.py')],
        [sys.executable, str(ROOT / 'agent/tasks/V-03/execution/validate_current.py')],
        [sys.executable, str(ROOT / 'agent/tasks/R-01/execution/validate_candidate.py')],
    ]
    checks = []
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
    for index, command in enumerate(commands, 1):
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        (evidence / f'check-{index}.txt').write_text(output, encoding='utf-8')
        print(output, end='', flush=True)
        checks.append({'command': command, 'exit_code': result.returncode})
        if result.returncode:
            break
    (evidence / 'verification.json').write_text(json.dumps({
        'task_id': 'U-07', 'checks': checks,
        'scope': 'current abstract design, source alignment, original specification migration and consumer boundaries',
        'unity_code_changed': False, 'unity_render_acceptance': 'NOT_RUN',
        'confound_measurement': 'NOT_RUN', 'human_review': 'NOT_RUN',
        'formal_collection': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
