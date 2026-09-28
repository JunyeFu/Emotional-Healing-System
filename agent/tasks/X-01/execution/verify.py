"""Check current tools and original X-01 synthetic scope, not real allocation."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]


def main():
    (TASK / 'evidence').mkdir(parents=True, exist_ok=True)
    commands = [
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_current_handoff.py'),
         str(ROOT / '02-技术研发/tests/randomization')],
        [sys.executable, str(TASK / 'execution/verify_x01.py')],
    ]
    checks = []
    for index, command in enumerate(commands, 1):
        run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                             capture_output=True, text=True, encoding='utf-8')
        (TASK / f'evidence/check-{index}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode})
        print(run.stdout + run.stderr, end='')
        if run.returncode:
            break
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'X-01', 'checks': checks, 'scope': 'synthetic software, original artifacts and migrated tool reproduction only',
        'real_activity': 'NOT_RUN', 'formal_list': 'NOT_GENERATED', 'unity': 'NOT_RUN', 'td': 'NOT_RUN',
        'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_RUN'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return checks[-1]['exit_code']


if __name__ == '__main__':
    sys.exit(main())
