"""Check actual SPEC behavior, current scope and preserved historical inputs."""
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
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_a03_current.py'), str(ROOT / '02-技术研发/tests/a03_spec')],
        [sys.executable, str(PLAN / '24_团队任务与项目治理/u12_upgrade/U12-04_panas_sap/validate.py')],
        [sys.executable, str(PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py')],
    ]
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
    checks = []
    evidence = TASK / 'evidence'
    for index, command in enumerate(commands, 1):
        run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
        (evidence / f'check-{index}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode})
        print(run.stdout + run.stderr, end='')
    (evidence / 'verification.json').write_text(json.dumps({
        'task_id': 'A-03', 'checks': checks,
        'scope': 'actual SPEC regression, non-overwriting CLI, current scope and preserved sources',
        'real_scoring_adapter': 'NOT_DELIVERED', 'blind_calibration': 'NOT_DELIVERED',
        'formal_freeze': 'NOT_RUN', 'new_human_acceptance': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(check['exit_code'] for check in checks))


if __name__ == '__main__':
    sys.exit(main())
