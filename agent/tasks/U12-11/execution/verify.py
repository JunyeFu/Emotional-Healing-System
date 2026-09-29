"""Verify freeze handoff, source identities and existing software only."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def main():
    commands = [
        ('handoff', ['-m', 'pytest', '-q', '--import-mode=importlib', TASK / 'execution/test_freeze_handoff.py', ROOT / 'agent/tasks/G-03/execution', ROOT / 'agent/tasks/E-03/execution', ROOT / 'agent/tasks/A-03/execution']),
        ('legacy-protocol', [GOV.parent / '99_验证与清单/validate_protocol_authority_v1_1.py']),
        ('governance', [GOV / 'u12_upgrade/validate_u12_governance.py']),
        ('registry', [GOV / '07_validate_task_packages.py']),
        ('dispatch', [GOV / '14_validate_ready_task_packages.py']),
        ('regression', ['-m', 'pytest', '-q']),
    ]
    checks = []
    for name, arguments in commands:
        command = [sys.executable, *map(str, arguments)]
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}, capture_output=True, text=True, encoding='utf-8')
        (TASK / f'evidence/{name}.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': result.returncode, 'log': f'evidence/{name}.txt'})
        print(result.stdout + result.stderr, end='', flush=True)
        if result.returncode:
            (TASK / 'evidence/initial-checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            return result.returncode
    report = {'task_id': 'U12-11', 'checks': checks, 'scope': 'current empty freeze indices and existing software only', 'real_research_freeze': 'NOT_RUN', 'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_SIGNED'}
    (TASK / 'evidence/verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
