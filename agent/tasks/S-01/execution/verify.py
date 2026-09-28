import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]


def main():
    (TASK / 'evidence').mkdir(exist_ok=True)
    command = [sys.executable, '-m', 'pytest', '-q',
               str(REPO / '02-技术研发/01-数据采集/tests'),
               str(REPO / '02-技术研发/05-通信协议/tests/contract'),
               str(TASK / 'execution/test_s01_contract.py')]
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding='utf-8')
    output = result.stdout + result.stderr
    (TASK / 'evidence/check-1.txt').write_text(output, encoding='utf-8')
    print(output, end='')
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'S-01', 'checks': [{'command': command, 'exit_code': result.returncode}],
        'scope': 'shared acquisition and protocol software tests plus current handoff checks only',
        'real_device_acceptance': 'NOT_RUN'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
