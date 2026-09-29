"""Verify current facts without authorizing a candidate build or publication."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
UNITY = ROOT / 'agent/modules/04-Unity视觉/SRP-Weather-Visual'
G02 = ROOT / 'agent/modules/07-数据治理'


def main():
    checks = []

    def run(label, arguments, allowed=(0,)):
        command = [sys.executable, *map(str, arguments)]
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'},
                                capture_output=True, text=True, encoding='utf-8')
        (TASK / 'evidence' / f'{label}.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        check = {'command': command, 'exit_code': result.returncode, 'log': f'evidence/{label}.txt'}
        if result.returncode == 2:
            check['disposition'] = 'Expected failure-closed asset gate; release remains blocked.'
        checks.append(check)
        print(result.stdout + result.stderr, end='')
        if result.returncode not in allowed:
            raise RuntimeError(f'{label} failed')

    run('check-1', ['-m', 'pytest', '-q', TASK / 'execution/test_delivery_handoff.py',
                    G02 / 'tests/test_assets.py', G02 / 'tests/test_unity_gate.py'])
    run('team-tools', [PLAN / '99_验证与清单/validate_team_tool_baseline.py'])
    run('asset-gate', [G02 / 'g02.py', 'scan-assets', '--repo-root', ROOT, '--unity-root', UNITY,
                      '--ledger', UNITY / 'Governance/asset_license_ledger.json',
                      '--baseline', UNITY / 'Governance/asset_inventory.json',
                      '--output', TASK / 'evidence/asset-scan.json'], (0, 2))
    asset = json.loads((TASK / 'evidence/asset-scan.json').read_text(encoding='utf-8'))
    report = {'task_id': 'Z-01', 'checks': checks,
              'scope': 'current authority, actual asset gate and existing evidence; not clean checkout product rebuild',
              'release_allowed': asset['release_allowed'], 'asset_blockers': len(asset['blockers']),
              'clean_checkout_rebuild': 'NOT_RUN', 'three_artifact_match': 'NOT_VERIFIED',
              'unity_td_runtime': 'NOT_RUN', 'live_e2e': 'NOT_RUN',
              'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_RUN'}
    (TASK / 'evidence/verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
