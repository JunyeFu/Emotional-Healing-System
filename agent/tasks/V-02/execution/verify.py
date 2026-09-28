"""Run scoped historical and current scene handoff checks."""
import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]


def main():
    commands = [
        [sys.executable, str(TASK / 'execution/validate_historical.py')],
        [sys.executable, str(TASK / 'execution/validate_current.py')],
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_current.py')],
        [sys.executable, str(REPO / 'agent/tasks/V-01/execution/validate_current.py')],
    ]
    checks = []
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        (TASK / f'evidence/check-{index + 1}.txt').write_text(output, encoding='utf-8')
        print(output, end='')
        checks.append({'command': command, 'exit_code': result.returncode})
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'V-02', 'checks': checks,
        'scope': 'historical scene confirmation and current handoff; no rendered runtime or research result'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(c['exit_code'] != 0 for c in checks))


if __name__ == '__main__':
    sys.exit(main())
