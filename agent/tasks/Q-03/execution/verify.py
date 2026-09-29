"""Verify Level C planning handoff without claiming real pretest evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'


def main():
    (TASK / 'evidence').mkdir(parents=True, exist_ok=True)
    commands = [
        [sys.executable, str(TASK / 'execution/build_preview.py')],
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_level_c_handoff.py'),
         str(ROOT / '02-技术研发/tests/randomization'), str(ROOT / '02-技术研发/tests/step_measurement')],
        [sys.executable, str(PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py')],
    ]
    checks = []
    for index, command in enumerate(commands, 1):
        run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                             capture_output=True, text=True, encoding='utf-8')
        (TASK / f'evidence/check-{index}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        checks.append({'command': command, 'exit_code': run.returncode})
        print(run.stdout + run.stderr, end='')
        if run.returncode:
            break
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'Q-03', 'checks': checks, 'scope': 'design cells, current handoff and existing synthetic software behavior only',
        'real_activity': 'NOT_RUN', 'real_annotations': 'NOT_RUN', 'new_configuration_freeze': 'NOT_RUN',
        'unity': 'NOT_RUN', 'td': 'NOT_RUN', 'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_RUN'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return checks[-1]['exit_code']


if __name__ == '__main__':
    sys.exit(main())
