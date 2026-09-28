import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]


def main():
    (TASK / 'evidence').mkdir(exist_ok=True)
    commands = [[sys.executable, '-m', 'pytest', '-q',
                 str(REPO / '02-技术研发/01-数据采集/tests'),
                 str(TASK / 'execution/test_current.py')]]
    checks = []
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        (TASK / f'evidence/check-{index + 1}.txt').write_text(output, encoding='utf-8')
        print(output, end='')
        checks.append({'command': command, 'exit_code': result.returncode})
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'D-01', 'checks': checks,
        'scope': 'normalization and legacy shared software tests only; no BLE scan or real hardware acceptance',
        'real_device_acceptance': 'NOT_RUN'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(c['exit_code'] != 0 for c in checks))


if __name__ == '__main__':
    sys.exit(main())
