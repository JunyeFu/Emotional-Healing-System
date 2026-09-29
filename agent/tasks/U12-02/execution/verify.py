"""Verify candidate materials and migrated consumers, not real measurement validity."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
PLAN = GOV.parent

def main():
    commands = [
        ('handoff', ['-m', 'pytest', '-q', TASK / 'execution/test_measurement_handoff.py', ROOT / '02-技术研发/tests/step_measurement', ROOT / 'agent/tasks/Q-02/execution/test_level_b_handoff.py', ROOT / 'agent/tasks/E-02/execution/test_execution_handoff.py']),
        ('materials', [TASK / 'execution/build_evidence.py', '--check']),
        ('legacy-protocol', [PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py']),
        ('governance', [GOV / 'u12_upgrade/validate_u12_governance.py']),
        ('registry', [GOV / '07_validate_task_packages.py']),
        ('dispatch', [GOV / '14_validate_ready_task_packages.py']),
        ('regression', ['-m', 'pytest', '-q']),
    ]
    checks = []
    for name, args in commands:
        command = [sys.executable, *map(str, args)]
        run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}, capture_output=True, text=True, encoding='utf-8')
        (TASK / f'evidence/{name}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode, 'log': f'evidence/{name}.txt'})
        print(run.stdout + run.stderr, end='', flush=True)
        if run.returncode:
            (TASK / 'evidence/initial-checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            return run.returncode
    report = {'task_id': 'U12-02', 'checks': checks, 'scope': 'synthetic measurement candidate and actual migration only', 'real_annotation': 'NOT_RUN', 'real_render_equivalence': 'NOT_RUN', 'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_SIGNED', 'unity': 'NOT_RUN', 'td': 'NOT_RUN'}
    (TASK / 'evidence/verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0

if __name__ == '__main__':
    sys.exit(main())
