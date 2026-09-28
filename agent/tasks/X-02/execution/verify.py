"""Verify policy handoff and original allocation behavior, not policy training."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'


def main():
    commands = [
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_policy_handoff.py'), str(ROOT / '02-技术研发/tests/randomization')],
        [sys.executable, str(PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py')],
    ]
    checks = []
    for number, command in enumerate(commands, 1):
        run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, capture_output=True, text=True, encoding='utf-8')
        (TASK / f'evidence/check-{number}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode})
        print(run.stdout + run.stderr, end='')
        if run.returncode:
            break
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'X-02', 'checks': checks,
        'scope': 'current handoff, archive bytes, route and existing synthetic allocation/protocol only',
        'real_training': 'NOT_RUN', 'ope': 'NOT_IMPLEMENTED', 'ess': 'NOT_IMPLEMENTED',
        'policy_freeze': 'NOT_RUN', 'unity': 'NOT_RUN', 'td': 'NOT_RUN',
        'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_RUN'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return checks[-1]['exit_code']


if __name__ == '__main__':
    sys.exit(main())
