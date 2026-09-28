import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]


def main():
    (TASK / 'evidence').mkdir(exist_ok=True)
    checks = []
    commands = [
        [sys.executable, str(TASK / 'execution/validate_preparation.py')],
        [sys.executable, str(TASK / 'execution/validate_historical.py')],
        [sys.executable, str(TASK / 'execution/validate_current.py')],
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_asset_registry.py'), str(TASK / 'execution/test_current.py')],
        [sys.executable, str(REPO / 'agent/tasks/V-02/execution/validate_current.py')],
    ]
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        (TASK / f'evidence/check-{index + 1}.txt').write_text(output, encoding='utf-8')
        print(output, end='')
        checks.append({'command': command, 'exit_code': result.returncode})
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'V-03', 'checks': checks,
        'scope': 'historical and current design, asset dependency consistency; no runtime visual or license clearance'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(c['exit_code'] != 0 for c in checks))


if __name__ == '__main__':
    sys.exit(main())
