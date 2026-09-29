"""Check I-01 handoff and existing host contracts without claiming LIVE_E2E."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]


def main():
    (TASK / 'evidence').mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_integration_handoff.py'),
               str(ROOT / 'agent/modules/tests/session_core'), str(ROOT / 'agent/modules/tests/session_store')]
    run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                         capture_output=True, text=True, encoding='utf-8')
    (TASK / 'evidence/check-1.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'I-01', 'checks': [{'command': command, 'exit_code': run.returncode}],
        'scope': 'handoff and synthetic Python host transport, recording and replay tests only',
        'real_devices': 'NOT_RUN', 'unity': 'NOT_RUN', 'td': 'NOT_RUN',
        'external_measurement': 'NOT_RUN', 'live_e2e': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(run.stdout + run.stderr, end='')
    return run.returncode


if __name__ == '__main__':
    sys.exit(main())
