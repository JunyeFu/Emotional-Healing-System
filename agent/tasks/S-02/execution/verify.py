import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]


def main():
    command = [sys.executable, '-m', 'pytest', '-q',
               str(REPO / 'agent/modules/02-信号处理/tests'),
               str(REPO / 'agent/modules/05-通信协议/tests/contract'),
               str(TASK / 'execution/test_s02_contract.py')]
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding='utf-8')
    output = result.stdout + result.stderr
    (TASK / 'evidence/check-1.txt').write_text(output, encoding='utf-8')
    print(output, end='')
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'S-02', 'checks': [{'command': command, 'exit_code': result.returncode}],
        'scope': 'legacy signal regression and signed protocol plus current handoff software checks only',
        'real_device_acceptance': 'NOT_RUN'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
