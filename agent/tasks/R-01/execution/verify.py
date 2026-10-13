"""Run scoped R-01 checks and retain their actual results."""
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator

from validate_candidate import FIXTURES, ROOT as DESIGN, SCHEMA, load_json

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]


def main():
    (TASK / 'evidence').mkdir(exist_ok=True)
    checks = []
    commands = [
        [sys.executable, str(TASK / 'execution/validate_candidate.py')],
        [sys.executable, '-m', 'pytest', '-q', str(TASK / 'execution/test_candidate.py')],
    ]
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        (TASK / f'evidence/check-{index + 1}.txt').write_text(output, encoding='utf-8')
        checks.append({'command': command, 'exit_code': result.returncode})
        print(output, end='')
    schema = Draft202012Validator(load_json(SCHEMA))
    fixtures = {}
    for path in sorted(FIXTURES.glob('*.json')):
        if path.name == 'comprehension-truth-minimal.json':
            continue
        fixtures[path.name] = [list(e.path) for e in schema.iter_errors(load_json(path))]
    authority = load_json(DESIGN / '00_总控/protocol_authority_v1.2.json')
    assert authority['primary']['report_even_if_functional_guard_fails'] is True
    assert authority['conditions']['native_is_not_hidden'] is True
    assert authority['manipulation_check']['role'] == 'manipulation_only'
    checks.append({'command': 'current v1.2 primary/manipulation/native interpretation', 'exit_code': 0})
    report = {'task_id': 'R-01', 'checks': checks, 'schema_error_paths': fixtures,
              'scope': 'candidate configuration and current usage, not Unity or human evidence'}
    (TASK / 'evidence/verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(any(c['exit_code'] != 0 for c in checks))


if __name__ == '__main__':
    sys.exit(main())
