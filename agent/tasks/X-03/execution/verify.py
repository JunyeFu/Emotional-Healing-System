"""Verify existing fixed interfaces and runtime handoff, not dynamic deployment."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]


def main():
    command = [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_runtime_handoff.py'),
               str(ROOT / '02-技术研发/tests/session_core/test_manifest.py'),
               str(ROOT / '02-技术研发/tests/session_store/test_recording_replay.py')]
    run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, capture_output=True, text=True, encoding='utf-8')
    (TASK / 'evidence/check-1.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'X-03', 'checks': [{'command': command, 'exit_code': run.returncode}],
        'scope': 'existing fixed core and replay restrictions, current runtime handoff only',
        'dynamic_policy': 'NOT_IMPLEMENTED', 'readonly_model': 'NOT_VERIFIED',
        'real_stage3': 'NOT_RUN', 'unity_same_build': 'NOT_VERIFIED', 'td': 'NOT_RUN',
        'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_RUN'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(run.stdout + run.stderr, end='')
    return run.returncode


if __name__ == '__main__':
    sys.exit(main())
