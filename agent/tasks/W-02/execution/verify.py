"""Check manuscript handoff and actual archive, not empirical conclusions."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'

def main():
    commands = [
        ('handoff', ['-m', 'pytest', '-q', TASK / 'execution/test_manuscript_handoff.py',
                     ROOT / 'agent/tasks/W-01/execution/test_w01_current.py',
                     ROOT / 'agent/tasks/A-04/execution/test_extension_analysis.py',
                     ROOT / 'agent/tasks/A-06/execution/test_scope_handoff.py']),
        ('literature-candidate', [ROOT / 'agent/tasks/W-01/execution/validate_candidate.py']),
        ('legacy-protocol', [PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py']),
        ('governance', [GOV / 'u12_upgrade/validate_u12_governance.py']),
        ('registry', [GOV / '07_validate_task_packages.py']),
        ('dispatch', [GOV / '14_validate_ready_task_packages.py']),
        ('regression', ['-m', 'pytest', '-q']),
    ]
    checks = []
    for name, arguments in commands:
        command = [sys.executable, *map(str, arguments)]
        run = subprocess.run(command, cwd=ROOT,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'},
            capture_output=True, text=True, encoding='utf-8')
        (TASK / f'evidence/{name}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode, 'log': f'evidence/{name}.txt'})
        print(run.stdout + run.stderr, end='', flush=True)
        if run.returncode:
            (TASK / 'evidence/initial-checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            return run.returncode
    report = {'task_id': 'W-02', 'checks': checks, 'scope': 'current writing contract and preserved historical sources',
              'real_manuscript': 'NOT_DELIVERED', 'observed_results': 'NOT_RUN',
              'full_text_review': 'NOT_RUN', 'similarity_check': 'NOT_RUN',
              'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_SIGNED',
              'unity': 'NOT_RUN', 'td': 'NOT_RUN', 'submission': 'NOT_RUN'}
    (TASK / 'evidence/verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0

if __name__ == '__main__':
    sys.exit(main())
