"""Verify current P-01 outputs without replacing signed golden evidence."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from generate_golden_trace import build_trace

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/P-01'
OUT = TASK / 'evidence/runtime'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def run(label, arguments):
        result = subprocess.run([sys.executable, *map(str, arguments)], cwd=ROOT,
                                capture_output=True, text=True, encoding='utf-8')
        log = OUT / f'{label}.log'
        log.write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(f'{label} failed; see {log.relative_to(ROOT)}')
        checks.append({'command': label, 'exit_code': 0, 'result': result.stdout.strip(),
                       'source': log.relative_to(ROOT).as_posix()})

    run('session-consumers', ['-m', 'pytest', '-q',
                            ROOT / '02-技术研发/tests/session_core',
                            ROOT / '02-技术研发/tests/session_store',
                            ROOT / '02-技术研发/05-通信协议/tests',
                            ROOT / '02-技术研发/07-数据治理/tests'])
    run('golden-generator', [TASK / 'execution/generate_golden_trace.py'])
    original = ROOT / '02-技术研发/srp_session_core/fixtures/golden/four-module-trace-v1.json'
    trace = json.loads((OUT / 'four-module-trace-v1.json').read_text(encoding='utf-8'))
    assert trace == json.loads(original.read_text(encoding='utf-8')) == build_trace()
    assert trace['summary']['status'] == 'COMPLETED'
    assert trace['summary']['session_elapsed_ns'] == 800_000_000_000
    counts = {name: len(trace[name]) for name in
              ('control_events', 'acks', 'render_receipts', 'session_events', 'policy_decisions')}
    assert counts == dict(control_events=19, acks=19, render_receipts=12,
                          session_events=54, policy_decisions=4)
    comparison = {'equal_to_historical_fixture': True, 'counts': counts,
                  'status': trace['summary']['status'], 'trace_hash': trace['trace_hash'],
                  'session_elapsed_ns': trace['summary']['session_elapsed_ns'],
                  'scope': 'Synthetic v2.1 core trace; no teaching, devices or live rendering.'}
    target = OUT / 'golden-comparison.json'
    target.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    checks.append({'command': 'golden-comparison', 'exit_code': 0,
                   'result': comparison, 'source': target.relative_to(ROOT).as_posix()})
    report = {'task_id': 'P-01', 'review_date': '2026-09-28',
              'scope': 'Core and consumers regression; not real training or formal eligibility.',
              'checks': checks}
    (TASK / 'evidence/verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS P-01 regression and deterministic golden comparison')


if __name__ == '__main__':
    main()
