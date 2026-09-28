"""Run G-02 checks without replacing historically signed evidence."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
MODULE = ROOT / '02-技术研发/07-数据治理'
UNITY = ROOT / '02-技术研发/04-Unity视觉/SRP-Weather-Visual'
TASK = ROOT / 'agent/tasks/G-02'
OUT = TASK / 'evidence/runtime'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def run(label, arguments, allowed=(0,)):
        command = [sys.executable, *map(str, arguments)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        log = OUT / f'{label}.log'
        log.write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode not in allowed:
            raise RuntimeError(f'{label} failed; see {log.relative_to(ROOT)}')
        checks.append({'command': label, 'exit_code': result.returncode,
                       'result': result.stdout.strip(), 'source': log.relative_to(ROOT).as_posix()})
        if result.returncode == 2:
            checks[-1]['disposition'] = 'Expected failure-closed gate; real readiness remains blocked.'

    run('governance-tests', ['-m', 'pytest', '-q', MODULE / 'tests'])
    run('synthetic-rehearsal', [MODULE / 'g02.py', 'synthetic-rehearsal', '--output', OUT / 'synthetic_rehearsal_report.json'])
    run('repository-privacy', [TASK / 'execution/verify_repository_privacy.py', '--repo-root', ROOT,
                             '--output', OUT / 'repository_privacy_report.json'])
    run('formal-environment', [MODULE / 'g02.py', 'check-environment', '--repo-root', ROOT,
                             '--output', OUT / 'formal_environment_report.json'], (0, 2))
    run('asset-scan', [MODULE / 'g02.py', 'scan-assets', '--repo-root', ROOT, '--unity-root', UNITY,
                      '--ledger', UNITY / 'Governance/asset_license_ledger.json',
                      '--baseline', UNITY / 'Governance/asset_inventory.json',
                      '--output', OUT / 'asset_scan_report.json'], (0, 2))
    report = {'task_id': 'G-02', 'review_date': '2026-09-28',
              'scope': 'Governance regression and read-only gates; synthetic inputs, not real participant evidence.',
              'checks': checks}
    (TASK / 'evidence/verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS G-02 checks; inspect actual environment and asset gate decisions')


if __name__ == '__main__':
    main()
