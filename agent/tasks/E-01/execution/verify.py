"""Verify normalization and synthetic scoring only; no recruitment or activity."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def main():
    evidence = TASK / 'evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    commands = [
        ('check-1', ['-m', 'pytest', '-q', TASK / 'execution/test_execution_handoff.py', ROOT / 'agent/tasks/Q-01/execution']),
        ('check-2', [ROOT / 'agent/tasks/Q-01/execution/validate_q01_materials.py']),
        ('consumer', [ROOT / 'agent/tasks/G-01/execution/verify.py']),
        ('registry', [GOV / '07_validate_task_packages.py']),
        ('dispatch', [GOV / '14_validate_ready_task_packages.py']),
        ('regression', ['-m', 'pytest', '-q']),
    ]
    checks = []
    for name, arguments in commands:
        command = [sys.executable, *map(str, arguments)]
        run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}, capture_output=True, text=True, encoding='utf-8')
        (evidence / f'{name}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode, 'log': f'evidence/{name}.txt'})
        print(run.stdout + run.stderr, end='')
        if run.returncode:
            (evidence / 'initial-checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            return run.returncode
    report = {'task_id': 'E-01', 'checks': checks, 'scope': 'source normalization and synthetic scoring, not real Level A',
              'real_activity': 'NOT_RUN', 'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_SIGNED'}
    (evidence / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
