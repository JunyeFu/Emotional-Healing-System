"""Verify original scope, actual statistical fixes, and migrated consumers."""
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
        ('contract', [TASK / 'execution/validate.py']),
        ('handoff', ['-m', 'pytest', '-q', TASK / 'execution/test_contract.py',
                     TASK / 'execution/test_statistics_handoff.py',
                     ROOT / 'agent/tasks/A-02/execution/test_a02_contract.py',
                     ROOT / 'agent/tasks/A-05/execution/test_analysis_handoff.py',
                     ROOT / 'agent/tasks/A-04/execution/test_extension_analysis.py',
                     ROOT / 'agent/tasks/G-03/execution/test_freeze_handoff.py',
                     ROOT / 'agent/tasks/A-03/execution/test_a03_current.py',
                     ROOT / '02-技术研发/tests/a03_spec']),
        ('identities', [TASK / 'execution/build_evidence.py', '--check']),
        ('measurement', [ROOT / 'agent/tasks/F-02/execution/build_current_measurement.py', '--check']),
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
    report = {'task_id': 'U12-04', 'checks': checks, 'scope': 'candidate SAP and corrected synthetic grid; actual relocation',
              'real_data_analysis': 'NOT_RUN', 'formal_mi': 'NOT_DELIVERED', 'formal_joint_power': 'NOT_DELIVERED',
              'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_SIGNED',
              'unity': 'NOT_RUN', 'td': 'NOT_RUN'}
    (TASK / 'evidence/verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
