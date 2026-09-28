import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]


def main():
    (TASK / 'evidence').mkdir(exist_ok=True)
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
    commands = [
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_u03_contract.py'),
         str(ROOT / 'agent/tasks/V-03/execution/test_current.py'),
         str(ROOT / '02-技术研发/tests/session_core')],
        [sys.executable, str(ROOT / 'agent/tasks/V-03/execution/validate_current.py')],
    ]
    checks = []
    for index, command in enumerate(commands, 1):
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        (TASK / f'evidence/check-{index}.txt').write_text(output, encoding='utf-8')
        print(output, end='')
        checks.append({'command': command, 'exit_code': result.returncode})
        if result.returncode:
            break
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'U-03', 'checks': checks,
        'scope': 'current design handoff, historical selection and Python core only',
        'unity_slice_acceptance': 'NOT_RUN', 'human_formative_review': 'NOT_RUN',
        'template_freeze': 'NOT_COMPLETED',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
