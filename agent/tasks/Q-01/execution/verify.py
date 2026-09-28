"""Run Q-01 material, scoring and migration checks without real-person activity."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]


def main():
    evidence = TASK / 'evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    commands = [
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution')],
        [sys.executable, str(TASK / 'execution/validate_q01_materials.py')],
    ]
    checks = []
    for index, command in enumerate(commands, 1):
        run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                             capture_output=True, text=True, encoding='utf-8')
        (evidence / f'check-{index}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        print(run.stdout + run.stderr, end='')
        checks.append({'command': command, 'exit_code': run.returncode})
    (evidence / 'verification.json').write_text(json.dumps({
        'task_id': 'Q-01', 'checks': checks, 'scope': 'synthetic material/scoring, current handoff and migration',
        'real_level_a': 'NOT_RUN', 'real_role_verification': 'NOT_RUN',
        'final_render_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(check['exit_code'] for check in checks))


if __name__ == '__main__':
    sys.exit(main())
