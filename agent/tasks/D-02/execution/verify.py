import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]


def main():
    (TASK / 'evidence').mkdir(exist_ok=True)
    command = [sys.executable, '-m', 'pytest', '-q',
               str(REPO / 'agent/modules/01-数据采集/tests'),
               str(REPO / 'agent/tasks/D-01/execution/test_current.py'),
               str(TASK / 'execution/test_d02_contract.py')]
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding='utf-8')
    output = result.stdout + result.stderr
    (TASK / 'evidence/check-1.txt').write_text(output, encoding='utf-8')
    print(output, end='')
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'D-02', 'checks': [{'command': command, 'exit_code': result.returncode}],
        'scope': 'software normalization, synthetic native batch and P-02 consumer checks only',
        'real_device_acceptance': 'NOT_RUN'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
