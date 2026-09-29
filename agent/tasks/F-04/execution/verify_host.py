"""Verify current host code and preserved signed artifacts without opening TD."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
MODULE = ROOT / 'agent/modules/03-TouchDesigner/f04_readonly_console'
sys.path.insert(0, str(MODULE))
from f04_node_plan import write_host_artifacts


def main():
    evidence = TASK / 'evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    tests = [
        'agent/modules/03-TouchDesigner/f04_readonly_console/tests/test_f04_console.py',
        'agent/modules/03-TouchDesigner/t01_telemetry_panel/tests/test_t01_telemetry.py',
    ]
    result = subprocess.run([sys.executable, '-m', 'pytest', *tests, '-q'],
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    (evidence / 'pytest.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    host = write_host_artifacts(evidence / 'host', MODULE / 'fixtures/f04-static-display-fixture-v1.json')
    expected = {
        'F04_ReadonlyConsole.toe': 'CBC982BE379C2A1D9A0BE7FC26508B1467A8CFCD920E51FBE4193E18AE74B9EA',
        'F04_ReadonlyConsole.tox': '1DEC705338AF14F623177BE60975B860FA3D86851D5EF7A7C6DF95BC04DE7F76',
    }
    actual = {name: sha256((MODULE / name).read_bytes()).hexdigest().upper() for name in expected}
    if actual != expected:
        raise ValueError('SIGNED_BINARY_MISMATCH')
    historical = json.loads((MODULE / 'evidence/touchdesigner/reopen_report.json').read_text(encoding='utf-8'))
    if not all(historical['checks'].values()) or historical['toe_sha256'] != actual['F04_ReadonlyConsole.toe']:
        raise ValueError('HISTORICAL_REOPEN_EVIDENCE_MISMATCH')
    checks = [
        {'command': 'py -3.14 -m pytest ' + ' '.join(tests) + ' -q', 'exit_code': 0,
         'result': result.stdout.strip(), 'source': 'agent/tasks/F-04/evidence/pytest.txt'},
        {'command': 'write_host_artifacts', 'exit_code': 0,
         'result': f"{host['page_count']} pages; {host['page_scenario_combinations']} combinations; raw_bytes fixture hash",
         'source': 'agent/tasks/F-04/evidence/host/host_build_manifest.json'},
        {'command': 'signed TOE/TOX byte comparison and historical reopen identity', 'exit_code': 0,
         'result': 'Both signed binaries unchanged; 13 historical reopen checks true. No current TD execution.',
         'sha256': actual},
    ]
    report = {'task_id': 'F-04', 'review_date': '2026-09-28', 'workspace': str(ROOT),
              'scope': 'Current host tests and signed artifact identity; historical runtime evidence is not a new TD run.',
              'checks': checks}
    (evidence / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(result.stdout.strip())
    print('F04_HOST_AND_PRESERVED_ARTIFACTS_PASS')


if __name__ == '__main__':
    main()
