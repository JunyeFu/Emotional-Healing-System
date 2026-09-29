"""Read-only admission checks; never provision credentials or conduct activities."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
G02 = ROOT / '02-技术研发/07-数据治理'


def main():
    (TASK / 'evidence').mkdir(parents=True, exist_ok=True)
    checks = []

    def run(label, arguments, allowed=(0,)):
        command = [sys.executable, *map(str, arguments)]
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'},
                                capture_output=True, text=True, encoding='utf-8')
        (TASK / 'evidence' / f'{label}.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        check = {'command': command, 'exit_code': result.returncode, 'log': f'evidence/{label}.txt'}
        if result.returncode == 2:
            check['disposition'] = 'Read-only local environment remains blocked; not formal-machine acceptance.'
        checks.append(check)
        print(result.stdout + result.stderr, end='')
        if result.returncode not in allowed:
            raise RuntimeError(f'{label} failed')

    run('check-1', ['-m', 'pytest', '-q', TASK / 'execution/test_admission_handoff.py', G02 / 'tests/test_environment.py'])
    run('governance', [GOV / '15_validate_audit_upgrade.py'])
    run('formal-environment', [G02 / 'g02.py', 'check-environment', '--repo-root', ROOT,
                               '--output', TASK / 'evidence/local-environment.json'], (0, 2))
    report = {'task_id': 'G-05', 'checks': checks, 'scope': 'current sources, existing negative gates and read-only local environment',
              'real_institution': 'NOT_VERIFIED', 'formal_machine': 'NOT_VERIFIED', 'u8_real': 'NOT_RUN',
              'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_RUN'}
    (TASK / 'evidence/verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
