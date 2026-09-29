"""Verify actual statistical specification and synthetic-tool boundaries."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
SAP = ROOT / 'agent/tasks/U12-04/execution'


def main():
    commands = [
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_a02_contract.py'), str(SAP / 'test_contract.py')],
        [sys.executable, str(SAP / 'validate.py')],
        [sys.executable, str(PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py')],
    ]
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
    evidence = TASK / 'evidence'
    checks = []
    for index, command in enumerate(commands, 1):
        run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
        (evidence / f'check-{index}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode})
        print(run.stdout + run.stderr, end='')
    (evidence / 'verification.json').write_text(json.dumps({
        'task_id': 'A-02', 'checks': checks,
        'scope': 'current contracts, actual U12-04 synthetic missingness scenario and archival',
        'A02_analysis_pipeline': 'NOT_DELIVERED', 'real_data_analysis': 'NOT_RUN',
        'formal_freeze': 'NOT_RUN', 'human_acceptance': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(check['exit_code'] for check in checks))


if __name__ == '__main__':
    sys.exit(main())
