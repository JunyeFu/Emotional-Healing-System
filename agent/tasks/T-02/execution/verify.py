"""Recheck current producers and the unimplemented TD request boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]


def main():
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
    command = [sys.executable, '-m', 'pytest', '-q',
               str(TASK / 'execution/test_t02_contract.py'),
               str(ROOT / '02-技术研发/tests/session_core'),
               str(ROOT / '02-技术研发/tests/session_store'),
               str(ROOT / '02-技术研发/03-TouchDesigner/t01_telemetry_panel/tests'),
               str(ROOT / '02-技术研发/03-TouchDesigner/f04_readonly_console/tests')]
    run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                         text=True, encoding='utf-8')
    evidence = TASK / 'evidence'
    evidence.mkdir(exist_ok=True)
    (evidence / 'check-1.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
    (evidence / 'verification.json').write_text(json.dumps({
        'task_id': 'T-02', 'checks': [{'command': command, 'exit_code': run.returncode}],
        'scope': 'existing producer regression, live loopback TD rejection, archival and handoff checks',
        'td_requests': 'NOT_IMPLEMENTED', 'td_operator_video': 'NOT_RUN',
        'unity_runtime': 'NOT_RUN', 'real_device_chain': 'NOT_RUN',
        'human_acceptance': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(run.stdout + run.stderr, end='')
    return run.returncode


if __name__ == '__main__':
    sys.exit(main())
