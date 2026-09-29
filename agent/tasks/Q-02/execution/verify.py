"""Check current Level B handoff and existing synthetic item behavior only."""
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
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_level_b_handoff.py'),
         str(ROOT / 'agent/modules/tests/step_measurement')],
        [sys.executable, str(ROOT / 'agent/tasks/U12-02/execution/build_evidence.py'), '--check'],
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
        'task_id': 'Q-02', 'checks': checks,
        'scope': 'current handoff, blank templates and existing synthetic item generation only',
        'real_activity': 'NOT_RUN', 'unity': 'NOT_RUN', 'td': 'NOT_RUN',
        'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return checks[-1]['exit_code']


if __name__ == '__main__':
    sys.exit(main())
