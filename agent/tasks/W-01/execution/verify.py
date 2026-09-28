"""Verify the preserved closest-work candidate and current paper handoff."""
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
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_w01_current.py')],
        [sys.executable, str(TASK / 'execution/validate_candidate.py')],
        [sys.executable, str(PLAN / '24_团队任务与项目治理/u12_upgrade/validate_u12_governance.py')],
    ]
    checks = []
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
    evidence = TASK / 'evidence'
    for index, command in enumerate(commands, 1):
        run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
        (evidence / f'check-{index}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode})
        print(run.stdout + run.stderr, end='')
    (evidence / 'verification.json').write_text(json.dumps({
        'task_id': 'W-01', 'checks': checks,
        'scope': 'historical candidate structure, actual path migration, current authority and reporting route',
        'new_literature_search': 'NOT_RUN', 'full_text_review': 'NOT_RUN',
        'human_second_review': 'NOT_RUN', 'observed_study_results': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(check['exit_code'] for check in checks))


if __name__ == '__main__':
    sys.exit(main())
