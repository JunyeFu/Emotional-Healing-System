"""Rebuild P-02 evidence in the fixed task directory, retaining signed originals."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from generate_golden_archive import MODULE_ROOT

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/P-02'
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

    run('storage-consumers', ['-m', 'pytest', '-q', MODULE_ROOT / 'tests/session_store',
                            MODULE_ROOT / 'tests/session_core', MODULE_ROOT / 'tests/randomization',
                            MODULE_ROOT / '05-通信协议/tests', MODULE_ROOT / '07-数据治理/tests'])
    run('golden-archive', [TASK / 'execution/generate_golden_archive.py'])
    run('synthetic-stress', [TASK / 'execution/generate_stress_report.py'])
    old = MODULE_ROOT / 'srp_session_store/fixtures/golden/session-archive-v1/evidence.json'
    original = json.loads(old.read_text(encoding='utf-8'))
    actual = json.loads((OUT / 'session-archive-v1/evidence.json').read_text(encoding='utf-8'))
    assert actual == original
    assert actual['replay_valid'] and actual['operation_count'] == 46
    stress = json.loads((OUT / 'synthetic_stress_report.json').read_text(encoding='utf-8'))
    assert stress['duration_seconds'] == 800
    assert stress['plux_sample_count'] == 320000 and stress['polar_sample_count'] == 104000
    assert stress['l1_frame_count'] == 16000 and stress['archive_l0_count'] == 1600
    assert stress['archive_l1_count'] == 16001
    assert stress['integrity_valid'] and stress['memory_stable']
    target = OUT / 'archive-comparison.json'
    comparison = {'equal_to_historical_evidence': True, 'operation_count': 46,
                  'replay_valid': actual['replay_valid'], 'replay_hash': actual['replay_hash'],
                  'final_state_hash': actual['final_state_hash'], 'file_count': len(actual['files']),
                  'scope': 'Synthetic core archive; no restricted originals or live devices.'}
    target.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    checks.append({'command': 'archive-comparison', 'exit_code': 0, 'result': comparison,
                   'source': target.relative_to(ROOT).as_posix()})
    report = {'task_id': 'P-02', 'review_date': '2026-09-28',
              'scope': 'Storage regression, deterministic replay and 800-second synthetic load.',
              'checks': checks}
    (TASK / 'evidence/verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS P-02 storage, replay and synthetic stress')


if __name__ == '__main__':
    main()
