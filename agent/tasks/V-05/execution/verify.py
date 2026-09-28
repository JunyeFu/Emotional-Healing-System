import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]


def main():
    checks = []
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
    commands = [
        [sys.executable, str(TASK / 'execution/check_core_matrix.py')],
        [sys.executable, '-m', 'pytest', '-q', str(ROOT / '02-技术研发/tests/session_core'),
         str(TASK / 'execution/test_v05_contract.py')],
    ]
    for index, command in enumerate(commands, 1):
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
        text = result.stdout + result.stderr
        (TASK / f'evidence/check-{index}.txt').write_text(text, encoding='utf-8')
        print(text, end='')
        checks.append({'command': command, 'exit_code': result.returncode})
        if result.returncode:
            break
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'V-05', 'checks': checks, 'scope': 'Python v2.2 core matrix and current design checks only',
        'unity_graybox_acceptance': 'NOT_RUN', 'human_formative_review': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
