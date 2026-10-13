import json
from pathlib import Path
import subprocess
import sys

from verify_historical import CHECKS, SOURCE, TASK, REPO, sha256


def main():
    before = {p.name: sha256(p) for p in SOURCE.glob('*.json')}
    commands = [[sys.executable, str(TASK / 'execution/verify_historical.py'), name] for name in CHECKS]
    commands += [[sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_current.py')],
                 [sys.executable, str(REPO / 'agent/tasks/V-03/execution/validate_current.py')]]
    checks = []
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        (TASK / f'evidence/check-{index + 1}.txt').write_text(output, encoding='utf-8')
        print(output, end='')
        checks.append({'command': command, 'exit_code': result.returncode})
    after = {p.name: sha256(p) for p in SOURCE.glob('*.json')}
    unchanged = before == after
    checks.append({'command': 'accepted source JSON unchanged byte for byte', 'exit_code': 0 if unchanged else 1})
    (TASK / 'evidence/verification.json').write_text(json.dumps({
        'task_id': 'V-04', 'checks': checks,
        'scope': 'signed preview media, decoded pixels and current handoff; not Unity or participant validation'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(c['exit_code'] != 0 for c in checks))


if __name__ == '__main__':
    sys.exit(main())
