"""Verify available storage consumers without claiming an offline pipeline."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'


def main():
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
    commands = [
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_a01_contract.py'),
         str(ROOT / '02-技术研发/tests/session_store')],
        [sys.executable, str(PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py')],
    ]
    evidence = TASK / 'evidence'
    evidence.mkdir(exist_ok=True)
    checks = []
    for index, command in enumerate(commands, 1):
        run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                             text=True, encoding='utf-8')
        (evidence / f'check-{index}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode})
        print(run.stdout + run.stderr, end='')
    (evidence / 'verification.json').write_text(json.dumps({
        'task_id': 'A-01', 'checks': checks,
        'scope': 'existing P-02 interfaces, synthetic input identities, read-only core replay and archival',
        'offline_pipeline': 'NOT_DELIVERED', 'real_device_chain': 'NOT_RUN',
        'formal_data_access': 'NOT_RUN', 'human_acceptance': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(check['exit_code'] for check in checks))


if __name__ == '__main__':
    sys.exit(main())
